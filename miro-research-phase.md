# Research Phase — Miro Board DataHack 2026 (Reto #3)

> Consolidado de la fase de **Research** del proyecto **STARK-MIND / STARK-VIX** — Asistente Inteligente para Artículos de Investigación.
>
> **Fuente:** [Miro Board — uXjVHeyNC2U](https://miro.com/app/board/uXjVHeyNC2U=/)
> **Fecha de extracción:** 2026-04-21

---

## Índice

1. [Plan de desarrollo DataHack (documento maestro)](#1-plan-de-desarrollo-datahack-documento-maestro)
2. [Benchmarking competitivo (7 productos)](#2-benchmarking-competitivo-7-productos)
3. [Arquitectura multiagente (diagrama)](#3-arquitectura-multiagente-diagrama)
4. [User Journeys — 3 personas objetivo](#4-user-journeys--3-personas-objetivo)
5. [Framework de decisiones UX (8 preguntas)](#5-framework-de-decisiones-ux-8-preguntas)
6. [Mapa del tablero](#6-mapa-del-tablero)

---

## 1. Plan de desarrollo DataHack (documento maestro)

**Reto #3:** Asistente inteligente para artículos de investigación.

### Contexto

Tanto en el entorno académico como en empresarial, la investigación es esencial para la innovación, el aprendizaje y la toma de decisiones. En **IU Pascual Bravo**, estudiantes e investigadores necesitan explorar literatura técnica de manera eficiente para apoyar cursos, proyectos aplicados e investigación académica.

En **SoftServe**, ingenieros y equipos orientados a R&D (Research and Discovery) necesitan seguir los avances en IA y otras áreas tecnológicas de vanguardia para identificar métodos relevantes, evaluar oportunidades y acelerar la innovación. En ambos contextos aparece el mismo problema de forma recurrente: hay demasiada información, muy poco tiempo y demasiado esfuerzo involucrado en encontrar los artículos adecuados, extraer sus ideas clave, compararlos y convertirlos en conocimiento útil.

### Desafío

Construir un **Asistente Inteligente para Artículos de Investigación**, una aplicación multiagente que ayude a los usuarios a interactuar con la literatura científica de una forma más práctica, eficiente y accionable. Más que funcionar como una simple herramienta de búsqueda, el asistente debe:

- Descubrir artículos relevantes.
- Resumir sus aportes.
- Comparar enfoques.
- Identificar tendencias importantes.
- Responder preguntas concretas con base en las fuentes disponibles.

Debe ser especialmente útil para temas de IA y otras tecnologías de frontera, donde aparecen nuevas publicaciones con rapidez y mantenerse al día con el estado del arte es difícil.

### MVP propuesto: STARK-MIND / STARK-VIX

#### North Star

Un **co-investigador multiagente** que convierte papers científicos en conocimiento accionable: descubre, resume, compara, detecta tendencias y responde con **citas trazables**.

#### 5 capacidades núcleo

1. **Descubrir** — búsqueda semántica sobre arXiv, bioRxiv, PubMed y Semantic Scholar.
2. **Resumir** — extracción estructurada (problema, método, resultados, limitaciones).
3. **Comparar** — tabla editable de papers lado a lado con enfoques y métricas.
4. **Detectar tendencias** — timeline de tópicos y señales de crecimiento.
5. **Q&A con citas** — respuestas con *anchors* al párrafo o figura exacta del paper.

#### Arquitectura multiagente (patrón Master Agent)

- **Orchestrator** coordina el plan de acción.
- **Discovery Agent** ejecuta queries a las fuentes.
- **Reader / RAG Agent** extrae contenido multimodal (texto, tablas, figuras).
- **Comparator Agent** alinea papers por dimensiones comparables.
- **Synthesizer Agent** produce reportes con tendencias y recomendaciones.
- **Citation-Guard Agent** valida que toda afirmación tenga fuente.

#### Stack propuesto

| Capa | Tecnología |
|---|---|
| LLM | Claude (Anthropic) — el que SoftServe usó en AgentForge |
| Orquestación | LangGraph con patrón jerárquico |
| Vector DB | pgvector o Pinecone |
| Cloud | AWS (Bedrock + Lambda + OpenSearch) |
| Frontend | Next.js + shadcn/ui + Tremor |

#### Diferenciadores que hablan a SoftServe

- Replica su **Multi-Agent RAG Platform** (AWS Marketplace) con dominio vertical.
- Es su **Insights Engine Pilot** aplicado a literatura científica.
- Comportamiento **agentic** (planea, ejecuta, autocorrige) vs. chatbot.
- **Evaluation harness** integrado: groundedness, faithfulness, citation accuracy.
- Salida exportable (Markdown, PDF, Notion, Jira).

> Documentación complementaria: análisis completo del sponsor y estrategia de pitch en `softserve-analisis-reto3.md`.

---

## 2. Benchmarking competitivo (7 productos)

Análisis de productos existentes con foco en **qué adoptar** y **qué evitar**. Las prioridades "Alta" son los referentes principales.

| # | Producto | Prioridad | Qué hace bien | Qué tomamos | Qué evitamos |
|---|---|---|---|---|---|
| 1 | **Elicit.com** | 🔴 Alta | Tabla viva de papers con columnas personalizables (método, datos, hallazgos). Extracción estructurada automática. Búsqueda semántica sobre literatura empírica. | Paradigma de **tabla comparativa editable**; columnas definibles por el usuario; extracción estándar problema/método/resultados/limitaciones. | Sesgo fuerte hacia biomedicina y empírico; UI densa sin jerarquía visual clara; no hay proceso agentic visible. |
| 2 | **Undermind.ai** | 🔴 Alta | Búsqueda agentic iterativa de literatura científica. Explica su proceso de descubrimiento. Muy preciso en papers de nicho. | Modelo de **búsqueda agentic explícita** (lo más cercano a nuestro concepto); transparencia del proceso; priorización por relevancia semántica. | UX muy lenta (minutos por query sin feedback intermedio); sin comparación estructurada entre resultados. |
| 3 | **Perplexity Deep Research** | 🔴 Alta | Streaming del pensamiento agentic en vivo. Iteración multi-query. Reporte largo final con citas numeradas. | **Streaming del proceso de razonamiento**; multi-step reasoning visible; estructura del reporte final con secciones y citas. | Optimizado para web general, no literatura científica; ignora metadata académica (venue, citas, autores, h-index). |
| 4 | **NotebookLM (Google)** | 🔴 Alta | Gold standard de **citas inline con preview** al párrafo exacto. Layout tri-panel (sources + notas + chat). Genera briefings y podcasts. | Patrón de **citas inline con popover** al párrafo; layout tri-panel; generación automática de briefings/reportes. | No descubre papers (el usuario debe subirlos); no es agentic; no compara sistemáticamente entre documentos. |
| 5 | **Consensus.app** | 🟡 Media | Consensus Meter que visualiza acuerdo/desacuerdo entre papers. Síntesis cuantitativa de evidencia. Ideal para preguntas Yes/No. | Idea del **medidor visual** para síntesis de evidencia; UX de pregunta → veredicto con soporte de papers. | Formato acotado a preguntas simples; poca profundidad para investigación exploratoria o descubrimiento abierto. |
| 6 | **ResearchRabbit** | 🟡 Media | Exploración visual tipo grafo de citas y co-autoría. Alertas de nuevos papers. Colecciones compartibles. | Grafo como **modo secundario** de exploración; patrón de colecciones persistentes; alertas de literatura nueva por tópico. | El grafo como UI principal abruma al usuario nuevo; poca síntesis del contenido real de los papers. |
| 7 | **SciSpace / Paperpal** | 🟢 Baja | Lector PDF con chat lateral contextual al paper. Explicación de fórmulas, figuras y términos técnicos al hover. | Experiencia de **lectura con chat contextual** por paper; explicación de elementos complejos on-demand. | Centrado en un paper a la vez; sin visión de corpus; sin síntesis cruzada entre múltiples fuentes. |

### Lecciones clave del benchmarking

- **Extracción estructurada** (Elicit) + **transparencia agentic** (Undermind) + **streaming** (Perplexity) + **citas inline con anchor** (NotebookLM) = combinación que ningún producto ofrece completa. Ese es nuestro espacio.
- Ningún competidor une descubrimiento agentic + comparación estructurada en un solo flujo.
- El grafo (ResearchRabbit) funciona como complemento, no como UI principal.
- El medidor de evidencia (Consensus) es un patrón valioso pero limitado a Y/N.

---

## 3. Arquitectura multiagente (diagrama)

### Overview

Sistema multiagente orquestado para buscar, analizar y sintetizar literatura académica con **citas trazables**.

### Elementos clave

- **User Interface** — punto de entrada donde el usuario envía queries.
- **Orchestrator** — componente central de decisión que rutea hacia agentes especializados.
- **Agentes especializados (6):**
  - **Discovery Agent** — busca a través de las fuentes de literatura.
  - **Reader / RAG Agent** — procesa y recupera contenido documental.
  - **Comparator Agent** — analiza y compara información.
  - **Synthesizer Agent** — combina información de múltiples fuentes.
  - **Citation-Guard Agent** — valida precisión y trazabilidad de citas.
- **Fuentes de literatura (4):** PubMed, Semantic Scholar, arXiv, bioRxiv.
- **Data Storage:** base de datos vectorial (pgvector) para embeddings.
- **Output:** respuesta con citas trazables.

### Flujo

1. La query del usuario entra por el nodo **Usuario**.
2. El **Orchestrator** la recibe y delega a agentes según el tipo de tarea: `Buscar`, `Leer`, `Comparar`, `Sintetizar`.
3. El **Discovery Agent** conecta con las cuatro fuentes de literatura para encontrar papers relevantes.
4. El **Reader/RAG Agent** interactúa con la base de datos vectorial para recuperación documental.
5. El **Comparator Agent** recibe datos del Synthesizer.
6. El **Synthesizer Agent** envía output al **Citation-Guard Agent** para validación.
7. El **Citation-Guard Agent** produce la respuesta final con citas verificadas.

### Convención visual

- **Verde**: puntos de contacto con usuario.
- **Azul**: orquestación.
- **Amarillo**: agentes de procesamiento y fuentes de datos.
- Etiquetas de comando del Orchestrator: `Buscar`, `Leer`, `Comparar`, `Sintetizar`, `Validar`.

---

## 4. User Journeys — 3 personas objetivo

Tres flujos paralelos que comparten patrón **research → analysis → synthesis → delivery**, pero difieren en contexto, cadencia y entregable.

### Persona 1 — Tesista de Pascual Bravo

```
Tesis o proyecto aplicado
  → Buscar tema relevante
  → Leer papers clave
  → Extraer ideas y métodos
  → Citar y comparar
  → Redactar marco teórico
```

- **Motivación:** entregable académico (tesis, proyecto aplicado).
- **Cadencia:** por semestre, intensiva al inicio.
- **Valor del asistente:** acelera la construcción del marco teórico con citas correctas.

### Persona 2 — R&D Engineer de SoftServe

```
Nuevo proyecto de R&D
  → State of the art
  → Comparar enfoques
  → Evaluar viabilidad técnica
  → Decidir método a usar
  → Proponer al equipo
```

- **Motivación:** elegir técnica/arquitectura para un proyecto cliente o interno.
- **Cadencia:** por proyecto (semanas).
- **Valor del asistente:** reduce el tiempo de *state-of-the-art* y documenta la decisión técnica con trazabilidad.

### Persona 3 — Intelligence Engineer

```
Monitoreo semanal
  → Escanear fuentes
  → Detectar tendencias
  → Validar señales
  → Compilar briefing
  → Compartir al equipo
```

- **Motivación:** inteligencia competitiva continua.
- **Cadencia:** semanal / continua.
- **Valor del asistente:** automatiza la detección de señales y el armado del briefing.

### Observaciones transversales

- Los tres journeys convergen en los mismos **5 núcleos** del MVP (descubrir → resumir → comparar → detectar tendencias → Q&A con citas), pero los pesos cambian:
  - **Tesista** → peso alto en *resumir* + *citar*.
  - **R&D Engineer** → peso alto en *comparar* + *evaluar viabilidad*.
  - **Intelligence Engineer** → peso alto en *detectar tendencias* + *sintetizar briefing*.
- Esto justifica la arquitectura multiagente: el mismo sistema atiende las 3 personas **reorganizando** qué agentes lideran cada flujo.

---

## 5. Framework de decisiones UX (8 preguntas)

Decisiones de diseño críticas con trade-offs explícitos y estado de resolución del equipo.

| # | Pregunta | Opción A | Opción B | Decisión | Trade-off clave |
|---|---|---|---|---|---|
| 1 | ¿Chat-first o workspace-first? | Chat puro tipo ChatGPT o Perplexity | Workspace multi-panel tipo NotebookLM (sources + chat + notas) | 🟡 **Híbrido** | Simplicidad y velocidad de entrada vs. densidad de información y control del usuario. |
| 2 | ¿Cómo visualizamos las citas? | Inline `[1]` con popover de preview | Panel lateral con highlights al párrafo o figura exacta | 🔵 **Opción A** | Flujo de lectura continuo vs. trazabilidad completa y auditoría de fuente. |
| 3 | ¿Cómo se comparan los papers? | Tabla comparativa editable (estilo Elicit) | Grafo visual de relaciones (estilo ResearchRabbit) | 🔵 **Opción A** | Profundidad analítica estructurada vs. descubrimiento de conexiones entre autores y temas. |
| 4 | ¿Cómo mostramos el pensamiento agentic del sistema? | Streaming en vivo del razonamiento (estilo Perplexity Deep Research) | Tarjetas colapsables por agente con su output | 🩷 **Opción B** | Transparencia y "sensación de magia" vs. ruido cognitivo y scroll infinito. |
| 5 | ¿Qué persiste entre sesiones? | Solo historial de queries | Proyectos persistentes con papers + notas + reportes | 🩷 **Opción B** | Simplicidad del MVP vs. valor acumulado del usuario y retención. |
| 6 | ¿Cómo mostramos tendencias temporales? | Timeline lineal de publicaciones y tópicos | Heatmap o bubble chart de tópicos emergentes | 🔵 **Opción A** | Evolución temporal clara vs. panorama general del espacio de investigación. |
| 7 | ¿Cómo exportamos el conocimiento generado? | Solo Markdown y PDF descargable | Integración directa con Notion, Obsidian, Jira o Confluence | 🟡 **Híbrido** | MVP rápido y sin fricción vs. valor empresarial alineado con SoftServe. |
| 8 | ¿Cómo diferenciamos de ChatGPT en los primeros 30 segundos? | Demo guiada con prompts preparados y output ejemplo | Empty state con 3 casos de uso visuales clickeables | 🔵 **Opción A** | Dirección fuerte del producto vs. libertad y exploración del usuario. |

### Síntesis de decisiones

- **Arquitectura de UI:** Workspace híbrido con chat panel — inline citations con popover — tabla comparativa editable — tarjetas colapsables por agente — proyectos persistentes — timeline lineal — export híbrido — demo guiada al empezar.
- **Patrón dominante:** equilibrio entre **simplicidad del MVP** y **valor enterprise** alineado con SoftServe (especialmente en #5 persistencia y #7 export).
- **Pendientes de validación:** ninguna decisión está "En discusión" — el framework está cerrado, pero los *híbridos* (#1, #7) requieren definición de alcance concreto para el MVP.

---

## 6. Mapa del tablero

Ubicación espacial de los artefactos en el tablero:

| Artefacto | Tipo | Coordenadas (aprox.) | URL |
|---|---|---|---|
| Plan desarrollo DataHack | Documento | `(-433, -977)` | [Abrir](https://miro.com/app/board/uXjVHeyNC2U=/?moveToWidget=3458764668785531066) |
| Benchmarking competitivo (7 productos) | Tabla | `(-461, 978)` | [Abrir](https://miro.com/app/board/uXjVHeyNC2U=/?moveToWidget=3458764668790178650) |
| Arquitectura multiagente | Diagrama | `(5020, -204)` | [Abrir](https://miro.com/app/board/uXjVHeyNC2U=/?moveToWidget=3458764668790178770) |
| User Journeys — 3 personas | Diagrama | `(5020, 1499)` | [Abrir](https://miro.com/app/board/uXjVHeyNC2U=/?moveToWidget=3458764668790418414) |
| Decisiones UX (8 preguntas) | Tabla | `(-452, 2118)` | [Abrir](https://miro.com/app/board/uXjVHeyNC2U=/?moveToWidget=3458764668790418450) |

### Lectura del tablero

El tablero sigue un flujo lógico **estrategia → research → arquitectura → experiencia de diseño**:

1. **Plan maestro** (arriba izquierda) — establece visión del producto y diferenciadores alineados con SoftServe.
2. **Benchmarking** (centro abajo) — informa qué patrones adoptar/evitar, alimenta directamente las decisiones UX.
3. **Arquitectura** (derecha arriba) — traduce el enfoque multiagente conceptual en flujo técnico.
4. **User Journeys** (derecha medio) — valida la arquitectura contra workflows reales de 3 personas.
5. **Decisiones UX** (abajo izquierda) — operacionaliza los insights del competitive research en elecciones concretas.

---

## Próximos pasos sugeridos (post-Research)

- [ ] Cerrar alcance de los **híbridos** pendientes (#1 chat/workspace, #7 export).
- [ ] Definir el **evaluation harness** concreto: métricas, dataset, umbrales de aceptación.
- [ ] Traducir la arquitectura a la implementación: especificar *tools*, contratos entre agentes y prompts base.
- [ ] Prototipar los 3 flujos de las personas en Figma o Miro Prototype.
- [ ] Preparar el pitch deck con la narrativa SoftServe (ver `softserve-analisis-reto3.md`).
