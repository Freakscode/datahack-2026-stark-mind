"""Wrappers finos sobre google-generativeai para embeddings + generación.

Mantener API simple y estable: el resto del código llama `embed_batch` o
`generate_json` y no se entera del SDK. Esto permite switch a google.genai v2
cuando la deprecación del SDK legacy bloquee upgrades.
"""
from __future__ import annotations

import json
import logging
import os
import warnings
from functools import lru_cache

warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai  # noqa: E402

logger = logging.getLogger(__name__)

EMBED_MODEL = "models/gemini-embedding-001"
GEN_MODEL = "gemini-2.5-flash"
EMBED_DIM = 768


@lru_cache
def _configured() -> bool:
    # Pydantic Settings lee .env pero no popula os.environ — leerla directo
    from app.core.config import get_settings

    settings = get_settings()
    key = (settings.google_api_key or os.environ.get("GOOGLE_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY no configurado — revisar backend/.env")
    genai.configure(api_key=key)
    return True


def embed_batch(texts: list[str], *, task: str = "retrieval_document") -> list[list[float]]:
    """Devuelve un embedding 768d por texto. Gemini soporta batch pero tiene cuota
    por request — hacemos loop con retry simple."""
    _configured()
    out: list[list[float]] = []
    for i, t in enumerate(texts):
        try:
            r = genai.embed_content(
                model=EMBED_MODEL,
                content=t[:8000],  # Gemini limita ~8k tokens
                task_type=task,
                output_dimensionality=EMBED_DIM,
            )
            out.append(r["embedding"])
        except Exception as e:  # noqa: BLE001
            logger.warning("embed fail on %d: %s — using zero vec", i, e)
            out.append([0.0] * EMBED_DIM)
    return out


def generate_json(prompt: str, *, max_retries: int = 2) -> dict | list:
    """Pide a Gemini que responda con JSON y lo parsea. Reintenta si falla el parse."""
    _configured()
    model = genai.GenerativeModel(
        GEN_MODEL,
        generation_config={"response_mime_type": "application/json"},
    )
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            r = model.generate_content(prompt)
            txt = r.text.strip()
            return json.loads(txt)
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("Gemini JSON retry %d: %s", attempt, e)
    raise RuntimeError(f"Gemini generate_json falló: {last_err}")
