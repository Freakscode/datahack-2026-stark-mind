"""Discovery Agent — descubre papers relevantes desde arXiv.

Flujo:
  1. Lee la Query (topic viene de `query.query_text`).
  2. Intenta fetch real a arXiv vía `arxiv_client.search`.
  3. Upserta los papers en `papers` (unique por `id`).
  4. Los linkea al proyecto vía `project_papers` si aún no existe el vínculo.
  5. Si arXiv falla o no devuelve nada, recae sobre los papers ya asociados
     al proyecto; como último recurso, top-3 más recientes globales.

Emite `AgentEvent` con la fuente real usada (arxiv | db-linked | db-recent)
para que el frontend pueda decidir si mostrar un banner de "degraded mode".
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import arxiv_client
from app.agents.events import emit
from app.db.models import Paper, ProjectPaper, Query

logger = logging.getLogger(__name__)

DEFAULT_K = 10


async def _upsert_paper(session: AsyncSession, record: dict) -> None:
    """Inserta o actualiza un paper según su `id`. No commitea."""
    stmt = (
        pg_insert(Paper)
        .values(**record)
        .on_conflict_do_update(
            index_elements=[Paper.id],
            set_={
                "title": record["title"],
                "abstract": record.get("abstract"),
                "authors": record.get("authors") or [],
                "url": record.get("url"),
                "pdf_url": record.get("pdf_url"),
                "doi": record.get("doi"),
                "published_at": record.get("published_at"),
                "raw_metadata": record.get("raw_metadata") or {},
            },
        )
    )
    await session.execute(stmt)


async def _link_papers_to_project(
    session: AsyncSession,
    project_id: UUID,
    paper_ids: list[str],
) -> None:
    """Crea ProjectPaper si no existe. No pisa relevance_score existente."""
    if not paper_ids:
        return
    for pid in paper_ids:
        stmt = (
            pg_insert(ProjectPaper)
            .values(
                project_id=project_id,
                paper_id=pid,
                relevance_score=Decimal("0.80"),
                added_by="discovery_agent",
            )
            .on_conflict_do_nothing(
                index_elements=["project_id", "paper_id"],
            )
        )
        await session.execute(stmt)


async def _fetch_linked_papers(
    session: AsyncSession, project_id: UUID
) -> list[Paper]:
    stmt = (
        select(Paper)
        .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
        .where(ProjectPaper.project_id == project_id)
        .order_by(ProjectPaper.added_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def search_papers(session: AsyncSession, query_id: UUID) -> list[Paper]:
    """Busca papers para la Query: arXiv primero, DB como fallback."""
    query: Query | None = await session.get(Query, query_id)
    if query is None:
        raise ValueError(f"Query not found: {query_id}")

    topic = (query.query_text or "").strip()

    await emit(
        session,
        query_id=query_id,
        agent="discovery",
        action="search_papers",
        status="started",
        payload={"k": DEFAULT_K, "source": "arxiv", "topic": topic},
    )

    source_used = "arxiv"
    fetched_records: list[dict] = []
    start = time.monotonic()

    if topic:
        try:
            fetched_records = await arxiv_client.search(topic, max_results=DEFAULT_K)
        except Exception as exc:  # noqa: BLE001 — fallback determinista
            logger.warning("arxiv fetch failed (%s) — falling back to DB", exc)
            fetched_records = []

    if fetched_records:
        for rec in fetched_records:
            await _upsert_paper(session, rec)
        await _link_papers_to_project(
            session, query.project_id, [r["id"] for r in fetched_records]
        )
        await session.commit()
        papers = await _fetch_linked_papers(session, query.project_id)
    else:
        # Fallback 1: papers ya vinculados al proyecto
        papers = await _fetch_linked_papers(session, query.project_id)
        source_used = "db-linked" if papers else "db-recent"

        if not papers:
            # Fallback 2: top-N más recientes globales — último recurso
            recent_stmt = (
                select(Paper).order_by(Paper.published_at.desc().nulls_last()).limit(DEFAULT_K)
            )
            papers = list((await session.execute(recent_stmt)).scalars().all())
            if papers:
                await _link_papers_to_project(
                    session, query.project_id, [p.id for p in papers]
                )
                await session.commit()

    latency_ms = int((time.monotonic() - start) * 1000)

    await emit(
        session,
        query_id=query_id,
        agent="discovery",
        action="search_papers",
        status="completed",
        payload={
            "results": len(papers),
            "source": source_used,
            "paper_ids": [p.id for p in papers],
        },
        telemetry={"latency_ms": latency_ms},
    )
    return papers
