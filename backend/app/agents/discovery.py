"""Discovery Agent — descubre papers relevantes (STUB).

STUB por ahora: si el proyecto ya tiene papers linked, los devuelve; si no,
toma los N papers más recientes globales y los linkea al proyecto.

Reemplazable por el adaptador arXiv + Google Scholar real (E3.1 · DAT-24).
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import emit
from app.db.models import Paper, ProjectPaper, Query

DEFAULT_K = 3
SIMULATED_LATENCY_MS = 320  # tiempo plausible de arXiv API


async def search_papers(session: AsyncSession, query_id: UUID) -> list[Paper]:
    """Devuelve papers asociados al proyecto; los linkea si no existían."""
    query: Query | None = await session.get(Query, query_id)
    if query is None:
        raise ValueError(f"Query not found: {query_id}")

    await emit(
        session,
        query_id=query_id,
        agent="discovery",
        action="search_papers",
        status="started",
        payload={"k": DEFAULT_K, "source": "arxiv-stub"},
    )

    await asyncio.sleep(SIMULATED_LATENCY_MS / 1000)

    # Papers ya linkeados al proyecto
    linked_stmt = (
        select(Paper)
        .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
        .where(ProjectPaper.project_id == query.project_id)
    )
    linked = list((await session.execute(linked_stmt)).scalars().all())

    if linked:
        papers = linked
    else:
        # Fallback: top-3 más recientes globales
        recent_stmt = (
            select(Paper).order_by(Paper.published_at.desc()).limit(DEFAULT_K)
        )
        papers = list((await session.execute(recent_stmt)).scalars().all())
        for p in papers:
            session.add(
                ProjectPaper(
                    project_id=query.project_id,
                    paper_id=p.id,
                    relevance_score=Decimal("0.85"),
                    added_by="discovery_agent",
                )
            )
        await session.commit()

    await emit(
        session,
        query_id=query_id,
        agent="discovery",
        action="search_papers",
        status="completed",
        payload={
            "results": len(papers),
            "paper_ids": [p.id for p in papers],
        },
        telemetry={"latency_ms": SIMULATED_LATENCY_MS},
    )
    return papers
