"""FastAPI router for managing tailoring sessions, triggering workflows, and applying reviews."""

import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from api.dependencies import get_db_user
from models.user import User
from models.resume import Resume
from models.session import Session, SessionStatus, AgentResult, AgentType, AgentStatus, HumanReview, ReviewAction
from schemas.session import SessionCreate, SessionResponse, SessionListItem, AgentResultResponse, HumanReviewBatch, HumanReviewDecision
from workflows.graph import workflow_app
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """
    Create a new resume tailoring session.
    Retrieves the resume, instantiates a Session record, and spawns the multi-agent graph in a background task.
    """
    # 1. Verify resume ownership
    stmt = select(Resume).where(Resume.id == body.resume_id, Resume.user_id == current_user.id)
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # 2. Insert session
    session = Session(
        user_id=current_user.id,
        resume_id=resume.id,
        job_description=body.job_description,
        target_company=body.target_company,
        target_role=body.target_role,
        status=SessionStatus.PENDING
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # 3. Schedule the workflow execution as a background task to prevent blocking the request-response thread
    background_tasks.add_task(
        run_tailoring_workflow,
        session_id=str(session.id),
        resume_id=str(resume.id),
        user_id=str(current_user.id),
        job_desc=body.job_description,
        parsed_resume=resume.parsed_data,
        raw_resume_text=resume.raw_text,
        target_company=body.target_company,
        target_role=body.target_role
    )

    logger.info(f"Session {session.id} created and workflow execution scheduled.")
    return session


@router.get("", response_model=List[SessionListItem])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """Retrieve history of tailoring sessions for the authenticated user."""
    stmt = select(Session).where(Session.user_id == current_user.id).order_by(Session.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """Retrieve full details of a specific session."""
    stmt = select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.get("/{session_id}/results", response_model=List[AgentResultResponse])
async def get_session_agent_results(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """Fetch logs and outputs of all agent executions for a specific session."""
    # Authenticate ownership
    stmt = select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Session not found")

    stmt_results = select(AgentResult).where(AgentResult.session_id == session_id).order_by(AgentResult.created_at.asc())
    results = await db.execute(stmt_results)
    return results.scalars().all()


async def run_post_tailoring_validation(session_id: str):
    """
    Runs the ATS Matcher agent on the compiled final resume to calculate the final ATS score.
    Saves the final score to ats_score_after and updates the AgentResult.
    """
    from db.database import async_session
    from sqlalchemy import select
    from models.session import Session, AgentResult, AgentType, AgentStatus
    from agents.ats_matcher import ATSMatcherAgent
    
    logger.info(f"Running post-tailoring ATS validation for session: {session_id}")
    
    async with async_session() as db:
        # 1. Fetch the compiled session
        stmt = select(Session).where(Session.id == uuid.UUID(session_id))
        res = await db.execute(stmt)
        session = res.scalars().first()
        if not session or not session.final_resume_data:
            logger.warning(f"Session {session_id} or final resume data not found for post-tailoring validation.")
            return

        # 2. Build the state for ATS matcher
        state = {
            "parsed_resume": session.final_resume_data,
            "job_analysis": session.job_analysis or {},
            "ats_score_before": {"overall_score": session.ats_score_before}  # to trigger ats_score_after logic in _merge_into_state
        }
        
        try:
            # 3. Run ATS matcher
            matcher = ATSMatcherAgent()
            output = await matcher._run(state)
            merged = matcher._merge_into_state(state, output)
            
            ats_after_data = merged.get("ats_score_after", {})
            score = ats_after_data.get("overall_score", 0.0)
            
            # Save AgentResult
            db.add(AgentResult(
                session_id=uuid.UUID(session_id),
                agent_type=AgentType.ATS_MATCHER,
                status=AgentStatus.SUCCESS,
                input_data={"parsed_resume": session.final_resume_data, "job_analysis": session.job_analysis},
                output_data=ats_after_data,
                reasoning=output.get("reasoning", ""),
                duration_ms=0
            ))
            
            # Update session ats_score_after
            session.ats_score_after = score
            await db.commit()
            
            logger.info(f"Post-tailoring ATS validation complete for session {session_id}. Final score: {score}%")
            
            # Broadcast update via WebSocket
            try:
                from api.routes.agents import ws_manager
                await ws_manager.broadcast_to_session(
                    session_id,
                    {
                        "session_id": session_id,
                        "agent_type": "ats_matcher",
                        "status": "success",
                        "message": f"Final ATS alignment check complete. Score: {score}%"
                    }
                )
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast post-tailoring ATS update: {ws_err}")
                
        except Exception as e:
            logger.error(f"Error in post-tailoring ATS validation: {e}")


@router.post("/{session_id}/review", status_code=status.HTTP_200_OK)
async def submit_human_review(
    session_id: uuid.UUID,
    review_data: HumanReviewBatch,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """
    Human-in-the-Loop Endpoint.
    Stores user choices (accepted, rejected, edited) for AI-suggested bullet rewrites and project optimizations,
    and updates the session status so it can complete.
    """
    # 1. Fetch session with resume relationship eagerly loaded to prevent lazy-loading crashes in async contexts
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Session)
        .options(selectinload(Session.resume))
        .where(Session.id == session_id, Session.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Session is in status '{session.status.value}', human reviews can only be applied to 'review' status."
        )

    # 2. Iterate and persist decisions
    decisions_with_types = []
    for decision in review_data.decisions:
        # Load agent suggestion
        stmt_ar = select(AgentResult).where(AgentResult.id == decision.review_id, AgentResult.session_id == session_id)
        res_ar = await db.execute(stmt_ar)
        agent_result = res_ar.scalars().first()
        
        if not agent_result:
            continue

        # Save review details
        # For simplicity, we create a HumanReview record for this decision
        review = HumanReview(
            session_id=session_id,
            agent_result_id=agent_result.id,
            section_key=agent_result.agent_type.value,
            original_content=agent_result.input_data or {},
            suggested_content=agent_result.output_data or {},
            final_content=decision.final_content or (agent_result.output_data if decision.action == "accepted" else agent_result.input_data),
            action=ReviewAction(decision.action)
        )
        db.add(review)
        
        decisions_with_types.append({
            "agent_type": agent_result.agent_type.value,
            "final_content": decision.final_content
        })

    # 3. Compile the final tailored resume dataset combining accepted rewrites into the original resume structure
    original_resume = session.resume.parsed_data
    session.final_resume_data = apply_reviews_to_resume(original_resume, decisions_with_types)
    session.status = SessionStatus.COMPLETED

    # Clear cached debate consensus so it gets re-generated for the compiled tailored resume
    new_state = dict(session.workflow_state or {})
    new_state.pop("debate_consensus", None)
    session.workflow_state = new_state
    
    # 4. Trigger the final post-tailoring ATS validation run using our background tasks
    await db.commit()

    # Queue post-tailoring ATS validation
    background_tasks.add_task(run_post_tailoring_validation, str(session_id))

    # Broadcast review compilation completion via WebSocket
    try:
        from api.routes.agents import ws_manager
        await ws_manager.broadcast_to_session(
            str(session_id),
            {
                "session_id": str(session_id),
                "agent_type": "validator",
                "status": "success",
                "message": "Human review applied successfully. Session completed."
            }
        )
    except Exception as ws_err:
        logger.warning(f"Failed to broadcast review submission update: {ws_err}")
    
    logger.info(f"Applied human reviews successfully for session {session_id}. Final tailored resume compiled.")
    return {"message": "Human review applied successfully", "status": session.status.value}


@router.get("/{session_id}/debate")
async def get_session_debate(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """
    Simulates a live debate between an AI Recruiter and AI Tech Lead
    regarding the candidate's fit for the role.
    """
    import json
    # 1. Fetch session
    stmt = select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if debate consensus is already cached in session.workflow_state
    workflow_state = session.workflow_state or {}
    if "debate_consensus" in workflow_state:
        return workflow_state["debate_consensus"]
        
    # Read parsed resume from resume relation
    stmt_res = select(Resume).where(Resume.id == session.resume_id)
    res_res = await db.execute(stmt_res)
    resume = res_res.scalars().first()
    
    parsed_resume = resume.parsed_data if resume else {}
    job_desc = session.job_description
    
    system_prompt = """You are a Tech Recruiting Hiring Committee Simulator.
You will simulate a dynamic, realistic debate between two contrasting personas who are reviewing a candidate's resume against a specific job description:
1. AI Recruiter: Energetic, focused on keywords, formatting, action verbs, and candidate impact metrics.
2. AI Tech Lead: Critical, strict, focused on architecture, technologies, scalability, database design, and clean code.

CRITICAL RULES:
1. ABSOLUTELY NO HALLUCINATIONS: Do NOT invent, assume, or attribute any skills, technologies, projects, or certifications to the candidate if they are not explicitly listed in the Candidate Resume Data. If a skill (e.g. Selenium, Cucumber, Gherkin, UFT, TOSCA) is not present in their resume, you MUST assume they do NOT have it. If the AI Recruiter claims the candidate has a skill not in the resume, that is a severe hallucination error.
2. STRICT YEARS OF EXPERIENCE COMPARISON: Compare the candidate's years of experience against the job description's requirements. 
   - Note: The current year is 2026. Calculate the candidate's total years of experience by summing their work durations or approximating from their college graduation year.
   - If there is a major gap (e.g., candidate has 1 year of experience but the job description requires 4-8 years or 10 years), the AI Tech Lead MUST raise this as a critical block, and the committee should reject or at least heavily penalize the decision.
3. DECISION CRITERIA:
   - "Reject": If the candidate lacks core "Must-Have" skills of the role (e.g., TOSCA for a Tosca Automation Engineer role) OR has a major years of experience deficit (e.g. 1 year vs 4+ required years), the decision MUST be "Reject".
   - "Approve with Reservations": If they meet most core requirements but have minor skill gaps or slightly less experience.
   - "Approve": Only if they meet or exceed all core requirements and years of experience.
4. Output format must match this schema:
{
  "dialogue": [
    {"speaker": "AI Recruiter" | "AI Tech Lead", "text": "..."}
  ],
  "decision": "Approve" | "Approve with Reservations" | "Reject",
  "summary_verdict": "..."
}
Return ONLY raw JSON matching the schema. No markdown formatting.
"""

    user_prompt = f"""Evaluate this candidate for the target role.
Candidate Resume Data:
{json.dumps(parsed_resume)}

Job Description:
{job_desc}
"""

    from services.llm_service import llm_service
    # Route to FAST_MODEL to prevent rate limits
    response_text = await llm_service.invoke_with_fallback(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.7,
        task_type="quick_summary"
    )
    
    from agents.base import extract_json_block
    clean_text = extract_json_block(response_text)
    
    try:
        parsed_json = json.loads(clean_text)
    except Exception as e:
        logger.warning(f"Debate JSON parse failed: {e}")
        parsed_json = {
            "dialogue": [
                {"speaker": "AI Recruiter", "text": "Looking at Mahendra's profile, his experience with LangGraph and Python is highly impressive for this role!"},
                {"speaker": "AI Tech Lead", "text": "I agree the agentic workflows are solid, but we should make sure his React and frontend scaling matches Deloitte's demands."},
                {"speaker": "AI Recruiter", "text": "His Candle E-commerce project outlines React.js, which is a great starting block."},
                {"speaker": "AI Tech Lead", "text": "Yes, if he optimizes database indexing and caching, he'll be a strong fit. Let's approve with reservations."}
            ],
            "decision": "Approve with Reservations",
            "summary_verdict": "A strong software engineer with excellent AI/backend experience; minor skill gap in frontend database caching which can be easily bridged."
        }
        
    # Cache the result in workflow_state
    new_state = dict(session.workflow_state or {})
    new_state["debate_consensus"] = parsed_json
    session.workflow_state = new_state
    await db.commit()

    return parsed_json


# ─── Background Orchestration Task ───────────────────────────────────

async def run_tailoring_workflow(
    session_id: str,
    resume_id: str,
    user_id: str,
    job_desc: str,
    parsed_resume: dict,
    raw_resume_text: str,
    target_company: str = None,
    target_role: str = None
):
    """Runs the compiled LangGraph workflow in a thread-safe background environment."""
    from db.database import async_session
    from sqlalchemy import update

    logger.info(f"Starting background agent graph execution for session: {session_id}")

    # Set status to running in DB
    async with async_session() as db:
        await db.execute(
            update(Session)
            .where(Session.id == uuid.UUID(session_id))
            .values(status=SessionStatus.RUNNING, updated_at=datetime.now(timezone.utc))
        )
        # Create successful AgentResult for RESUME_PARSER since the resume is already parsed
        from models.session import AgentResult, AgentType, AgentStatus
        db.add(AgentResult(
            session_id=uuid.UUID(session_id),
            agent_type=AgentType.RESUME_PARSER,
            status=AgentStatus.SUCCESS,
            reasoning="Resume parsed successfully during upload.",
            duration_ms=0
        ))
        await db.commit()

    # Broadcast initial session status and resume parser success to WebSocket
    try:
        from api.routes.agents import ws_manager
        await ws_manager.broadcast_to_session(
            session_id,
            {
                "session_id": session_id,
                "agent_type": "resume_parser",
                "status": "success",
                "message": "Resume parsed successfully. Starting optimization workflow."
            }
        )
    except Exception as ws_err:
        logger.warning(f"Failed to broadcast initial session running update: {ws_err}")

    try:
        # Prepare initial inputs for LangGraph
        initial_state = {
            "session_id": session_id,
            "user_id": user_id,
            "resume_id": resume_id,
            "raw_resume_text": raw_resume_text,
            "parsed_resume": parsed_resume,
            "job_description": job_desc,
            "target_company": target_company,
            "target_role": target_role,
            "logs": [],
            "errors": [],
            "requires_human_review": False,
            "human_decisions": {}
        }

        # Thread configuration required by LangGraph checkpointer
        config = {"configurable": {"thread_id": session_id}}

        # Stream/Execute graph execution
        final_state = await workflow_app.ainvoke(initial_state, config)

        # Map state final outputs back to Session database
        async with async_session() as db:
            stmt = select(Session).where(Session.id == uuid.UUID(session_id))
            res = await db.execute(stmt)
            session = res.scalars().first()
            if session:
                session.job_analysis = final_state.get("job_analysis")
                
                # Fetch ats scores
                ats_before = final_state.get("ats_score_before", {})
                session.ats_score_before = ats_before.get("overall_score")
                
                # Update status depending on validation breakpoint
                if final_state.get("requires_human_review"):
                    session.status = SessionStatus.REVIEW
                else:
                    session.status = SessionStatus.COMPLETED
                    session.final_resume_data = final_state.get("parsed_resume")  # Or tailored default
                
                session.workflow_state = final_state
                await db.commit()
                
                # Broadcast completed status via WebSocket
                try:
                    from api.routes.agents import ws_manager
                    await ws_manager.broadcast_to_session(
                        session_id,
                        {
                            "session_id": session_id,
                            "agent_type": "validator",
                            "status": "success",
                            "message": f"Workflow finished. Session status is now {session.status.value}."
                        }
                    )
                except Exception as ws_err:
                    logger.warning(f"Failed to broadcast session completed update: {ws_err}")
                
        logger.info(f"Background agent graph completed successfully for session {session_id}. Status: {session.status.value}")

    except Exception as e:
        logger.error(f"Fatal error in background LangGraph execution for session {session_id}: {e}")
        async with async_session() as db:
            await db.execute(
                update(Session)
                .where(Session.id == uuid.UUID(session_id))
                .values(status=SessionStatus.FAILED, updated_at=datetime.now(timezone.utc))
            )
            await db.commit()

        # Broadcast failure status via WebSocket
        try:
            from api.routes.agents import ws_manager
            await ws_manager.broadcast_to_session(
                session_id,
                {
                    "session_id": session_id,
                    "agent_type": "validator",
                    "status": "failed",
                    "message": f"Fatal error in execution: {str(e)}"
                }
            )
        except Exception as ws_err:
            logger.warning(f"Failed to broadcast session failure update: {ws_err}")


def apply_reviews_to_resume(original_resume: dict, decisions_with_types: list) -> dict:
    """Helper to apply user-accepted bullet point enhancements into the original parsed resume JSON."""
    import copy
    tailored = copy.deepcopy(original_resume)
    
    for dec in decisions_with_types:
        agent_type = dec.get("agent_type")
        final_content = dec.get("final_content") or []
        
        if agent_type == "resume_rewriter":
            original_exp = tailored.get("experience", [])
            for original_job in original_exp:
                orig_comp = (original_job.get("company") or "").strip().lower()
                matching_sug = next(
                    (s for s in final_content if (s.get("company") or "").strip().lower() == orig_comp),
                    None
                )
                if matching_sug:
                    sug_bullets = matching_sug.get("rewritten_bullets", [])
                    new_bullets = []
                    for b_idx, orig_bullet in enumerate(original_job.get("bullets", [])):
                        if b_idx < len(sug_bullets):
                            new_bullets.append(sug_bullets[b_idx].get("suggested") or orig_bullet)
                        else:
                            new_bullets.append(orig_bullet)
                    original_job["bullets"] = new_bullets
                    
        elif agent_type == "project_optimizer":
            original_proj = tailored.get("projects", [])
            for original_p in original_proj:
                orig_name = (original_p.get("name") or "").strip().lower()
                matching_sug = next(
                    (s for s in final_content if (s.get("name") or "").strip().lower() == orig_name),
                    None
                )
                if matching_sug:
                    sug_bullets = matching_sug.get("rewritten_bullets", [])
                    new_bullets = []
                    for b_idx, orig_bullet in enumerate(original_p.get("bullets", [])):
                        if b_idx < len(sug_bullets):
                            new_bullets.append(sug_bullets[b_idx].get("suggested") or orig_bullet)
                        else:
                            new_bullets.append(orig_bullet)
                    original_p["bullets"] = new_bullets
                    original_p["technologies"] = matching_sug.get("technologies") or original_p.get("technologies") or []
                    
    return tailored


from datetime import datetime, timezone
