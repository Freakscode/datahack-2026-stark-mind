"""Queries router: POST para disparar pipeline + GET SSE para streamear eventos."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.agents.pipeline import run_pipeline
from app.api.deps import SessionDep
from app.core.db import SessionLocal
from app.db.models import AgentEvent, Project, Query, Report
from app.db.schemas import (
    AgentEventStream,
    QueryCreate,
    QueryRead,
    ReportRead,
)

router = APIRouter(tags=["queries"])

POLL_INTERVAL_SECONDS = 0.25
HEARTBEAT_INTERVAL_SECONDS = 15


# =============================================================================
# POST /projects/{project_id}/queries — dispara el pipeline en background
# =============================================================================
@router.post(
    "/projects/{project_id}/queries",
    response_model=QueryRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_query(
    project_id: UUID,
    payload: QueryCreate,
    background: BackgroundTasks,
    session: SessionDep,
) -> Query:
    project: Project | None = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    query = Query(
        project_id=project_id,
        query_text=payload.query_text,
        query_type=payload.query_type,
        execution_mode=payload.execution_mode,
        status="pending",
    )
    session.add(query)
    await session.commit()
    await session.refresh(query)

    background.add_task(run_pipeline, query.id)
    return query


# =============================================================================
# GET /queries/{query_id} — detalle de una query
# =============================================================================
@router.get("/queries/{query_id}", response_model=QueryRead)
async def get_query(query_id: UUID, session: SessionDep) -> Query:
    query: Query | None = await session.get(Query, query_id)
    if query is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Query not found")
    return query


# =============================================================================
# GET /queries/{query_id}/report — report con citations verificadas
# =============================================================================
@router.get("/queries/{query_id}/report", response_model=ReportRead)
async def get_report(query_id: UUID, session: SessionDep) -> Report:
    stmt = select(Report).where(Report.query_id == query_id)
    report = (await session.execute(stmt)).scalar_one_or_none()
    if report is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Report not yet available"
        )
    return report


# =============================================================================
# GET /queries/{query_id}/events  (SSE)
# =============================================================================
@router.get("/queries/{query_id}/events")
async def stream_events(query_id: UUID):
    async def generator() -> AsyncGenerator[dict, None]:
        last_event_id = 0
        heartbeat_ticker = 0

        while True:
            async with SessionLocal() as session:
                # ¿existe la query?
                query: Query | None = await session.get(Query, query_id)
                if query is None:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": "query_not_found"}),
                    }
                    return

                # Traer eventos nuevos
                stmt = (
                    select(AgentEvent)
                    .where(
                        AgentEvent.query_id == query_id,
                        AgentEvent.id > last_event_id,
                    )
                    .order_by(AgentEvent.id.asc())
                )
                events = list((await session.execute(stmt)).scalars().all())

                for ev in events:
                    stream_payload = AgentEventStream.model_validate(ev).model_dump(
                        by_alias=True, mode="json"
                    )
                    yield {
                        "event": "agent",
                        "id": str(ev.id),
                        "data": json.dumps(stream_payload, default=str),
                    }
                    last_event_id = ev.id

                # ¿terminó el pipeline?
                if query.status in ("completed", "failed"):
                    yield {
                        "event": "done",
                        "data": json.dumps(
                            {"status": query.status, "error": query.error}
                        ),
                    }
                    return

            # Heartbeat para que el cliente sepa que el túnel sigue vivo
            heartbeat_ticker += 1
            if heartbeat_ticker * POLL_INTERVAL_SECONDS >= HEARTBEAT_INTERVAL_SECONDS:
                yield {"event": "ping", "data": "{}"}
                heartbeat_ticker = 0

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    return EventSourceResponse(generator())
