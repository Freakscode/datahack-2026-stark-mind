"""Chatbot con contexto del proyecto — gemma4:26b local via Ollama.

El contexto se arma on-the-fly desde:
  1. Extracciones de los papers del proyecto (motivation + methodology + results snippet)
  2. Resumen del latent-map (clusters y gaps detectados)

Esto no es RAG "de verdad" (no hay retrieval semántico) — es prompt-stuffing
con citas estructuradas. Para el MVP con <20 papers por proyecto basta.

Si el chat tiene que escalar a cientos de papers, switch a:
  - Embeddings ya cacheados en latent_map → top-k similares a la query
  - Solo esos top-k se meten en el prompt
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.services.gemini import _configured as _gemini_configured

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Eres el asistente de investigación de STARK-VIX, un copiloto multiagente
para exploración de literatura científica. Respondes en español, de forma
concisa y técnica, citando papers específicos por su número de referencia
entre corchetes (ej. [2], [5]).

Reglas:
1. NUNCA inventes resultados numéricos. Si un número no aparece en el contexto,
   dí "no tengo ese dato en los papers cargados".
2. Cuando el usuario pregunte por "zonas vacías" o "gaps" del mapa latente,
   interpreta eso como oportunidades de investigación y sugiere combinaciones
   de técnicas de clusters existentes.
3. Si el usuario pide comparar papers, organiza la respuesta en tabla markdown.
4. Si no tienes contexto suficiente, dilo explícitamente — no alucines.
"""


def _extract_snippets(extraction: dict, *, max_bullets_per_col: int = 1) -> dict[str, list[str]]:
    """De un extraction.json saca los bullets más importantes por columna."""
    out: dict[str, list[str]] = {}
    summary = extraction.get("summary") or {}
    for col in ("motivation", "methodology", "materials", "results"):
        items = summary.get(col, []) or []
        bullets: list[str] = []
        for it in items[:max_bullets_per_col]:
            if isinstance(it, dict):
                t = it.get("text") or ""
                anchor = it.get("anchor") or ""
                if t:
                    bullets.append(f"{t[:160]} [{anchor}]" if anchor else t[:160])
            elif isinstance(it, str):
                bullets.append(it[:160])
        out[col] = bullets
    return out


def build_context_block(extractions: list[dict], latent_summary: dict | None) -> str:
    """Arma el contexto textual que se inyecta al system prompt."""
    parts: list[str] = []
    parts.append("### PAPERS CARGADOS EN EL PROYECTO\n")
    for i, ext in enumerate(extractions, start=1):
        src = ext.get("source", {}) or {}
        title = src.get("title", f"paper-{i}")
        snippets = _extract_snippets(ext)
        parts.append(f"[{i}] {title}")
        for col, bullets in snippets.items():
            if bullets:
                parts.append(f"  {col}:")
                for b in bullets:
                    parts.append(f"    - {b}")
        # Añade key_metrics y benefit de golpe
        metrics = ext.get("key_metrics", []) or []
        if metrics:
            parts.append("  key_metrics:")
            for m in metrics[:2]:
                if isinstance(m, dict):
                    parts.append(f"    - {m.get('name','')}: {m.get('value','')} {m.get('unit','')} [{m.get('anchor','')}]")
        benefit = ext.get("benefit") or ""
        if benefit:
            parts.append(f"  benefit: {benefit[:180]}")
        parts.append("")

    if latent_summary:
        parts.append("### MAPA LATENTE (UMAP 2D)")
        clusters = latent_summary.get("clusters", [])
        parts.append(f"- {len(clusters)} clusters detectados")
        for c in clusters:
            kws = ", ".join(c.get("keywords", [])[:4])
            parts.append(f"  · cluster {c['id']}: [{kws}] ({c['count']} papers)")
        gaps = latent_summary.get("gaps", [])
        if gaps:
            parts.append(f"- {len(gaps)} gaps detectados (áreas vacías rodeadas de densidad)")
        stats = latent_summary.get("stats", {})
        parts.append(
            f"- total {stats.get('total', 0)} puntos "
            f"({stats.get('real', 0)} reales, {stats.get('synthetic', 0)} sintéticos)"
        )
        parts.append("")
    return "\n".join(parts)


def answer(
    question: str,
    extractions: list[dict],
    latent_summary: dict | None = None,
) -> str:
    """Respuesta sincrónica usando gemini-2.5-flash (demo: latencia <3s).

    Nota de arquitectura: el procesamiento principal (extracción multiagente)
    corre en gemma4:26b local. Para el chat del pitch usamos Gemini por
    velocidad — la lógica del prompt y contexto es la misma.
    """
    import warnings

    warnings.filterwarnings("ignore", category=FutureWarning)
    import google.generativeai as genai

    _gemini_configured()

    ctx = build_context_block(extractions, latent_summary)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{ctx}\n\n### PREGUNTA\n{question}"
    logger.info("chat invoke — %d chars context, question=%r", len(ctx), question[:80])

    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(full_prompt)
    return (resp.text or "(sin respuesta)").strip()


def load_project_extractions(papers_root: Path, paper_ids: list[str]) -> list[dict]:
    """Carga los extraction.json de los papers del proyecto."""
    import json

    out: list[dict] = []
    for pid in paper_ids:
        p = papers_root / pid / "extraction.json"
        if p.exists():
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception as e:  # noqa: BLE001
                logger.warning("skip extraction %s: %s", pid, e)
    return out
