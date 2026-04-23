"""
Pydantic v2 schemas para API FastAPI.

Patrón Create/Read/Update por entidad.
Requiere: pip install pydantic>=2
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Tipos literales (espejo de los CHECK constraints)
# =============================================================================
ProviderT = Literal["local", "openai", "anthropic", "google", "voyage"]
ModelKindT = Literal["embedding", "llm", "rerank"]
ExecutionModeT = Literal["local", "frontier_mock"]
ProjectStatusT = Literal["pending", "in_progress", "completed", "archived"]
PaperSourceT = Literal["arxiv", "scholar", "manual"]
AddedByT = Literal["discovery_agent", "user"]
QueryTypeT = Literal["search", "deep_read", "compare", "trend", "qa"]
QueryStatusT = Literal["pending", "running", "completed", "failed"]
QueryExecutionModeT = Literal["local", "frontier_mock", "hybrid"]
AgentT = Literal[
    "orchestrator", "discovery", "reader", "comparator", "synthesizer", "citation_guard"
]
AgentStatusT = Literal["started", "in_progress", "completed", "failed"]


# =============================================================================
# Base común
# =============================================================================
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 1. Model (catálogo)
# =============================================================================
class ModelBase(BaseModel):
    provider: ProviderT
    kind: ModelKindT
    execution_mode: ExecutionModeT
    input_cost_per_1m_tokens: Decimal | None = None
    output_cost_per_1m_tokens: Decimal | None = None
    embedding_dimension: int | None = None
    context_window: int | None = None
    default_tokens_per_second: Decimal | None = None
    notes: str | None = None


class ModelCreate(ModelBase):
    id: str


class ModelRead(ModelBase, ORMModel):
    id: str
    is_active: bool
    created_at: datetime


# =============================================================================
# 2. Project
# =============================================================================
class ProjectBase(BaseModel):
    topic: str
    description: str | None = None
    status: ProjectStatusT = "pending"
    # El atributo del ORM se llama `meta` (no `metadata` para no chocar con Base.metadata
    # de SQLAlchemy). Se serializa como "metadata" hacia el API pública.
    meta: dict[str, Any] = Field(default_factory=dict, serialization_alias="metadata")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    topic: str | None = None
    description: str | None = None
    status: ProjectStatusT | None = None
    meta: dict[str, Any] | None = Field(default=None, serialization_alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class ProjectRead(ProjectBase, ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 3. Paper
# =============================================================================
class PaperBase(BaseModel):
    source: PaperSourceT
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    published_at: date | None = None
    doi: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    citations_count: int | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class PaperCreate(PaperBase):
    id: str


class PaperRead(PaperBase, ORMModel):
    id: str
    ingested_at: datetime


# =============================================================================
# 4. Chunk (no exponemos el vector completo en el API, solo metadata)
# =============================================================================
class ChunkRead(ORMModel):
    id: int
    paper_id: str
    chunk_index: int
    section: str | None = None
    page: int | None = None
    figure_ref: str | None = None
    text: str
    token_count: int | None = None
    embedded_by: str | None = None
    created_at: datetime


# =============================================================================
# 5. ProjectPaper
# =============================================================================
class ProjectPaperRead(ORMModel):
    project_id: UUID
    paper_id: str
    relevance_score: Decimal | None = None
    added_by: AddedByT
    added_at: datetime


class ProjectPaperAttach(BaseModel):
    paper_id: str
    relevance_score: Decimal | None = None
    added_by: AddedByT = "user"


# =============================================================================
# 6. Query
# =============================================================================
class QueryCreate(BaseModel):
    query_text: str
    query_type: QueryTypeT | None = None
    execution_mode: QueryExecutionModeT = "local"


class QueryRead(ORMModel):
    id: UUID
    project_id: UUID
    query_text: str
    query_type: QueryTypeT | None = None
    intent: str | None = None
    status: QueryStatusT
    error: str | None = None
    execution_mode: QueryExecutionModeT
    created_at: datetime
    completed_at: datetime | None = None


# =============================================================================
# 7. AgentEvent (stream) + proyección ligera para SSE
# =============================================================================
class AgentEventRead(ORMModel):
    id: int
    query_id: UUID
    agent: AgentT
    action: str
    status: AgentStatusT
    payload: dict[str, Any] = Field(default_factory=dict)
    model_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    tokens_per_second: Decimal | None = None
    latency_ms: int | None = None
    cost_estimated_usd: Decimal | None = None
    emitted_at: datetime


class AgentEventStream(BaseModel):
    """Proyección ligera para enviar por SSE al frontend.

    El nombre del campo coincide con el atributo del ORM para que
    `from_attributes=True` funcione; los alias se aplican solo en serialización.
    """

    agent: AgentT
    action: str
    status: AgentStatusT
    model_id: str | None = None
    tokens_per_second: Decimal | None = Field(default=None, serialization_alias="tok_per_sec")
    cost_estimated_usd: Decimal | None = Field(default=None, serialization_alias="cost_usd")
    latency_ms: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =============================================================================
# 8. Report
# =============================================================================
class ReportRead(ORMModel):
    id: UUID
    query_id: UUID
    title: str | None = None
    summary: str | None = None
    body_markdown: str
    structured_output: dict[str, Any] = Field(default_factory=dict)
    groundedness_score: Decimal | None = None
    citation_accuracy_score: Decimal | None = None
    faithfulness_score: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class ReportUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    body_markdown: str | None = None
    structured_output: dict[str, Any] | None = None


# =============================================================================
# 9. Citation
# =============================================================================
class CitationRead(ORMModel):
    id: int
    report_id: UUID
    citation_key: str
    paper_id: str
    chunk_id: int | None = None
    quote: str | None = None
    page: int | None = None
    figure_ref: str | None = None
    verified: bool
    verified_at: datetime | None = None
    created_at: datetime


# =============================================================================
# 10. Note
# =============================================================================
class NoteCreate(BaseModel):
    body: str


class NoteRead(ORMModel):
    id: UUID
    project_id: UUID
    body: str
    created_at: datetime
    updated_at: datetime


class NoteUpdate(BaseModel):
    body: str


# =============================================================================
# 11. EvalRun
# =============================================================================
class EvalRunRead(ORMModel):
    id: UUID
    query_id: UUID | None = None
    dataset_version: str | None = None
    groundedness: Decimal | None = None
    faithfulness: Decimal | None = None
    citation_accuracy: Decimal | None = None
    judge_model_id: str | None = None
    notes: str | None = None
    ran_at: datetime


# =============================================================================
# Aggregates (para dashboard)
# =============================================================================
class ProjectCostSummary(BaseModel):
    project_id: UUID
    topic: str
    total_queries: int
    total_events: int
    total_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int


class AgentLoadItem(BaseModel):
    agent: AgentT
    active_queries: int
