"""Contexto compacto de STARK-VIX inyectado a los nodos del extractor.

Sirve como marco para que el agente compute:
  - `benefit`: por qué este paper importa al proyecto
  - `pitch_mapping`: mapeo sección→dimensión del pitch

Mantener este bloque < 700 tokens para no comerse el budget del modelo local.
Las fuentes canónicas son `softserve-analisis-reto3.md` + `miro-research-phase.md`
(workspace raíz). Si esas cambian, revisar consistencia aquí.
"""
from __future__ import annotations

PROJECT_BRIEF: str = """
# STARK-VIX · Asistente de Investigación Multi-Agente (DataHack 2026 · Reto #3)

## Propósito
Acelerar el descubrimiento, lectura crítica y síntesis de literatura científica.
Tres perfiles lo usan: (a) tesistas de IU Pascual Bravo, (b) R&D Engineers de
SoftServe, (c) Intelligence Engineers corporativos.

## Sponsor y tesis del pitch
Sponsor del reto: SoftServe. El MVP replica deliberadamente su *Multi-Agent RAG
Platform* (AWS Marketplace) y su *Insights Engine Pilot*. Todo paper que valide
esta arquitectura es alto valor para el pitch.

## Stack técnico (decisiones firmes)
- Orquestación: LangGraph con patrón jerárquico Master Agent + sub-agentes.
- LLMs: agnóstico — default local con Gemma 2 via Ollama; providers cloud
  disponibles (Anthropic, OpenAI, Google) — el usuario elige su set.
- Retrieval: pgvector (local) o Pinecone; embeddings BGE / voyage / arctic.
- Infra: AWS (Bedrock, Lambda, OpenSearch) como referencia de despliegue.

## Pilares de valor (dog-whistles del pitch)
1. **Multi-Agent RAG**: retrieval + reasoning como tareas agénticas coordinadas.
2. **Citas trazables con anchor**: cada afirmación del asistente apunta a una
   sección/figura/tabla/página verificable en el PDF original.
3. **Evaluation harness**: groundedness, faithfulness, citation accuracy,
   process-aware metrics — no solo output-level.
4. **Guardrails**: autonomía con planning horizons acotados, tool-access
   policies, stopping criteria explícitos. Explainability + auditability como
   first-class design goals.
5. **Agentic (no chatbot)**: flujos multi-paso con decisión dinámica sobre
   cuándo recuperar, reformular, validar y parar.

## Dimensiones del pitch (para pitch_mapping)
- `architecture`: arquitectura master-agent + sub-agentes especializados
- `stack_validation`: frameworks (LangGraph, LlamaIndex, CrewAI, Bedrock…)
- `corrective_layer`: validación de citas / detección de alucinación
- `document_workflows`: ingesta estructurada de papers (parse → rules → state)
- `responsible_deployment`: traceability, auditability, explainability
- `evaluation_harness`: groundedness, faithfulness, citation accuracy
- `domain_fit`: especialización de dominio amplifica valor agéntico

## Qué convierte un paper en útil
- **Alto valor**: papers fundacionales de reasoning+acting/agentes (ReAct,
  Reflexion, CRITIC), surveys de Agentic RAG, papers de eval de groundedness.
- **Valor medio**: papers empíricos con métricas concretas replicables.
- **Valor bajo**: opinión sin experimentos, surveys sin taxonomía propia.
""".strip()


__all__ = ["PROJECT_BRIEF"]
