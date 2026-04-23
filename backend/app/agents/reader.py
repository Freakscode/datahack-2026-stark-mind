"""Reader/RAG Agent — recupera chunks relevantes (STUB sin embeddings reales)."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import emit, get_model_by_id
from app.agents.telemetry import compute_telemetry
from app.db.models import Chunk, Paper

EMBEDDING_MODEL_ID = "bge-large-en-v1.5"
SIMULATED_LATENCY_MS = 180


async def retrieve_chunks(
    session: AsyncSession,
    query_id: UUID,
    papers: list[Paper],
    *,
    top_k: int = 5,
) -> list[Chunk]:
    """Recupera los top_k chunks de los papers descubiertos.

    STUB: como no hay embeddings reales del query (E3.4 · DAT-27), tomamos los
    primeros chunks de los papers. Cuando estén los embeddings, el query pasa a
    ser `ORDER BY embedding <=> :query_vector LIMIT :k`.
    """
    model = await get_model_by_id(session, EMBEDDING_MODEL_ID)

    await emit(
        session,
        query_id=query_id,
        agent="reader",
        action="retrieve_chunks",
        status="started",
        payload={"top_k": top_k, "paper_ids": [p.id for p in papers]},
    )

    await asyncio.sleep(SIMULATED_LATENCY_MS / 1000)

    if not papers:
        chunks: list[Chunk] = []
    else:
        paper_ids = [p.id for p in papers]
        stmt = (
            select(Chunk)
            .where(Chunk.paper_id.in_(paper_ids))
            .order_by(Chunk.paper_id, Chunk.chunk_index)
            .limit(top_k)
        )
        chunks = list((await session.execute(stmt)).scalars().all())

    tel = compute_telemetry(
        model,
        input_tokens=sum(c.token_count or 0 for c in chunks) or None,
        output_tokens=None,
        extra_latency_ms=SIMULATED_LATENCY_MS,
    )

    await emit(
        session,
        query_id=query_id,
        agent="reader",
        action="retrieve_chunks",
        status="completed",
        payload={
            "chunks_retrieved": len(chunks),
            "papers_hit": list({c.paper_id for c in chunks}),
        },
        telemetry=tel,
    )
    return chunks
