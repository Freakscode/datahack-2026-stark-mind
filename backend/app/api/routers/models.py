"""Catálogo de modelos (LLM + embeddings, local + frontier mock)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep
from app.db.models import Model
from app.db.schemas import ModelRead

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelRead])
async def list_models(session: SessionDep) -> list[Model]:
    """Lista modelos activos ordenados por provider y kind."""
    stmt = (
        select(Model)
        .where(Model.is_active.is_(True))
        .order_by(Model.provider, Model.kind, Model.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
