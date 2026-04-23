"""Synthesizer Agent — genera un Report markdown con citas inline (STUB)."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import emit, get_model_by_id
from app.agents.telemetry import compute_telemetry
from app.db.models import Chunk, Query, Report

SYNTH_MODEL_ID = "qwen2.5:7b-instruct"


def _build_body(
    chunks: list[Chunk], query_text: str
) -> tuple[str, str, str, list[dict[str, Any]]]:
    """Devuelve (title, summary, body_markdown, pending_citations)."""
    if not chunks:
        title = f"Respuesta a: {query_text[:60]}"
        summary = "No se encontraron fragmentos relevantes en el corpus indexado."
        body = (
            f"# {title}\n\n"
            "El pipeline no encontró chunks con similaridad suficiente.\n"
        )
        return title, summary, body, []

    title = f"Síntesis · {query_text[:60]}"
    summary = (
        f"Se sintetizan {len(chunks)} fragmentos de "
        f"{len({c.paper_id for c in chunks})} papers relevantes."
    )
    lines = [f"# {title}", "", summary, ""]
    citations: list[dict[str, Any]] = []

    for idx, chunk in enumerate(chunks, start=1):
        citations.append(
            {
                "citation_key": str(idx),
                "paper_id": chunk.paper_id,
                "chunk_id": chunk.id,
                "quote": chunk.text[:140],
                "page": chunk.page,
                "figure_ref": chunk.figure_ref,
            }
        )
        excerpt = chunk.text.strip().split(". ")[0]
        lines.append(f"- {excerpt} [{idx}]")

    lines.append("")
    lines.append("## Referencias")
    for c in citations:
        lines.append(f"- [{c['citation_key']}] paper `{c['paper_id']}` — p. {c['page'] or '—'}")

    return title, summary, "\n".join(lines), citations


async def draft_report(
    session: AsyncSession, query_id: UUID, chunks: list[Chunk]
) -> Report:
    """Crea un Report y guarda placeholders de citations en el state."""
    query: Query | None = await session.get(Query, query_id)
    if query is None:
        raise ValueError(f"Query not found: {query_id}")

    model = await get_model_by_id(session, SYNTH_MODEL_ID)

    await emit(
        session,
        query_id=query_id,
        agent="synthesizer",
        action="draft_report",
        status="started",
        payload={"chunks_in": len(chunks)},
    )

    input_tokens = max(1, sum(c.token_count or 0 for c in chunks))
    output_tokens = 180
    tel = compute_telemetry(model, input_tokens=input_tokens, output_tokens=output_tokens)

    if tel.get("latency_ms"):
        await asyncio.sleep(tel["latency_ms"] / 1000)

    title, summary, body, pending_citations = _build_body(chunks, query.query_text)

    report = Report(
        query_id=query_id,
        title=title,
        summary=summary,
        body_markdown=body,
        structured_output={"pending_citations": pending_citations},
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    await emit(
        session,
        query_id=query_id,
        agent="synthesizer",
        action="draft_report",
        status="completed",
        payload={
            "report_id": str(report.id),
            "claims": len(pending_citations),
            "chars": len(body),
        },
        telemetry=tel,
    )
    return report
