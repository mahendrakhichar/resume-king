"""Interview Preparation Agent."""

import json
from typing import Dict, Any

from agents.base import BaseAgent
from models.session import AgentType
from services.llm_service import llm_service
from schemas.session import InterviewPrep
from utils.logger import get_logger

logger = get_logger(__name__)

INTERVIEW_SYSTEM_PROMPT = """You are a Senior Technical Interviewer and Engineering Lead Agent.
Your objective is to generate highly custom, relevant interview preparation questions based on a candidate's resume, their target job, and company.

You must generate:
1. A list of specific preparation questions with Category, Question text, Difficulty, and custom helpful Tips.
   The categories MUST cover:
   - dsa: Data Structures & Algorithms (relevant to the target company's tier, e.g. FAANG vs Startup).
   - hr: Standard behavior/HR questions matching the candidate's background and company culture.
   - system_design: System architecture/design questions relevant to the seniority level.
   - project: Specific, probing technical questions about the actual projects listed on the candidate's resume.
2. A list of high-impact general preparation tips.

Rules:
- Be highly specific. Probing project questions should reference actual technology decisions listed on their projects.
- Return ONLY valid JSON matching the schema perfectly. No code block formatting.
"""

INTERVIEW_USER_TEMPLATE = """Generate interview preparation materials:

--- TARGET COMPANY ---
{target_company}

--- TARGET ROLE ---
{target_role}

--- CANDIDATE RESUME ---
{parsed_resume}

--- JOB DESCRIPTION ---
{job_description}
"""


class InterviewAgent(BaseAgent):
    """Agent responsible for crafting mock interview questions spanning DSA, HR, System Design, and Project audits."""

    def __init__(self):
        super().__init__(AgentType.INTERVIEW_AGENT)

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        parsed_resume = state.get("parsed_resume", {})
        job_description = state.get("job_description", "")
        target_company = state.get("target_company") or "Target Company"
        target_role = state.get("target_role") or "Software Engineer"

        user_prompt = INTERVIEW_USER_TEMPLATE.format(
            target_company=target_company,
            target_role=target_role,
            parsed_resume=json.dumps(parsed_resume),
            job_description=job_description
        )

        response_text = await llm_service.invoke_with_fallback(
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            task_type="interview_prep",
        )

        from agents.base import extract_json_block
        clean_text = extract_json_block(response_text)

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Interview agent JSON parsing failed: {e}. Raw response: {response_text}")
            parsed_json = {
                "questions": [],
                "preparation_tips": ["Review target core engineering concepts."]
            }

        try:
            validated_prep = InterviewPrep(**parsed_json)
        except Exception as e:
            logger.warning(f"Interview schema validation failed, using lenient fallback: {e}")
            validated_prep = InterviewPrep(
                questions=[],
                preparation_tips=parsed_json.get("preparation_tips", parsed_json.get("tips", [])),
            )

        return {
            "output": validated_prep.model_dump(),
            "reasoning": f"Generated custom interview preparation bank tailored to the candidate's stack and target role at {target_company}."
        }

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.strftime('%H:%M:%S')
        return {
            "interview_prep": agent_output.get("output"),
            "logs": [f"[Interview_Agent] Custom technical & behavioral interview prep guide created at {timestamp}"],
            "current_agent": self.agent_type.value,
            "progress": 90
        }


import time
