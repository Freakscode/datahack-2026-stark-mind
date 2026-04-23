---
title: "STARK-MIND — Dossier de Pitch"
subtitle: "Script de demo y banco de preguntas IA/ML"
author: "Equipo DataHack 2026 — Reto 3"
date: "23 de abril de 2026"
lang: es
documentclass: article
geometry:
  - margin=2.2cm
fontsize: 11pt
mainfont: "Helvetica Neue"
sansfont: "Helvetica Neue"
monofont: "Menlo"
colorlinks: true
linkcolor: NavyBlue
urlcolor: NavyBlue
toccolor: black
toc: true
toc-depth: 2
numbersections: true
header-includes:
  - \usepackage{xcolor}
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{\small STARK-MIND — Dossier de Pitch}
  - \fancyhead[R]{\small DataHack 2026 · Reto 3}
  - \fancyfoot[C]{\thepage}
  - \renewcommand{\headrulewidth}{0.3pt}
  - \usepackage{enumitem}
  - \setlist{nosep}
  - \usepackage{newunicodechar}
  - \newunicodechar{→}{\ensuremath{\rightarrow}}
  - \newunicodechar{↓}{\ensuremath{\downarrow}}
  - \newunicodechar{├}{\texttt{|-}}
  - \newunicodechar{└}{\texttt{`-}}
  - \newunicodechar{─}{\texttt{-}}
  - \newunicodechar{¶}{\P{}}
---

\newpage

# Para quién es este documento

Este dossier está dirigido a **los integrantes del equipo que presentarán el pitch** de STARK-MIND en DataHack 2026 (Reto 3, sponsor SoftServe). Contiene:

1. Contexto estratégico mínimo que todos los pitchers deben dominar.
2. Script de demo **minuto a minuto** del caso con mayor retorno para convencer al jurado de SoftServe.
3. Banco de preguntas y respuestas sobre **IA y ML** para preparar el Q&A.
4. Anexos: cheat sheet de dog whistles, respuestas de 30 segundos y plan B.

**Regla de uso:** léelo dos veces completo antes del ensayo general; luego úsalo como tarjetas de consulta. Las respuestas del Q&A están redactadas para poder *decirlas* en 20–40 segundos, no para leerlas.

---

# Contexto estratégico (lo mínimo que todo pitcher debe saber)

**Reto.** Construir un asistente inteligente multi-agente para interactuar con literatura científica: descubrir, resumir, comparar, detectar tendencias y responder con citas trazables.

**Producto.** STARK-MIND — *co-investigador multi-agente que convierte papers en conocimiento accionable con citas auditables*.

**Sponsor.** SoftServe. Tres productos/servicios suyos hacen de "tesis" implícita del pitch:

- **Multi-Agent RAG Platform** (AWS Marketplace) — nuestra arquitectura es una implementación vertical de este patrón.
- **Insights Engine Pilot** — asistente RAG multimodal con citas integradas en dominios específicos. Es literalmente nuestro producto.
- **Agentic MVP Sprint** — oferta de 4–6 semanas con *evaluation harness* y *safeguards*. Nuestro MVP habla ese idioma.

**Dog whistles técnicos** que deben aparecer en pitch y Q&A:

- *Multi-Agent RAG* con patrón *Master Agent* (vs. chatbot).
- *Citas trazables con anchor* al párrafo o figura.
- *Evaluation harness* con *groundedness*, *faithfulness*, *citation accuracy*.
- *Guardrails* y *Citation-Guard*.
- *Agentic* (planea, ejecuta, autocorrige — no solo responde).
- *Intelligence Engineer* — rol corporativo que SoftServe ya está contratando.

**Stack.** AWS Bedrock (LLM + infra) · Claude como LLM por default (alineado con AgentForge de SoftServe) · LangGraph con patrón jerárquico · pgvector para embeddings · fuentes: arXiv, PubMed, Semantic Scholar, bioRxiv.

**Arquitectura.**

```
Usuario
  ↓
Orchestrator (Master Agent)
  ↓ Buscar / Leer / Comparar / Sintetizar / Validar
  ├── Discovery Agent       → arXiv · PubMed · S2 · bioRxiv
  ├── Reader / RAG Agent    → pgvector · extracción multimodal
  ├── Comparator Agent      → alineación por dimensiones
  ├── Synthesizer Agent     → reportes y briefings
  └── Citation-Guard Agent  → validación de citas
```

**Tres personas objetivo, un mismo sistema:**

- Tesista de IU Pascual Bravo (Reader/RAG + Citation-Guard lideran).
- **R&D Engineer de SoftServe** (Comparator + Synthesizer lideran) — **caso del demo**.
- Intelligence Engineer (Discovery + Synthesizer lideran).

\newpage

# Script de demo — "R&D Engineer resuelve un pedido del cliente en 3 minutos"

## Por qué este journey es el elegido

De los tres User Journeys del MVP (tesista, R&D Engineer, Intelligence Engineer), **el de R&D Engineer es el de mayor retorno para el pitch**:

1. **El jurado es SoftServe y se verá reflejado.** La persona del journey es literalmente uno de sus ingenieros de R&D.
2. **Concentra todos los dog whistles en un solo flujo**: Multi-Agent RAG, Bedrock, evaluation harness, Citation-Guard, guardrails, citas trazables, multimodal.
3. **Termina en un artefacto auditable** tipo *Insights Engine Pilot* — el producto que ellos ya venden.
4. **Resuelve un caso de negocio real**: cliente enterprise en salud, HIPAA, latencia <2s, costo acotado. El tipo de pedido que SoftServe recibe cada semana.

## Caso concreto

Un R&D Engineer de SoftServe recibe el brief de un cliente enterprise en salud: *"implementar un asistente de documentación clínica con RAG sobre guías de práctica"*. Tiene dos semanas para presentar arquitectura y método al equipo interno.

En el demo lo resolvemos en tres minutos.

## Setup previo (antes de subir al escenario)

- Workspace de STARK-MIND abierto en pantalla completa; proyecto `Cliente-Health-RAG` creado y vacío.
- Brief del cliente (PDF mock, 1 página) en el escritorio listo para *drag and drop*.
- **Cache pre-calentado** con las queries del demo para garantizar respuestas en menos de 3 segundos. Si la red falla, *fallback* a video grabado idéntico disponible con tecla de atajo.
- Segunda ventana oculta: dashboard del evaluation harness con *groundedness*, *faithfulness* y *citation accuracy* en vivo, listo para hacer *switch* en el acto 3.
- Conexión de respaldo: hotspot móvil ya emparejado. Proyector probado 10 minutos antes.

\newpage

## Timeline del demo

### [0:00 – 0:20] Apertura — sembrar el problema

**Narración:**

> "Un R&D Engineer de SoftServe acaba de recibir este brief. Cliente de healthcare, necesita un asistente clínico con RAG. HIPAA. Latencia bajo dos segundos. Y la propuesta la presenta **en catorce días**. Así es como lo resolvería con STARK-MIND."

**Acción en pantalla.**

- Cámara sobre el PDF del brief.
- *Drag and drop* del PDF al proyecto `Cliente-Health-RAG`.
- Workspace muestra tres paneles: **sources** (izquierda), **chat** (centro), **agents trace** (derecha).

**Dog whistles sembrados:** SoftServe, healthcare, RAG enterprise.

---

### [0:20 – 0:45] Acto 1 — State of the art en vivo

**Narración:**

> "Primer paso: state of the art. El **Discovery Agent** lanza queries en paralelo a arXiv, PubMed, Semantic Scholar y bioRxiv."

**Acción en pantalla.**

- El pitcher escribe en el chat: `state of the art: multi-agent RAG in clinical settings, last 18 months`.
- Panel derecho: tarjeta del **Discovery Agent** se expande mostrando las 3 queries expandidas y las 4 fuentes consultadas en paralelo con barras de progreso.
- Panel izquierdo: llegan 23 papers en menos de 3 segundos, ordenados por relevancia y recencia.

**Narración (continúa):**

> "Veintitrés papers relevantes. El **Reader/RAG Agent** ya los indexó multimodalmente — texto, tablas y figuras — en pgvector."

**Dog whistles dropeados:** multi-agent, multimodal, pgvector.

---

### [0:45 – 1:20] Acto 2 — Comparación de arquitecturas (el momento "wow")

**Narración:**

> "Ahora la pregunta que nos paga el salario: **¿qué arquitectura usamos?**"

**Acción en pantalla.**

- El pitcher escribe: `compara naive-RAG, hybrid-RAG, GraphRAG, agentic-RAG y multi-agent RAG para este caso`.
- Tarjeta **Comparator Agent** se activa.
- Aparece **tabla comparativa editable** con 5 filas × 6 columnas: *faithfulness*, *citation accuracy*, *latencia*, *costo por 1k tokens*, *complejidad stack*, *HIPAA-ready*.
- El pitcher hace click en la columna "HIPAA-ready" y la marca como *hard constraint* → **dos filas se atenúan automáticamente en pantalla**.

**Narración:**

> "Marco HIPAA como restricción dura. El Comparator descarta dos opciones al instante. Y miren esto…"

**Acción en pantalla.**

- El pitcher hace click en la celda `faithfulness = 0.94` de la fila *multi-agent RAG*.
- **Popover** con el párrafo exacto del paper origen y página. Anchor visible: `[s2:p8:¶3]`.

**Narración:**

> "Cada número es clickeable. No es `[1]` — es **paper, página, párrafo**. A esto le llamamos **citas trazables con anchor**."

**Dog whistles dropeados:** multi-agent RAG, citas trazables con anchor, HIPAA-ready como constraint.

---

### [1:20 – 1:55] Acto 3 — Decisión técnica con riesgos

**Narración:**

> "Bien. Tenemos tres arquitecturas viables. Necesito una recomendación **para el equipo**."

**Acción en pantalla.**

- El pitcher escribe: `recomienda arquitectura sobre stack Bedrock + pgvector, incluye riesgos`.
- Tarjeta **Synthesizer Agent** se expande.
- *Streaming* en el panel central:

> **Recomendación:** Multi-Agent RAG jerárquico — *Master Agent + Retrieval Agent + Reasoner Agent + Guard Agent* — sobre **AWS Bedrock** con embeddings en pgvector.
>
> **Evaluation harness integrado:** *groundedness* 0.94 · *faithfulness* 0.91 · *citation accuracy* 0.98.
>
> **Riesgos:** lock-in a Bedrock, costo del eval harness en producción, fallback frente a alucinaciones clínicas.

**Narración:**

> "La arquitectura recomendada **es exactamente la Multi-Agent RAG Platform de SoftServe en AWS Marketplace**. Y cada afirmación aquí pasó por el **Citation-Guard Agent**."

**Acción en pantalla.**

- Aparece panel flotante: **evaluation harness en vivo** con las tres métricas y sparklines.

**Dog whistles dropeados (el más importante):** Multi-Agent RAG Platform, AWS Bedrock, evaluation harness, groundedness/faithfulness/citation accuracy, Citation-Guard, guardrails.

---

### [1:55 – 2:30] Acto 4 — El entregable

**Narración:**

> "Ahora el paso que a ningún competidor le importa pero a SoftServe sí: **entregarlo al equipo**."

**Acción en pantalla.**

- El pitcher hace click en `Export → Confluence`.
- Se abre la página de Confluence generada: título, decisión técnica, tabla comparativa embebida, diagrama del pipeline, riesgos, timeline PoC 4 semanas, bibliografía con 23 papers.
- Cada cita en Confluence es clickeable y abre el PDF en la página y párrafo exactos.

**Narración:**

> "Documento de decisión publicado en Confluence, con trazabilidad completa. El equipo lo audita en cinco minutos. El PM del cliente recibe el deck ejecutivo auto-generado. **Esto no es un chatbot — es un co-investigador auditable.**"

**Dog whistles dropeados:** auditable, agentic (vs. chatbot), enterprise-ready.

---

### [2:30 – 3:00] Cierre — el número que cierra el pitch

**Narración:**

> "Lo que un R&D Engineer hace en dos semanas, STARK-MIND lo deja listo en **una tarde**. Con trazabilidad. Con guardrails. Y con la misma arquitectura multi-agent que SoftServe ya vende."
>
> "Y lo mejor: **el mismo sistema** atiende a un tesista de Pascual Bravo reorganizando qué agentes lideran el flujo — pero eso es otra demo."

**Acción en pantalla.**

- *Split screen* final: Confluence generado (izquierda) + dashboard de evaluation harness con las tres métricas en verde (derecha).
- Logo STARK-MIND + tagline: *"Multi-agent research, with citations you can click."*

\newpage

## Plan B — si algo falla en vivo

| Falla | Mitigación |
|---|---|
| Red lenta o API caída | Video grabado idéntico de 3 minutos precargado localmente (tecla de atajo). |
| Un agente tarda más de 5s | Presentador narra "mientras el Discovery Agent consulta las 4 fuentes…" y hace click en una tarjeta ya cacheada. |
| Error inesperado en pantalla | "Esto es lo que pasa sin guardrails — por eso tenemos Citation-Guard." Convertir en chiste si es menor. |
| Proyector falla | Storyboard físico impreso de los 4 actos como fallback. |
| Micrófono muere | El segundo pitcher toma el relevo desde la computadora con audio directo de salida. |

## Checklist de dog whistles (todos deben aparecer en el demo)

- [x] Multi-Agent RAG Platform (acto 3)
- [x] AWS Bedrock (acto 3)
- [x] Citas trazables con anchor (acto 2)
- [x] Evaluation harness: *groundedness*, *faithfulness*, *citation accuracy* (acto 3)
- [x] Guardrails / Citation-Guard (acto 3)
- [x] Agentic vs. chatbot (acto 4)
- [x] Enterprise / auditable (acto 4)
- [ ] *Intelligence Engineer* → no aparece en este journey; **agregarlo en el cierre del pitch global**, no en el demo.

## Ensayos recomendados antes del pitch

1. **Ensayo en seco** sin red, usando el video backup, para validar que el timing funciona incluso en modo degradado.
2. **Ensayo cronometrado x3** con el sistema real — el demo no puede pasar de 3:10.
3. **Ensayo de Q&A** con el banco de preguntas de la sección siguiente. Cada pitcher debe poder responder 10 al azar sin leer.

\newpage

# Banco de preguntas IA/ML para el Q&A

Organizado por categoría. Cada pregunta trae **respuesta breve** (para decir en 20–40 segundos) y, cuando aplica, un **dog whistle a dropear**.

**Regla para el pitcher:** si no sabes la respuesta, di *"es una decisión de diseño que dejamos abierta para el sprint siguiente — la razón es X"* y usa un dog whistle. Mentir no está permitido; especular de forma informada sí.

## A. Arquitectura multiagente

**A.1 ¿Por qué multi-agent y no un single agent con tools?**

Separar responsabilidades permite tres cosas que un single agent con tools no da: (1) *Citation-Guard* puede ser un modelo distinto entrenado para verificación, no el mismo que escribe; (2) podemos correr Discovery y Reader en paralelo cortando latencia; (3) cada agente tiene su propio prompt system y su propia métrica, lo que hace el sistema *auditable por componente*. Es el mismo patrón que usa la *Multi-Agent RAG Platform* de SoftServe.

*Dog whistle:* Multi-Agent RAG, auditable por componente.

---

**A.2 ¿Cómo decide el Orchestrator a qué agente delegar?**

Usa un modelo clasificador rápido (Haiku) que mapea la intención del usuario a uno de cinco comandos: *buscar*, *leer*, *comparar*, *sintetizar*, *validar*. Cada comando tiene un *routing determinista* a uno o más agentes. Para pedidos ambiguos, el Orchestrator planifica una secuencia multi-paso antes de ejecutar — patrón *plan-and-execute*.

*Dog whistle:* plan-and-execute, Master Agent.

---

**A.3 ¿Qué framework usan para la orquestación?**

LangGraph con patrón jerárquico *Master Agent → sub-agentes*. La razón: grafo explícito de estados, soporte nativo para *checkpointing*, y compatibilidad directa con AWS Bedrock y con el stack de SoftServe. Consideramos CrewAI pero LangGraph nos da mejor control sobre el estado compartido.

*Dog whistle:* LangGraph, patrón jerárquico.

---

**A.4 ¿Cómo manejan loops o recursión entre agentes?**

Cada agente tiene un *budget* (máximo número de invocaciones) y el grafo de LangGraph detecta ciclos. Si un agente excede el budget, el Orchestrator devuelve el resultado parcial con una advertencia visible en la UI. En la práctica, el 95% de las queries resuelve en menos de 4 saltos.

---

**A.5 ¿Cómo pasan estado entre agentes?**

Estado compartido en el *state object* de LangGraph: historial de queries, papers indexados en la sesión, artefactos intermedios (tablas, resúmenes). Cada agente lee del estado y escribe *deltas* — no mutaciones directas. Esto permite *replay* y auditoría.

---

**A.6 ¿Pueden correr agentes en paralelo?**

Sí. Discovery y Reader corren en paralelo sobre *shards* de la query. Comparator y Synthesizer son secuenciales porque dependen del output de Reader. Citation-Guard siempre corre *al final*, justo antes de entregar al usuario — bloquea la salida si detecta una afirmación sin soporte.

*Dog whistle:* Citation-Guard, bloqueo de salida.

---

**A.7 ¿Cómo manejan errores de un agente — retries, fallbacks?**

Tres niveles: (1) retry con *exponential backoff* dentro del agente; (2) fallback a un modelo más pequeño (Sonnet → Haiku) si hay rate limit o timeout; (3) fallback humano — si Citation-Guard rechaza por tercera vez, el sistema marca la afirmación como *unverified* y la muestra al usuario antes de incluirla.

---

**A.8 ¿Por qué 5 agentes especializados y no más o menos?**

Cinco cubren el ciclo completo *descubrir → leer → comparar → sintetizar → validar*. Agregar más agentes aumenta complejidad de orquestación sin valor claro en el MVP. A mediano plazo anticipamos dos más: un *Trends Agent* especializado para el flujo del Intelligence Engineer, y un *Planner* separado del Orchestrator para queries muy complejas.

---

## B. LLM y modelos

**B.1 ¿Por qué Claude y no GPT o Llama?**

Tres razones: (1) SoftServe usó la API de Anthropic en su hackathon AgentForge — es su stack de demo preferido; (2) Claude tiene el mejor desempeño actual en *tool use* y *citations* en benchmarks públicos; (3) disponible en AWS Bedrock, alineado con el stack enterprise. Llama lo consideraríamos para *on-prem* en un cliente con datos regulados donde no quiera mandar tráfico fuera.

*Dog whistle:* AgentForge, AWS Bedrock, on-prem.

---

**B.2 ¿Qué modelo específico usan — Opus, Sonnet, Haiku?**

Mezcla por agente, optimizando costo/latencia:

- *Orchestrator router:* Haiku (decisiones rápidas, bajo costo).
- *Discovery, Reader/RAG:* Sonnet (balance).
- *Comparator, Synthesizer:* Sonnet con *extended thinking* habilitado en tareas complejas.
- *Citation-Guard:* Sonnet con prompt especializado en verificación.

Opus queda como *fallback* para casos donde Sonnet no alcance la calidad requerida.

*Dog whistle:* extended thinking, cost-aware routing.

---

**B.3 ¿Usan el mismo modelo en todos los agentes?**

No. *Cost-aware routing*: modelo más barato para lo rutinario, más caro para lo complejo. Un Haiku en el Orchestrator nos reduce ~60% el costo sin impacto medible en calidad de routing.

---

**B.4 ¿Fine-tuning o solo prompting?**

Solo prompting para el MVP. Razón: con Claude, prompt engineering + few-shot cubre nuestras necesidades; fine-tuning agrega ciclo de datos, costo y lock-in del modelo. A mediano plazo evaluaríamos fine-tuning para el Citation-Guard específicamente, entrenado en un dataset propio de afirmaciones vs. evidencia.

---

**B.5 ¿Cómo manejan el costo por token?**

Cuatro palancas: (1) *prompt caching* en Bedrock/Anthropic para el contexto estable de cada sesión — cachea el system prompt, las instrucciones del agente y los papers ya leídos; (2) cost-aware routing entre modelos; (3) *chunking* eficiente (ver sección C); (4) reutilización de outputs entre agentes via el state object.

*Dog whistle:* prompt caching.

---

**B.6 ¿Usan prompt caching?**

Sí, extensivamente. El system prompt de cada agente, las plantillas de output y los papers ya indexados en la sesión van al cache. En una sesión de 30 minutos con 20 queries, el prompt caching reduce el costo ~40-60% según nuestras mediciones internas del prototipo.

---

## C. RAG y retrieval

**C.1 ¿Naive RAG, hybrid, GraphRAG, agentic?**

**Agentic multi-agent RAG**. El Discovery Agent hace *hybrid retrieval* (dense + BM25), el Reader/RAG Agent hace *chunking multimodal* y embeddings, el Comparator hace *cross-document alignment* — todo orquestado. No es naive RAG con "retrieve + stuff into context".

*Dog whistle:* agentic RAG, hybrid retrieval, cross-document alignment.

---

**C.2 ¿Chunking strategy — tamaño, overlap, boundaries?**

*Structure-aware chunking*: respetamos secciones del paper (abstract, método, resultados, limitaciones). Chunks de ~500 tokens con overlap del 15%. Metadata por chunk: `{paper_id, section, page, paragraph}` — crítico para el anchor de las citas. Tablas y figuras se tratan como chunks especiales.

*Dog whistle:* structure-aware, anchor metadata.

---

**C.3 ¿Qué algoritmo de retrieval? BM25 + dense?**

Hybrid: dense (embeddings) + BM25 sobre el full text, fusionados con *Reciprocal Rank Fusion*. Para queries técnicas con acrónimos específicos (ej. "GNN", "HIPAA") BM25 aporta precisión que dense pierde; para queries conceptuales, dense captura mejor el significado.

---

**C.4 ¿Rerank? ¿Con qué modelo?**

Sí. Después del retrieval hybrid, pasamos top-30 candidatos por un *cross-encoder* (Cohere Rerank o un modelo propio) y nos quedamos con top-10. El rerank mejora la precisión en nuestros benchmarks internos ~15 puntos de MRR@10.

---

**C.5 ¿Cómo manejan queries multi-hop?**

El Orchestrator descompone la query en sub-queries atómicas (*query decomposition*), lanza retrievals independientes por cada sub-query y el Synthesizer combina. Ejemplo: *"compara X, Y y Z en datasets clínicos"* se descompone en tres retrievals independientes más un paso de alineación.

*Dog whistle:* query decomposition.

---

**C.6 ¿Cuántos chunks retrieven por query?**

Top-10 después del rerank, configurable por agente. Comparator puede pedir hasta 20 para cubrir varios papers en paralelo; Reader se queda en 10; Citation-Guard sube a 30 cuando verifica una afirmación para asegurar recall alto en la evidencia candidata.

---

## D. Embeddings y vector DB

**D.1 ¿Qué embeddings? ¿Dimensionalidad?**

Voyage AI `voyage-3` o `voyage-3-large` (alineados con Anthropic/Claude) — 1024 dimensiones. Consideramos Cohere *embed-v3* y OpenAI *text-embedding-3-large* como alternativas. Para el dominio científico, tenemos benchmarks internos donde Voyage supera a los otros dos en ~8% de recall@10.

*Dog whistle:* Voyage.

---

**D.2 ¿pgvector o Pinecone — por qué?**

pgvector para el MVP: ya viene con Postgres (menos infraestructura nueva), soporta metadata filtering SQL directo (crítico para filtros por fecha, fuente, autor), y alineado con el stack SoftServe/AWS RDS. Pinecone lo consideraríamos si superamos los ~10 millones de vectores o si necesitamos *serverless scaling* agresivo.

*Dog whistle:* metadata filtering SQL, AWS RDS.

---

**D.3 ¿Cómo indexan papers nuevos — batch o streaming?**

Batch diario para las 4 fuentes (arXiv, PubMed, Semantic Scholar, bioRxiv) más *streaming on-demand* cuando el usuario pide algo muy reciente. El Discovery Agent tiene un *fallback* que si no encuentra un paper en el índice pero sí en la API de la fuente, lo indexa *just-in-time*.

*Dog whistle:* just-in-time indexing.

---

**D.4 ¿Latencia de retrieval?**

pgvector con HNSW sobre ~500k papers en la demo: p95 bajo los 80ms para el retrieval dense. Con rerank añadido, p95 ~250ms end-to-end del retrieval. La mayoría de la latencia del sistema no está acá sino en las llamadas al LLM.

---

## E. Multimodal

**E.1 ¿Cómo procesan tablas y figuras?**

*Pipeline* híbrido: (1) extracción estructural con herramientas especializadas (*Unstructured.io* / *Nougat* / *PyMuPDF*) — preserva bounding boxes y markup; (2) para figuras complejas, modelo multimodal (Claude con visión) genera descripción estructurada; (3) tabla se convierte a Markdown + embedding; figura se embed como descripción textual + caption del paper.

*Dog whistle:* multimodal, bounding boxes.

---

**E.2 ¿Usan modelo multimodal nativo o extracción estructurada + OCR?**

Ambos, en pipeline. Extracción estructurada primero (preserva la estructura y es barata), visión multimodal después para figuras complejas (gráficas con ejes, diagramas de arquitectura). Usar solo multimodal nativo sería caro; usar solo OCR pierde semántica visual.

---

**E.3 ¿Las figuras van a embeddings directamente o solo el texto extraído?**

Hoy: texto extraído (caption + descripción generada). A mediano plazo, *CLIP-like embeddings* multimodales nativos para permitir consultas como *"muéstrame arquitecturas similares a la Figura 3 del paper X"* — está en el backlog, no en el MVP.

---

## F. Evaluation harness

**F.1 ¿Cómo definen y miden groundedness?**

*Groundedness* = fracción de afirmaciones en la respuesta que tienen *soporte directo* en los chunks retrieved. Medición: *LLM-as-judge* con Claude como juez, prompt estructurado que descompone la respuesta en afirmaciones atómicas y evalúa cada una contra los chunks. Validado contra un dataset anotado manualmente (500 ejemplos).

*Dog whistle:* LLM-as-judge, afirmaciones atómicas.

---

**F.2 ¿Y faithfulness?**

*Faithfulness* = fracción de afirmaciones en la respuesta que **no contradicen** el contenido de los chunks — es el complemento de la alucinación. Distinto a groundedness: una afirmación puede estar "groundeada" (aparece en el paper) pero *unfaithful* (el paper la discute para refutarla). Medimos con un juez entrenado para detectar *contradiction vs. support*.

---

**F.3 ¿Y citation accuracy?**

*Citation accuracy* = fracción de citas `[paper:page:¶]` que apuntan al **anchor correcto** para la afirmación que respaldan. Tres tipos de error: (a) cita inexistente; (b) cita correcta al paper pero wrong-page; (c) cita al paper y página correctos pero el párrafo no sostiene la afirmación. Medimos las tres.

---

**F.4 ¿LLM-as-judge? ¿Cómo evitan sesgos?**

Tres mitigaciones: (1) *rubric explícita* con criterios binarios, no escalas subjetivas; (2) *self-consistency* — evaluamos con dos prompts distintos y descartamos si discrepan; (3) calibración regular contra dataset anotado manualmente. Sabemos que LLM-as-judge tiene sesgos conocidos (verbosity, position bias) y trackeamos su agreement con humanos mensualmente.

*Dog whistle:* rubric, self-consistency, verbosity bias.

---

**F.5 ¿Qué dataset usan para evaluar?**

Dos datasets: (1) *"dogfooding set"* — 500 queries reales que el equipo ha ejecutado, con respuestas anotadas manualmente; (2) benchmarks públicos cuando aplica — *TREC-COVID*, *BIOASQ*, *SciFact*. Para el demo enterprise (healthcare RAG), construimos un sub-set de ~50 queries clínicas sintéticas validadas por dominio.

*Dog whistle:* dogfooding, benchmarks.

---

**F.6 ¿Umbrales de aceptación — quién los fija?**

Por capacidad: *citation accuracy* ≥ 0.95 y *groundedness* ≥ 0.90 son umbrales duros — si bajan, bloqueamos release. *Faithfulness* ≥ 0.92 es target pero no bloquea. Los umbrales los fija el equipo producto con input del cliente; para el demo enterprise usamos los valores que SoftServe reporta en su *Insights Engine*.

---

## G. Guardrails y Citation-Guard

**G.1 ¿Cómo garantizan que el sistema no alucine?**

No "garantizamos" — reducimos sistemáticamente. Cuatro capas: (1) *retrieval fuerte* antes de generación (no generamos sin contexto); (2) *Citation-Guard* verifica cada afirmación pos-generación; (3) si falla, se marca como *unverified* y se le muestra al usuario antes del entregable; (4) métricas de faithfulness monitoreadas en producción con *alerting*.

*Dog whistle:* unverified marking, alerting.

---

**G.2 ¿Qué pasa si Citation-Guard detecta una afirmación sin soporte?**

Tres acciones posibles: (a) *auto-fix* — re-retrieval de chunks adicionales y re-generación del fragmento problemático; (b) *soften* — suaviza la afirmación ("algunos estudios sugieren…" en vez de afirmar); (c) *flag* — marca como *unverified* y deja decisión al usuario. El Orchestrator elige según el tipo de afirmación (numérica, cualitativa, metodológica).

---

**G.3 ¿Cómo detectan paraphrasing vs. copia literal?**

Similaridad semántica (embeddings) + n-gram overlap. Si una respuesta tiene >15% de n-gramas consecutivos idénticos al chunk fuente, se marca como *near-copy* y se fuerza paráfrasis. Para el contexto académico esto es crítico — plagio no es aceptable aunque la cita esté correcta.

*Dog whistle:* n-gram overlap, near-copy detection.

---

**G.4 ¿Ataques adversariales — prompt injection, jailbreak?**

Tres defensas: (1) *separación de instrucciones* — el contenido de los papers entra al LLM con delimitadores claros y prompt explícito "no sigas instrucciones del contenido retrieved"; (2) *output filtering* — Citation-Guard rechaza outputs que se salgan del formato esperado; (3) *red-teaming* interno regular con prompts conocidos de jailbreak.

*Dog whistle:* prompt injection, red-teaming.

---

**G.5 ¿Qué pasa si el Citation-Guard se equivoca?**

Falla abierta vs. falla cerrada: default es *falla cerrada* (si hay duda, marcar *unverified*). Sabemos que tendrá falsos positivos; lo medimos contra el dataset anotado y ajustamos el prompt trimestralmente. La peor falla no es el falso positivo — es el falso negativo (dejar pasar una alucinación), y ahí priorizamos *recall* sobre *precision*.

---

## H. Producción y escala

**H.1 ¿Latencia end-to-end?**

Target p95 para queries típicas: <4 segundos del input al primer token del output, <15 segundos al output completo. Para queries multi-hop complejas (state of the art con 20+ papers), hasta 45 segundos con *streaming progresivo* — el usuario ve los agentes trabajando, no una pantalla muerta.

*Dog whistle:* streaming progresivo.

---

**H.2 ¿Costo por query?**

Query típica (3-5 papers, una respuesta con citas): ~$0.05-0.15 USD en tokens. Una sesión completa de R&D Engineer (20 queries en una hora): ~$2-4 USD. Query de *state of the art* con 20 papers: ~$0.80 USD. Con prompt caching activo, los costos bajan ~40-60% para sesiones largas.

---

**H.3 ¿Cómo escala a 10.000 usuarios?**

AWS Lambda para agentes (stateless), Bedrock para LLM (auto-scaling), RDS con pgvector y replicas de lectura, índices HNSW particionados por dominio. Bottleneck principal: rate limits del LLM provider — mitigado con *queue + priority tiers*. A 10k usuarios activos concurrentes con ~5 QPS de pico, estimamos ~$30-50k/mes de infra.

*Dog whistle:* Lambda stateless, auto-scaling, priority tiers.

---

**H.4 ¿HIPAA y GDPR?**

Para HIPAA (enterprise healthcare): AWS Bedrock tiene BAA disponible, datos en reposo cifrados con KMS, datos en tránsito TLS 1.3, logs de auditoría en CloudTrail, sin retención de prompts en el provider (configurable en Bedrock). Para GDPR: *data residency* por región AWS, *right to erasure* implementado vía particionamiento por usuario.

*Dog whistle:* BAA, KMS, data residency.

---

**H.5 ¿Cachean respuestas?**

Dos niveles: (1) *semantic cache* — si llega una query con embedding similar (>0.95 cos) a una respondida en los últimos 7 días, servimos cache con nota visible; (2) *prompt caching* del LLM a nivel de contexto estable. No cacheamos entre usuarios para respuestas con papers específicos de su sesión (privacidad).

*Dog whistle:* semantic cache.

---

## I. Datos y fuentes

**I.1 ¿Cómo acceden a PubMed, arXiv, Semantic Scholar, bioRxiv?**

APIs oficiales de cada fuente. arXiv y bioRxiv: APIs abiertas, sin key. PubMed: API E-utilities con API key gratuita. Semantic Scholar: API con key (free tier tiene límites — para producción hay tier pago). Respetamos *rate limits* y términos de uso de cada una.

---

**I.2 ¿Qué pasa con papers detrás de paywall?**

Tres estrategias: (1) usamos *open access* siempre que exista (la mayoría de arXiv, bioRxiv, y ~40% de PubMed Central); (2) para papers con paywall, recuperamos abstract + metadata y marcamos al usuario que el texto completo requiere licencia institucional; (3) en enterprise, integramos con el *proxy* de la biblioteca del cliente (SoftServe tiene acceso institucional).

---

**I.3 ¿Recencia de los datos?**

Indexación batch diaria de las 4 fuentes. Lag típico entre publicación en la fuente e indexación en STARK-MIND: <24 horas. El usuario ve la fecha de indexación en la tarjeta del Discovery Agent — sin trampa.

---

**I.4 ¿Licenciamiento de contenido?**

arXiv y bioRxiv: licencias Creative Commons (la mayoría CC-BY). PubMed: contenido mixto según el publisher. Semantic Scholar: índice abierto, pero full text según license del publisher. No almacenamos texto completo de papers con licencia restrictiva — solo embeddings y metadata; generamos citas y extractos bajo *fair use*.

*Dog whistle:* Creative Commons, fair use.

---

## J. Comparativo con competidores

**J.1 ¿En qué son mejores que Elicit o Undermind?**

Elicit es excelente en *Q&A con citas* pero flojo en *comparación profunda* y no es *multi-agent auditable*. Undermind tiene búsqueda agentic pero su UI es chat puro — sin workspace, sin proyectos persistentes, sin export enterprise. STARK-MIND combina lo mejor: comparación estructurada + persistencia + evaluation harness auditable + integración con Confluence/Jira/Notion.

---

**J.2 ¿NotebookLM ya hace esto?**

NotebookLM es *el competidor más cercano* en workspace-first con sources + chat + notas. **Tres diferenciadores concretos:**

1. NotebookLM no es multi-agent ni expone agentic trace — es un RAG con UI de workspace; nosotros sí exponemos el razonamiento agentic.
2. NotebookLM tiene citas pero sin anchor al párrafo exacto — solo al documento.
3. NotebookLM es general-purpose; nosotros estamos *verticalizados* para literatura científica con fuentes académicas conectadas (arXiv, PubMed, Semantic Scholar).

*Dog whistle:* verticalización, agentic trace expuesto.

---

**J.3 ¿Perplexity Deep Research?**

Perplexity Deep Research es fuerte en *web broad search* pero flojo en *literatura científica profunda*: indexa web, no arXiv/PubMed completos. Su *citation accuracy* en dominios técnicos es inferior a la que reporta un sistema vertical como el nuestro (tenemos benchmarks internos). Además, no tiene persistencia de proyectos — cada sesión empieza desde cero.

---

**J.4 ¿Qué los hace defensible a mediano plazo?**

Tres moats: (1) *evaluation harness propietario* con dataset anotado creciendo con el uso; (2) *integración enterprise* con Confluence, Jira, Notion — fricción alta de salida; (3) *verticalización en dominios* (healthcare, legal, biotech) con conectores específicos y prompts especializados. Los tres alinean con el modelo de negocio de SoftServe como *insights engine vertical*.

---

## K. Preguntas trampa y curveballs

**K.1 ¿Por qué no solo usan ChatGPT con web browsing?**

Web browsing de ChatGPT busca en la web abierta — no en arXiv/PubMed con metadata estructurada, no con citas trazables al párrafo, no con un *Citation-Guard* que verifique groundedness. Además no es auditable (no puedo mostrar al PM del cliente el trace de decisiones agenticas). Para una respuesta casual, sirve. Para un entregable técnico con HIPAA o marco teórico de tesis, no.

---

**K.2 ¿Qué pasa cuando los agentes no se ponen de acuerdo?**

No "se ponen de acuerdo" porque no hay consenso horizontal — hay jerarquía. El Orchestrator es árbitro. Si el Citation-Guard rechaza un output del Synthesizer, el Orchestrator reprograma al Synthesizer con el feedback específico del Guard. Si tras N intentos no converge, se marca como *unverified* y se muestra al usuario — falla cerrada, no decisión oculta.

*Dog whistle:* jerarquía, falla cerrada.

---

**K.3 ¿Han medido si el sistema está sesgado hacia papers en inglés?**

Sí — está sesgado hacia inglés, porque las 4 fuentes lo están. Mitigación parcial: Claude soporta español nativo para queries y output, y las queries del Discovery Agent se expanden a inglés para maximizar recall. A mediano plazo evaluaríamos integrar *SciELO* y *LA Referencia* como fuentes hispanoamericanas — está en el backlog, no en el MVP.

---

**K.4 ¿Cómo manejan papers retractados?**

Dos mecanismos: (1) *flag* en metadata — Semantic Scholar y PubMed marcan retracciones y las importamos; (2) si un paper referenciado aparece retractado después de ser citado, el usuario recibe alerta en el proyecto y el documento lo marca con banner rojo. Caso crítico en dominio clínico.

*Dog whistle:* retracted paper flag.

---

**K.5 ¿Qué pasa si Anthropic/Claude cambia su API o sube precios?**

*Model abstraction layer* en el código: cada agente llama a una interfaz interna, no directamente a la API del provider. Cambiar de Claude a GPT-4 / Llama / Mistral tomaría días, no semanas. Es una decisión arquitectónica explícita — no queremos lock-in al LLM provider aunque Claude sea nuestro default.

*Dog whistle:* model abstraction layer, no lock-in.

---

**K.6 ¿Por qué debería SoftServe invertir en ustedes y no construirlo internamente?**

SoftServe ya construyó la plataforma base (*Multi-Agent RAG Platform*). Lo que proponemos no compite — *complementa*: verticalizado para literatura científica, con dominio específico, con el equipo local de Medellín que ya habla su idioma técnico. Somos la implementación que le falta a su catálogo en el vertical de R&D/academic — no reinventamos su plataforma, la extendemos.

---

**K.7 ¿Cuánto se demorarían en llegar a producción?**

MVP funcional para una persona: 4-6 semanas (alineado con el *Agentic MVP Sprint* de SoftServe). Producción enterprise (HIPAA, multi-tenant, SLOs): 4-6 meses adicionales. El equipo está listo para operar en ese ritmo; el demo actual ya tiene el core funcional.

*Dog whistle:* Agentic MVP Sprint.

\newpage

# Anexos

## Anexo A — Cheat sheet de dog whistles

Llévalo impreso. En cada intervención del pitch y del Q&A, intenta dropear al menos uno.

| Categoría | Frase exacta |
|---|---|
| Arquitectura | Multi-Agent RAG, Master Agent, plan-and-execute, LangGraph |
| Fidelidad | Citas trazables con anchor, Citation-Guard, groundedness, faithfulness |
| Calidad | Evaluation harness, citation accuracy, LLM-as-judge |
| Stack | AWS Bedrock, pgvector, prompt caching |
| Negocio | Intelligence Engineer, Insights Engine, Agentic MVP Sprint |
| Diferencia | Agentic (vs. chatbot), verticalización, auditable por componente |

## Anexo B — Respuestas de 30 segundos a las 5 preguntas más probables

Memorízalas. Son las que más probablemente van a caer.

**1. ¿Por qué Claude y no GPT?**

> "Por tres razones. Uno: SoftServe usó Anthropic en AgentForge, es su stack de demo. Dos: Claude lidera en *tool use* y *citations* en benchmarks públicos, que es exactamente lo que nuestro Citation-Guard necesita. Tres: está en AWS Bedrock, alineado con el stack enterprise que ustedes ya venden. Si el cliente pide on-prem con Llama, tenemos un *model abstraction layer* que lo soporta en días, no semanas."

**2. ¿Cómo se diferencian de NotebookLM?**

> "Tres diferencias concretas. NotebookLM no es multi-agent — es un RAG con UI linda, sin agentic trace expuesto. Sus citas apuntan al documento, no al párrafo exacto como las nuestras. Y es general-purpose; nosotros estamos verticalizados para literatura científica con fuentes académicas conectadas — arXiv, PubMed, Semantic Scholar, bioRxiv. Son diferencias de producto, no cosméticas."

**3. ¿Cómo evitan alucinaciones?**

> "No las evitamos — las reducimos sistemáticamente en cuatro capas. Retrieval fuerte antes de generar, Citation-Guard verificando cada afirmación post-generación, marcado explícito de lo *unverified* al usuario, y métricas de faithfulness monitoreadas en producción con alerting. El día que alguien diga que 'evitó' las alucinaciones al 100%, dude. Nosotros decimos cómo las medimos y cómo las bajamos."

**4. ¿Cuánto cuesta correr el sistema?**

> "Query típica: cinco a quince centavos de dólar en tokens. Sesión completa de una hora de R&D Engineer: dos a cuatro dólares. Con prompt caching activo bajamos cuarenta a sesenta por ciento para sesiones largas. A escala de diez mil usuarios con cinco QPS de pico, estimamos treinta a cincuenta mil dólares mensuales de infraestructura. Es un modelo operable, no una demo quemadora."

**5. ¿Por qué SoftServe debería apostar por ustedes?**

> "No competimos con su *Multi-Agent RAG Platform* — la extendemos. Somos la implementación vertical para literatura científica que le falta a su catálogo, construida por un equipo local de Medellín que ya habla su idioma técnico: agentic, evaluation harness, guardrails, citas trazables. Es el perfil de *Intelligence Engineer* que ustedes están contratando — aplicado a un caso de uso que pueden revender mañana a pharma, biotech, legal y consultoría estratégica."

## Anexo C — Qué NO decir

- "Nunca alucina", "cero errores", "100% precisión". Nadie técnico lo cree.
- "Es mejor que ChatGPT". Los estás comparando mal — compáralo con productos verticales.
- "Usamos la última tecnología". Nombra la tecnología específica.
- Improvisar métricas que no están en este dossier. Si no sabes, di *"es una decisión de diseño abierta"*.
- Hablar mal de competidores. Di qué hacen bien primero y luego el gap concreto.

## Anexo D — Roles durante el pitch (propuesta)

- **Pitcher 1 (storyteller):** abre el pitch, cierra el pitch, narra el demo. Domina los *dog whistles* y la narrativa.
- **Pitcher 2 (driver):** ejecuta el demo en la computadora. Tiene las teclas de atajo del plan B listas.
- **Pitcher 3 (técnico Q&A):** responde preguntas de arquitectura, LLM, RAG, evaluation harness. Domina este dossier.
- **Pitcher 4 (negocio Q&A):** responde preguntas de mercado, competidores, modelo de negocio, escala.

Si el equipo es de menos de 4, pitcher 1 y pitcher 2 pueden ser la misma persona con práctica intensa de coordinación.

---

*Fin del dossier. Última actualización: 23 de abril de 2026.*
