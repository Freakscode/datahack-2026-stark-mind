"""Hybrid figure extractor for scientific PDFs.

Two passes per document:
  - Pass A: extract embedded raster images (page.get_images + doc.extract_image).
  - Pass B: detect 'Figure N:' / 'Table N:' captions in page text and render
            the adjacent region as PNG via page.get_pixmap(clip=bbox).
            When a Pass-A raster sits inside the caption region, we prefer
            the embedded raster for quality.

Output (default): stark-insight-forge/public/papers/<paper_id>/
  - manifest.json       (schema documented below)
  - figures/*.png       (one per detected figure/table)

Manifest schema:
  {
    "paper_id": str,
    "pdf_path": str,
    "extracted_at": "YYYY-MM-DD",
    "extractor": "pymupdf-hybrid-v1",
    "pages": int,
    "total_figures": int,
    "total_tables": int,
    "figures": [
      {
        "id": "figure-3" | "table-1",
        "kind": "figure" | "table",
        "number": int,
        "page": int,               # 1-indexed
        "bbox": [x0, y0, x1, y1],  # PDF points
        "method": "raster" | "vector",
        "filename": str,
        "caption": str,            # truncated to 500 chars
        "width": int,
        "height": int,
      }, ...
    ]
  }

Usage:
  # run on both default targets (react, agentic-rag)
  uv run python backend/scripts/extract_figures.py

  # or on a specific PDF
  uv run python backend/scripts/extract_figures.py path/to/paper.pdf --paper-id some-id
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import pymupdf as fitz

CAPTION_RE = re.compile(
    r"^\s*(Figure|Fig\.?|Table)\s+(\d+)(?:\s*[:\.]\s*(.{0,400}))?",
    re.IGNORECASE,
)

MIN_IMG_DIM = 80
MIN_REGION_HEIGHT = 40
SIDE_MARGIN = 18
VECTOR_DPI = 200
# Cuando el heurístico de body text deja una región demasiado fina (típico en
# papers con figuras de dos columnas o con párrafos justo encima del caption),
# abrimos la región a un porcentaje de la altura de la página hacia arriba.
FALLBACK_PAGE_FRACTION = 0.35
HEADER_OFFSET = 32  # reserve space for journal headers ("Published as..." etc.)


@dataclass
class FigureRecord:
    id: str
    kind: str
    number: int
    page: int
    bbox: tuple[float, float, float, float]
    method: str
    filename: str
    caption: str
    width: int
    height: int


def _dump_raw_embedded(doc, raw_dir: Path) -> list[dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    seen_xrefs: set[int] = set()
    results: list[dict] = []
    for pnum, page in enumerate(doc, start=1):
        for idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            base = doc.extract_image(xref)
            w, h = base["width"], base["height"]
            if w < MIN_IMG_DIM or h < MIN_IMG_DIM:
                continue
            rects = page.get_image_rects(xref)
            bbox = tuple(rects[0]) if rects else (0.0, 0.0, float(w), float(h))
            ext = base["ext"]
            filename = f"_raw_p{pnum}_i{idx}.{ext}"
            (raw_dir / filename).write_bytes(base["image"])
            results.append(
                {
                    "xref": xref,
                    "page": pnum,
                    "bbox": bbox,
                    "filename": filename,
                    "ext": ext,
                    "width": w,
                    "height": h,
                }
            )
    return results


def _detect_captions(page) -> list[dict]:
    captions: list[dict] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        lines = block.get("lines", [])
        if not lines:
            continue
        first_line = "".join(span["text"] for span in lines[0]["spans"]).strip()
        m = CAPTION_RE.match(first_line)
        if not m:
            continue
        kind = "table" if m.group(1).lower().startswith("tab") else "figure"
        number = int(m.group(2))
        full = " ".join(
            " ".join(span["text"] for span in line["spans"]) for line in lines
        ).strip()
        captions.append(
            {
                "kind": kind,
                "number": number,
                "text": full,
                "bbox": tuple(block["bbox"]),
            }
        )
    return captions


_CONTROL_CHARS = {c for c in range(0, 32) if c not in {9, 10, 13}}


def _is_body_text_block(block) -> bool:
    """Heuristic: a 'real' body-text block contains no control characters in its
    text and has ≥3 ASCII letters in its first line.

    Vector figures (TikZ from LaTeX) expose their labels as text blocks too, but
    those come back with 0x03 (ETX) and similar control bytes interleaved — the
    cipher used by the embedded font. We use that signal to discard
    figure-internal text from the region-boundary search.
    """
    full = "".join(
        span["text"]
        for line in block.get("lines", [])
        for span in line["spans"]
    )
    if any(ord(c) in _CONTROL_CHARS for c in full):
        return False
    letters = sum(1 for c in full[:200] if c.isascii() and c.isalpha())
    return letters >= 3


def _tight_bounds_above(page_rect, text_blocks, cy0) -> float:
    """Return the bottom y of the nearest body-text block strictly above y=cy0."""
    above_bottom = page_rect.y0
    for b in text_blocks:
        if not _is_body_text_block(b):
            continue
        _, _, _, by1 = b["bbox"]
        if by1 < cy0 - 4 and by1 > above_bottom:
            above_bottom = by1
    return above_bottom


def _tight_bounds_below(page_rect, text_blocks, cy1) -> float:
    """Return the top y of the nearest body-text block strictly below y=cy1."""
    below_top = page_rect.y1
    for b in text_blocks:
        if not _is_body_text_block(b):
            continue
        _, by0, _, _ = b["bbox"]
        if by0 > cy1 + 4 and by0 < below_top:
            below_top = by0
    return below_top


def _compute_region(page, caption, text_blocks) -> tuple[float, float, float, float]:
    """Compute the clip rect for the artifact associated with a caption.

    For figures: the artifact is conventionally above the caption.
    For tables: the convention is inconsistent (ReAct = below-artifact caption,
    Agentic RAG = above-artifact caption). We resolve by computing both regions
    and picking the one with more vertical room to hold the artifact.
    """
    page_rect = page.rect
    cx0, cy0, cx1, cy1 = caption["bbox"]
    left = page_rect.x0 + SIDE_MARGIN
    right = page_rect.x1 - SIDE_MARGIN
    fallback_height = page_rect.height * FALLBACK_PAGE_FRACTION

    def build_above() -> tuple[tuple[float, float, float, float], float]:
        tight_top = max(_tight_bounds_above(page_rect, text_blocks, cy0) + 4, page_rect.y0)
        top = tight_top
        if cy0 - top < MIN_REGION_HEIGHT:
            top = max(cy0 - fallback_height, page_rect.y0 + HEADER_OFFSET)
        bbox = (left, top, right, cy0 - 2)
        return bbox, bbox[3] - bbox[1]

    def build_below() -> tuple[tuple[float, float, float, float], float]:
        tight_bottom = min(_tight_bounds_below(page_rect, text_blocks, cy1) - 2, page_rect.y1)
        bottom = tight_bottom
        if bottom - cy1 < MIN_REGION_HEIGHT:
            bottom = min(cy1 + fallback_height, page_rect.y1 - HEADER_OFFSET)
        bbox = (left, cy1 + 2, right, bottom)
        return bbox, bbox[3] - bbox[1]

    if caption["kind"] == "figure":
        bbox, _ = build_above()
        return bbox

    # Tables: try both directions. Convention varies — ReAct puts captions below
    # the table, Agentic RAG puts them above. We resolve by counting how many
    # text blocks each candidate region contains: the side with more (smaller)
    # blocks is the table side (cells vs. paragraphs).
    above_bbox, above_h = build_above()
    below_bbox, below_h = build_below()

    def blocks_inside(bbox) -> int:
        x0, y0, x1, y1 = bbox
        return sum(
            1
            for b in text_blocks
            if b["bbox"][0] >= x0 - 4
            and b["bbox"][2] <= x1 + 4
            and b["bbox"][1] >= y0 - 4
            and b["bbox"][3] <= y1 + 4
        )

    above_n = blocks_inside(above_bbox)
    below_n = blocks_inside(below_bbox)
    # Ties (or both small) → prefer the side with more vertical room.
    if above_n == below_n:
        return above_bbox if above_h >= below_h else below_bbox
    return above_bbox if above_n > below_n else below_bbox


def _render_region(page, bbox, out_path: Path) -> tuple[int, int]:
    clip = fitz.Rect(bbox)
    mat = fitz.Matrix(VECTOR_DPI / 72, VECTOR_DPI / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    pix.save(out_path)
    return pix.width, pix.height


def _find_raster_inside(page_num: int, bbox, embedded) -> dict | None:
    x0, y0, x1, y1 = bbox
    best: dict | None = None
    best_area = 0.0
    for emb in embedded:
        if emb["page"] != page_num:
            continue
        ex0, ey0, ex1, ey1 = emb["bbox"]
        if ex0 >= x0 - 6 and ey0 >= y0 - 6 and ex1 <= x1 + 6 and ey1 <= y1 + 6:
            area = (ex1 - ex0) * (ey1 - ey0)
            if area > best_area:
                best_area = area
                best = emb
    return best


def _materialize_from_raster(src: Path, dst: Path, ext: str) -> None:
    """Mueve/convierte el raster crudo al destino final.

    Si `src` ya no existe (lo que ocurre cuando la misma embedded image fue
    reclamada por un caption anterior en la misma página), omitir silencioso.
    """
    if not src.exists():
        return
    if ext == "png":
        try:
            src.rename(dst)
        except FileNotFoundError:
            return
        return
    # convert to PNG via fitz
    pix = fitz.Pixmap(str(src))
    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    pix.save(dst)
    if src.exists():
        src.unlink()


def extract(pdf_path: Path, paper_id: str, output_root: Path) -> dict:
    out_dir = output_root / paper_id
    fig_dir = out_dir / "figures"
    if fig_dir.exists():
        shutil.rmtree(fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    embedded = _dump_raw_embedded(doc, fig_dir)

    records: list[FigureRecord] = []
    seen_ids: set[tuple[str, int]] = set()

    for pnum, page in enumerate(doc, start=1):
        text_blocks = [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]
        for cap in _detect_captions(page):
            key = (cap["kind"], cap["number"])
            if key in seen_ids:
                continue
            bbox = _compute_region(page, cap, text_blocks)
            if bbox[3] - bbox[1] < MIN_REGION_HEIGHT:
                continue
            seen_ids.add(key)

            fig_id = f"{cap['kind']}-{cap['number']}"
            filename = f"{fig_id}_p{pnum}.png"
            out_path = fig_dir / filename

            match = _find_raster_inside(pnum, bbox, embedded) if cap["kind"] == "figure" else None
            if match and match["width"] >= MIN_IMG_DIM * 2:
                src = fig_dir / match["filename"]
                _materialize_from_raster(src, out_path, match["ext"])
                method = "raster"
                width, height = match["width"], match["height"]
            else:
                width, height = _render_region(page, bbox, out_path)
                method = "vector"

            records.append(
                FigureRecord(
                    id=fig_id,
                    kind=cap["kind"],
                    number=cap["number"],
                    page=pnum,
                    bbox=tuple(round(v, 2) for v in bbox),
                    method=method,
                    filename=filename,
                    caption=cap["text"][:500],
                    width=width,
                    height=height,
                )
            )

    # cleanup orphan _raw_ files
    for f in fig_dir.glob("_raw_*"):
        f.unlink()

    manifest = {
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "extracted_at": date.today().isoformat(),
        "extractor": "pymupdf-hybrid-v1",
        "pages": doc.page_count,
        "total_figures": sum(1 for r in records if r.kind == "figure"),
        "total_tables": sum(1 for r in records if r.kind == "table"),
        "figures": [asdict(r) for r in records],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    doc.close()
    return manifest


DEFAULT_TARGETS: list[tuple[str, str]] = [
    ("backend/scripts/fixtures/react.pdf", "react"),
    ("backend/scripts/fixtures/agentic-rag.pdf", "agentic-rag"),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hybrid figure extractor for scientific PDFs (pymupdf).",
    )
    parser.add_argument("pdf_path", nargs="?", type=Path)
    parser.add_argument("--paper-id", type=str)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("stark-insight-forge/public/papers"),
    )
    args = parser.parse_args()

    if args.pdf_path:
        if not args.paper_id:
            parser.error("--paper-id is required when pdf_path is provided")
        targets: list[tuple[Path, str]] = [(args.pdf_path, args.paper_id)]
    else:
        targets = [(Path(p), pid) for p, pid in DEFAULT_TARGETS]

    for pdf_path, paper_id in targets:
        if not pdf_path.exists():
            print(f"✗ skipping {pdf_path} (not found)")
            continue
        manifest = extract(pdf_path, paper_id, args.output_root)
        print(
            f"✓ {paper_id}: {manifest['total_figures']} figs + "
            f"{manifest['total_tables']} tables → "
            f"{args.output_root}/{paper_id}/"
        )


if __name__ == "__main__":
    main()
