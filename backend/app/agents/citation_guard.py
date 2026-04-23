"""Citation-Guard Agent — valida citas y persiste la tabla `citations`.

STUB: valida que el `chunk_id` exista y marca `verified=true`. Reemplazable
por entailment classifier real (DeBERTa-v3 etc.) cuando se implemente.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import emit, get_model_by_id
from app.agents.telemetry import compute_telemetry
from app.db.models import Citation, Report

GUARD_MODEL_ID = "gemini-2.5-flash"


async def validate_citations(session: AsyncSession, query_id: UUID, report: Report) -> Report:
    """Crea registros en `citations` y calcula scores del report."""
    model = await get_model_by_id(session, GUARD_MODEL_ID)
    pending = report.structured_output.get("pending_citations", [])

    await emit(
        session,
        query_id=query_id,
        agent="citation_guard",
        action="validate_citations",
        status="started",
        payload={"claims": len(pending)},
    )

    input_tokens = max(1, len(pending) * 40)
    output_tokens = max(1, len(pending) * 10)
    tel = compute_telemetry(model, input_tokens=input_tokens, output_tokens=output_tokens)

    if tel.get("latency_ms"):
        await asyncio.sleep(tel["latency_ms"] / 1000)

    verified_count = 0
    rejected_count = 0
    for c in pending:
        # STUB: si tenemos chunk_id, se considera válida.
        verified = bool(c.get("chunk_id"))
        if verified:
            verified_count += 1
        else:
            rejected_count += 1

        session.add(
            Citation(
                report_id=report.id,
                citation_key=str(c["citation_key"]),
                paper_id=c["paper_id"],
                chunk_id=c.get("chunk_id"),
                quote=c.get("quote"),
                page=c.get("page"),
                figure_ref=c.get("figure_ref"),
                verified=verified,
                verified_at=datetime.now(timezone.utc) if verified else None,
            )
        )

    # Limpia el bloque pending y actualiza scores
    structured = dict(report.structured_output)
    structured.pop("pending_citations", None)
    structured["citation_stats"] = {"verified": verified_count, "rejected": rejected_count}
    report.structured_output = structured

    total = max(1, verified_count + rejected_count)
    report.citation_accuracy_score = Decimal(verified_count) / Decimal(total)
    report.groundedness_score = Decimal("0.9") * (Decimal(verified_count) / Decimal(total))
    report.faithfulness_score = Decimal("0.92") * (Decimal(verified_count) / Decimal(total))

    await session.commit()

    await emit(
        session,
        query_id=query_id,
        agent="citation_guard",
        action="validate_citations",
        status="completed",
        payload={
            "verified": verified_count,
            "rejected": rejected_count,
            "citation_accuracy": float(report.citation_accuracy_score),
        },
        telemetry=tel,
    )
    return report
