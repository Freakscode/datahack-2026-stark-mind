"""Runner del pipeline multi-agente.

Flujo lineal: orchestrator → discovery → reader → synthesizer → citation_guard.
Cada agente emite eventos en `agent_events` consumidos por SSE.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.agents import citation_guard, discovery, orchestrator, reader, synthesizer
from app.agents.events import emit
from app.core.db import SessionLocal
from app.db.models import Query

logger = logging.getLogger(__name__)


async def run_pipeline(query_id: UUID) -> None:
    """Ejecuta el pipeline completo para una Query.

    Se corre como BackgroundTask — no bloquea la respuesta del POST.
    """
    async with SessionLocal() as session:
        try:
            await orchestrator.route_intent(session, query_id)
            papers = await discovery.search_papers(session, query_id)
            chunks = await reader.retrieve_chunks(session, query_id, papers)
            report = await synthesizer.draft_report(session, query_id, chunks)
            await citation_guard.validate_citations(session, query_id, report)

            query: Query | None = await session.get(Query, query_id)
            if query is not None:
                query.status = "completed"
                query.completed_at = datetime.now(timezone.utc)
                await session.commit()

        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("Pipeline failed for query %s", query_id)
            async with SessionLocal() as error_session:
                query: Query | None = await error_session.get(Query, query_id)
                if query is not None:
                    query.status = "failed"
                    query.error = str(exc)
                    await error_session.commit()
                await emit(
                    error_session,
                    query_id=query_id,
                    agent="orchestrator",
                    action="pipeline_failed",
                    status="failed",
                    payload={"error": str(exc)},
                )
            raise
