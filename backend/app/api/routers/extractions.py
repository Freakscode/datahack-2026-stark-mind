"""Router para upload + extracción de papers via UI.

Flujo asíncrono:
  1. POST /api/papers/extract — multipart(pdf, paper_id?) → guarda PDF, lanza
     extractor en BackgroundTask, devuelve 202 con paper_id y status=processing.
  2. GET /api/papers/{paper_id}/status → polling. Devuelve:
       - {status: "processing"} mientras corre
       - {status: "done", extraction: {...}} cuando el JSON está escrito
       - {status: "failed", error: "..."} si el grafo falló

El estado vive en memoria (dict) por simplicidad. Para producción se moverá a
Postgres o Redis, pero para el MVP del pitch con un usuario es suficiente.
"""
from __future__ import annotations

import logging
import re
import traceback
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/papers", tags=["extractions"])

# Raíz del proyecto = 3 niveles arriba de este archivo (backend/app/api/routers/..)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PAPERS_ROOT = PROJECT_ROOT / "stark-insight-forge" / "public" / "papers"

# Estado in-memory por paper_id → {status, error?, extraction?}
_JOBS: dict[str, dict] = {}

_SLUG_RE = re.compile(r"[^a-z0-9\-]+")
_ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)


def _slugify(name: str) -> str:
    stem = Path(name).stem.lower()
    s = _SLUG_RE.sub("-", stem).strip("-")
    return s or "paper"


def _extract_arxiv_id(raw: str) -> str | None:
    """Si raw es arXiv URL o ID, devuelve el ID canónico. None si no aplica."""
    m = _ARXIV_ID_RE.search(raw.strip())
    return m.group(1) if m else None


def _normalize_pdf_url(raw: str) -> tuple[str, str]:
    """Dada una URL/ID de arXiv o URL directa a PDF, devuelve (pdf_url, paper_id).

    - "2303.11366" → ("https://arxiv.org/pdf/2303.11366.pdf", "arxiv-2303-11366")
    - "https://arxiv.org/abs/2303.11366" → igual
    - "https://arxiv.org/pdf/2303.11366v2.pdf" → igual (canonical id sin versión)
    - URL PDF directa no-arXiv → (url, slug del basename)
    """
    raw = raw.strip()
    arxiv_id = _extract_arxiv_id(raw)
    if arxiv_id:
        paper_id = f"arxiv-{arxiv_id.replace('.', '-')}"
        return (f"https://arxiv.org/pdf/{arxiv_id}.pdf", paper_id)
    # URL directa a PDF (no-arXiv): usamos el basename
    if raw.startswith(("http://", "https://")):
        basename = raw.rstrip("/").split("/")[-1] or "paper.pdf"
        stem = Path(basename).stem or "paper"
        return (raw, _slugify(stem))
    # Input ambiguo: error
    raise ValueError(f"URL/ID no reconocido: {raw!r}")


class ExtractResponse(BaseModel):
    paper_id: str
    status: Literal["processing", "done", "failed"]
    pdf_url: str


class NodeEvent(BaseModel):
    node: str
    status: Literal["running", "done"]
    t: float


class StatusResponse(BaseModel):
    paper_id: str
    status: Literal["processing", "done", "failed"]
    error: str | None = None
    extraction: dict | None = None
    pdf_url: str | None = None
    events: list[NodeEvent] = []


# Nodos del grafo que nos interesa trackear (matchean los registrados en graph.py)
TRACKED_NODES = {
    "preprocess",
    "classify",
    "motivation",
    "methodology",
    "materials",
    "results",
    "key_metrics",
    "benefit",
    "consolidate",
}


def _append_event(paper_id: str, node: str, status: str) -> None:
    """Agrega un evento node-start/end al job actual sin reemplazar eventos previos."""
    import time

    job = _JOBS.get(paper_id)
    if not job:
        return
    evts = job.setdefault("events", [])
    evts.append({"node": node, "status": status, "t": time.time()})


async def _run_graph_with_events(paper_id: str, state: dict) -> dict:
    """Ejecuta el grafo vía astream_events y registra cada node-start/end.

    Para LangGraph, los nodos individuales emiten eventos on_chain_start y
    on_chain_end bajo su nombre registrado ('preprocess', 'classify', etc.).
    """
    from app.agents.extractor.graph import build_extractor_graph

    graph = build_extractor_graph()
    final_state: dict = {}
    async for event in graph.astream_events(state, version="v2"):
        event_name = event.get("event")
        name = event.get("name")
        if name not in TRACKED_NODES:
            continue
        if event_name == "on_chain_start":
            _append_event(paper_id, name, "running")
        elif event_name == "on_chain_end":
            _append_event(paper_id, name, "done")
            # Capturamos el state acumulado en cada node-end; el último contendrá
            # la extracción completa del nodo consolidate.
            output = event.get("data", {}).get("output") or {}
            if isinstance(output, dict):
                final_state.update(output)
    return final_state


def _run_extraction(pdf_path: Path, paper_id: str, out_dir: Path) -> None:
    """Corre el grafo extractor en un background task.

    Escribe extraction.json y actualiza el estado en _JOBS, y va emitiendo
    eventos de cada nodo para que el UI los muestre en tiempo real.
    """
    import asyncio
    import json

    from app.agents._paper_schema import SourceMeta
    from app.agents.llm_providers import DEFAULT_CONFIG

    try:
        state = {
            "pdf_path": str(pdf_path),
            "llm_config": DEFAULT_CONFIG,
            "source": SourceMeta(title=paper_id, pdf_path=str(pdf_path)),
        }
        loop = asyncio.new_event_loop()
        try:
            final = loop.run_until_complete(_run_graph_with_events(paper_id, state))
        finally:
            loop.close()

        extraction = final.get("extraction")
        if extraction is None:
            raise RuntimeError("El grafo terminó sin producir extraction (consolidate falló?)")

        out_dir.mkdir(parents=True, exist_ok=True)
        extraction_path = out_dir / "extraction.json"
        extraction_json = extraction.model_dump(mode="json")
        extraction_path.write_text(
            json.dumps(extraction_json, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        try:
            from scripts.extract_figures import extract as extract_figures

            extract_figures(pdf_path, paper_id, PAPERS_ROOT)
        except Exception as fig_err:  # noqa: BLE001
            logger.warning("figure extraction skipped: %s", fig_err)

        prev_events = _JOBS.get(paper_id, {}).get("events", [])
        _JOBS[paper_id] = {
            "status": "done",
            "extraction": extraction_json,
            "pdf_url": f"/papers/{paper_id}/paper.pdf",
            "events": prev_events,
        }
        logger.info("extraction done for %s (%d events)", paper_id, len(prev_events))
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        logger.error("extraction failed for %s: %s\n%s", paper_id, e, tb)
        prev_events = _JOBS.get(paper_id, {}).get("events", [])
        _JOBS[paper_id] = {
            "status": "failed",
            "error": f"{type(e).__name__}: {e}",
            "events": prev_events,
        }


@router.post("/extract", response_model=ExtractResponse, status_code=202)
async def extract_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    paper_id: str | None = Form(default=None),
) -> ExtractResponse:
    """Sube un PDF y lanza el extractor en background."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Se requiere un archivo PDF.")

    pid = paper_id.strip() if paper_id else _slugify(file.filename)
    pid = _slugify(pid)  # normaliza incluso si viene del usuario
    out_dir = PAPERS_ROOT / pid
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = out_dir / "paper.pdf"
    contents = await file.read()
    pdf_path.write_bytes(contents)
    logger.info("uploaded %s (%d bytes) as paper_id=%s", file.filename, len(contents), pid)

    _JOBS[pid] = {"status": "processing", "events": []}
    background_tasks.add_task(_run_extraction, pdf_path, pid, out_dir)

    return ExtractResponse(
        paper_id=pid,
        status="processing",
        pdf_url=f"/papers/{pid}/paper.pdf",
    )


class ExtractFromUrlRequest(BaseModel):
    url: str
    paper_id: str | None = None
    force: bool = False


@router.post("/extract-from-url", response_model=ExtractResponse, status_code=202)
async def extract_from_url(
    body: ExtractFromUrlRequest,
    background_tasks: BackgroundTasks,
) -> ExtractResponse:
    """Ingesta por URL: descarga el PDF (arXiv o URL directa) y lanza el pipeline.

    Matches the shape of Isabela's `extract_paper(pdf_url)` script but delega al
    mismo grafo LangGraph que /extract (upload manual).
    """
    try:
        pdf_url, auto_id = _normalize_pdf_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    pid = _slugify(body.paper_id) if body.paper_id else auto_id
    out_dir = PAPERS_ROOT / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "paper.pdf"

    extraction_path = out_dir / "extraction.json"
    if not body.force and extraction_path.exists():
        import json

        extraction_json = json.loads(extraction_path.read_text(encoding="utf-8"))
        _JOBS[pid] = {
            "status": "done",
            "extraction": extraction_json,
            "pdf_url": f"/papers/{pid}/paper.pdf",
            "events": [],
        }
        logger.info("cache hit for %s — skipping pipeline", pid)
        return ExtractResponse(
            paper_id=pid,
            status="done",
            pdf_url=f"/papers/{pid}/paper.pdf",
        )

    # Descarga sincrónica con timeout corto. Si el PDF es grande (>20MB) pymupdf
    # lo rechazará downstream, así que no hay razón para ser generosos aquí.
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(pdf_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not resp.content.startswith(b"%PDF"):
                raise HTTPException(
                    status_code=415,
                    detail=f"La URL no devolvió un PDF válido. Content-Type: {content_type}",
                )
            pdf_path.write_bytes(resp.content)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"No pude descargar el PDF: {e}") from e
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"La URL devolvió {e.response.status_code}",
        ) from e

    logger.info("downloaded %s (%d bytes) as paper_id=%s", pdf_url, pdf_path.stat().st_size, pid)

    _JOBS[pid] = {"status": "processing", "events": []}
    background_tasks.add_task(_run_extraction, pdf_path, pid, out_dir)

    return ExtractResponse(
        paper_id=pid,
        status="processing",
        pdf_url=f"/papers/{pid}/paper.pdf",
    )


@router.get("/{paper_id}/status", response_model=StatusResponse)
async def get_status(paper_id: str) -> StatusResponse:
    job = _JOBS.get(paper_id)
    if job is None:
        # Puede que el server reinició y el PDF + extraction.json estén en disco
        extraction_path = PAPERS_ROOT / paper_id / "extraction.json"
        if extraction_path.exists():
            import json

            return StatusResponse(
                paper_id=paper_id,
                status="done",
                extraction=json.loads(extraction_path.read_text()),
                pdf_url=f"/papers/{paper_id}/paper.pdf",
            )
        raise HTTPException(status_code=404, detail=f"paper_id '{paper_id}' no encontrado.")

    return StatusResponse(
        paper_id=paper_id,
        status=job["status"],
        error=job.get("error"),
        extraction=job.get("extraction"),
        pdf_url=job.get("pdf_url"),
        events=job.get("events", []),
    )


@router.get("/jobs")
async def list_jobs() -> dict[str, dict]:
    """Debug: lista todos los jobs in-memory."""
    return {k: {"status": v.get("status"), "error": v.get("error")} for k, v in _JOBS.items()}
