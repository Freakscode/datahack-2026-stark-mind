# Investigación de SoftServe aplicada al Reto 3

> **Reto DataHack 2026 - Reto 3**: Asistente Inteligente para Artículos de Investigación (aplicación multiagente).

---

## Snapshot de SoftServe Colombia

- **Llegada a Medellín**: 2022, oficinas en FIC 48 (Cra. 48 #18 A 14, piso 5). Reconocida por ACI Medellín.
- **Áreas activas localmente**: software engineering, cloud/DevOps, big data & analytics, **AI/ML**, IoT, XR, robotics.
- **Vínculo con talento local**: alianzas con Ruta N, Fundación Juanfe, Código Comuna 13 (formación TI, ~600 colombianos capacitados en 2023).

---

## Los 3 servicios de SoftServe que son LITERALMENTE el reto

Este es el hallazgo más importante: **el reto DataHack 3 es prácticamente el caso de uso insignia de tres productos/servicios que SoftServe ya comercializa**. Si lo resolvemos bien, estamos construyendo una demo de su propio portafolio — ese es el ángulo de convencimiento.

| Servicio SoftServe | Qué es | Conexión con Reto 3 |
|---|---|---|
| **Multi-Agent RAG Platform** (AWS Marketplace) | Master Agent orquestando agentes: Multimodal RAG, Text-to-SQL, Chart Generation, Function Calling | Arquitectura base del asistente: un orquestador que coordina agentes de búsqueda, lectura, comparación y visualización |
| **Insights Engine Pilot** (servicio de IA) | "Asistente RAG multimodal con **citas integradas**, enfocado en **dominios específicos**" | Es exactamente el producto: RAG con citas sobre literatura científica como dominio |
| **Agentic MVP Sprint** (oferta comercial) | Desarrollo en 4-6 semanas de agentes/copilots con **evaluation harness y safeguards** | El formato del hackathon (pocos días) imita su sprint. Mostrar evaluación + guardrails habla su idioma |

---

## Qué está persiguiendo SoftServe EN ESTE MOMENTO (2026)

Contexto crítico para la propuesta:

1. **Febrero 2026**: lanzaron la **Agentic Engineering Suite** — 7 agentes autónomos para el ciclo de software (QA, BA, Code Gen, Architect, Maintenance, CI/CD, Code Conversion). Bandera clara: agentes > chatbots.
2. **Abril 2026**: corrieron **AgentX Hackathon** (Medellín, Santiago, Guadalajara) — premio de $10K USD y **entrada directa al equipo global de R&D**. Target explícito: "developers, R&D engineers, ML engineers y agentic systems creators".
3. **AgentForge** (hackathon global): construido sobre **API de Anthropic** → Claude es su LLM de demo preferido para agentes.
4. Nuevo rol corporativo: **"Intelligence Engineers"** — ingenieros que trabajan directamente con agentes de IA en todo el ciclo.
5. Áreas de R&D declaradas: **IA Multimodal, Agentic Engineering, Biotech (bioinformática, diseño de fármacos), HPC, Edge AI, Quantum Computing**.

**Conclusión**: SoftServe está invirtiendo agresivamente en **agentes autónomos** y busca señales de talento local en Medellín que entienda esa dirección. El reto es una oportunidad para ellos de identificar equipos, no solo un ejercicio académico.

---

## Cómo diseñar el MVP para "convencerlos"

Estos son los **"dog whistles"** técnicos y de producto que deberían estar presentes en la demo/pitch.

### Arquitectura (hablarles en su jerga)

- **Master Agent + agentes especializados**, no un LLM monolítico. Mínimo:
  `Orchestrator → {Discovery, Reader/RAG, Comparator, Synthesizer, Citation-Guard}`.
- **Multimodal RAG**: los papers incluyen tablas, figuras, fórmulas. Mostrar que extraemos más que texto plano.
- **Function Calling** a fuentes reales: arXiv, bioRxiv, PubMed, Semantic Scholar.
- **Evaluation harness**: métricas de groundedness, faithfulness, citation accuracy. SoftServe lo menciona en cada servicio de IA.
- **Guardrails**: detección de alucinaciones, refuerzo de citas obligatorias.

### Stack alineado con sus partnerships

- **LLM**: Claude (Anthropic) — porque usaron su API en AgentForge.
- **Cloud**: AWS (Bedrock, Lambda, OpenSearch) o Azure — coinciden con sus partners top.
- **Vector DB**: pgvector o Pinecone.
- **Orquestación**: LangGraph o CrewAI con patrón jerárquico (Master Agent).

### Diferenciadores que apuntan a su negocio

| Señal | Por qué les importa |
|---|---|
| **Verticalización del dominio** (ej: demo en biotech/IA/materiales) | Les permite revender el patrón a clientes en life sciences, pharma, manufactura |
| **Citas trazables con anchor al párrafo/figura** | Es el diferencial de su "Insights Engine" |
| **Comportamiento agentic**: planea, ejecuta, autocorrige | Separa "chatbot" de "agente autónomo" — su bandera de 2026 |
| **Modo "co-investigador R&D"**: genera hipótesis, detecta gaps de literatura | Habla al caso de uso interno de sus propios ingenieros de R&D |
| **Panel de tendencias/timeline** | Les sirve como herramienta interna de inteligencia competitiva |
| **Exportable** (Notion, PDF, Markdown, Jira) | Integración con flujos corporativos — lo que ellos hacen por default |

### El pitch de convencimiento (estructura sugerida)

1. **Problema**: sus propios R&D engineers pierden 30–40% del tiempo en literatura → dogfooding interno posible.
2. **Solución**: un Insights Engine vertical para papers — usa su mismo patrón multi-agente.
3. **Demo**: caso real en un dominio (ej: "últimos 6 meses de RAG agentic en arXiv") mostrando descubrir → resumir → comparar → sintetizar con citas.
4. **Monetización para ellos**: el patrón se revende como Insights Engine a clientes pharma, biotech, legal, consultoría estratégica.
5. **Talento**: el equipo está listo para el rol de Intelligence Engineers que ya están contratando.

---

## Próximos pasos posibles

- Diseñar la arquitectura multiagente detallada (nodos, mensajes, tools).
- Definir el evaluation harness (métricas y dataset de validación).
- Elegir el stack concreto (LangGraph vs CrewAI vs custom).
- Preparar el pitch deck alineado con la narrativa SoftServe.

---

## Fuentes

- [SoftServe Colombia - Career](https://career.softserveinc.com/es/about/colombia)
- [SoftServe AI Services](https://www.softserveinc.com/en-us/services/artificial-intelligence)
- [SoftServe Research & Development](https://www.softserveinc.com/en-us/services/research-and-development)
- [SoftServe Multi-Agent RAG Platform on AWS](https://aws.amazon.com/marketplace/pp/prodview-yrneq3pcltnka)
- [SoftServe Generative AI](https://www.softserveinc.com/en-us/generative-ai)
- [SoftServe Agentic Engineering Suite launch](https://www.softserveinc.com/en-us/news/softserve-launches-agentic-engineering-suite)
- [AgentX Hackathon 2026 (SoftServe)](https://app.softserveinc.com/apply/agentx-hackathon/)
- [AgentX lanzamiento regional (Descubre.vc)](https://www.descubre.vc/noticia/softserve-lanza-agentx-el-primer-hackathon-regional-de-ia-en-chile-colombia-y-m-xico-2026-03-19)
- [AgentForge Hackathon (SoftServe)](https://www.softserveinc.com/en-us/news/next-generation-ai-agents-softserve-hackathon)
- [SoftServe Colombia ACI Medellín recognition](https://www.softserveinc.com/en-us/news/softserve-colombia-recognized-by-aci-medellin)
- [Roles y procesos para agentic engineering (SoftServe blog)](https://www.softserveinc.com/en-us/blog/roles-and-processes-for-agentic-engineering)
