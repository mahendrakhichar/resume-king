"""Orchestration of the Multi-Agent Resume Tailoring workflow using LangGraph."""

import uuid
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from workflows.state import AgentState
from workflows.nodes import (
    jd_analysis_node,
    ats_matching_node,
    resume_rewriting_node,
    project_optimization_node,
    recruiter_outreach_node,
    interview_prep_node,
    validation_node,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def should_rewrite(state: Dict[str, Any]) -> Literal["rewrite_fork", "skip_to_validate"]:
    """
    Conditional routing: if the initial ATS score is already very high (>= 90),
    we can skip rewriting/optimization completely and proceed straight to QA validation!
    """
    ats_before = state.get("ats_score_before", {})
    score = ats_before.get("overall_score", 0.0)
    
    if score >= 90.0:
        logger.info(f"Initial compatibility score is extremely high ({score}%). Skipping tailored optimizations.")
        return "skip_to_validate"
    
    return "rewrite_fork"


def build_workflow_graph():
    """Assemble the multi-agent graph with parallel loops and memory persistence checkpoints."""
    
    # 1. Initialize State Graph
    workflow = StateGraph(AgentState)

    # 2. Add all nodes
    workflow.add_node("jd_analyzer", jd_analysis_node)
    workflow.add_node("ats_matcher", ats_matching_node)
    workflow.add_node("resume_rewriter", resume_rewriting_node)
    workflow.add_node("project_optimizer", project_optimization_node)
    workflow.add_node("recruiter_agent", recruiter_outreach_node)
    workflow.add_node("interview_agent", interview_prep_node)
    workflow.add_node("validator", validation_node)

    # 3. Connect nodes with linear edges
    workflow.add_edge(START, "jd_analyzer")
    workflow.add_edge("jd_analyzer", "ats_matcher")

    # 4. Conditional routing based on ATS evaluation
    workflow.add_conditional_edges(
        "ats_matcher",
        should_rewrite,
        {
            "rewrite_fork": "resume_rewriter",     # Begins optimizations
            "skip_to_validate": "validator"        # Jumps straight to validation
        }
    )

    # 5. Parallel execution pathways starting from the rewriter node.
    # When using LangGraph, we can branch to multiple nodes from a single parent to run them in parallel!
    # Let's run Project, Recruiter, and Interview generators concurrently alongside the rewriter!
    workflow.add_edge("resume_rewriter", "project_optimizer")
    workflow.add_edge("resume_rewriter", "recruiter_agent")
    workflow.add_edge("resume_rewriter", "interview_agent")

    # 6. Join parallel branches back into the Validator node
    workflow.add_edge("project_optimizer", "validator")
    workflow.add_edge("recruiter_agent", "validator")
    workflow.add_edge("interview_agent", "validator")

    # 7. Complete execution
    workflow.add_edge("validator", END)

    # 8. Setup memory checkpointer (essential for human-in-the-loop interrupts)
    memory = MemorySaver()

    # Compile the graph
    app = workflow.compile(
        checkpointer=memory,
        # Interrupt BEFORE validator or human review step if needed
        # We can interrupt_before=["validator"] to review and accept/edit suggestions before finalizing
    )
    
    logger.info("LangGraph multi-agent workflow compiled successfully.")
    return app


# Compiled Singleton instance
workflow_app = build_workflow_graph()
