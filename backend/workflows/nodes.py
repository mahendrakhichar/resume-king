"""Node functions mapping the LangGraph state updates to AI Agent executions."""

from typing import Dict, Any

from agents.jd_analyzer import JDAnalyzerAgent
from agents.ats_matcher import ATSMatcherAgent
from agents.resume_rewriter import ResumeRewriterAgent
from agents.project_optimizer import ProjectOptimizerAgent
from agents.recruiter_agent import RecruiterAgent
from agents.interview_agent import InterviewAgent
from agents.validator import ValidatorAgent
from utils.logger import get_logger

logger = get_logger(__name__)


# ─── Instantiating Stateless/Stateful Agents ──────────────────────────
jd_analyzer = JDAnalyzerAgent()
ats_matcher = ATSMatcherAgent()
resume_rewriter = ResumeRewriterAgent()
project_optimizer = ProjectOptimizerAgent()
recruiter_agent = RecruiterAgent()
interview_agent = InterviewAgent()
validator = ValidatorAgent()


# ─── LangGraph Node Functions ─────────────────────────────────────────

async def jd_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute JD dissection."""
    return await jd_analyzer.execute_in_workflow(state)


async def ats_matching_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute initial or final ATS evaluation."""
    return await ats_matcher.execute_in_workflow(state)


async def resume_rewriting_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute experience rewriting."""
    return await resume_rewriter.execute_in_workflow(state)


async def project_optimization_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute project architecture adjustments."""
    return await project_optimizer.execute_in_workflow(state)


async def recruiter_outreach_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute LinkedIn connection/email generation."""
    return await recruiter_agent.execute_in_workflow(state)


async def interview_prep_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute customized behavioral/technical Q&A generation."""
    return await interview_agent.execute_in_workflow(state)


async def validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute quality assurance review."""
    return await validator.execute_in_workflow(state)
