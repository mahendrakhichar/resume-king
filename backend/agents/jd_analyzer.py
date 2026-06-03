"""Job Description Analyzer Agent."""

import json
from typing import Dict, Any

from agents.base import BaseAgent
from models.session import AgentType
from services.llm_service import llm_service
from schemas.session import JDAnalysis
from utils.logger import get_logger

logger = get_logger(__name__)

JD_ANALYZER_SYSTEM_PROMPT = """You are a professional Tech Recruiter and Job Description Parser Agent.
Your objective is to read a raw job description and extract a comprehensive, structured JSON analysis.

You must extract:
1. skills_required: Hard skills/languages/frameworks that are explicitly required (e.g. Python, React).
2. skills_preferred: Hard skills that are nice-to-have or preferred.
3. tools_and_technologies: Development tools, databases, platforms mentioned (e.g. AWS, Git, Postgres).
4. experience_level: Entry, Mid, Senior, Lead, or Principal based on description context.
5. keywords: Crucial high-impact industry buzzwords and ATS terms (e.g., CI/CD, Microservices, Scalability).
6. responsibilities: Core tasks of this role. Keep them concise.
7. company_culture_hints: Attributes like fast-paced, collaborative, self-starter, learning mindset, etc.

Rules:
- Return ONLY valid JSON matching the schema perfectly. Do not include markdown code block formatting.
- Be highly precise and avoid pulling generic words as technical skills.
"""

JD_ANALYZER_USER_TEMPLATE = """Analyze the following Job Description:

--- JOB DESCRIPTION ---
{job_description}
--- END JOB DESCRIPTION ---
"""


class JDAnalyzerAgent(BaseAgent):
    """Agent responsible for dissecting a Job Description to build target keyword structures."""

    def __init__(self):
        super().__init__(AgentType.JD_ANALYZER)

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        job_desc = state.get("job_description", "")
        
        user_prompt = JD_ANALYZER_USER_TEMPLATE.format(job_description=job_desc)
        
        # Invoke LLM with task-based routing (routes to FAST_MODEL)
        response_text = await llm_service.invoke_with_fallback(
            system_prompt=JD_ANALYZER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,  # Low temperature for highly analytical facts
            task_type="jd_analysis",
        )

        # Parse JSON output
        from agents.base import extract_json_block
        clean_text = extract_json_block(response_text)

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"JD analyzer JSON parsing failed: {e}. Raw response: {response_text}")
            parsed_json = {
                "skills_required": [],
                "skills_preferred": [],
                "tools_and_technologies": [],
                "experience_level": "Mid-Level",
                "keywords": [],
                "responsibilities": [],
                "company_culture_hints": []
            }
        
        # Resilient validation with lenient fallback
        try:
            validated_analysis = JDAnalysis(**parsed_json)
        except Exception as e:
            logger.warning(f"JD schema validation failed, using lenient fallback: {e}")
            validated_analysis = JDAnalysis(
                skills_required=parsed_json.get("skills_required", []),
                skills_preferred=parsed_json.get("skills_preferred", []),
                tools_and_technologies=parsed_json.get("tools_and_technologies", []),
                experience_level=parsed_json.get("experience_level"),
                keywords=parsed_json.get("keywords", []),
                responsibilities=parsed_json.get("responsibilities", []),
                company_culture_hints=parsed_json.get("company_culture_hints", []),
            )
        
        return {
            "output": validated_analysis.model_dump(),
            "reasoning": "dissected core skills, technologies, seniority level, and target keywords from Job Description successfully."
        }

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.strftime('%H:%M:%S')
        return {
            "job_analysis": agent_output.get("output"),
            "logs": [f"[JD_Analyzer] Job description analyzed at {timestamp}"],
            "current_agent": self.agent_type.value,
            "progress": 25
        }


import time
