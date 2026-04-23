"""CLI del extractor de papers.

Uso:
    # Dry-run: muestra todos los prompts que se enviarían al LLM sin invocarlo.
    uv run --project backend --extra agents python backend/scripts/run_extractor.py \\
        backend/scripts/fixtures/react.pdf --paper-id react --dry-run

    # Invocación real (requiere Ollama corriendo + modelo pulled).
    uv run --project backend --extra agents python backend/scripts/run_extractor.py \\
        backend/scripts/fixtures/react.pdf --paper-id react --invoke

    # Con otro provider:
    ... --provider anthropic --model claude-opus-4-7 --invoke
    ... --provider ollama --model gemma2:9b --invoke   (si quieres cambiar de 27b)

Output (--invoke):
    backend/scripts/fixtures/<paper_id>.extraction.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Permitir `python backend/scripts/run_extractor.py` sin entrar a backend/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents._paper_schema import PaperExtraction, SourceMeta  # noqa: E402
from app.agents.extractor.graph import build_extractor_graph  # noqa: E402
from app.agents.extractor.nodes import COLUMN_LABELS  # noqa: E402
from app.agents.extractor.prompts import (  # noqa: E402
    format_valid_anchors,
    render_benefit,
    render_classify,
    render_extract_column,
)
from app.agents.llm_providers import LLMConfig, check_ollama_health  # noqa: E402
from app.agents.pdf_preprocessor import preprocess_pdf, route_sections_to_columns  # noqa: E402


def _render_dry_run(pdf_path: Path, title: str) -> str:
    """Imprime lo que cada nodo enviaría al LLM, sin llamarlo."""
    pre = preprocess_pdf(pdf_path)
    out: list[str] = []
    out.append(f"=== Preprocesado ===")
    out.append(f"PDF: {pdf_path}  ({pre.total_pages} páginas)")
    out.append(f"Secciones detectadas: {len(pre.sections)} (fallback_used={pre.fallback_used})")
    for s in pre.sections[:30]:
        out.append(f"  · [{s.id:<20}] {s.title!r:<40} pp {s.page_start}-{s.page_end}  ~{s.token_estimate()} tok")
    out.append(f"Captions detectadas: {len(pre.captions)}")

    valid_anchors = format_valid_anchors(pre.captions, pre.sections)

    out.append("\n=== Prompt: CLASSIFY ===")
    intro_section = pre.section_by_id("introduction") or (pre.sections[0] if pre.sections else None)
    abstract_chunk = pre.full_text[:1200]
    intro_chunk = intro_section.text[:3000] if intro_section else pre.full_text[:3000]
    sys_c, user_c = render_classify(title=title, abstract=abstract_chunk, intro=intro_chunk)
    out.append(f"-- SYSTEM ({len(sys_c)} chars) --")
    out.append(sys_c)
    out.append(f"-- USER ({len(user_c)} chars) --")
    out.append(user_c[:1200] + ("...[truncado]" if len(user_c) > 1200 else ""))

    for column in ("motivation", "methodology", "materials", "results"):
        out.append(f"\n=== Prompt: EXTRACT_{column.upper()} ===")
        sections = route_sections_to_columns(pre, column)
        section_text = "\n\n".join(f"[{s.title}]\n{s.text}" for s in sections)
        sys_e, user_e = render_extract_column(
            column=column,
            column_label=COLUMN_LABELS[column],
            paper_title=title,
            paper_type="(?)",
            domain="(?)",
            valid_anchors=valid_anchors,
            section_ids=[s.id for s in sections],
            section_text=section_text[:4000] + ("...[truncado]" if len(section_text) > 4000 else ""),
        )
        out.append(f"-- SYSTEM ({len(sys_e)} chars) --")
        out.append(sys_e[:800] + ("...[truncado]" if len(sys_e) > 800 else ""))
        out.append(f"-- USER (full secciones ~{sum(len(s.text) for s in sections)} chars) --")
        out.append(user_e[:1500] + ("...[truncado]" if len(user_e) > 1500 else ""))

    out.append("\n=== Prompt: BENEFIT ===")
    sys_b, user_b = render_benefit(
        paper_title=title,
        paper_type="(?)",
        category="(?)",
        domain="(?)",
        bullets_dump="(se llenará con bullets ya extraídos)",
        valid_anchors=valid_anchors,
    )
    out.append(f"-- SYSTEM ({len(sys_b)} chars) --")
    out.append(sys_b[:1500] + ("...[truncado]" if len(sys_b) > 1500 else ""))
    out.append(f"-- USER ({len(user_b)} chars) --")
    out.append(user_b[:800] + ("...[truncado]" if len(user_b) > 800 else ""))
    return "\n".join(out)


async def _invoke(pdf_path: Path, paper_id: str, cfg: LLMConfig, output_dir: Path) -> PaperExtraction:
    graph = build_extractor_graph()
    state = {
        "pdf_path": str(pdf_path),
        "llm_config": cfg,
        "source": SourceMeta(title=paper_id, pdf_path=str(pdf_path)),
    }
    final = await graph.ainvoke(state)
    extraction: PaperExtraction = final["extraction"]
    out_path = output_dir / f"{paper_id}.extraction.json"
    out_path.write_text(
        json.dumps(extraction.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return extraction


def main() -> None:
    parser = argparse.ArgumentParser(description="Runner CLI del extractor de papers (LangGraph).")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        # Default: <backend>/scripts/fixtures/ independiente del CWD.
        default=Path(__file__).resolve().parent / "fixtures",
    )
    parser.add_argument("--provider", default="ollama", choices=["ollama", "anthropic", "openai", "google_genai"])
    parser.add_argument("--model", default=None, help="default por provider: ollama=gemma2:27b, anthropic=claude-opus-4-7, openai=gpt-4o, google_genai=gemini-1.5-pro")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--dry-run", action="store_true", help="No invoca el LLM, solo imprime los prompts.")
    parser.add_argument("--invoke", action="store_true", help="Ejecuta el grafo y guarda la extracción.")
    args = parser.parse_args()

    if not args.pdf_path.exists():
        parser.error(f"PDF no encontrado: {args.pdf_path}")
    if not (args.dry_run or args.invoke):
        parser.error("Usa --dry-run o --invoke.")

    # Default model por provider
    default_models = {
        "ollama": "gemma4:26b",
        "anthropic": "claude-opus-4-7",
        "openai": "gpt-4o",
        "google_genai": "gemini-1.5-pro",
    }
    model = args.model or default_models[args.provider]
    cfg = LLMConfig(
        provider=args.provider,  # type: ignore[arg-type]
        model=model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    if args.dry_run:
        rendered = _render_dry_run(args.pdf_path, args.paper_id)
        print(rendered)
        return

    # invoke
    if args.provider == "ollama":
        try:
            check_ollama_health(model=cfg.model)
        except RuntimeError as e:
            print(f"✗ {e}", file=sys.stderr)
            sys.exit(2)

    # Resolver el output-dir absoluto para evitar duplicación si el CWD ya es
    # backend/ (caso típico: `cd backend && uv run ...` termina escribiendo a
    # backend/backend/scripts/fixtures/).
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"→ invocando extractor sobre {args.pdf_path.name} con {cfg.provider}/{cfg.model}")
    extraction = asyncio.run(_invoke(args.pdf_path, args.paper_id, cfg, output_dir))
    print(
        f"✓ {len(extraction.summary.motivation)} motivation · "
        f"{len(extraction.summary.methodology)} methodology · "
        f"{len(extraction.summary.materials)} materials · "
        f"{len(extraction.summary.results)} results"
    )
    print(f"  → {output_dir}/{args.paper_id}.extraction.json")


if __name__ == "__main__":
    main()
