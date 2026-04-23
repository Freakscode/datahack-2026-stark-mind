"""Router de latent-map + chat para proyectos.

Endpoints:
  - POST /api/projects/{project_id}/expand     → genera N sintéticos por paper
  - GET  /api/projects/{project_id}/latent-map → devuelve UMAP + clusters + gaps
  - POST /api/projects/{project_id}/chat       → pregunta al proyecto
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.routers.extractions import PAPERS_ROOT
from app.services.chat import answer, load_project_extractions
from app.services.latent_map import build_latent_map
from app.services.synthetic_papers import expand_paper, load_all_synthetic, persist_synthetic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["latent"])

_CACHE_DIR = PAPERS_ROOT / ".cache"
_EMBED_CACHE = _CACHE_DIR / "embeddings.json"


class ExpandRequest(BaseModel):
    paper_ids: list[str]
    n_per_paper: int = 10


class ExpandResponse(BaseModel):
    generated: int
    papers_expanded: list[str]
    skipped: list[str]


@router.post("/{project_id}/expand", response_model=ExpandResponse)
async def expand(project_id: str, body: ExpandRequest) -> ExpandResponse:
    """Para cada paper_id, genera n_per_paper variantes sintéticas con Gemini."""
    expanded: list[str] = []
    skipped: list[str] = []
    total = 0
    for pid in body.paper_ids:
        extraction_path = PAPERS_ROOT / pid / "extraction.json"
        if not extraction_path.exists():
            skipped.append(pid)
            continue
        try:
            extraction = json.loads(extraction_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            logger.warning("bad extraction %s: %s", pid, e)
            skipped.append(pid)
            continue
        papers = expand_paper(pid, extraction, n=body.n_per_paper)
        if not papers:
            skipped.append(pid)
            continue
        persist_synthetic(PAPERS_ROOT, pid, papers)
        expanded.append(pid)
        total += len(papers)
    return ExpandResponse(generated=total, papers_expanded=expanded, skipped=skipped)


class LatentMapResponse(BaseModel):
    points: list[dict]
    clusters: list[dict]
    gaps: list[dict]
    stats: dict


@router.get("/{project_id}/latent-map", response_model=LatentMapResponse)
async def get_latent_map(project_id: str, paper_ids: str | None = None) -> LatentMapResponse:
    """Construye el mapa latente a partir de los papers del proyecto + sintéticos.

    paper_ids: lista separada por comas de IDs de papers reales (del schema del
    proyecto). Si no se pasa, incluye TODOS los extraction.json + sintéticos
    que haya en disco.
    """
    ids_filter: set[str] | None = None
    if paper_ids:
        ids_filter = {p.strip() for p in paper_ids.split(",") if p.strip()}

    # 1) Papers reales
    points: list[dict] = []
    for paper_dir in PAPERS_ROOT.iterdir():
        if not paper_dir.is_dir() or paper_dir.name.startswith("."):
            continue
        if ids_filter and paper_dir.name not in ids_filter:
            continue
        ext_path = paper_dir / "extraction.json"
        if not ext_path.exists():
            continue
        try:
            ext = json.loads(ext_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        src = ext.get("source", {}) or {}
        classif = ext.get("classification") or {}
        summary = ext.get("summary") or {}
        motivation = summary.get("motivation", []) or []
        methodology = summary.get("methodology", []) or []
        abstract_bits = [m.get("text", "") for m in motivation[:2] if isinstance(m, dict)]
        abstract_bits += [m.get("text", "") for m in methodology[:1] if isinstance(m, dict)]
        # fallback: si todo vacío, usa title + domain + paper_type para embedding
        if not any(abstract_bits):
            abstract_bits = [
                f"{classif.get('domain','')} {classif.get('paper_type','')} {classif.get('category','')}"
            ]
        points.append({
            "id": paper_dir.name,
            "title": src.get("title", paper_dir.name),
            "abstract": " ".join(abstract_bits)[:1200],
            "domain": classif.get("domain", "ai"),
            "paper_type": classif.get("paper_type", ""),
            "year": classif.get("year"),
            "synthetic": False,
        })

    # 2) Sintéticos (solo los asociados a papers del filtro, si hay filtro)
    synthetic = load_all_synthetic(PAPERS_ROOT)
    for s in synthetic:
        if ids_filter and s.get("base_paper_id") not in ids_filter:
            continue
        points.append({
            "id": s.get("id"),
            "title": s.get("title", ""),
            "abstract": s.get("abstract", ""),
            "domain": s.get("domain", "ai"),
            "paper_type": s.get("paper_type", ""),
            "year": s.get("year"),
            "synthetic": True,
            "base_paper_id": s.get("base_paper_id"),
        })

    if not points:
        raise HTTPException(404, "No hay papers para construir el mapa")

    result = build_latent_map(points, _EMBED_CACHE)
    return LatentMapResponse(**result)


class ChatRequest(BaseModel):
    question: str
    paper_ids: list[str] = []
    include_latent_summary: bool = True


class ChatResponse(BaseModel):
    answer: str
    context_chars: int
    papers_used: int


@router.post("/{project_id}/chat", response_model=ChatResponse)
async def chat(project_id: str, body: ChatRequest) -> ChatResponse:
    """Responde la pregunta usando extracciones de los papers indicados."""
    extractions = load_project_extractions(PAPERS_ROOT, body.paper_ids)
    if not extractions and not body.paper_ids:
        raise HTTPException(400, "Indica al menos un paper_id en el proyecto")

    latent_summary = None
    if body.include_latent_summary and len(extractions) >= 2:
        try:
            # Mini-summary: solo clusters y gaps (sin refacer el map completo)
            ids = ",".join(body.paper_ids)
            lm = await get_latent_map(project_id, ids)
            latent_summary = {
                "clusters": lm.clusters,
                "gaps": lm.gaps,
                "stats": lm.stats,
            }
        except Exception as e:  # noqa: BLE001
            logger.warning("skip latent summary: %s", e)

    try:
        reply = answer(body.question, extractions, latent_summary)
    except Exception as e:  # noqa: BLE001
        logger.exception("chat failed")
        raise HTTPException(500, f"chat error: {e}") from e

    ctx_chars = sum(len(str(e)) for e in extractions)
    return ChatResponse(answer=reply, context_chars=ctx_chars, papers_used=len(extractions))
