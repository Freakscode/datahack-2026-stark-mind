"""Projects CRUD."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep
from app.db.models import Note, Project, ProjectPaper
from app.db.schemas import (
    NoteRead,
    ProjectCreate,
    ProjectPaperWithPaper,
    ProjectRead,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(session: SessionDep) -> list[Project]:
    """Lista todos los proyectos ordenados por fecha de creación descendente."""
    stmt = select(Project).order_by(Project.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, session: SessionDep) -> Project:
    """Crea un proyecto desde el formulario `/new` del frontend."""
    project = Project(
        topic=payload.topic,
        description=payload.description,
        status=payload.status,
        meta=payload.meta,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: UUID, session: SessionDep) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/{project_id}/papers", response_model=list[ProjectPaperWithPaper])
async def list_project_papers(project_id: UUID, session: SessionDep) -> list[ProjectPaper]:
    """Lista papers vinculados al proyecto con metadata completa del paper.

    Ordenados por `added_at` desc para que los últimos descubrimientos del
    Discovery Agent aparezcan primero en la UI.
    """
    stmt = (
        select(ProjectPaper)
        .options(selectinload(ProjectPaper.paper))
        .where(ProjectPaper.project_id == project_id)
        .order_by(ProjectPaper.added_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{project_id}/notes", response_model=list[NoteRead])
async def list_project_notes(project_id: UUID, session: SessionDep) -> list[Note]:
    stmt = (
        select(Note)
        .where(Note.project_id == project_id)
        .order_by(Note.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
