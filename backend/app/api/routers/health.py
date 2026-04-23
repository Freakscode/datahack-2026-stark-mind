"""Health + readiness probes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: el proceso está vivo."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    """Readiness: hay conexión a la DB y extensión vector disponible."""
    result = await session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
    version = result.scalar_one_or_none()
    return {
        "status": "ok" if version else "degraded",
        "pgvector": version or "missing",
    }
