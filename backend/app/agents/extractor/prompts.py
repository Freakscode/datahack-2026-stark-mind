"""Templates de prompt para los nodos del grafo.

Principios de diseño:
  1. Un prompt por nodo, cada uno ≤ 3k tokens efectivos (budget de Gemma 2
     con 8192 de contexto).
  2. System + rules + few-shot son estáticos por nodo → prompt cache friendly
     cuando se use un provider con cache (Anthropic).
  3. Salida SIEMPRE JSON. Prefill `{"bullets":[` cuando el provider lo acepta
     (Ollama, Anthropic). Si no, regex + retry.
  4. Anchors cerrados al manifest de pymupdf + secciones detectadas: el modelo
     recibe la lista de anchors válidos y la instrucción dura de no inventar.

Estos templates son Jinja-like pero usamos `str.format` para evitar
dependencias innecesarias. Las llaves de JSON se escapan con `{{` / `}}`.
"""
from __future__ import annotations

from app.agents._paper_schema import Bullet
from app.agents._project_brief import PROJECT_BRIEF


# ---------------------------------------------------------------------------
# Classify paper
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM = """Eres un clasificador de papers científicos. Lees el abstract + introducción y devuelves tres campos.

Devuelve SOLO JSON con este shape exacto:
{{"category": "Contexto" | "Características" | "Resultados" | "Limitaciones",
  "paper_type": "empírico" | "survey" | "teórico" | "dataset" | "tutorial" | "opinión",
  "domain": "nombre corto del dominio, 2-6 palabras"}}

Criterios:
- category: "Contexto" (paper fundacional/revisión general), "Características" (demuestra un método/arquitectura específica), "Resultados" (benchmark o evaluación comparativa), "Limitaciones" (identifica un problema o gap).
- paper_type: clasifica por la naturaleza del trabajo.
- domain: ej. "perovskite solar cells", "multi-agent RAG", "protein folding", "causal inference"."""

CLASSIFY_USER = """TITULO: {title}

ABSTRACT:
{abstract}

EXTRACTO DE INTRODUCCIÓN (primeros {intro_chars} chars):
{intro}

Devuelve JSON."""


# ---------------------------------------------------------------------------
# Extract column (one template, parametrized)
# ---------------------------------------------------------------------------

# Guías específicas por columna (parametrizadas por paper_type cuando aplica).
COLUMN_GUIDES: dict[str, str] = {
    "motivation": (
        "Motivación = por qué el paper importa. Captura: qué problema existe, qué gap ataca, "
        "qué supuesto previo rompe. 3-5 bullets. No describas métodos ni resultados aquí."
    ),
    "methodology": (
        "Metodología = cómo aborda el problema. "
        "Si el paper es EMPÍRICO: paradigma/técnica propuesta, pasos del pipeline, baselines "
        "comparados, protocolo experimental. "
        "Si el paper es SURVEY: taxonomía propuesta, dimensiones de análisis, criterios de "
        "comparación entre paradigmas, patrones de workflow catalogados. "
        "4-7 bullets."
    ),
    "materials": (
        "Materiales = con qué recursos concretos trabaja el paper. Extrae nombres propios "
        "literalmente del texto. 3-7 bullets.\n"
        "Si es EMPÍRICO: modelo base (PaLM-540B, GPT-3, etc.), datasets (HotpotQA, FEVER…), "
        "entornos (Wikipedia API, ALFWorld…), action space, hyperparámetros, exemplars.\n"
        "Si es SURVEY: cada bullet recoge una CATEGORÍA DE RECURSOS INVENTARIADA con los "
        "nombres literales del paper. Ejemplos:\n"
        "  - 'Frameworks inventariados: LangChain/LangGraph, LlamaIndex, CrewAI, AutoGen, "
        "    Bedrock, Vertex AI, Semantic Kernel, IBM watsonx, Pinecone, Neo4j'\n"
        "  - 'Benchmarks referenciados: BEIR, MS MARCO, HotpotQA, MuSiQue, 2WikiMultiHopQA, "
        "    RAGBench, BERGEN, FlashRAG, GNN-RAG'\n"
        "  - 'Patrones agénticos: Reflection, Planning, Tool Use, Multi-Agent Collaboration'\n"
        "  - 'Arquitecturas catalogadas: Single-Agent Router, Multi-Agent, Hierarchical, "
        "    Corrective, Adaptive, Graph-Based (Agent-G, GeAR), ADW'\n"
        "Copia los nombres exactos del texto fuente. Si el texto no menciona alguna categoría, "
        "omite ese bullet — no inventes."
    ),
    "results": (
        "Resultados = qué encontró. "
        "Si el paper es EMPÍRICO: métricas numéricas con valores exactos, comparativas clave "
        "ReAct 71% vs Act 45%), hallazgos estadísticamente significativos. "
        "Si el paper es SURVEY: lessons learned, trade-offs entre arquitecturas, cuellos de "
        "botella identificados, hallazgos taxonómicos comparativos. "
        "4-8 bullets. Prioriza referencias a Tables/Figures concretas."
    ),
}

EXTRACT_COLUMN_SYSTEM = """Eres un extractor de la columna {column_label} de un paper científico.

{column_guide}

FORMATO DE SALIDA (SOLO JSON, nada más):
{{"bullets": [
  {{"text": "afirmación concreta de 25-45 palabras en español", "anchor": "§N o Fig. N o Table N o App. X"}},
  ...
]}}

REGLAS DURAS:
1. Cada bullet termina en un anchor válido tomado de la lista ANCHORS_VÁLIDOS.
2. Si no puedes fundamentar un bullet con un anchor de la lista, NO lo incluyas. Es preferible devolver
   menos bullets que inventar referencias.
3. Si ninguno se puede extraer con evidencia, devuelve {{"bullets": []}}.
4. Prohibido inventar métricas numéricas. Solo cita números si aparecen literalmente en el texto provisto.
5. Idioma: español. Terminología técnica en inglés se mantiene en inglés (ej. "prompt chaining", "self-consistency").
6. Formato corto y denso. Sin meta-comentarios ("este paper dice...", "según la sección X..."): la afirmación directa."""

EXTRACT_COLUMN_USER = """PAPER: {paper_title}
TIPO: {paper_type} · DOMINIO: {domain}

ANCHORS_VÁLIDOS (solo puedes usar estos):
{valid_anchors}

TEXTO FUENTE (secciones {section_ids}):
---
{section_text}
---

Devuelve JSON {{"bullets": [...]}} para la columna {column_label}."""


# ---------------------------------------------------------------------------
# Compute benefit (ve los bullets ya extraídos + project brief)
# ---------------------------------------------------------------------------

BENEFIT_SYSTEM = """Eres responsable de escribir el campo `benefit` del PaperExtraction: un párrafo de 60-150 palabras que explica por qué ESTE paper importa al proyecto STARK-VIX, y construir un `pitch_mapping` que mapea dimensiones del pitch a citas concretas del paper.

IDIOMA OBLIGATORIO: **ESPAÑOL EN TODO EL OUTPUT**.
  - El `benefit` completo en español. Cero frases en inglés.
  - Los valores de `pitch_mapping.entries` en español.
  - Terminología técnica consolidada en inglés se mantiene: "multi-agent RAG", "chain-of-thought", "prompt chaining", "self-consistency", "groundedness", "faithfulness", "hallucination", "few-shot", "fine-tuning", nombres de modelos/benchmarks/frameworks (PaLM, GPT-3, HotpotQA, LangGraph, etc.) y nombres propios de conceptos del paper (ReAct, CoT, BUTLER, etc.).
  - Todo lo demás — verbos, conectores, artículos, adjetivos, descripciones — en español.

DIMENSIONES DEL PITCH (claves EXACTAS que debes usar en pitch_mapping.entries):
  1. **architecture** — arquitectura master-agent + sub-agentes especializados
  2. **stack_validation** — frameworks mencionados (LangGraph, LlamaIndex, CrewAI, AutoGen, Bedrock, Vertex AI, Semantic Kernel, etc.)
  3. **corrective_layer** — validación de citas / detección de alucinación / self-correction
  4. **document_workflows** — ingesta estructurada de papers (parse → rules → state → output)
  5. **responsible_deployment** — traceability, auditability, explainability, governance
  6. **evaluation_harness** — groundedness, faithfulness, citation accuracy, process-aware metrics
  7. **domain_fit** — especialización de dominio que amplifica valor agéntico

REGLAS (sigue TODAS):
1. El `benefit` DEBE referenciar al menos 2 anchors inline del paper (ej. "(Table 2)", "(§5.3)", "(Fig. 3)").
2. El `pitch_mapping.entries` DEBE contener **2-4 dimensiones** cuando el paper valide ≥2 (caso típico). Una sola solo si el paper es muy unidimensional.
3. Cada valor del pitch_mapping es una cita corta EN ESPAÑOL con anchor: formato `"{{método/concepto clave en español}} ({{anchor}})"`.
4. Si el paper NO valida ninguna dimensión, devuelve `pitch_mapping` vacío y clasifica el paper como "cita de background" en el benefit.
5. Formato del benefit: texto plano, un solo párrafo, sin bullets, sin encabezados.
6. **REGLA OBLIGATORIA DE stack_validation**: revisa los bullets extraídos (especialmente los de `materials`) buscando menciones de frameworks del conjunto — {{LangGraph, LangChain, LlamaIndex, CrewAI, AutoGen/AG2, OpenAI Swarm, Amazon Bedrock, Google Vertex AI, Microsoft Semantic Kernel, IBM watsonx, Hugging Face, Pinecone, Weaviate, Milvus, Qdrant, Neo4j}}. Si encuentras ≥3 de estos en los bullets, `stack_validation` DEBE aparecer en pitch_mapping con una cita que ENUMERE los frameworks detectados (ej. "nombra LangGraph, LlamaIndex, CrewAI, AutoGen, Bedrock como frameworks de referencia (§8)"). Este caso es universal en surveys de infraestructura y es la dimensión de más alto valor para el pitch.

EJEMPLO (paper empírico tipo ReAct):
{{"benefit": "Este paper establece el paradigma de razonamiento y acción intercalados (Fig. 1, §2) que sustenta la arquitectura multiagente de STARK-VIX. La evidencia de reducción de alucinación del 56% al 0% en HotpotQA (Table 2) justifica directamente nuestro pilar de citas trazables con anchor y el corrective_layer del Orchestrator.",
  "pitch_mapping": {{
    "architecture": "patrón de pensamiento-acción intercalados (Fig. 1, §2)",
    "corrective_layer": "alucinación baja del 56% al 0% (Table 2)",
    "evaluation_harness": "taxonomía de modos de éxito y fallo process-aware (Table 2)"
  }}}}

EJEMPLO (paper tipo survey de infraestructura):
{{"benefit": "Este survey valida literalmente la pila técnica de STARK-VIX: nombra LangGraph, LlamaIndex, CrewAI, AutoGen, Bedrock, Vertex AI y Semantic Kernel como frameworks de referencia (§8). La Tabla 3 provee 12 dimensiones taxonómicas que el Orchestrator puede adoptar como configuración.",
  "pitch_mapping": {{
    "stack_validation": "nombra LangGraph, LlamaIndex, CrewAI, AutoGen, Bedrock como frameworks de referencia (§8)",
    "architecture": "patrón jerárquico master-agent formalizado (§5.3, Fig. 18)",
    "document_workflows": "categoría Agentic Document Workflows definida (§5.7, Fig. 23)",
    "responsible_deployment": "explainability, traceability y auditability como first-class goals (§10.7)"
  }}}}

SALIDA (SOLO JSON, nada más):
{{"benefit": "<párrafo 60-150 palabras en español con 2+ anchors inline>",
  "pitch_mapping": {{"<dimension>": "<cita en español (anchor)>", ...}}}}

BRIEF DEL PROYECTO:
{project_brief}"""

BENEFIT_USER = """PAPER: {paper_title}
TIPO: {paper_type} · CATEGORÍA: {category} · DOMINIO: {domain}

BULLETS EXTRAÍDOS:
{bullets_dump}

ANCHORS DISPONIBLES:
{valid_anchors}

Devuelve JSON {{"benefit": "...", "pitch_mapping": {{...}}}}."""


# ---------------------------------------------------------------------------
# Compress section (mini-prompt cuando una sección excede el budget)
# ---------------------------------------------------------------------------

COMPRESS_SYSTEM = """Eres un compresor de texto científico de alta fidelidad. Recibes un fragmento largo de un paper y devuelves una versión comprimida que preserva toda la información factual. Objetivo: ~{target_chars} caracteres (puedes ir hasta 1.2x si es necesario para no perder datos).

PRESERVA SIEMPRE, SIN EXCEPCIÓN:
1. **Todas las métricas numéricas**: porcentajes (34%, 71%), scores (35.1, 64.6), time/count (T80 840 h, 3000 trajectories), deltas (+34 puntos), rates (0% vs 56%). No redondees. No inventes. No uses aproximaciones ("aprox", "cerca de").
2. **Nombres propios técnicos**: modelos (PaLM-540B, GPT-3, Claude, Gemma 2, BGE, Qwen), benchmarks (HotpotQA, FEVER, ALFWorld, WebShop, MMLU, BEIR, MS MARCO), datasets (ImageNet, MuSiQue, 2WikiMultihopQA), frameworks (LangChain, LangGraph, LlamaIndex, CrewAI, AutoGen, Amazon Bedrock, Vertex AI, Semantic Kernel), APIs (Wikipedia API, search/lookup/finish).
3. **Todas las referencias estructurales**: §N, §N.M, Fig. N, Figure N, Table N, Tab. N, Appendix X, App. X.Y, p. N, pp. N-M, equation (N), citation keys.
4. **Decisiones de diseño discretas**: valores de hyperparámetros, tamaños de muestra (6 few-shot, 21 CoT-SC samples), protocolos (ISOS-L-2, 85% RH), arquitecturas (transformer, MoE), nombres de funciones (search[entity], lookup[string], finish[answer]).
5. **Comparativas con deltas explícitos**: "ReAct 71% vs Act 45%" — mantén ambos números y el nombre de la baseline.

ELIMINA:
- Ejemplos redundantes que ilustran el mismo concepto.
- Meta-texto ("we propose", "in this section", "as shown").
- Transiciones ("furthermore", "moreover", "additionally").
- Paráfrasis que reformulan la idea anterior sin añadir información nueva.
- Fillers sin contenido ("importantly", "notably" cuando siguen un hecho trivial).

FORMATO:
- Idioma: el original (no traduzcas).
- Escribe como bullets si el original es prosa densa con múltiples hechos; sino mantén párrafos cortos.
- Devuelve SOLO el texto comprimido. Sin prefacio, sin comentarios, sin marcadores como "Comprimido:"."""

COMPRESS_USER = """FRAGMENTO:
{text}

Comprime a ~{target_chars} chars."""


# ---------------------------------------------------------------------------
# Helpers de ensamblaje
# ---------------------------------------------------------------------------


def format_valid_anchors(captions: list, sections: list) -> str:
    """Devuelve un string multilínea con los anchors disponibles para este paper."""
    lines: list[str] = []
    for c in captions[:40]:  # cap para no explotar el budget
        lines.append(f"  - {c.anchor}  (p{c.page}): {c.text[:100]}")
    for s in sections:
        lines.append(f"  - §{s.title.split()[0] if s.title else s.id}  (pp {s.page_start}-{s.page_end})")
    return "\n".join(lines) if lines else "(ninguno — el PDF no expuso captions ni headings)"


def format_bullets_dump(summary_dict: dict) -> str:
    """Formatea los bullets de las 4 columnas para el prompt de benefit."""
    out: list[str] = []
    for col in ("motivation", "methodology", "materials", "results"):
        bullets = summary_dict.get(col) or []
        if not bullets:
            continue
        out.append(f"\n[{col.upper()}]")
        for b in bullets:
            if isinstance(b, Bullet):
                anchor = f" [{b.anchor}]" if b.anchor else ""
                out.append(f"  · {b.text}{anchor}")
            else:
                anchor = f" [{b.get('anchor')}]" if b.get("anchor") else ""
                out.append(f"  · {b['text']}{anchor}")
    return "\n".join(out) if out else "(sin bullets extraídos)"


def render_classify(title: str, abstract: str, intro: str) -> tuple[str, str]:
    intro_chars = len(intro)
    return (
        CLASSIFY_SYSTEM,
        CLASSIFY_USER.format(title=title, abstract=abstract, intro=intro, intro_chars=intro_chars),
    )


def render_extract_column(
    *,
    column: str,
    column_label: str,
    paper_title: str,
    paper_type: str,
    domain: str,
    valid_anchors: str,
    section_ids: list[str],
    section_text: str,
) -> tuple[str, str]:
    guide = COLUMN_GUIDES.get(column, "")
    system = EXTRACT_COLUMN_SYSTEM.format(column_label=column_label, column_guide=guide)
    user = EXTRACT_COLUMN_USER.format(
        paper_title=paper_title,
        paper_type=paper_type,
        domain=domain,
        valid_anchors=valid_anchors,
        section_ids=", ".join(section_ids) or "(ninguna detectada)",
        section_text=section_text,
        column_label=column_label,
    )
    return system, user


def render_benefit(
    *,
    paper_title: str,
    paper_type: str,
    category: str,
    domain: str,
    bullets_dump: str,
    valid_anchors: str,
) -> tuple[str, str]:
    system = BENEFIT_SYSTEM.format(project_brief=PROJECT_BRIEF)
    user = BENEFIT_USER.format(
        paper_title=paper_title,
        paper_type=paper_type,
        category=category,
        domain=domain,
        bullets_dump=bullets_dump,
        valid_anchors=valid_anchors,
    )
    return system, user


def render_compress(text: str, target_chars: int) -> tuple[str, str]:
    system = COMPRESS_SYSTEM.format(target_chars=target_chars)
    user = COMPRESS_USER.format(text=text, target_chars=target_chars)
    return system, user


# ---------------------------------------------------------------------------
# Extract key_metrics (métricas numéricas estructuradas)
# ---------------------------------------------------------------------------

METRICS_SYSTEM = """Eres un extractor de métricas numéricas de papers científicos.

IDIOMA: los nombres (`name`) van en **español** (excepto nombres propios de benchmarks/modelos/métricas en inglés que se mantienen: HotpotQA, FEVER, PaLM-540B, GPT-3, EM, Acc, SR, etc.). Los `value` son numéricos literales del texto. `unit` y `anchor` pueden ser strings cortos en cualquier idioma.

Recibes regiones de texto que contienen tablas y resultados. Tu tarea es emitir
un JSON con TODAS las métricas numéricas relevantes encontradas, cada una con:
  - name: nombre corto y descriptivo EN ESPAÑOL (ej. "HotpotQA EM de ReAct→CoT-SC", "T80 de MAPbI₃ con Cs 10%", "Tasa de alucinación de CoT")
  - value: el valor EXACTO como aparece (ej. "35.1", "64.6", "71%", "0% vs 56%", "840 h")
  - unit: unidad cuando aplique (ej. "%", "h", "EM", "Acc", null si no aplica)
  - anchor: origen ("Table 1", "Table 2", "Fig. 3", "§3.3")

FORMATO DE SALIDA (SOLO JSON, nada más):
{"metrics": [
  {"name": "...", "value": "...", "unit": "...|null", "anchor": "Table N"},
  ...
]}

REGLAS DURAS:
1. Solo métricas que aparecen LITERALMENTE en el texto. No inventes, no extrapoles.
2. Prioriza comparativas: "ReAct 71% vs Act 45%" → dos metrics separadas O una con value="71% vs 45%".
3. Mantén los números EXACTOS (no redondees ni uses aproximaciones).
4. Máximo 12 métricas — solo las más impactantes para el paper.
5. **Para SURVEYS**, también cuentan como métricas válidas los conteos de enumeración explícitos en el texto:
   - Número de referencias citadas ("104 references", "40 studies")
   - Número de frameworks inventariados ("11 frameworks named")
   - Número de paradigmas/arquitecturas/patrones catalogados ("5 RAG paradigms", "8 architectures")
   - Número de dimensiones taxonómicas ("12 dimensions in Table 3")
   - Número de benchmarks/datasets referenciados ("10+ benchmarks")
   Usa unit="count" para estos. Si un survey no tiene NINGÚN número explícito, devuelve {"metrics": []}.
6. Para papers empíricos sin números en las regiones recibidas, devuelve {"metrics": []}."""

METRICS_USER = """PAPER: {paper_title}
DOMINIO: {domain}

REGIONES DE TABLA (principal fuente de métricas):
{table_regions_text}

SECCIÓN RESULTS (contexto adicional):
{results_text}

Devuelve JSON {{"metrics": [...]}} con las métricas más destacadas del paper."""


def render_extract_metrics(
    *,
    paper_title: str,
    domain: str,
    table_regions_text: str,
    results_text: str,
) -> tuple[str, str]:
    system = METRICS_SYSTEM
    user = METRICS_USER.format(
        paper_title=paper_title,
        domain=domain,
        table_regions_text=table_regions_text or "(ninguna tabla detectada)",
        results_text=results_text or "(no hay sección results explícita)",
    )
    return system, user


__all__ = [
    "COLUMN_GUIDES",
    "format_bullets_dump",
    "format_valid_anchors",
    "render_benefit",
    "render_classify",
    "render_compress",
    "render_extract_column",
    "render_extract_metrics",
]
