"""ATS Matching and Scoring Agent."""

import json
from typing import Dict, Any

from agents.base import BaseAgent
from models.session import AgentType
from services.llm_service import llm_service
from schemas.session import ATSAnalysis
from utils.logger import get_logger

logger = get_logger(__name__)

ATS_MATCHER_SYSTEM_PROMPT = """You are an Applicant Tracking System (ATS) Simulation and Optimization Agent.
Your objective is to compare a parsed resume against a job description analysis and return a comprehensive compatibility report.

You must calculate:
1. overall_score: A weighted fit score between 0 and 100 representing how well the candidate fits the role.
2. keyword_match_rate: Percentage of target keywords present in the resume.
3. missing_keywords: All technical skills (from skills_required, skills_preferred, tools_and_technologies) and keywords mentioned in the job description analysis that are NOT present in the candidate's resume (e.g., if Angular, Vue.js, or CI/CD are in the job description but not in the resume, you MUST list them here).
4. matched_keywords: All technical skills (from skills_required, skills_preferred, tools_and_technologies) and keywords from the job description analysis that are successfully found in the candidate's resume (e.g., if React, Node.js, JavaScript, HTML, CSS, or Git are in both the resume and the job description, you MUST explicitly list them here).
5. section_scores: A list of breakdown scores for each key resume section (contact, skills, experience, education, projects) with specific actionable feedback.
6. suggestions: General actionable advice to raise the compatibility score.

Rules:
- Be realistic and rigorous. Do not give a high score (e.g. above 80) unless the candidate has a strong match in core requirements.
- Ensure that ALL matched skills (including React, Node.js, JavaScript, HTML, CSS, Git, etc. if present in the resume) are explicitly listed in matched_keywords. Do not omit them.
- Return ONLY valid JSON matching the schema. No code block formatting.
"""

ATS_MATCHER_USER_TEMPLATE = """Evaluate the compatibility between this resume and the job description analysis.

--- STRUCTURED RESUME ---
{parsed_resume}
--- END STRUCTURED RESUME ---

--- JOB DESCRIPTION ANALYSIS ---
{job_analysis}
--- END JOB DESCRIPTION ANALYSIS ---
"""


class ATSMatcherAgent(BaseAgent):
    """Agent responsible for auditing the resume against job demands and producing an ATS compatibility score."""

    def __init__(self):
        super().__init__(AgentType.ATS_MATCHER)

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        parsed_resume = state.get("parsed_resume", {})
        job_analysis = state.get("job_analysis", {})

        user_prompt = ATS_MATCHER_USER_TEMPLATE.format(
            parsed_resume=json.dumps(parsed_resume),
            job_analysis=json.dumps(job_analysis)
        )

        response_text = await llm_service.invoke_with_fallback(
            system_prompt=ATS_MATCHER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,  # Low temperature for analytical objectivity
            task_type="ats_matching",
        )

        from agents.base import extract_json_block
        clean_text = extract_json_block(response_text)

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"ATS matcher JSON parsing failed: {e}. Raw response: {response_text}")
            parsed_json = {
                "overall_score": 50.0,
                "keyword_match_rate": 0.0,
                "missing_keywords": [],
                "matched_keywords": [],
                "suggestions": ["Failed to parse ATS scoring suggestions. Please retry."]
            }

        # Resilient validation: if strict Pydantic fails, extract core fields manually
        try:
            validated_analysis = ATSAnalysis(**parsed_json)
        except Exception as validation_err:
            logger.warning(f"ATS schema validation failed, using lenient fallback: {validation_err}")
            # Extract what we can from the raw JSON
            validated_analysis = ATSAnalysis(
                overall_score=float(parsed_json.get("overall_score", 50.0)),
                keyword_match_rate=float(parsed_json.get("keyword_match_rate", 0.0)),
                missing_keywords=parsed_json.get("missing_keywords", []),
                matched_keywords=parsed_json.get("matched_keywords", []),
                section_scores=[],  # Skip section scores if they caused the error
                suggestions=parsed_json.get("suggestions", []),
            )

        return {
            "output": validated_analysis.model_dump(),
            "reasoning": f"Simulated ATS match scoring. Overall score calculated: {validated_analysis.overall_score}%."
        }

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.strftime('%H:%M:%S')
        output_data = agent_output.get("output", {})
        score = output_data.get("overall_score", 0.0)
        
        # Decide if this is the initial ATS evaluation or the post-tailoring evaluation
        if state.get("ats_score_before") is None:
            return {
                "ats_score_before": output_data,
                "final_score": score,
                "logs": [f"[ATS_Matcher] Initial compatibility check complete. Score: {score}% at {timestamp}"],
                "current_agent": self.agent_type.value,
                "progress": 40
            }
        else:
            return {
                "ats_score_after": output_data,
                "final_score": score,
                "logs": [f"[ATS_Matcher] Final tailored compatibility check complete. Score: {score}% at {timestamp}"],
                "current_agent": self.agent_type.value,
                "progress": 95
            }


import time
