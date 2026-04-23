"""Helpers para persistir `AgentEvent` desde cualquier agente."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.telemetry import Telemetry
from app.db.models import AgentEvent


async def emit(
    session: AsyncSession,
    *,
    query_id: UUID,
    agent: str,
    action: str,
    status: str,
    payload: dict[str, Any] | None = None,
    telemetry: Telemetry | None = None,
) -> AgentEvent:
    """Crea y commitea un AgentEvent con telemetría opcional."""
    kwargs: dict[str, Any] = {
        "query_id": query_id,
        "agent": agent,
        "action": action,
        "status": status,
        "payload": payload or {},
    }
    if telemetry:
        for key in (
            "model_id",
            "input_tokens",
            "output_tokens",
            "tokens_per_second",
            "latency_ms",
            "cost_estimated_usd",
        ):
            if key in telemetry:
                kwargs[key] = telemetry[key]

    ev = AgentEvent(**kwargs)
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return ev


async def get_model_by_id(session: AsyncSession, model_id: str):
    """Helper para obtener un Model por id — se usa mucho en los agentes."""
    from app.db.models import Model  # evita import cíclico al cargar

    return await session.get(Model, model_id)
