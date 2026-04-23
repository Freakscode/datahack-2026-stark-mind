"""Pydantic schema del output estructurado del extractor de papers.

Mirror del ground truth de `backend/scripts/fixtures/*.summary.json`. Lo usa:
  - extractor (nodos LangGraph) para validar JSON parseado tras cada LLM call
  - API FastAPI si eventualmente expone el resultado
  - reader_agent / orchestrator al consumir extracciones persistidas

Diseño:
  - `PaperExtraction` es lo que produce el grafo del extractor completo.
  - Los *agent outputs* intermedios (un nodo por columna) usan
    `ColumnExtraction` (una lista de Bullets con metadata mínima).
  - `PaperSummaryCore` es la agregación de las 4 columnas, que es lo que el UI
    renderiza en el drawer.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal["Contexto", "Características", "Resultados", "Limitaciones"]
PaperType = Literal["empírico", "survey", "teórico", "dataset", "tutorial", "opinión"]


class Bullet(BaseModel):
    """Unidad mínima de la extracción: una afirmación anclada a una sección/figura/tabla/página."""

    text: str = Field(..., min_length=10, max_length=600)
    anchor: str | None = Field(
        None,
        description=(
            "Ancla de trazabilidad. Aceptado: §N, §N.N, Fig. N, Figure N, Table N, "
            "App. X.Y, Appendix X, p. N. None solo si el agente no pudo fundamentar."
        ),
    )

    @field_validator("anchor")
    @classmethod
    def _strip_anchor(cls, v: str | None) -> str | None:
        return v.strip() if v else None


class ColumnExtraction(BaseModel):
    """Output de un nodo de extracción de columna."""

    bullets: list[Bullet] = Field(default_factory=list)

    @field_validator("bullets")
    @classmethod
    def _min_one_if_non_empty(cls, v: list[Bullet]) -> list[Bullet]:
        # No forzamos mínimo: un paper puede no tener results (teórico puro).
        return v


class PaperSummaryCore(BaseModel):
    """Las 4 columnas del esquema comparativo."""

    motivation: list[Bullet] = Field(default_factory=list)
    methodology: list[Bullet] = Field(default_factory=list)
    materials: list[Bullet] = Field(default_factory=list)
    results: list[Bullet] = Field(default_factory=list)


class PaperClassification(BaseModel):
    category: Category
    paper_type: PaperType
    domain: str = Field(..., min_length=2, max_length=80)


class KeyMetric(BaseModel):
    """Métrica numérica única con su ancla. Útil solo para papers empíricos."""

    name: str
    value: str  # string libre: "35.1", "24.0%", "840 h", "0% vs 56%"
    unit: str | None = None
    anchor: str | None = None


class SourceMeta(BaseModel):
    """Metadata bibliográfica. La mayoría se extrae del PDF o del manifest de scrapers."""

    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    url: str | None = None
    pdf_path: str | None = None
    pages: int | None = None


class PitchMapping(BaseModel):
    """Mapeo de secciones del paper a partes del pitch/proyecto STARK-VIX.

    Clave = dimensión del pitch (architecture, corrective_layer, stack_validation,
    responsible_deployment, etc.). Valor = cita con ancla que la fundamenta.
    """

    entries: dict[str, str] = Field(default_factory=dict)


class PaperExtraction(BaseModel):
    """Output completo del grafo del extractor."""

    source: SourceMeta
    classification: PaperClassification
    summary: PaperSummaryCore
    benefit: str = Field(..., min_length=20, max_length=1500)
    key_metrics: list[KeyMetric] | None = None
    pitch_mapping: PitchMapping | None = None

    # Trazabilidad de la extracción
    provider: str | None = None  # "ollama" | "anthropic" | ...
    model: str | None = None  # "gemma2:27b" | "claude-opus-4-7" | ...
    extractor_version: str = "langgraph-v1"


__all__ = [
    "Bullet",
    "Category",
    "ColumnExtraction",
    "KeyMetric",
    "PaperClassification",
    "PaperExtraction",
    "PaperSummaryCore",
    "PaperType",
    "PitchMapping",
    "SourceMeta",
]
