"""LangGraph StateGraph del extractor.

Topología:
    START
      │
      ▼
    preprocess  (síncrono, solo pymupdf)
      │
      ▼
    classify
      │
      ├───────────────┬───────────────┬───────────────┐
      ▼               ▼               ▼               ▼
    motivation    methodology     materials       results   (paralelos, concurrencia max 4)
      │               │               │               │
      └───────────────┴───────────────┴───────────────┘
                          │
                          ▼
                     compute_benefit
                          │
                          ▼
                     consolidate (→ PaperExtraction)
                          │
                          ▼
                         END

El state es un TypedDict que LangGraph mergea: cada nodo devuelve solo los
keys que produce y LangGraph aplica reducers (default = overwrite).
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents._paper_schema import (
    Bullet,
    KeyMetric,
    PaperClassification,
    PaperExtraction,
    PaperSummaryCore,
    PitchMapping,
    SourceMeta,
)
from app.agents.extractor.nodes import (
    node_classify,
    node_compute_benefit,
    node_extract_materials,
    node_extract_methodology,
    node_extract_metrics,
    node_extract_motivation,
    node_extract_results,
)
from app.agents.llm_providers import DEFAULT_CONFIG, LLMConfig
from app.agents.pdf_preprocessor import PaperPreprocessed, preprocess_pdf


# Reducer default: overwrite. Para los campos que paralelos escriben (bullets
# por columna) cada key es único, así que el default va bien.
class ExtractorState(TypedDict, total=False):
    # Inputs
    pdf_path: str
    title: str
    llm_config: LLMConfig
    source: SourceMeta

    # Preprocess
    preprocessed: PaperPreprocessed

    # Classify
    classification: PaperClassification

    # Parallel column outputs
    motivation: list[Bullet]
    methodology: list[Bullet]
    materials: list[Bullet]
    results: list[Bullet]
    key_metrics: list[KeyMetric]

    # Post
    summary_core: PaperSummaryCore
    benefit: str
    pitch_mapping: PitchMapping | None

    # Final
    extraction: PaperExtraction


async def node_preprocess(state: ExtractorState) -> dict:
    pdf_path = state["pdf_path"]
    pre = preprocess_pdf(pdf_path)
    title = state.get("title")
    if not title and pre.sections:
        # Best-effort: primer heading si no venía título del scraper
        title = pre.sections[0].title if pre.sections[0].level == 1 else Path(pdf_path).stem
    return {"preprocessed": pre, "title": title or Path(pdf_path).stem}


async def node_consolidate(state: ExtractorState) -> dict:
    """Ensambla el PaperExtraction final mergeando outputs parciales + metadata del preprocesador."""
    cfg = state.get("llm_config") or DEFAULT_CONFIG
    classification = state["classification"]
    summary = state.get("summary_core") or PaperSummaryCore(
        motivation=state.get("motivation") or [],
        methodology=state.get("methodology") or [],
        materials=state.get("materials") or [],
        results=state.get("results") or [],
    )

    # Preferimos: source override del estado (scraper ya lo dio) → metadata
    # extraída del PDF → best-effort desde el path.
    pre = state["preprocessed"]
    m = pre.metadata
    explicit_source = state.get("source")
    paper_id_placeholder = explicit_source and explicit_source.title and all(
        c.isalnum() or c in "-_" for c in explicit_source.title
    )
    if explicit_source:
        source = explicit_source
        # Si el title del source es un paper_id placeholder (sin espacios, solo
        # letras/números/guiones), priorizamos el title real del metadata.
        if paper_id_placeholder and m.title:
            source = source.model_copy(update={"title": m.title})
        # Enriquecer campos vacíos con lo que saque el preprocesador
        if not source.arxiv_id and m.arxiv_id:
            source = source.model_copy(update={"arxiv_id": m.arxiv_id})
        if not source.year and m.year:
            source = source.model_copy(update={"year": m.year})
        if not source.venue and m.venue:
            # Trim trailing garbage como '\nREACT' que el regex de venue captura
            venue_clean = m.venue.split("\n")[0].strip()
            source = source.model_copy(update={"venue": venue_clean})
        if not source.authors and m.authors:
            source = source.model_copy(update={"authors": m.authors})
        if not source.pages:
            source = source.model_copy(update={"pages": pre.total_pages})
        if not source.url and m.arxiv_id:
            source = source.model_copy(
                update={"url": f"https://arxiv.org/abs/{m.arxiv_id}"}
            )
    else:
        source = SourceMeta(
            title=m.title or state.get("title") or Path(state["pdf_path"]).stem,
            authors=m.authors,
            year=m.year,
            venue=m.venue,
            arxiv_id=m.arxiv_id,
            url=f"https://arxiv.org/abs/{m.arxiv_id}" if m.arxiv_id else None,
            pdf_path=state["pdf_path"],
            pages=pre.total_pages,
        )
    extraction = PaperExtraction(
        source=source,
        classification=classification,
        summary=summary,
        benefit=state.get("benefit") or "(no generado)",
        key_metrics=state.get("key_metrics") or None,
        pitch_mapping=state.get("pitch_mapping"),
        provider=cfg.provider,
        model=cfg.model,
    )
    return {"extraction": extraction}


def build_extractor_graph() -> "CompiledStateGraph":  # type: ignore[name-defined]
    """Compila el grafo. Puede llamarse desde la CLI o desde un endpoint."""
    g: StateGraph = StateGraph(ExtractorState)

    g.add_node("preprocess", node_preprocess)
    g.add_node("classify", node_classify)
    g.add_node("motivation", node_extract_motivation)
    g.add_node("methodology", node_extract_methodology)
    g.add_node("materials", node_extract_materials)
    g.add_node("results", node_extract_results)
    g.add_node("key_metrics", node_extract_metrics)
    g.add_node("benefit", node_compute_benefit)
    g.add_node("consolidate", node_consolidate)

    g.add_edge(START, "preprocess")
    g.add_edge("preprocess", "classify")
    # Fan-out paralelo: 4 columnas + key_metrics corren simultáneamente
    for node in ("motivation", "methodology", "materials", "results", "key_metrics"):
        g.add_edge("classify", node)
        g.add_edge(node, "benefit")
    g.add_edge("benefit", "consolidate")
    g.add_edge("consolidate", END)

    return g.compile()


__all__ = ["ExtractorState", "build_extractor_graph", "node_consolidate", "node_preprocess"]
