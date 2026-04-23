"""Gemini-based paper expansion: toma un paper extraído y genera N variaciones
temáticamente cercanas pero con énfasis distinto — sirve para poblar el mapa
latente con 50+ puntos sin esperar a que el usuario ingeste papers reales.

Cada variación sintética es un paper *verosímil* (título + abstract + autores
ficticios + año + keywords) que ocuparía una celda adyacente en el espacio
latente del paper base. El objetivo es que el mapa muestre clusters naturales
y huecos plausibles.

NOTA: Las variaciones se marcan `synthetic=True` en el output. El UI las
renderiza con un glifo diferente para que el usuario entienda que son
"vecindarios potenciales" no papers reales.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.services.gemini import generate_json

logger = logging.getLogger(__name__)

_PROMPT = """Eres un experto en literatura científica. Dada la información de un paper real,
genera exactamente {n} papers SINTÉTICOS plausibles que podrían existir en el mismo espacio
de investigación — variaciones temáticas cercanas pero con enfoques distintos.

Paper base:
- Título: {title}
- Abstract (motivación + metodología): {abstract}
- Dominio: {domain}
- Tipo: {paper_type}

Para cada paper sintético, genera un JSON con estos campos:
- title: string (título nuevo, plausible, 8-15 palabras)
- abstract: string (abstract de 3-5 frases con enfoque técnico distinto al base)
- year: int (entre {min_year} y {max_year})
- keywords: list[string] (4-6 keywords técnicos)
- enfoque: string (una frase describiendo qué hace DIFERENTE de los otros sintéticos; p.ej. "aplicación en biomédicos", "variante hardware-aware", "comparación empírica a escala")
- authors: list[string] (2-4 nombres ficticios plausibles)

Requisitos estrictos:
1. Los {n} papers deben cubrir enfoques VARIADOS — distribuir entre: teórico, empírico, survey, aplicación industrial, benchmark, extensión a otro dominio, optimización hardware.
2. NO copies frases del abstract base.
3. Usa vocabulario técnico real (LangGraph, attention, qubit, variational, RAG, etc. según corresponda).
4. Los años deben distribuirse entre {min_year} y {max_year}.

Devuelve UN solo JSON con la forma:
{{"papers": [...{n} objetos...]}}
"""


def expand_paper(
    paper_id: str,
    extraction: dict,
    *,
    n: int = 10,
    min_year: int = 2022,
    max_year: int = 2026,
) -> list[dict]:
    """Genera N papers sintéticos cercanos al extraction dado."""
    source = extraction.get("source", {})
    title = source.get("title", paper_id)
    classif = extraction.get("classification") or extraction.get("classify") or {}
    domain = classif.get("domain", "ai")
    paper_type = classif.get("paper_type", "empírico")

    # Extracto del abstract = motivación + primera línea de metodología
    summary = extraction.get("summary") or {}
    motivacion = summary.get("motivation", []) or []
    methodology = summary.get("methodology", []) or []
    abstract_bits: list[str] = []
    for m in motivacion[:2]:
        t = m.get("text") if isinstance(m, dict) else str(m)
        if t:
            abstract_bits.append(t[:300])
    for m in methodology[:1]:
        t = m.get("text") if isinstance(m, dict) else str(m)
        if t:
            abstract_bits.append(t[:300])
    abstract = " ".join(abstract_bits) or f"paper sobre {paper_type} en {domain}"

    prompt = _PROMPT.format(
        n=n,
        title=title,
        abstract=abstract,
        domain=domain,
        paper_type=paper_type,
        min_year=min_year,
        max_year=max_year,
    )
    try:
        result = generate_json(prompt)
    except Exception as e:  # noqa: BLE001
        logger.error("synthetic expansion failed for %s: %s", paper_id, e)
        return []

    papers_out = result.get("papers", []) if isinstance(result, dict) else []
    # Enriquecer con metadata del base
    for i, p in enumerate(papers_out):
        p["synthetic"] = True
        p["base_paper_id"] = paper_id
        p["id"] = f"syn-{paper_id}-{i:02d}"
        p.setdefault("domain", domain)
        p.setdefault("paper_type", paper_type)
    return papers_out[:n]


def persist_synthetic(papers_root: Path, base_id: str, papers: list[dict]) -> Path:
    """Guarda los sintéticos bajo PAPERS_ROOT/.synthetic/{base_id}.json."""
    synthetic_dir = papers_root / ".synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    out_path = synthetic_dir / f"{base_id}.json"
    out_path.write_text(
        json.dumps({"base_id": base_id, "papers": papers}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path


def load_all_synthetic(papers_root: Path) -> list[dict]:
    """Carga todas las variaciones sintéticas persistidas."""
    synthetic_dir = papers_root / ".synthetic"
    if not synthetic_dir.exists():
        return []
    out: list[dict] = []
    for f in synthetic_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out.extend(data.get("papers", []))
        except Exception as e:  # noqa: BLE001
            logger.warning("skip synthetic %s: %s", f.name, e)
    return out
