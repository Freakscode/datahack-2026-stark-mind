"""Nodos del grafo del extractor.

Cada nodo:
  1. Arma los prompts (system + user) usando `prompts.py`.
  2. Invoca el ChatModel vía LangChain (`.ainvoke`).
  3. Parsea la respuesta como JSON con reintento si el formato falla.
  4. Devuelve el subset del estado que el nodo produce (para que LangGraph
     lo mergee).

La parseo de JSON es deliberadamente tolerante: Gemma 2 a veces envuelve la
salida en ```json``` o añade preámbulo. `_extract_json` busca el primer
objeto JSON válido con parentheses-matching.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents._paper_schema import (
    Bullet,
    ColumnExtraction,
    KeyMetric,
    PaperClassification,
    PaperSummaryCore,
    PitchMapping,
)
from app.agents.extractor.prompts import (
    format_bullets_dump,
    format_valid_anchors,
    render_benefit,
    render_classify,
    render_compress,
    render_extract_column,
    render_extract_metrics,
)
from app.agents.llm_providers import LLMConfig, get_chat_model_with_fallback
from app.agents.pdf_preprocessor import (
    PaperPreprocessed,
    route_sections_to_columns,
)

logger = logging.getLogger(__name__)

# Regex para extraer anchor cuando el modelo lo dejó al final del `text` en
# lugar de separarlo al campo `anchor`. Acepta: §2, §3.1, Table 1, Fig. 3,
# Figure 5, App. A.1, Appendix B, p. 4.
_TRAILING_ANCHOR_RE = re.compile(
    r"""
    \s*(?:[.,;:\-—]\s*)?                       # separador opcional antes del anchor
    (?P<anchor>
        §\s*\d+(?:\.\d+){0,2}                  # §N o §N.M
        | Table\s+\d+                          # Table N
        | Fig\.?\s*\d+                         # Fig. N o Fig N
        | Figure\s+\d+                         # Figure N
        | App(?:endix)?\.?\s*[A-Z](?:\.\d+)?   # App. A.1 / Appendix A / Appendix A.2
        | p\.\s*\d+                            # p. 4
    )
    \s*$
    """,
    re.VERBOSE,
)


def _split_trailing_anchor(text: str) -> tuple[str, str | None]:
    """Si `text` termina en un anchor reconocible, lo separa del cuerpo.

    Devuelve (text_limpio, anchor) o (text, None) si no se encontró.
    """
    if not text:
        return text, None
    m = _TRAILING_ANCHOR_RE.search(text)
    if not m:
        return text, None
    anchor = m.group("anchor").strip()
    # Normalizar: "Fig 3" → "Fig. 3", "§ 2" → "§2"
    anchor = re.sub(r"^(Fig)\s+(\d)", r"Fig. \2", anchor)
    anchor = re.sub(r"^§\s+", "§", anchor)
    return text[: m.start()].rstrip(" .,;:—-"), anchor


def _fix_bullet_anchors(bullets: list[Bullet]) -> list[Bullet]:
    """Mueve anchors trailing del text al campo anchor cuando éste es null."""
    fixed: list[Bullet] = []
    for b in bullets:
        if b.anchor or not b.text:
            fixed.append(b)
            continue
        new_text, extracted = _split_trailing_anchor(b.text)
        if extracted:
            fixed.append(Bullet(text=new_text, anchor=extracted))
        else:
            fixed.append(b)
    return fixed


COLUMN_LABELS = {
    "motivation": "Motivación",
    "methodology": "Metodología",
    "materials": "Materiales y Métodos",
    "results": "Resultados",
}

# Budget efectivo para la sección de texto dentro del user prompt de extracción.
# 8192 (contexto Gemma 2) - 1500 (system) - 700 (anchors) - 500 (overhead) ≈ 5500 tokens ≈ 22k chars.
SECTION_TEXT_BUDGET_CHARS = 18_000
COMPRESS_TARGET_CHARS = 6_000


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json(text: str) -> dict | list:
    """Extrae el primer JSON object/array válido del texto de respuesta del LLM.

    Tolera: fences markdown, preámbulo/epílogo, trailing commas.
    """
    cleaned = _FENCE_RE.sub("", text).strip()
    # Intento directo
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Buscar primer {...} balanceado
    match = _JSON_OBJECT_RE.search(cleaned)
    if not match:
        raise ValueError(f"no pude encontrar JSON en: {text[:200]!r}")
    candidate = match.group(0)
    # Arreglar trailing commas comunes en modelos locales
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    return json.loads(candidate)


async def _call_llm(cfg: LLMConfig, system: str, user: str, *, max_retries: int = 2) -> str:
    """Invoca el ChatModel con retry en errores transitorios.

    Para thinking models (gemma4, deepseek-r1, qwen3-thinking) el content
    principal viene limpio pero si reasoning consumió todo el budget la
    respuesta puede salir vacía. En ese caso hacemos fallback al
    `reasoning_content` que suele contener el JSON intermedio.
    """
    chat = get_chat_model_with_fallback(cfg)
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await chat.ainvoke(messages)
            content = response.content
            if isinstance(content, list):
                content = "".join(
                    part if isinstance(part, str) else part.get("text", "")
                    for part in content
                )
            content = content or ""  # type: ignore[assignment]
            if not content.strip():
                # Fallback: thinking model se quedó sin tokens para la respuesta.
                # El `reasoning_content` a menudo tiene el JSON candidato.
                reasoning = response.additional_kwargs.get("reasoning_content", "") or ""
                if reasoning.strip():
                    logger.warning(
                        "LLM devolvió content vacío; reintentando con reasoning_content "
                        "(%d chars)",
                        len(reasoning),
                    )
                    return reasoning
            return content  # type: ignore[return-value]
        except Exception as e:  # noqa: BLE001
            last_exc = e
            logger.warning("LLM call failed (attempt %s/%s): %s", attempt + 1, max_retries + 1, e)
            if attempt < max_retries:
                await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_exc}")


async def _call_json(
    cfg: LLMConfig, system: str, user: str, *, json_retries: int = 2
) -> dict:
    """Invoca el LLM y parsea como JSON, reintentando con hint si falla.

    Para thinking models, si los retries normales fallan, hace un último
    intento con `reasoning=False` — fuerza al modelo a saltar el bloque de
    thinking y emitir la respuesta directa (perdemos la "calidad de razonamiento"
    pero ganamos determinismo en formato).
    """
    last_raw = ""
    for attempt in range(json_retries + 1):
        raw = await _call_llm(cfg, system, user)
        last_raw = raw
        try:
            return _extract_json(raw)  # type: ignore[return-value]
        except (ValueError, json.JSONDecodeError) as e:
            if attempt >= json_retries:
                # Último escape: reintento sin reasoning (solo para thinking models).
                if cfg.reasoning is True:
                    logger.warning(
                        "JSON falló tras %d intentos con reasoning; intentando sin reasoning",
                        json_retries + 1,
                    )
                    cfg_direct = LLMConfig(
                        provider=cfg.provider,
                        model=cfg.model,
                        temperature=cfg.temperature,
                        max_tokens=cfg.max_tokens,
                        num_ctx=cfg.num_ctx,
                        reasoning=False,
                        extras=cfg.extras,
                    )
                    try:
                        raw = await _call_llm(cfg_direct, system, user)
                        return _extract_json(raw)  # type: ignore[return-value]
                    except (ValueError, json.JSONDecodeError) as e2:
                        last_raw = raw
                        e = e2  # propagamos el error del último intento
                raise RuntimeError(
                    f"LLM no devolvió JSON válido tras {json_retries + 2} intentos. "
                    f"Último raw: {last_raw[:300]!r}. Error: {e}"
                )
            # Re-prompt con hint de corrección
            user = (
                f"{user}\n\n"
                f"Tu respuesta anterior no era JSON válido ({e}). "
                f"Responde SOLO con JSON, sin prosa ni fences."
            )
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------------------
# Compresión recursiva para secciones largas
# ---------------------------------------------------------------------------


async def compress_if_needed(cfg: LLMConfig, text: str, *, budget: int = SECTION_TEXT_BUDGET_CHARS) -> str:
    """Si el texto excede el budget, llama al LLM para comprimirlo a ~COMPRESS_TARGET_CHARS."""
    if len(text) <= budget:
        return text
    logger.info("compressing section: %s chars → ~%s", len(text), COMPRESS_TARGET_CHARS)
    system, user = render_compress(text, COMPRESS_TARGET_CHARS)
    compressed = await _call_llm(cfg, system, user)
    return compressed.strip()


# ---------------------------------------------------------------------------
# Nodos del grafo
# ---------------------------------------------------------------------------


async def node_classify(state: dict) -> dict:
    """Clasifica el paper a partir del abstract + intro."""
    pre: PaperPreprocessed = state["preprocessed"]
    cfg: LLMConfig = state["llm_config"]
    title = state.get("title") or "(desconocido)"

    # Abstract: sección introductoria + primeras líneas del primer tercio
    intro_section = pre.section_by_id("introduction") or (pre.sections[0] if pre.sections else None)
    abstract_chunk = (pre.full_text[:1200]).strip()
    intro_chunk = (intro_section.text[:3000] if intro_section else pre.full_text[:3000]).strip()

    system, user = render_classify(title=title, abstract=abstract_chunk, intro=intro_chunk)
    payload = await _call_json(cfg, system, user)
    try:
        classification = PaperClassification.model_validate(payload)
    except ValidationError as e:
        raise RuntimeError(f"classify_paper devolvió JSON inválido: {e}") from e
    return {"classification": classification}


def _format_table_regions(pre: PaperPreprocessed, max_chars: int = 10_000) -> str:
    """Concatena table_regions como bloques etiquetados. Útil para results + metrics."""
    if not pre.table_regions:
        return ""
    parts: list[str] = []
    budget = max_chars
    for t in pre.table_regions:
        header = f"[{t.anchor}  p{t.page}] {t.caption[:120]}"
        chunk = f"{header}\n{t.text}\n"
        if budget - len(chunk) < 0:
            chunk = chunk[:budget]
        parts.append(chunk)
        budget -= len(chunk)
        if budget <= 200:
            break
    return "\n\n".join(parts)


async def _extract_column(
    state: dict, column: str
) -> list[Bullet]:
    pre: PaperPreprocessed = state["preprocessed"]
    cfg: LLMConfig = state["llm_config"]
    classification: PaperClassification = state["classification"]
    title = state.get("title") or "(desconocido)"

    sections = route_sections_to_columns(pre, column, classification.paper_type)
    section_text = "\n\n".join(f"[{s.title}]\n{s.text}" for s in sections)

    # Para la columna results, inyectamos también las table_regions ANTES de
    # comprimir — las tablas son la fuente principal de números y vale la pena
    # sacrificar contexto de prosa por retener celdas numéricas.
    if column == "results" and pre.table_regions:
        tables_block = _format_table_regions(pre, max_chars=8_000)
        section_text = f"TABLAS DEL PAPER:\n{tables_block}\n\n---\nPROSA DE RESULTS:\n{section_text}"

    section_text = await compress_if_needed(cfg, section_text)

    valid_anchors = format_valid_anchors(pre.captions, pre.sections)
    system, user = render_extract_column(
        column=column,
        column_label=COLUMN_LABELS[column],
        paper_title=title,
        paper_type=classification.paper_type,
        domain=classification.domain,
        valid_anchors=valid_anchors,
        section_ids=[s.id for s in sections],
        section_text=section_text,
    )
    payload = await _call_json(cfg, system, user)
    try:
        ext = ColumnExtraction.model_validate(payload)
    except ValidationError as e:
        logger.warning("columna %s: JSON inválido, devolviendo []. err=%s", column, e)
        return []
    return _fix_bullet_anchors(ext.bullets)


async def node_extract_motivation(state: dict) -> dict:
    return {"motivation": await _extract_column(state, "motivation")}


async def node_extract_methodology(state: dict) -> dict:
    return {"methodology": await _extract_column(state, "methodology")}


async def node_extract_materials(state: dict) -> dict:
    return {"materials": await _extract_column(state, "materials")}


async def node_extract_results(state: dict) -> dict:
    return {"results": await _extract_column(state, "results")}


async def node_extract_metrics(state: dict) -> dict:
    """Nodo dedicado de extracción de métricas numéricas.

    Lee las table_regions del preprocesador + el texto de la sección results
    y emite una lista de KeyMetric (name, value, unit, anchor). Corre en
    paralelo con los 4 nodos de columnas.
    """
    pre: PaperPreprocessed = state["preprocessed"]
    cfg: LLMConfig = state["llm_config"]
    classification: PaperClassification = state["classification"]
    title = state.get("title") or "(desconocido)"

    tables_text = _format_table_regions(pre, max_chars=9_000)
    results_sections = route_sections_to_columns(pre, "results", classification.paper_type)
    results_text = "\n\n".join(f"[{s.title}]\n{s.text}" for s in results_sections)
    # Budget conservador: el prompt de metrics es más corto que el de columnas.
    if len(results_text) > 6000:
        results_text = results_text[:6000] + "…[truncado]"

    # Si no hay ni tablas ni results detectados, no llamamos al LLM.
    if not tables_text and not results_text:
        return {"key_metrics": []}

    system, user = render_extract_metrics(
        paper_title=title,
        domain=classification.domain,
        table_regions_text=tables_text,
        results_text=results_text,
    )
    try:
        payload = await _call_json(cfg, system, user)
    except RuntimeError as e:
        logger.warning("key_metrics falló, devolviendo []. err=%s", e)
        return {"key_metrics": []}

    raw_metrics = payload.get("metrics") if isinstance(payload, dict) else None
    if not isinstance(raw_metrics, list):
        return {"key_metrics": []}
    metrics: list[KeyMetric] = []
    for m in raw_metrics[:15]:
        if not isinstance(m, dict):
            continue
        try:
            metrics.append(
                KeyMetric(
                    name=str(m.get("name", "")).strip()[:120] or "(sin nombre)",
                    value=str(m.get("value", "")).strip()[:60] or "(sin valor)",
                    unit=(str(m.get("unit")).strip()[:20] if m.get("unit") not in (None, "null") else None),
                    anchor=(str(m.get("anchor")).strip()[:40] if m.get("anchor") else None),
                )
            )
        except ValidationError as e:
            logger.warning("métrica inválida saltada: %s", e)
            continue
    return {"key_metrics": metrics}


async def node_compute_benefit(state: dict) -> dict:
    """Arma `benefit` y opcionalmente `pitch_mapping` con los bullets ya extraídos."""
    pre: PaperPreprocessed = state["preprocessed"]
    cfg: LLMConfig = state["llm_config"]
    classification: PaperClassification = state["classification"]
    title = state.get("title") or "(desconocido)"

    summary = PaperSummaryCore(
        motivation=state.get("motivation") or [],
        methodology=state.get("methodology") or [],
        materials=state.get("materials") or [],
        results=state.get("results") or [],
    )
    bullets_dump = format_bullets_dump(summary.model_dump())
    valid_anchors = format_valid_anchors(pre.captions, pre.sections)

    system, user = render_benefit(
        paper_title=title,
        paper_type=classification.paper_type,
        category=classification.category,
        domain=classification.domain,
        bullets_dump=bullets_dump,
        valid_anchors=valid_anchors,
    )
    payload = await _call_json(cfg, system, user)
    benefit = payload.get("benefit") or ""
    mapping_raw = payload.get("pitch_mapping") or {}
    mapping: PitchMapping | None = None
    if isinstance(mapping_raw, dict) and mapping_raw:
        mapping = PitchMapping(entries={k: str(v) for k, v in mapping_raw.items()})
    return {"benefit": benefit, "pitch_mapping": mapping, "summary_core": summary}


__all__ = [
    "COLUMN_LABELS",
    "compress_if_needed",
    "node_classify",
    "node_compute_benefit",
    "node_extract_materials",
    "node_extract_methodology",
    "node_extract_metrics",
    "node_extract_motivation",
    "node_extract_results",
]
