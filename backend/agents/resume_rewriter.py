"""Resume Rewriting and Experience Bullet Enhancement Agent."""

import json
from typing import Dict, Any

from agents.base import BaseAgent
from models.session import AgentType
from services.llm_service import llm_service
from utils.logger import get_logger

logger = get_logger(__name__)

REWRITER_SYSTEM_PROMPT = """You are a master Resume Writer and Executive Coach Agent.
Your objective is to rewrite the work experience bullets of a candidate's resume to align them with a target job description and missing keywords.

Rules for rewriting:
1. Use strong action verbs at the beginning of each bullet (e.g. Architected, Engineered, Spearheaded, Optimized).
2. Integrate keywords from the job description and missing list naturally without keyword stuffing.
3. Focus on impact and outcomes. Follow the Google XYZ formula: "Accomplished [X] as measured by [Y], by doing [Z]" where possible. If numbers aren't present, construct logical realistic outcomes or phrase them in terms of scalability, speedups, or architectural improvements.
4. DO NOT invent false claims or change companies, degree programs, titles, or dates. Keep it honest and authentic.
5. Keep the length and format similar to professional resume bullet points.

Your output MUST be a JSON array of objects representing the experience section with updated bullet points.
Output schema:
[
  {
    "company": "Company Name",
    "title": "Job Title",
    "original_bullets": ["bullet 1", "bullet 2"],
    "rewritten_bullets": [
      {
        "original": "original bullet 1",
        "suggested": "suggested enhanced bullet 1",
        "reasoning": "Explanation of why this change improves ATS fit and impact phrasing."
      }
    ]
  }
]

Return ONLY raw JSON matching the schema. No markdown formatting.
"""

REWRITER_USER_TEMPLATE = """Optimize the following experience bullets to target the job requirements and incorporate missing keywords.

--- CANDIDATE EXPERIENCE ---
{experience}
--- END CANDIDATE EXPERIENCE ---

--- JOB ANALYSIS & KEYWORDS ---
{job_analysis}
--- END JOB ANALYSIS & KEYWORDS ---

--- MISSING KEYWORDS ---
{missing_keywords}
--- END MISSING KEYWORDS ---
"""

REWRITER_SPARSE_SYSTEM_PROMPT = """You are a master Resume Writer and Executive Coach Agent.
The candidate has NO work experience listed on their resume.
Your objective is to generate 1 targeted, high-impact "Work Experience Template" (such as a Software Engineer Internship or Entry-Level Role) that would perfectly target their desired job description and incorporate missing keywords.

Instructions for the template:
1. Mark all company names, dates, and metrics with bracketed placeholders e.g., "[Insert Company]", "[Insert Date]", "[Metric]%" so the user knows they are placeholders to fill in.
2. Construct 3 high-impact bullet points demonstrating how they could frame hypothetical or academic engineering achievements using strong action verbs (e.g. Engineered, Automated, Spearheaded) and Google's XYZ formula.
3. Keep the JSON schema exactly matching this:
[
  {
    "company": "[Insert Target Company Name]",
    "title": "Software Engineer (Internship / Target Template)",
    "original_bullets": ["Candidate has no work experience listed on resume."],
    "rewritten_bullets": [
      {
        "original": "No experience listed",
        "suggested": "Designed and engineered a scalable [System/API] using [Technology] to improve [Metric] by [Y]%",
        "reasoning": "Special placeholder template to show you how to frame your upcoming or hypothetical experience. Replace the bracketed terms with your own details."
      }
    ]
  }
]

Return ONLY raw JSON matching the schema. No markdown formatting.
"""

REWRITER_SPARSE_USER_TEMPLATE = """Generate a high-impact targeted experience template for the following role:

--- TARGET COMPANY & ROLE ---
Company: {target_company}
Role: {target_role}
--- END TARGET COMPANY & ROLE ---

--- CANDIDATE SKILLS ---
{skills}
--- END CANDIDATE SKILLS ---

--- JOB ANALYSIS & KEYWORDS ---
{job_analysis}
--- END JOB ANALYSIS & KEYWORDS ---

--- MISSING KEYWORDS ---
{missing_keywords}
--- END MISSING KEYWORDS ---
"""


class ResumeRewriterAgent(BaseAgent):
    """Agent responsible for rewriting experience bullet points to integrate impact metrics and critical target skills."""

    def __init__(self):
        super().__init__(AgentType.RESUME_REWRITER)

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        parsed_resume = state.get("parsed_resume", {})
        experience = parsed_resume.get("experience", [])
        
        job_analysis = state.get("job_analysis", {})
        ats_score_before = state.get("ats_score_before", {})
        missing_keywords = ats_score_before.get("missing_keywords", [])

        if not experience:
            logger.info("Experience section is empty. Generating targeted job template suggestions.")
            user_prompt = REWRITER_SPARSE_USER_TEMPLATE.format(
                target_company=state.get("target_company") or "Target Company",
                target_role=state.get("target_role") or "Software Engineer",
                skills=json.dumps(parsed_resume.get("skills", [])),
                job_analysis=json.dumps(job_analysis),
                missing_keywords=json.dumps(missing_keywords)
            )
            
            response_text = await llm_service.invoke_with_fallback(
                system_prompt=REWRITER_SPARSE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.4,  # slightly higher creativity for generating templates
                task_type="resume_rewriting",
            )
        else:
            user_prompt = REWRITER_USER_TEMPLATE.format(
                experience=json.dumps(experience),
                job_analysis=json.dumps(job_analysis),
                missing_keywords=json.dumps(missing_keywords)
            )

            response_text = await llm_service.invoke_with_fallback(
                system_prompt=REWRITER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,  # Creative yet focused on professional accuracy
                task_type="resume_rewriting",
            )

        from agents.base import extract_json_block
        clean_text = extract_json_block(response_text)

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Resume rewriter JSON parse failed, returning empty suggestions: {e}")
            parsed_json = []

        # If it was sparse, reasoning should reflect that
        reasoning = f"Generated targeted work experience template to bridge empty work history." if not experience else f"Enhanced experience bullets for {len(experience)} jobs to improve action verb and keyword compatibility."

        return {
            "output": parsed_json,
            "reasoning": reasoning
        }

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.strftime('%H:%M:%S')
        return {
            "suggested_rewrites": agent_output.get("output"),
            "logs": [f"[Rewriter] Resume experience bullets optimized at {timestamp}"],
            "current_agent": self.agent_type.value,
            "progress": 60
        }


import time
