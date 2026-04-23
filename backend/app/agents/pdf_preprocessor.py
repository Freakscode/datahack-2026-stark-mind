"""PDF → texto estructurado por secciones.

Objetivo: producir un dict de secciones canónicas (intro, método, materiales,
resultados, related, conclusión, referencias, appendix) que los nodos del
grafo puedan consumir sin leer el PDF completo.

Estrategia:
  1. Extraer texto con pymupdf (por bloque, con coordenadas).
  2. Detectar headings numerados ("1 Introduction", "2.1 Setup", etc.) usando
     regex + heurísticas de tamaño de fuente.
  3. Asignar cada bloque al heading más reciente.
  4. Canonicalizar: mapear títulos heterogéneos ("Intro", "Introduction",
     "Background", "Motivation") a ids estándar (`introduction`, `methods`,
     `materials`, `results`, `related_work`, `conclusion`, `references`,
     `appendix`).
  5. Fallback: si no se detectan headings, segmentar por tercios.

Salida:
    PaperPreprocessed(
      sections=[Section(id, title, level, pages, text), ...],
      captions=[Caption(kind, number, text, anchor, page), ...],  # ya se usa el manifest del pymupdf
      full_text=str,  # utilidad
      total_pages=int,
    )

El extractor usa `route_sections_to_columns()` para obtener los excerpts que
cada nodo necesita.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz

# Heading patterns:
#   'N\nTITLE'   (ICLR small-caps: "2\nREACT: SYNERGIZING REASONING + ACTING")
#   'N.M\nTitle' (arXiv default title-case: "2.1\nOverview of Retrieval-Augmented Generation (RAG)")
#   'N TITLE'    (one-line variant)
# El título acepta ALL-CAPS o Title-Case. pymupdf concatena líneas de un mismo
# bloque con '\n'.
NUMBERED_HEADING_RE = re.compile(
    r"""
    ^\s*
    (?P<num>\d{1,2}(?:\.\d{1,2}){0,2})   # 1 | 2.1 | 3.1.2
    [\s\n]+                               # espacio o newline
    (?P<title>[A-Z][A-Za-z0-9&\+\-\:\s\/\'\.\(\)]{2,95}?)   # TITULO o Title Case
    \s*$
    """,
    re.VERBOSE | re.MULTILINE | re.DOTALL,
)

# Chars que delatan texto TikZ con encoding corrupto (cipher de la fuente
# embebida). Si un bloque los contiene, NO es un heading legítimo.
_CONTROL_CHARS = frozenset({c for c in range(0, 32) if c not in {9, 10, 13}})


def _has_control_chars(text: str) -> bool:
    return any(ord(c) in _CONTROL_CHARS for c in text)

# Headings sin numeración: Abstract, References, Acknowledgments, etc.
UNNUMBERED_HEADING_TITLES = {
    "abstract": "abstract",
    "references": "references",
    "bibliography": "references",
    "acknowledgments": "acknowledgments",
    "acknowledgements": "acknowledgments",
    "ethics statement": "ethics_statement",
    "reproducibility statement": "reproducibility_statement",
    "appendix": "appendix",
    "appendices": "appendix",
    "supplementary material": "appendix",
}

# Canonical section → substrings que, si aparecen en el título normalizado
# (lowercase, sin espacios ni puntuación), cuentan como match.
# Orden importa: se evalúan de más específico a más general.
CANONICAL_SUBSTRINGS: list[tuple[str, str]] = [
    ("reproducibility", "reproducibility_statement"),
    ("ethics", "ethics_statement"),
    ("acknowledgment", "acknowledgments"),
    ("acknowledgement", "acknowledgments"),
    ("relatedwork", "related_work"),
    ("priorwork", "related_work"),
    ("literature", "related_work"),
    ("stateoftheart", "related_work"),
    ("references", "references"),
    ("bibliography", "references"),
    ("appendix", "appendix"),
    ("appendices", "appendix"),
    ("supplementary", "appendix"),
    ("introduction", "introduction"),
    ("background", "introduction"),
    ("overview", "introduction"),
    ("motivation", "motivation"),
    ("methodology", "methods"),
    ("approach", "methods"),
    ("method", "methods"),  # matches "Methods" y "Method"
    ("paradigm", "methods"),
    ("framework", "methods"),
    ("architecture", "methods"),
    ("design", "methods"),
    ("setup", "materials"),
    ("dataset", "materials"),
    ("actionspace", "materials"),
    ("taxonomy", "materials"),
    ("scope", "materials"),
    ("implementation", "materials"),
    ("results", "results"),
    ("observations", "results"),
    ("experiments", "results"),
    ("evaluations", "results"),
    ("evaluation", "results"),
    ("findings", "results"),
    ("empirical", "results"),
    ("comparative", "results"),
    ("analysis", "results"),
    ("lessonslearned", "results"),  # en surveys las "lessons" son los resultados clave
    ("openresearch", "results"),
    ("openchallenges", "discussion"),
    ("discussion", "discussion"),
    ("limitations", "discussion"),
    ("practicalguidance", "discussion"),
    ("futurework", "conclusion"),
    ("futuredirections", "conclusion"),
    ("conclusion", "conclusion"),
    ("summary", "conclusion"),
]


@dataclass
class Section:
    id: str  # canonical id ("introduction", "methods", ...) o "section_3_2" si no hubo match
    title: str  # título original del paper ("3.2 Evaluation Setup")
    level: int  # 1 para §3, 2 para §3.2, 3 para §3.2.1
    page_start: int
    page_end: int
    text: str

    def token_estimate(self) -> int:
        """Estimación cruda para budget: 1 token ≈ 4 chars en-es."""
        return max(1, len(self.text) // 4)


@dataclass
class Caption:
    kind: str  # "figure" | "table"
    number: int
    text: str
    anchor: str
    page: int


@dataclass
class TableRegion:
    """Texto adyacente a un caption de Table N, donde viven los datos numéricos.

    Lo usa el nodo `results` y el nodo dedicado `key_metrics`. La dirección
    (arriba o abajo del caption) se resuelve por densidad de bloques — mismo
    heurístico que `extract_figures.py`.
    """

    number: int
    caption: str
    text: str                # contenido de la región sin el caption
    anchor: str              # "Table 3"
    page: int                # 1-indexed

    def token_estimate(self) -> int:
        return max(1, len(self.text) // 4)


@dataclass
class PaperMetadata:
    """Metadata bibliográfica extraída de la primera página."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    arxiv_id: str | None = None
    arxiv_version: str | None = None
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None


@dataclass
class PaperPreprocessed:
    pdf_path: str
    total_pages: int
    sections: list[Section] = field(default_factory=list)
    captions: list[Caption] = field(default_factory=list)
    table_regions: list[TableRegion] = field(default_factory=list)
    metadata: PaperMetadata = field(default_factory=PaperMetadata)
    full_text: str = ""
    fallback_used: bool = False

    def section_by_id(self, sid: str) -> Section | None:
        for s in self.sections:
            if s.id == sid:
                return s
        return None

    def sections_by_ids(self, sids: list[str]) -> list[Section]:
        return [s for s in self.sections if s.id in sids]


CAPTION_RE = re.compile(
    r"^\s*(Figure|Fig\.?|Table)\s+(\d+)(?:\s*[:\.]\s*(.{0,400}))?",
    re.IGNORECASE,
)


def _extract_table_regions(doc) -> list[TableRegion]:
    """Por cada caption 'Table N', extrae el texto de la región adyacente.

    Heurísticos:
      1. Caption puede estar arriba del cuerpo (Agentic RAG) o abajo (ICLR-style).
      2. La región correcta es la que tiene MÁS bloques de texto cercanos
         (tablas con muchas celdas vs. párrafos densos con pocos bloques).
      3. Si hay OTRO caption de tabla en la misma página, dividimos por X-range
         del caption para manejar layouts side-by-side (ReAct p8 Table 3 izq,
         Table 4 der) — evita que ambas tablas aspiren el mismo texto.
      4. Se limita a 50% de la altura de página para no tragar páginas enteras.
    """
    out: list[TableRegion] = []
    seen: set[int] = set()

    # Primer pase: detectamos todos los captions por página para saber cuándo
    # hay varios que compiten por el mismo espacio.
    captions_by_page: dict[int, list[dict]] = {}
    for pnum, page in enumerate(doc, start=1):
        page_caps: list[dict] = []
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            if not lines:
                continue
            first_line = "".join(s["text"] for s in lines[0]["spans"]).strip()
            m = re.match(r"^\s*Table\s+(\d+)", first_line, re.IGNORECASE)
            if not m:
                continue
            num = int(m.group(1))
            if num in seen:
                continue
            full = " ".join(
                " ".join(s["text"] for s in line["spans"]) for line in lines
            ).strip()
            page_caps.append(
                {
                    "num": num,
                    "block": block,
                    "bbox": block["bbox"],
                    "caption_text": full[:300],
                }
            )
        if page_caps:
            captions_by_page[pnum] = page_caps

    for pnum, page_caps in captions_by_page.items():
        page = doc[pnum - 1]
        page_rect = page.rect
        text_blocks_raw = [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]
        fallback_span = page_rect.height * 0.5

        # ¿Tenemos tablas side-by-side en esta página?
        side_by_side = len(page_caps) > 1 and _are_side_by_side(page_caps)

        for cap in page_caps:
            num = cap["num"]
            if num in seen:
                continue
            seen.add(num)
            block = cap["block"]
            cx0, cy0, cx1, cy1 = cap["bbox"]

            # X-range de la región: por defecto página completa, pero si hay
            # side-by-side usamos el X del caption ± margen.
            if side_by_side:
                margin = (cx1 - cx0) * 0.3 + 15  # 30% del ancho del caption + margen
                region_x0 = max(page_rect.x0 + 4, cx0 - margin)
                region_x1 = min(page_rect.x1 - 4, cx1 + margin)
            else:
                region_x0 = page_rect.x0 + 10
                region_x1 = page_rect.x1 - 10

            # Candidatas arriba/abajo
            above_bbox = (
                region_x0,
                max(cy0 - fallback_span, page_rect.y0 + 30),
                region_x1,
                cy0 - 2,
            )
            below_bbox = (
                region_x0,
                cy1 + 2,
                region_x1,
                min(cy1 + fallback_span, page_rect.y1 - 30),
            )

            def _count_and_text(bbox, skip_block) -> tuple[int, str]:
                x0, y0, x1, y1 = bbox
                blocks_in = [
                    b
                    for b in text_blocks_raw
                    if b["bbox"][0] >= x0 - 4
                    and b["bbox"][2] <= x1 + 4
                    and b["bbox"][1] >= y0 - 4
                    and b["bbox"][3] <= y1 + 4
                    and b is not skip_block
                ]
                collected = []
                for b in blocks_in:
                    block_text = " ".join(
                        " ".join(s["text"] for s in line["spans"])
                        for line in b.get("lines", [])
                    ).strip()
                    if not block_text or _has_control_chars(block_text):
                        continue
                    collected.append(block_text)
                return len(collected), "\n".join(collected)

            above_count, above_text = _count_and_text(above_bbox, block)
            below_count, below_text = _count_and_text(below_bbox, block)
            if above_count == below_count:
                chosen_text = above_text if len(above_text) >= len(below_text) else below_text
            else:
                chosen_text = above_text if above_count > below_count else below_text

            out.append(
                TableRegion(
                    number=num,
                    caption=cap["caption_text"],
                    text=chosen_text[:4000],
                    anchor=f"Table {num}",
                    page=pnum,
                )
            )
    return out


def _are_side_by_side(captions_on_page: list[dict]) -> bool:
    """True si hay ≥2 captions con Y cercano (diferencia < 50pt) y X disjunto."""
    if len(captions_on_page) < 2:
        return False
    bboxes = [c["bbox"] for c in captions_on_page]
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            ax0, ay0, ax1, ay1 = bboxes[i]
            bx0, by0, bx1, by1 = bboxes[j]
            y_mid_a = (ay0 + ay1) / 2
            y_mid_b = (by0 + by1) / 2
            # Si Y-diff es pequeña y los X-ranges no se solapan sustancialmente
            if abs(y_mid_a - y_mid_b) < 50 and (ax1 < bx0 + 20 or bx1 < ax0 + 20):
                return True
    return False


def _extract_captions(doc) -> list[Caption]:
    captions: list[Caption] = []
    seen: set[tuple[str, int]] = set()
    for pnum, page in enumerate(doc, start=1):
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            if not lines:
                continue
            first = "".join(s["text"] for s in lines[0]["spans"]).strip()
            m = CAPTION_RE.match(first)
            if not m:
                continue
            kind = "table" if m.group(1).lower().startswith("tab") else "figure"
            num = int(m.group(2))
            if (kind, num) in seen:
                continue
            seen.add((kind, num))
            full = " ".join(
                " ".join(s["text"] for s in line["spans"]) for line in lines
            ).strip()
            anchor = f"Fig. {num}" if kind == "figure" else f"Table {num}"
            captions.append(Caption(kind=kind, number=num, text=full[:400], anchor=anchor, page=pnum))
    return captions


def _classify_heading(title: str) -> str | None:
    """Devuelve el id canónico si el título matchea por substring, o None.

    Robusto contra artifactos de small-caps que fragmentan palabras: normaliza
    a lowercase + solo letras/dígitos y busca substrings canónicos.
    """
    normalized = "".join(c.lower() for c in title if c.isalnum())
    for substring, canon in CANONICAL_SUBSTRINGS:
        if substring in normalized:
            return canon
    return None


def _detect_section_headings(doc) -> list[tuple[int, int, int, str, str]]:
    """Devuelve (page, y_top, level, title_raw, canonical_or_sectionN).

    Estrategias (en orden):
      1. `get_text('blocks')` con regex multiline que captura 'N\\nTITLE' (ICLR).
      2. Headings sin numeración por lookup en UNNUMBERED_HEADING_TITLES.
      3. Las sub-secciones (3.1, 3.2) se capturan naturalmente por la misma regex.
    """
    out: list[tuple[int, int, int, str, str]] = []
    for pnum, page in enumerate(doc, start=1):
        # get_text('blocks') devuelve [(x0, y0, x1, y1, text, block_no, block_type), ...]
        for b in page.get_text("blocks"):
            if len(b) < 6:
                continue
            x0, y0, _x1, _y1, text, _bno = b[:6]
            if len(b) >= 7 and b[6] != 0:
                continue
            text_stripped = text.strip()
            if not text_stripped or len(text_stripped) > 250:
                # Headings largos no existen; bloques de >250 chars son párrafos.
                continue
            if _has_control_chars(text_stripped):
                # Texto TikZ con encoding corrupto — no es un heading real.
                continue
            if _is_noise_block(text_stripped):
                # Datos tabulares, numeración suelta, fragmentos sin contexto.
                continue

            # 1) Numbered heading
            m = NUMBERED_HEADING_RE.match(text_stripped)
            if m:
                num = m.group("num")
                title_raw = _clean_smallcaps_artifacts(m.group("title"))
                level = num.count(".") + 1
                canon = _classify_heading(title_raw) or f"section_{num.replace('.', '_')}"
                out.append((pnum, int(y0), level, f"{num} {title_raw}", canon))
                continue

            # 2) Unnumbered common heading (Abstract, References, etc.)
            normalized = text_stripped.lower().strip(":. ")
            if normalized in UNNUMBERED_HEADING_TITLES:
                canon = UNNUMBERED_HEADING_TITLES[normalized]
                out.append((pnum, int(y0), 1, text_stripped, canon))
                continue

            # 3) Fallback: un solo bloque en mayúsculas con <= 6 palabras
            if (
                text_stripped.isupper()
                and 4 <= len(text_stripped) <= 60
                and 1 <= len(text_stripped.split()) <= 6
            ):
                canon = _classify_heading(text_stripped) or f"section_{len(out)}"
                out.append((pnum, int(y0), 1, text_stripped, canon))

    # Dedupe: la primera aparición se queda con el id canónico; las siguientes
    # que colisionan se re-etiquetan como section_{num_o_ordinal} para no
    # perder el contenido (esencial en surveys donde §5, §8 y §11 pueden
    # compartir canónicos por palabras clave genéricas).
    seen: set[str] = set()
    dedup: list[tuple[int, int, int, str, str]] = []
    fallback_counter = 0
    for item in sorted(out, key=lambda h: (h[0], h[1])):
        page, y, level, title, canon = item
        if canon.startswith("section_") or canon not in seen:
            dedup.append(item)
            seen.add(canon)
            continue
        # Colisión: re-etiquetamos como section_N para preservar el contenido.
        fallback_id = _derive_numeric_section_id(title, fallback_counter)
        if fallback_id is None:
            fallback_counter += 1
            fallback_id = f"section_dup_{fallback_counter}"
        dedup.append((page, y, level, title, fallback_id))
    return dedup


def _derive_numeric_section_id(title: str, counter: int) -> str | None:
    """Intenta extraer el número de la sección del título ('8 Tools and...' → section_8)."""
    m = re.match(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,2})\s+", title)
    if m:
        return f"section_{m.group(1).replace('.', '_')}"
    return None


def _clean_smallcaps_artifacts(text: str) -> str:
    """Normaliza títulos small-caps extraídos de PDFs LaTeX.

    Casos típicos que pymupdf genera al extraer fuentes small-caps:
      - 'REAC T' → 'REACT'          (ligadura parcial)
      - 'R E A CT' → 'REACT'        (cada letra emitida por separado)
      - 'SYNERGIZINGR EASONING' → 'SYNERGIZING REASONING' (kerning)
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    # Caso 1: join letra-sola mayúscula con siguiente token mayúscula.
    # "R E A CT" → "REACT"
    tokens = cleaned.split()
    merged: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        # Si token es letra sola uppercase y el siguiente empieza con uppercase,
        # consumimos consecutivos para reconstruir la palabra.
        while (
            i + 1 < len(tokens)
            and len(t) == 1
            and t.isupper()
            and tokens[i + 1]
            and tokens[i + 1][0].isupper()
        ):
            t = t + tokens[i + 1]
            i += 1
        merged.append(t)
        i += 1
    cleaned = " ".join(merged)
    # Caso 2: palabra terminando en ALL-CAPS seguida de 1-2 letras mayúsculas
    # al final del título. "REAC T" → "REACT". Solo se aplica si la cola corta
    # es SEGUIDA por puntuación o fin de string (evita fusionar títulos con
    # siglas cortas como "USING AI MODELS").
    cleaned = re.sub(r"\b([A-Z]{3,})\s+([A-Z]{1,2})(?=[:\.\s]|$)", r"\1\2", cleaned)
    # No intentamos resolver "SYNERGIZINGR EASONING" o "RESULT SAND" a nivel
    # de string — confiamos en `_classify_heading` que normaliza el título
    # completo y busca substrings canónicos. Eso tolera los artifactos mejor
    # que cualquier heurística de separación.
    return cleaned


def _is_noise_block(text: str) -> bool:
    """True si el bloque es ruido (números de tabla, fragmentos de página, etc.)."""
    if not text:
        return True
    # >70% dígitos/whitespace/punctuación numérica = datos tabulares
    digits = sum(1 for c in text if c.isdigit() or c in " \t\n.,%")
    if digits / len(text) > 0.7:
        return True
    # Sin espacios ni letras = ruido
    if not any(c.isalpha() for c in text):
        return True
    return False


def _build_sections(doc, headings: list[tuple[int, int, int, str, str]]) -> list[Section]:
    """Asigna todo el texto del documento al heading previo más cercano."""
    if not headings:
        return []
    # Flatten todos los bloques con su posición absoluta (page, y_top).
    ordered_headings = sorted(headings, key=lambda h: (h[0], h[1]))
    bounds = [(h[0], h[1]) for h in ordered_headings]

    # Texto por heading
    buckets: list[list[str]] = [[] for _ in ordered_headings]
    page_span: list[tuple[int, int]] = [(h[0], h[0]) for h in ordered_headings]

    for pnum, page in enumerate(doc, start=1):
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            y_top = int(block["bbox"][1])
            # encontrar el último heading cuyo (page, y) ≤ (pnum, y_top)
            idx = -1
            for i, (hp, hy) in enumerate(bounds):
                if (hp, hy) <= (pnum, y_top):
                    idx = i
                else:
                    break
            if idx == -1:
                continue
            lines = block.get("lines", [])
            if not lines:
                continue
            text = " ".join(
                " ".join(s["text"] for s in line["spans"]) for line in lines
            ).strip()
            if not text:
                continue
            buckets[idx].append(text)
            ps, pe = page_span[idx]
            page_span[idx] = (ps, max(pe, pnum))

    sections: list[Section] = []
    for i, (pnum, _, level, title_raw, canon) in enumerate(ordered_headings):
        ps, pe = page_span[i]
        sections.append(
            Section(
                id=canon,
                title=title_raw,
                level=level,
                page_start=ps,
                page_end=pe,
                text="\n".join(buckets[i]),
            )
        )
    return sections


def _fallback_thirds(doc) -> list[Section]:
    """Si no hay headings detectados, segmenta el texto en 3 tercios."""
    all_text: list[tuple[int, str]] = []
    for pnum, page in enumerate(doc, start=1):
        all_text.append((pnum, page.get_text("text").strip()))
    total_chars = sum(len(t) for _, t in all_text)
    if total_chars == 0:
        return []
    per_third = total_chars / 3
    thirds: list[list[tuple[int, str]]] = [[], [], []]
    acc = 0
    for pnum, t in all_text:
        bucket = min(int(acc / per_third), 2)
        thirds[bucket].append((pnum, t))
        acc += len(t)

    out: list[Section] = []
    for i, label in enumerate(["first_third", "middle_third", "last_third"]):
        if not thirds[i]:
            continue
        pstart = thirds[i][0][0]
        pend = thirds[i][-1][0]
        out.append(
            Section(
                id=label,
                title=label.replace("_", " ").title(),
                level=1,
                page_start=pstart,
                page_end=pend,
                text="\n\n".join(t for _, t in thirds[i]),
            )
        )
    return out


_ARXIV_WATERMARK_RE = re.compile(
    r"arXiv:(?P<id>\d{4}\.\d{4,5})(?:v(?P<v>\d+))?\s*\[[\w\.\-]+\]\s*(?P<date>\d{1,2}\s+\w+\s+\d{4})?"
)
_VENUE_RE = re.compile(
    r"(?:Published\s+as\s+a\s+conference\s+paper\s+at|Accepted\s+at|Proceedings\s+of)\s+(?P<venue>[A-Z][\w\s&\-\']{2,80})",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\{?[a-z][\w\.\-]*(?:,[\w\.\-]+)*\}?@[\w\.\-]+")


def _extract_metadata(doc) -> PaperMetadata:
    """Parse la primera página para extraer title, authors, arxiv_id, venue.

    Estrategia:
      - title: bloque con fontsize máximo en la mitad superior de p1.
      - authors: bloque(s) entre title y abstract, con >2 comas o "and".
      - arxiv_id: regex sobre full text del doc completo.
      - venue: "Published as ... at VENUE" o "Accepted at VENUE".
      - abstract: entre heading "ABSTRACT" y el siguiente heading/párrafo grande.
    """
    meta = PaperMetadata()
    if doc.page_count == 0:
        return meta

    first_page = doc[0]
    full_text = "\n".join(p.get_text("text") for p in doc[:2])  # primeras 2 páginas

    # arXiv watermark
    m = _ARXIV_WATERMARK_RE.search(full_text)
    if m:
        meta.arxiv_id = m.group("id")
        if m.group("v"):
            meta.arxiv_version = f"v{m.group('v')}"
        if m.group("date"):
            date_str = m.group("date")
            for tok in date_str.split():
                if tok.isdigit() and len(tok) == 4:
                    meta.year = int(tok)
                    break

    # Venue
    m = _VENUE_RE.search(full_text[:3000])
    if m:
        venue = m.group("venue").strip().rstrip(".,")
        meta.venue = venue
        # Year en la línea del venue
        after = full_text[m.end() : m.end() + 40]
        ym = re.search(r"\b(19|20)\d{2}\b", after)
        if ym and not meta.year:
            meta.year = int(ym.group(0))

    # Title: bloque con mayor font size en la mitad superior de p1.
    # Excluye arXiv watermark (texto rotado 90° en el borde izquierdo, suele
    # contener "arXiv:" literal).
    blocks = first_page.get_text("dict")["blocks"]
    page_h = first_page.rect.height
    page_w = first_page.rect.width
    candidates: list[tuple[float, float, str]] = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        y_top = b["bbox"][1]
        x_left = b["bbox"][0]
        if y_top > page_h * 0.45:
            continue
        for line in b.get("lines", []):
            spans = line["spans"]
            if not spans:
                continue
            sz = max(s["size"] for s in spans)
            text = " ".join(s["text"] for s in spans).strip()
            if not text or len(text) > 200:
                continue
            # Reject watermarks: "arXiv:..." literal, text in left margin strip.
            if "arXiv:" in text or text.startswith("arxiv"):
                continue
            if x_left < page_w * 0.08:  # texto en margen izquierdo = watermark rotado
                continue
            if _has_control_chars(text):
                continue
            if sz >= 12 and len(text) >= 8:
                candidates.append((sz, y_top, text))
    if candidates:
        # Max size, tiebreak: topmost
        candidates.sort(key=lambda c: (-c[0], c[1]))
        top_size = candidates[0][0]
        title_lines = [c[2] for c in candidates if abs(c[0] - top_size) < 0.2]
        meta.title = _clean_smallcaps_artifacts(" ".join(title_lines))

    # Authors: primer bloque después del título que contiene "@", comas o "and"
    # Capturamos todo texto de p1 ordenado por y
    p1_text_blocks: list[tuple[float, str]] = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        y = b["bbox"][1]
        text = " ".join(
            " ".join(s["text"] for s in line["spans"]) for line in b.get("lines", [])
        ).strip()
        if text:
            p1_text_blocks.append((y, text))
    p1_text_blocks.sort()

    for y, text in p1_text_blocks:
        if meta.title and text.startswith(meta.title[:20]):
            continue
        if y < 80:  # encabezado/arxiv watermark
            continue
        if "@" in text or _EMAIL_RE.search(text):
            # bloque de emails → authors ya pasaron
            break
        if text.isupper() and len(text) < 20:
            continue
        if 20 <= len(text) <= 400 and ("," in text or " and " in text or " AND " in text):
            names = [n.strip() for n in re.split(r",|\band\b", text) if n.strip()]
            names = [n for n in names if 2 <= len(n.split()) <= 5 and n[0].isalpha()]
            if len(names) >= 2:
                meta.authors = [re.sub(r"[\d\*\†\‡\§\¶\#]+$", "", n).strip() for n in names][:20]
                break

    # Abstract
    abstract_start = full_text.lower().find("abstract")
    if abstract_start != -1:
        rest = full_text[abstract_start + len("abstract") :].lstrip(": \n")
        # Cortar en el primer '1 INTRODUCTION' o '1\nINTRODUCTION' o bloque con mayúsculas
        end_match = re.search(r"\n\s*\d+(?:\.\d+)?[\s\n]+[A-Z][A-Z\s&\+\-]{3,80}", rest)
        if end_match:
            meta.abstract = rest[: end_match.start()].strip()[:2000]
        else:
            meta.abstract = rest[:2000].strip()

    return meta


def preprocess_pdf(pdf_path: str | Path) -> PaperPreprocessed:
    pdf_path = str(pdf_path)
    doc = fitz.open(pdf_path)
    try:
        metadata = _extract_metadata(doc)
        headings = _detect_section_headings(doc)
        sections = _build_sections(doc, headings)
        fallback = False
        if not sections:
            sections = _fallback_thirds(doc)
            fallback = True
        captions = _extract_captions(doc)
        table_regions = _extract_table_regions(doc)
        full_text = "\n\n".join(page.get_text("text") for page in doc)
        return PaperPreprocessed(
            pdf_path=pdf_path,
            total_pages=doc.page_count,
            sections=sections,
            captions=captions,
            table_regions=table_regions,
            metadata=metadata,
            full_text=full_text,
            fallback_used=fallback,
        )
    finally:
        doc.close()


# Routing por tipo de paper.
# Empirical = paper con experimentos propios (ReAct, Kim 2025).
# Survey = revisión analítica/narrativa (Agentic RAG).
# Para theoretical/dataset/tutorial/opinion, fallback a "empirical".
SECTION_ROUTING: dict[str, dict[str, list[str]]] = {
    "empirical": {
        "motivation": ["introduction", "motivation", "related_work"],
        "methodology": ["methods", "section_2", "section_3"],
        "materials": ["materials", "methods", "appendix"],
        "results": ["results", "discussion", "conclusion"],
    },
    "survey": {
        "motivation": ["introduction", "motivation"],
        # En surveys el "método" es la taxonomía y el framework de análisis.
        "methodology": ["methods", "section_2", "section_3", "section_5"],
        # En surveys los "materiales" son el scope: frameworks/benchmarks.
        "materials": ["materials", "section_8", "section_11"],
        # Resultados + lessons learned + challenges.
        "results": ["results", "discussion", "section_10", "section_12"],
    },
}


def route_sections_to_columns(
    pre: PaperPreprocessed,
    column: str,
    paper_type: str = "empírico",
) -> list[Section]:
    """Devuelve las secciones del paper relevantes para una columna.

    Routing por `paper_type`:
      - "empírico", "teórico", "dataset" → mapeo empirical (con experimentos propios).
      - "survey", "tutorial", "opinión" → mapeo survey (taxonomía + scope).

    Si ninguna match por id canónico, fallback a primeros headings detectados.
    """
    survey_types = {"survey", "tutorial", "opinión"}
    routing = SECTION_ROUTING["survey"] if paper_type in survey_types else SECTION_ROUTING["empirical"]
    wanted = routing.get(column, [])
    matched = [s for s in pre.sections if s.id in wanted]
    if matched:
        return matched

    # Fallback por tercio si el PDF no tenía estructura
    if pre.fallback_used:
        thirds_map = {
            "motivation": ["first_third"],
            "methodology": ["first_third", "middle_third"],
            "materials": ["middle_third"],
            "results": ["last_third", "middle_third"],
        }
        ids = thirds_map.get(column, ["first_third"])
        return [s for s in pre.sections if s.id in ids]

    # Último recurso: primeras secciones detectadas
    return pre.sections[:3]


__all__ = [
    "Caption",
    "PaperMetadata",
    "PaperPreprocessed",
    "SECTION_ROUTING",
    "Section",
    "TableRegion",
    "preprocess_pdf",
    "route_sections_to_columns",
]
