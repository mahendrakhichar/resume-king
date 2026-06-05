"""Pydantic schemas for session and agent-related API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, model_validator


# ─── Job Description Analysis ──────────────────────────────────────

class JDAnalysis(BaseModel):
    """Structured output from the JD Analyzer agent."""
    skills_required: list[str] = Field(default_factory=list)
    skills_preferred: list[str] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    company_culture_hints: list[str] = Field(default_factory=list)


# ─── ATS Analysis ──────────────────────────────────────────────────

class ATSSectionScore(BaseModel):
    """Score breakdown for a single resume section."""
    section: Optional[str] = "general"
    score: float = 0.0
    max_score: float = Field(default=100.0)     # Some LLMs omit this; default to 100
    feedback: str = Field(default="")            # Some LLMs return 'comments' instead
    comments: Optional[str] = None               # Alias some LLMs use instead of 'feedback'

    def model_post_init(self, __context) -> None:
        # If feedback is empty but comments was provided, use comments
        if not self.feedback and self.comments:
            self.feedback = self.comments


class ATSAnalysis(BaseModel):
    """Output from the ATS Matching agent."""
    overall_score: float = Field(default=50.0, ge=0, le=100)
    keyword_match_rate: float = Field(default=0.0, ge=0, le=100)
    missing_keywords: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    section_scores: list[ATSSectionScore] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def clean_section_scores(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If section_scores is a dict instead of a list, convert it to a list of objects
            if "section_scores" in data and isinstance(data["section_scores"], dict):
                scores_list = []
                for sect, val in data["section_scores"].items():
                    if isinstance(val, dict):
                        score_val = val.get("score", 0.0)
                        feedback_val = val.get("feedback") or val.get("comments") or ""
                        scores_list.append({
                            "section": sect,
                            "score": float(score_val),
                            "feedback": feedback_val
                        })
                    else:
                        scores_list.append({
                            "section": sect,
                            "score": float(val),
                            "feedback": ""
                        })
                data["section_scores"] = scores_list
        return data


# ─── Session Schemas ───────────────────────────────────────────────

class SessionCreate(BaseModel):
    """Request to create a new tailoring session."""
    resume_id: uuid.UUID
    job_description: str = Field(min_length=50, max_length=10000)
    target_company: Optional[str] = None
    target_role: Optional[str] = None


class SessionResponse(BaseModel):
    """Response with session details."""
    id: uuid.UUID
    resume_id: uuid.UUID
    job_description: str
    target_company: Optional[str] = None
    target_role: Optional[str] = None
    status: str
    ats_score_before: Optional[float] = None
    ats_score_after: Optional[float] = None
    job_analysis: Optional[JDAnalysis] = None
    parsed_resume: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionListItem(BaseModel):
    """Lightweight session for list views."""
    id: uuid.UUID
    target_company: Optional[str] = None
    target_role: Optional[str] = None
    status: str
    ats_score_before: Optional[float] = None
    ats_score_after: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Agent Result Schemas ──────────────────────────────────────────

class AgentResultResponse(BaseModel):
    """Response with agent execution result."""
    id: uuid.UUID
    agent_type: str
    status: str
    output_data: Optional[Any] = None
    reasoning: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentStatusUpdate(BaseModel):
    """WebSocket message for real-time agent updates."""
    session_id: uuid.UUID
    agent_type: str
    status: str
    progress: Optional[int] = Field(None, ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Any] = None


# ─── Human Review Schemas ──────────────────────────────────────────

class HumanReviewItem(BaseModel):
    """A single suggestion awaiting user review."""
    id: uuid.UUID
    agent_result_id: uuid.UUID
    section_key: str
    original_content: Any
    suggested_content: Any
    reasoning: Optional[str] = None


class HumanReviewDecision(BaseModel):
    """User's decision on a suggestion."""
    review_id: uuid.UUID
    action: str = Field(pattern="^(accepted|rejected|edited)$")
    final_content: Optional[Any] = None


class HumanReviewBatch(BaseModel):
    """Batch submit multiple review decisions."""
    decisions: list[HumanReviewDecision]


# ─── Recruiter Messages ───────────────────────────────────────────

class RecruiterMessages(BaseModel):
    """Output from the Recruiter Message agent."""
    linkedin_connection: Optional[str] = ""
    referral_request: Optional[str] = ""
    cold_email: Optional[str] = ""
    follow_up: Optional[str] = ""


# ─── Interview Prep ───────────────────────────────────────────────

class InterviewQuestion(BaseModel):
    """A single interview question with context."""
    category: Optional[str] = "general"
    question: Optional[str] = ""
    difficulty: Optional[str] = None
    tips: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize Category
            for k in ["Category", "category_name", "Category name"]:
                if k in data and "category" not in data:
                    data["category"] = data[k]
            # Normalize Question
            for k in ["Question text", "Question", "question_text", "text", "Question Text"]:
                if k in data and ("question" not in data or not data["question"]):
                    data["question"] = data[k]
            # Normalize Difficulty
            for k in ["Difficulty", "level"]:
                if k in data and "difficulty" not in data:
                    data["difficulty"] = data[k]
            # Normalize Tips
            for k in ["Tips", "tip", "prep_tips"]:
                if k in data and "tips" not in data:
                    data["tips"] = data[k]
        return data


class InterviewPrep(BaseModel):
    """Output from the Interview Prep agent."""
    questions: list[InterviewQuestion] = Field(default_factory=list)
    preparation_tips: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize questions list key
            for k in ["preparation_questions", "Questions", "questions_list", "prep_questions"]:
                if k in data and "questions" not in data:
                    data["questions"] = data[k]
            # Normalize preparation_tips key
            for k in ["general_preparation_tips", "prep_tips", "tips", "Preparation Tips", "preparation_tips_list"]:
                if k in data and "preparation_tips" not in data:
                    data["preparation_tips"] = data[k]
            
            # Ensure lists are lists, else empty
            if "questions" in data and data["questions"] is None:
                data["questions"] = []
            if "preparation_tips" in data and data["preparation_tips"] is None:
                data["preparation_tips"] = []
        return data
