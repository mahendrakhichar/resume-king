"""Project Optimization Agent."""

import json
from typing import Dict, Any

from agents.base import BaseAgent
from models.session import AgentType
from services.llm_service import llm_service
from utils.logger import get_logger

logger = get_logger(__name__)

PROJECT_OPT_SYSTEM_PROMPT = """You are a Principal Software Engineer and System Architect Agent.
Your objective is to review a candidate's projects and optimize their technical framing, architectural descriptions, and keywords.

Rules:
1. Elevate technical vocabulary: describe backend architectures, databases, system scaling, cloud patterns, and API interactions.
2. Ensure technical tools and stack are explicitly emphasized in the context of system decisions.
3. Suggest missing feature improvements or architectural enhancements that fit the target job (e.g. adding caching, messaging queues, containerization).
4. Maintain honesty. Do not assert the candidate built things they did not, but rather describe their projects' existing codebases with premium engineering wording.

Your output MUST be a JSON array of objects representing projects with updated points.
Output schema:
[
  {
    "name": "Project Name",
    "technologies": ["React", "Node.js"],
    "original_bullets": ["bullet 1"],
    "rewritten_bullets": [
      {
        "original": "original bullet 1",
        "suggested": "architecturally improved bullet 1",
        "reasoning": "How this framing makes the engineer look mid/senior or system-aware."
      }
    ],
    "suggested_extensions": [
      {
        "feature": "Implement Redis Caching",
        "impact": "Reduces database load and cuts API read latencies by up to 60%."
      }
    ]
  }
]

Return ONLY raw JSON matching the schema. No markdown formatting.
"""

PROJECT_OPT_USER_TEMPLATE = """Optimize the following project descriptions for technical depth, architectural wording, and keyword fit.

--- PROJECTS ---
{projects}
--- END PROJECTS ---

--- JOB ANALYSIS ---
{job_analysis}
--- END JOB ANALYSIS ---
"""

PROJECT_SPARSE_SYSTEM_PROMPT = """You are a Principal Software Engineer and System Architect Agent.
The candidate has NO projects listed on their resume.
Your objective is to suggest 2 customized, high-impact "Bridge Projects" that the candidate should build and write on their resume to target their desired job description and incorporate missing keywords.

Instructions for the projects:
1. For each project, generate a targeted Name, list of modern Technologies (e.g., React, Go, Redis, Docker), and 2 high-impact suggested bullet points utilizing bracketed placeholders like "[Insert Metric]%" so the user can easily customize them.
2. Provide a suggested technical extension (e.g., adding caching, monitoring, or queueing) with its impact.
3. Keep the JSON schema exactly matching this:
[
  {
    "name": "[Target Project Name: e.g., Cloud Task Queue]",
    "technologies": ["Go", "Redis", "Docker"],
    "original_bullets": ["Candidate has no projects listed on resume."],
    "rewritten_bullets": [
      {
        "original": "No projects listed",
        "suggested": "Designed and deployed a distributed task queue utilizing [Redis] and [Go] to process up to [X] requests/sec.",
        "reasoning": "Special bridge project template to help you fill your technical skills gap. Replace bracketed terms when you implement/describe the system."
      }
    ],
    "suggested_extensions": [
      {
        "feature": "Implement Prometheus metrics",
        "impact": "Provides real-time visibility into workers and execution latency."
      }
    ]
  }
]

Return ONLY raw JSON matching the schema. No markdown formatting.
"""

PROJECT_SPARSE_USER_TEMPLATE = """Generate 2 custom bridge project templates for the following role:

--- TARGET ROLE & JD ---
Role: {target_role}
JD: {job_description}
--- END TARGET ROLE & JD ---

--- CANDIDATE SKILLS ---
{skills}
--- END CANDIDATE SKILLS ---

--- JOB ANALYSIS ---
{job_analysis}
--- END JOB ANALYSIS ---
"""


class ProjectOptimizerAgent(BaseAgent):
    """Agent responsible for polishing projects to showcase system engineering and architecture proficiency."""

    def __init__(self):
        super().__init__(AgentType.PROJECT_OPTIMIZER)

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        parsed_resume = state.get("parsed_resume", {})
        projects = parsed_resume.get("projects", [])
        job_analysis = state.get("job_analysis", {})

        if not projects:
            logger.info("Projects section is empty. Generating bridge project template suggestions.")
            user_prompt = PROJECT_SPARSE_USER_TEMPLATE.format(
                target_role=state.get("target_role") or "Software Engineer",
                job_description=state.get("job_description", ""),
                skills=json.dumps(parsed_resume.get("skills", [])),
                job_analysis=json.dumps(job_analysis)
            )
            
            response_text = await llm_service.invoke_with_fallback(
                system_prompt=PROJECT_SPARSE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.4,  # higher creativity for template generation
                task_type="project_optimization",
            )
        else:
            user_prompt = PROJECT_OPT_USER_TEMPLATE.format(
                projects=json.dumps(projects),
                job_analysis=json.dumps(job_analysis)
            )

            response_text = await llm_service.invoke_with_fallback(
                system_prompt=PROJECT_OPT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                task_type="project_optimization",
            )

        from agents.base import extract_json_block
        clean_text = extract_json_block(response_text)

        try:
            parsed_json = json.loads(clean_text)
            if isinstance(parsed_json, dict):
                parsed_json = [parsed_json]
        except json.JSONDecodeError as e:
            logger.warning(f"Project optimizer JSON parse failed, returning empty list: {e}")
            parsed_json = []

        reasoning = f"Generated targeted bridge project templates to fill missing projects history." if not projects else f"Enhanced {len(projects)} projects, improving system engineering terminology and suggesting target scalability extensions."

        return {
            "output": parsed_json,
            "reasoning": reasoning
        }

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.strftime('%H:%M:%S')
        return {
            "suggested_projects": agent_output.get("output"),
            "logs": [f"[Project_Optimizer] Resume projects optimized and structural suggestions generated at {timestamp}"],
            "current_agent": self.agent_type.value,
            "progress": 75
        }


import time
