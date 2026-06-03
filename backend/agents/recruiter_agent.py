"""Recruiter Outreach Agent."""

import json
from typing import Dict, Any

from agents.base import BaseAgent
from models.session import AgentType
from services.llm_service import llm_service
from schemas.session import RecruiterMessages
from utils.logger import get_logger

logger = get_logger(__name__)

RECRUITER_SYSTEM_PROMPT = """You are a Networking Specialist and Recruiter Outreach Agent.
Your objective is to generate highly optimized, tailored, and persuasive outreach templates based on a candidate's resume, the target job description, and the company.

You must generate 4 customized messages:
1. linkedin_connection: A 300-character-limit LinkedIn invite note. Friendly, professional, and personalized.
2. referral_request: A message to a current software engineer at the target company asking for a referral. Highlights common tech alignment.
3. cold_email: A formal outreach email to a hiring manager/recruiter detailing why the candidate fits, drawing on key achievements.
4. follow_up: A polite, prompt follow-up message to send 5 days after initial outreach.

Rules:
- Make the tone warm, confident, and concise. Avoid generic templates; customize using actual details from the candidate's resume and target JD.
- Return ONLY valid JSON matching the schema perfectly. Do not include markdown code block formatting.
"""

RECRUITER_USER_TEMPLATE = """Generate recruiter outreach templates for the target role:

--- TARGET COMPANY ---
{target_company}

--- TARGET ROLE ---
{target_role}

--- CANDIDATE RESUME ---
{parsed_resume}

--- JOB DESCRIPTION ---
{job_description}
"""


class RecruiterAgent(BaseAgent):
    """Agent responsible for crafting personalized networking and job application outreach templates."""

    def __init__(self):
        super().__init__(AgentType.RECRUITER_AGENT)

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        parsed_resume = state.get("parsed_resume", {})
        job_description = state.get("job_description", "")
        target_company = state.get("target_company") or "Target Company"
        target_role = state.get("target_role") or "Software Engineer"

        user_prompt = RECRUITER_USER_TEMPLATE.format(
            target_company=target_company,
            target_role=target_role,
            parsed_resume=json.dumps(parsed_resume),
            job_description=job_description
        )

        response_text = await llm_service.invoke_with_fallback(
            system_prompt=RECRUITER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,  # Higher temperature for polished, elegant language
            task_type="recruiter_outreach",
        )

        from agents.base import extract_json_block
        clean_text = extract_json_block(response_text)

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Recruiter JSON parsing failed: {e}. Raw response: {response_text}")
            parsed_json = {
                "linkedin_connection": "Hi, I'd love to connect and learn more about opportunities at your company.",
                "referral_request": "Hi, I noticed your work and would love to ask for a referral if you have a moment.",
                "cold_email": "Dear Hiring Manager, I am very interested in the role at your company.",
                "follow_up": "Hi, following up on my previous message."
            }

        try:
            validated_messages = RecruiterMessages(**parsed_json)
        except Exception as e:
            logger.warning(f"Recruiter schema validation failed, using lenient fallback: {e}")
            validated_messages = RecruiterMessages(
                linkedin_connection=parsed_json.get("linkedin_connection", "") or "Hi, I'd love to connect and learn more about opportunities at your company.",
                referral_request=parsed_json.get("referral_request", "") or "Hi, I noticed your work and would love to ask for a referral if you have a moment.",
                cold_email=parsed_json.get("cold_email", "") or "Dear Hiring Manager, I am very interested in the role.",
                follow_up=parsed_json.get("follow_up", "") or "Hi, following up on my previous message."
            )

        return {
            "output": validated_messages.model_dump(),
            "reasoning": f"Generated custom outreach materials for {target_company} ({target_role})."
        }

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.strftime('%H:%M:%S')
        return {
            "recruiter_messages": agent_output.get("output"),
            "logs": [f"[Recruiter_Agent] Customized outreach templates generated at {timestamp}"],
            "current_agent": self.agent_type.value,
            "progress": 85
        }


import time
