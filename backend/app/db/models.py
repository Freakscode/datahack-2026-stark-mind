"""
SQLAlchemy 2.0 ORM models para STARK-VIX.

Requiere:
    pip install sqlalchemy[asyncio] asyncpg pgvector
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


# =============================================================================
# 1. models — catálogo de LLMs y embeddings (local + frontier mock)
# =============================================================================
class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    execution_mode: Mapped[str] = mapped_column(Text, nullable=False)
    input_cost_per_1m_tokens: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    output_cost_per_1m_tokens: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    embedding_dimension: Mapped[int | None] = mapped_column(Integer)
    context_window: Mapped[int | None] = mapped_column(Integer)
    default_tokens_per_second: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("provider IN ('local','openai','anthropic','google','voyage')"),
        CheckConstraint("kind IN ('embedding','llm','rerank')"),
        CheckConstraint("execution_mode IN ('local','frontier_mock')"),
    )


# =============================================================================
# 2. projects
# =============================================================================
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    queries: Mapped[list["Query"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    paper_links: Mapped[list["ProjectPaper"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('pending','in_progress','completed','archived')"),
    )


# =============================================================================
# 3. papers
# =============================================================================
class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    venue: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[date | None] = mapped_column(Date)
    doi: Mapped[str | None] = mapped_column(Text, unique=True)
    url: Mapped[str | None] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    citations_count: Mapped[int | None] = mapped_column(Integer)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    project_links: Mapped[list["ProjectPaper"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("source IN ('arxiv','scholar','manual')"),
    )


# =============================================================================
# 4. chunks (pgvector)
# =============================================================================
class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(
        Text, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    figure_ref: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    embedded_by: Mapped[str | None] = mapped_column(
        Text, ForeignKey("models.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    paper: Mapped[Paper] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("paper_id", "chunk_index"),
    )


# =============================================================================
# 5. project_papers (N:M)
# =============================================================================
class ProjectPaper(Base):
    __tablename__ = "project_papers"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    paper_id: Mapped[str] = mapped_column(
        Text, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    added_by: Mapped[str] = mapped_column(Text, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="paper_links")
    paper: Mapped[Paper] = relationship(back_populates="project_links")

    __table_args__ = (
        CheckConstraint("added_by IN ('discovery_agent','user')"),
    )


# =============================================================================
# 6. queries
# =============================================================================
class Query(Base):
    __tablename__ = "queries"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    execution_mode: Mapped[str] = mapped_column(Text, nullable=False, default="local")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="queries")
    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="query", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="query", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("query_type IN ('search','deep_read','compare','trend','qa')"),
        CheckConstraint("status IN ('pending','running','completed','failed')"),
        CheckConstraint("execution_mode IN ('local','frontier_mock','hybrid')"),
    )


# =============================================================================
# 7. agent_events (stream persistido + telemetría)
# =============================================================================
class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    query_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    model_id: Mapped[str | None] = mapped_column(Text, ForeignKey("models.id"))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    tokens_per_second: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_estimated_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    emitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    query: Mapped[Query] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint(
            "agent IN ('orchestrator','discovery','reader','comparator','synthesizer','citation_guard')"
        ),
        CheckConstraint("status IN ('started','in_progress','completed','failed')"),
    )


# =============================================================================
# 8. reports
# =============================================================================
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    structured_output: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    groundedness_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    citation_accuracy_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    faithfulness_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    query: Mapped[Query] = relationship(back_populates="report")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


# =============================================================================
# 9. citations
# =============================================================================
class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    citation_key: Mapped[str] = mapped_column(Text, nullable=False)
    paper_id: Mapped[str] = mapped_column(
        Text, ForeignKey("papers.id"), nullable=False
    )
    chunk_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chunks.id")
    )
    quote: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    figure_ref: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    report: Mapped[Report] = relationship(back_populates="citations")

    __table_args__ = (
        UniqueConstraint("report_id", "citation_key"),
    )


# =============================================================================
# 10. notes
# =============================================================================
class Note(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="notes")


# =============================================================================
# 11. eval_runs
# =============================================================================
class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE")
    )
    dataset_version: Mapped[str | None] = mapped_column(Text)
    groundedness: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    faithfulness: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    citation_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    judge_model_id: Mapped[str | None] = mapped_column(Text, ForeignKey("models.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
