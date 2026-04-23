"""Cliente async de arXiv para el Discovery Agent.

Usa la API pública de arXiv (`http://export.arxiv.org/api/query`), que devuelve
Atom XML. Parseo mínimo con stdlib `xml.etree.ElementTree` — no hace falta lxml.

Contrato: `search(topic, max_results)` devuelve una lista de dicts con el
formato esperado por `Paper` del ORM (campos con el mismo nombre para que el
caller arme `Paper(**record)` directamente).

arXiv recomienda ≥3s entre requests. El rate limit se configura vía
`ARXIV_RATE_LIMIT` (segundos). El cliente también tolera caídas ocasionales:
los timeouts propagan excepción y el caller decide el fallback.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import date, datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

_WS_RE = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", text).strip()


def _parse_entry(entry: ET.Element) -> dict[str, Any] | None:
    """Convierte un `<entry>` de Atom en un dict listo para `Paper(**dict)`."""
    id_el = entry.find("atom:id", _NS)
    if id_el is None or not id_el.text:
        return None

    # id tiene la forma "http://arxiv.org/abs/2401.12345v2" — el id canónico
    # es "arxiv:2401.12345" sin versión. La source_id incluye el versioning.
    raw_id = id_el.text.strip()
    m = re.search(r"arxiv\.org/abs/([\w\.\-/]+?)(v\d+)?$", raw_id)
    if not m:
        return None
    arxiv_id = m.group(1)
    paper_id = f"arxiv:{arxiv_id}"

    title = _clean((entry.findtext("atom:title", namespaces=_NS) or "").strip())
    if not title:
        return None

    abstract = _clean(entry.findtext("atom:summary", namespaces=_NS) or "")

    authors = [
        _clean(name_el.text)
        for name_el in entry.findall("atom:author/atom:name", _NS)
        if name_el.text
    ]

    published_txt = entry.findtext("atom:published", namespaces=_NS) or ""
    published_at: date | None = None
    if published_txt:
        try:
            published_at = datetime.fromisoformat(
                published_txt.replace("Z", "+00:00")
            ).date()
        except ValueError:
            published_at = None

    # Links: abs (url) + pdf
    url: str | None = None
    pdf_url: str | None = None
    for link in entry.findall("atom:link", _NS):
        rel = link.attrib.get("rel", "alternate")
        href = link.attrib.get("href")
        typ = link.attrib.get("type", "")
        if not href:
            continue
        if rel == "alternate" and typ in ("text/html", ""):
            url = href
        elif link.attrib.get("title") == "pdf" or typ == "application/pdf":
            pdf_url = href

    doi_el = entry.find("arxiv:doi", _NS)
    doi = _clean(doi_el.text) if doi_el is not None else None

    primary_category_el = entry.find("arxiv:primary_category", _NS)
    primary_category = (
        primary_category_el.attrib.get("term") if primary_category_el is not None else None
    )

    categories = [
        cat.attrib.get("term", "")
        for cat in entry.findall("atom:category", _NS)
        if cat.attrib.get("term")
    ]

    return {
        "id": paper_id,
        "source": "arxiv",
        "title": title,
        "abstract": abstract or None,
        "authors": authors,
        "venue": "arXiv",
        "published_at": published_at,
        "doi": doi,
        "url": url,
        "pdf_url": pdf_url,
        "citations_count": None,
        "raw_metadata": {
            "arxiv_id": arxiv_id,
            "primary_category": primary_category,
            "categories": categories,
        },
    }


async def search(
    topic: str,
    *,
    max_results: int = 10,
    sort_by: str = "relevance",
    timeout_s: float = 12.0,
) -> list[dict[str, Any]]:
    """Busca en arXiv y devuelve papers normalizados.

    Args:
        topic: términos de búsqueda en lenguaje natural. Se envía tal cual al
            campo `all:` de arXiv (coincide en título + abstract + autores).
        max_results: tope duro por request (arXiv admite hasta 2000, pero con
            3s de rate limit no tiene sentido más de ~30 en un MVP).
        sort_by: "relevance" (default) | "lastUpdatedDate" | "submittedDate".
        timeout_s: timeout de red. Si expira, se propaga httpx.TimeoutException.

    Returns:
        Lista de dicts con shape compatible con `Paper(**record)`. Puede ser
        vacía si arXiv no encontró resultados.
    """
    if not topic.strip():
        return []

    rate_limit_s = float(os.environ.get("ARXIV_RATE_LIMIT", "3"))
    query = f"all:{topic.strip()}"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max(1, min(max_results, 30)),
        "sortBy": sort_by,
        "sortOrder": "descending",
    }

    logger.info(
        "arxiv.search topic=%r max_results=%d sort_by=%s",
        topic,
        params["max_results"],
        sort_by,
    )

    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
        resp = await client.get(ARXIV_API_URL, params=params)
        resp.raise_for_status()
        body = resp.text

    # Rate-limit polite
    if rate_limit_s > 0:
        await asyncio.sleep(rate_limit_s)

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        logger.error("arxiv: XML parse error — %s", exc)
        return []

    entries = root.findall("atom:entry", _NS)
    papers: list[dict[str, Any]] = []
    for entry in entries:
        record = _parse_entry(entry)
        if record:
            papers.append(record)

    logger.info("arxiv.search returned %d papers (of %d entries)", len(papers), len(entries))
    return papers


__all__ = ["search"]
