# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Naturaleza del workspace

Esta carpeta **no es un repositorio de código** — es un workspace de **planificación y estrategia** para el **DataHack 2026 — Reto #3** (Asistente Inteligente para Artículos de Investigación, MVP **STARK-MIND / STARK-VIX**). No hay build, tests ni lint. El trabajo consiste en producir, mantener y razonar sobre documentos `.md` que consolidan research, arquitectura y estrategia de pitch.

## Archivos clave y su rol

- `softserve-analisis-reto3.md` (+ `.txt`) — Análisis del sponsor (SoftServe) y **estrategia de convencimiento**. Es la base del pitch: servicios de SoftServe alineados con el reto, "dog whistles" técnicos, diferenciadores y estructura sugerida del pitch. Cualquier decisión de producto debería validarse contra este documento.
- `miro-research-phase.md` — Consolidado de la **fase de Research** extraído del tablero Miro. Contiene plan maestro, benchmarking de 7 productos competidores, arquitectura multiagente, user journeys de 3 personas y framework de 8 decisiones UX.
- `.mcp.json` — Configura el servidor MCP de Miro (HTTP en `https://mcp.miro.com/`). Sin credenciales locales — la autenticación la maneja el host.

## Fuente de verdad del research

El **tablero de Miro** es la fuente viva: `https://miro.com/app/board/uXjVHeyNC2U=/`

Artefactos del tablero (ver `miro-research-phase.md` §6 "Mapa del tablero" para IDs y coordenadas):

- **Plan desarrollo DataHack** (documento) — visión, capacidades núcleo, stack.
- **Benchmarking** (tabla, 7 filas) — Elicit, Undermind, Perplexity Deep Research, NotebookLM como prioridad **Alta**.
- **Arquitectura multiagente** (diagrama) — Orchestrator + 6 agentes especializados + 4 fuentes.
- **User Journeys** (diagrama) — Tesista Pascual Bravo, R&D Engineer SoftServe, Intelligence Engineer.
- **Decisiones UX** (tabla, 8 preguntas) — 5 cerradas, 2 en híbrido, 0 en discusión.

Antes de reconsolidar o modificar `miro-research-phase.md`, **siempre re-extraer desde Miro** (con las herramientas `mcp__miro__*`) para no trabajar sobre una copia desactualizada.

## Contexto estratégico crítico (no derivable del código)

Estos puntos condicionan decisiones de producto y deben preservarse al editar:

- **SoftServe es el sponsor** del reto. El MVP está **intencionadamente diseñado para replicar** su *Multi-Agent RAG Platform* (AWS Marketplace) e *Insights Engine Pilot*. No es coincidencia — es la tesis del pitch.
- **LLM por default: Claude (Anthropic)**. Razón: SoftServe usó la API de Anthropic en su hackathon AgentForge. Cualquier sugerencia de otro LLM debería justificarse explícitamente.
- **Stack alineado con partnerships de SoftServe**: AWS (Bedrock, Lambda, OpenSearch), pgvector/Pinecone, LangGraph con patrón jerárquico Master Agent.
- **"Dog whistles" que deben aparecer** en cualquier propuesta/pitch: *Multi-Agent RAG*, *citas trazables con anchor*, *evaluation harness* (groundedness, faithfulness, citation accuracy), *guardrails*, *agentic* (vs. chatbot), *Intelligence Engineer*.
- **Público objetivo triple**: tesistas de IU Pascual Bravo + R&D Engineers de SoftServe + Intelligence Engineers. El mismo sistema atiende a los tres reorganizando qué agentes lideran cada flujo.

## Convenciones de escritura

- **Idioma:** español en todo artefacto de este workspace (documentos, commits, comentarios, respuestas al usuario).
- **Formato:** Markdown con tablas para comparativas, fenced code blocks solo cuando aplique, headings jerárquicos. Los `.txt` espejo existen para copiar/pegar en entornos sin markdown — si actualizas el `.md`, considera si vale propagar al `.txt`.
- **Citas a fuentes externas:** enlaces en la sección final del documento, no inline.
- **No inventar contenido de Miro**: si un dato no aparece en `miro-research-phase.md` ni puede re-extraerse del tablero, no escribirlo como si fuera canónico.

## MCP disponibles en este workspace

- **Miro** (`mcp__miro__*`) — uso principal: `context_explore` para mapear el tablero, `context_get` / `doc_get` / `table_list_rows` para extraer contenido detallado de items específicos (vía `?moveToWidget=<id>`). Ver `miro-research-phase.md` para los IDs ya conocidos.
