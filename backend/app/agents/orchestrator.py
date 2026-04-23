"""Orchestrator Agent — clasifica intent y registra el inicio del pipeline."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import emit, get_model_by_id
from app.agents.telemetry import compute_telemetry
from app.db.models import Query

ROUTER_MODEL_ID = "qwen2.5:7b-instruct"


async def route_intent(session: AsyncSession, query_id: UUID) -> str:
    """Clasifica el intent del query y actualiza la Query.

    Stub: siempre devuelve `qa`. Reemplazable por un clasificador basado en
    keywords o un LLM real cuando esté disponible.
    """
    query: Query | None = await session.get(Query, query_id)
    if query is None:
        raise ValueError(f"Query not found: {query_id}")

    model = await get_model_by_id(session, ROUTER_MODEL_ID)

    # --- emit started -------------------------------------------------------
    await emit(
        session,
        query_id=query_id,
        agent="orchestrator",
        action="route_intent",
        status="started",
        payload={"model": ROUTER_MODEL_ID},
    )

    # Aprox. tokens: input = chars/4, output = 15 (intent classification)
    input_tokens = max(1, len(query.query_text) // 4)
    output_tokens = 15
    tel = compute_telemetry(model, input_tokens=input_tokens, output_tokens=output_tokens)

    # Simula latencia del modelo local
    if tel.get("latency_ms"):
        await asyncio.sleep(tel["latency_ms"] / 1000)

    # Stub: heurística liviana para intent
    text = query.query_text.lower()
    if any(k in text for k in ("compara", "diferencia", "vs ")):
        intent = "compare"
    elif any(k in text for k in ("tendencia", "timeline", "últimos")):
        intent = "trend"
    elif any(k in text for k in ("lee", "deep", "profund")):
        intent = "deep_read"
    else:
        intent = "qa"

    query.intent = intent
    query.status = "running"
    await session.commit()

    await emit(
        session,
        query_id=query_id,
        agent="orchestrator",
        action="route_intent",
        status="completed",
        payload={"intent": intent},
        telemetry=tel,
    )
    return intent
