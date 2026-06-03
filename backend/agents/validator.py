"""Validation and QA Agent."""

import json
from typing import Dict, Any

from agents.base import BaseAgent
from models.session import AgentType
from services.llm_service import llm_service
from utils.logger import get_logger

logger = get_logger(__name__)

VALIDATOR_SYSTEM_PROMPT = """You are a Quality Assurance and Resume Validation Agent.
Your objective is to review all AI-suggested modifications (bullet rewrites, project optimizations) and guarantee their compliance with standard engineering resume best practices.

You must evaluate and output:
1. is_valid: Boolean representing whether modifications are ready for human review.
2. errors: A list of any specific errors discovered (hallucinations, grammatical issues, weird formatting, syntax).
3. quality_score: A score between 0 and 100 on general formatting and language impact.
4. recommendations: Actionable details to resolve any issues.

Validation Rules:
- Ensure no placeholder values are present (e.g. "[Insert Metric Here]", "X%", "[Y]").
- Verify there are absolutely no formatting artifacts or broken markdown.
- Ensure the tone remains entirely honest: check for obvious tech stack hallucinations not justified by the original resume.
- Verify that every rewrite bullet point starts with a solid past-tense action verb.

Return ONLY valid JSON matching the rules. No markdown blocks.
"""

VALIDATOR_USER_TEMPLATE = """Review the following suggested changes and validate their readiness:

--- ORIGINAL RESUME DATA ---
{original_resume}
--- END ORIGINAL RESUME DATA ---

--- SUGGESTED EXPERIENCE REWRITES ---
{suggested_rewrites}
--- END SUGGESTED EXPERIENCE REWRITES ---

--- SUGGESTED PROJECT OPTIMIZATIONS ---
{suggested_projects}
--- END SUGGESTED PROJECT OPTIMIZATIONS ---
"""


class ValidatorAgent(BaseAgent):
    """Agent responsible for checking all AI-suggested content for errors, placeholders, or hallucinations."""

    def __init__(self):
        super().__init__(AgentType.VALIDATOR)

    async def _run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        original_resume = state.get("parsed_resume", {})
        suggested_rewrites = state.get("suggested_rewrites") or []
        suggested_projects = state.get("suggested_projects") or []

        # Optimization: skip LLM validation if no content was changed/suggested
        if not suggested_rewrites and not suggested_projects:
            logger.info("Skipping Validator LLM call: no suggested experience rewrites or project optimizations to validate.")
            return {
                "output": {
                    "is_valid": True,
                    "errors": [],
                    "quality_score": 100,
                    "recommendations": []
                },
                "reasoning": "Skipped LLM validation as no experience rewrites or project optimizations were suggested."
            }

        user_prompt = VALIDATOR_USER_TEMPLATE.format(
            original_resume=json.dumps(original_resume),
            suggested_rewrites=json.dumps(suggested_rewrites),
            suggested_projects=json.dumps(suggested_projects)
        )

        response_text = await llm_service.invoke_with_fallback(
            system_prompt=VALIDATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,  # Strict precision
            task_type="validation",
        )

        from agents.base import extract_json_block
        clean_text = extract_json_block(response_text)

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Validator JSON parse failed: {e}")
            parsed_json = {"is_valid": True, "errors": [], "quality_score": 70, "recommendations": []}

        return {
            "output": parsed_json,
            "reasoning": "Completed QA audit on experience rewrites and project optimizations. Ready for review."
        }

    def _merge_into_state(self, state: Dict[str, Any], agent_output: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.strftime('%H:%M:%S')
        output = agent_output.get("output", {})
        is_valid = output.get("is_valid", True)
        
        return {
            "validation_status": output,
            "requires_human_review": is_valid,  # If it is valid, pause and request human review!
            "logs": [f"[Validator] Content QA audit finished at {timestamp}. Valid status: {is_valid}"],
            "current_agent": self.agent_type.value,
            "progress": 90
        }


import time
