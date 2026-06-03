"""State definitions for the LangGraph multi-agent workflow."""

from typing import TypedDict, Annotated, Optional, Dict, Any, List
from operator import add


def pick_last_agent(left: Optional[str], right: Optional[str]) -> str:
    """Reducer to select the latest agent name in parallel execution steps."""
    return right if right is not None else (left or "")


def pick_max_progress(left: Optional[int], right: Optional[int]) -> int:
    """Reducer to select the highest progress percentage in parallel steps."""
    return max(left or 0, right or 0)


class AgentState(TypedDict):
    """The central state schema for the LangGraph resume tailoring workflow."""

    # ─── Inputs ──────────────────────────────────────────────────────────
    session_id: str
    user_id: str
    resume_id: str
    raw_resume_text: str
    parsed_resume: Dict[str, Any]      # Extracted resume data
    job_description: str
    target_company: Optional[str]
    target_role: Optional[str]

    # ─── Agent Outputs ───────────────────────────────────────────────────
    job_analysis: Optional[Dict[str, Any]]
    ats_score_before: Optional[Dict[str, Any]]
    ats_score_after: Optional[Dict[str, Any]]
    
    # AI recommendations (awaiting review or accepted)
    suggested_rewrites: Optional[List[Dict[str, Any]]]    # Experiential bullet point enhancements
    suggested_projects: Optional[List[Dict[str, Any]]]    # Project impact optimizations
    recruiter_messages: Optional[Dict[str, Any]]          # LinkedIn message, Cold Email, Referral Msg
    interview_prep: Optional[Dict[str, Any]]              # DSA, HR, System design Q&As
    validation_status: Optional[Dict[str, Any]]           # Validation agent output

    # ─── Workflow Control ────────────────────────────────────────────────
    current_agent: Annotated[str, pick_last_agent]
    progress: Annotated[int, pick_max_progress]                                          # 0 to 100 percentage
    logs: Annotated[List[str], add]                       # Append-only logs
    errors: Annotated[List[str], add]                     # Append-only errors
    requires_human_review: bool
    human_decisions: Dict[str, Any]                        # Accepted/rejected review decisions

    # ─── Outputs ─────────────────────────────────────────────────────────
    final_tailored_resume: Optional[Dict[str, Any]]
    final_score: Optional[float]
