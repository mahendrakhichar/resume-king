"""SQLAlchemy ORM models for tailoring sessions and agent results."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Float, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class SessionStatus(str, enum.Enum):
    """Lifecycle status of a tailoring session."""
    PENDING = "pending"
    RUNNING = "running"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, enum.Enum):
    """Types of AI agents in the workflow."""
    RESUME_PARSER = "resume_parser"
    JD_ANALYZER = "jd_analyzer"
    ATS_MATCHER = "ats_matcher"
    RESUME_REWRITER = "resume_rewriter"
    PROJECT_OPTIMIZER = "project_optimizer"
    RECRUITER_AGENT = "recruiter_agent"
    INTERVIEW_AGENT = "interview_agent"
    VALIDATOR = "validator"


class AgentStatus(str, enum.Enum):
    """Execution status of an individual agent."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReviewAction(str, enum.Enum):
    """User action on an AI suggestion."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class Session(Base):
    """A tailoring session: one resume + one job description → one workflow run."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    job_analysis: Mapped[dict] = mapped_column(JSONB, nullable=True)
    target_company: Mapped[str] = mapped_column(String(255), nullable=True)
    target_role: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.PENDING
    )
    ats_score_before: Mapped[float] = mapped_column(Float, nullable=True)
    ats_score_after: Mapped[float] = mapped_column(Float, nullable=True)
    workflow_state: Mapped[dict] = mapped_column(JSONB, nullable=True)
    final_resume_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="sessions")
    resume = relationship("Resume", back_populates="sessions")
    agent_results = relationship(
        "AgentResult", back_populates="session", cascade="all, delete-orphan"
    )
    human_reviews = relationship(
        "HumanReview", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session {self.id} status={self.status}>"


class AgentResult(Base):
    """Output from a single agent execution within a session."""

    __tablename__ = "agent_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.PENDING
    )
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    session = relationship("Session", back_populates="agent_results")
    human_reviews = relationship(
        "HumanReview", back_populates="agent_result", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AgentResult {self.agent_type} status={self.status}>"


class HumanReview(Base):
    """User review/decision on an AI-generated suggestion."""

    __tablename__ = "human_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    agent_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_results.id", ondelete="CASCADE"), nullable=False
    )
    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    original_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    suggested_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    final_content: Mapped[dict] = mapped_column(JSONB, nullable=True)
    action: Mapped[ReviewAction] = mapped_column(Enum(ReviewAction), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    session = relationship("Session", back_populates="human_reviews")
    agent_result = relationship("AgentResult", back_populates="human_reviews")

    def __repr__(self) -> str:
        return f"<HumanReview section={self.section_key} action={self.action}>"
