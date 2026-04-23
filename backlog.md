# Backlog STARK-VIX — DataHack 2026 Reto #3

> Tracking local del backlog Jira (proyecto **DAT**).
> **Deadline duro:** jueves 23 abril 2026, 11:59 AM (envío del formulario).
> **Hoy:** 2026-04-21.

- **Jira:** https://aura360-team.atlassian.net/jira/software/projects/DAT
- **Plan timeline:** https://aura360-team.atlassian.net/jira/plans/1/scenarios/1/timeline?vid=4

---

## Leyenda

- 🔴 Camino crítico (bloquea la demo / pitch).
- 🟡 Importante pero paralelizable.
- 🟢 Nice-to-have / opcional.
- 👤 Assignee primario · 🤝 Colaboradora (mention).

## Owners

| Owner | Handle Jira | Scope |
|---|---|---|
| Gabriel Cardona | `Gabriel Jaime Cardona Osorio` | E1, E2, E5, E7 (23 issues) |
| Isabella Aristizabal | `isabella Aristizabal` | E3 (5 issues) |
| Valentina Pérez | `Valentina Pérez` | E4 (5) + colaboradora E6 |
| Dani Montoya | `Dani Montoya` | E6 (7) + colaboradora E4 |

---

## E1 · Infraestructura & Setup 🔴

Owner: **Gabriel Cardona** · Timebox: Día 1 mañana (≤ 3h).

| Key | Tipo | Título | Bloqueado por | Bloquea |
|---|---|---|---|---|
| [DAT-5](https://aura360-team.atlassian.net/browse/DAT-5) | Epic | E1 · Infraestructura & Setup | — | — |
| [DAT-12](https://aura360-team.atlassian.net/browse/DAT-12) | Tarea | E1.1 · Crear monorepo Git | — | DAT-13, DAT-14, DAT-15, DAT-16 |
| [DAT-13](https://aura360-team.atlassian.net/browse/DAT-13) | Tarea | E1.2 · Variables de entorno y secretos | DAT-12 | DAT-15 |
| [DAT-14](https://aura360-team.atlassian.net/browse/DAT-14) | Tarea | E1.3 · Bootstrap Next.js + shadcn/ui + Tremor | DAT-12 | DAT-28 |
| [DAT-15](https://aura360-team.atlassian.net/browse/DAT-15) | Tarea | E1.4 · Bootstrap FastAPI + LangGraph | DAT-12, DAT-13 | DAT-17, DAT-29 |
| [DAT-16](https://aura360-team.atlassian.net/browse/DAT-16) | Tarea | E1.5 · Levantar pgvector | DAT-12 | DAT-19 |

- [ ] DAT-12 — Crear monorepo
- [ ] DAT-13 — Configurar .env
- [ ] DAT-14 — Next.js + shadcn + Tremor
- [ ] DAT-15 — FastAPI + LangGraph
- [ ] DAT-16 — pgvector

---

## E2 · Agentes & Orquestación 🔴

Owner: **Gabriel Cardona** · Timebox: Día 1 tarde — Día 2 mañana.

| Key | Tipo | Título | Bloqueado por | Bloquea |
|---|---|---|---|---|
| [DAT-6](https://aura360-team.atlassian.net/browse/DAT-6) | Epic | E2 · Agentes & Orquestación | — | — |
| [DAT-17](https://aura360-team.atlassian.net/browse/DAT-17) | Historia | E2.1 · Orchestrator (LangGraph) | DAT-15, DAT-23 | DAT-18–22, DAT-32 |
| [DAT-18](https://aura360-team.atlassian.net/browse/DAT-18) | Historia | E2.2 · Discovery Agent | DAT-17, DAT-24, DAT-25 | — |
| [DAT-19](https://aura360-team.atlassian.net/browse/DAT-19) | Historia | E2.3 · Reader/RAG Agent | DAT-17, DAT-16, DAT-27 | — |
| [DAT-20](https://aura360-team.atlassian.net/browse/DAT-20) | Historia | E2.4 · Comparator Agent | DAT-17 | — |
| [DAT-21](https://aura360-team.atlassian.net/browse/DAT-21) | Historia | E2.5 · Synthesizer Agent | DAT-17 | — |
| [DAT-22](https://aura360-team.atlassian.net/browse/DAT-22) | Historia | E2.6 · Citation-Guard Agent | DAT-17 | DAT-34 |
| [DAT-23](https://aura360-team.atlassian.net/browse/DAT-23) | Tarea | E2.7 · Contracts & logging stream | — | DAT-17 |

- [ ] DAT-17 — Orchestrator
- [ ] DAT-18 — Discovery
- [ ] DAT-19 — Reader/RAG
- [ ] DAT-20 — Comparator
- [ ] DAT-21 — Synthesizer
- [ ] DAT-22 — Citation-Guard
- [ ] DAT-23 — Contracts + SSE

---

## E3 · Ingesta arXiv + Google Scholar 🔴

Owner: **Isabella Aristizabal** · Timebox: Día 1 tarde.

| Key | Tipo | Título | Bloqueado por | Bloquea |
|---|---|---|---|---|
| [DAT-7](https://aura360-team.atlassian.net/browse/DAT-7) | Epic | E3 · Ingesta arXiv + Google Scholar | — | — |
| [DAT-24](https://aura360-team.atlassian.net/browse/DAT-24) | Tarea | E3.1 · Adaptador arXiv | — | DAT-18 |
| [DAT-25](https://aura360-team.atlassian.net/browse/DAT-25) | Tarea | E3.2 · Adaptador Scholar (SerpAPI) | — | DAT-18 |
| [DAT-26](https://aura360-team.atlassian.net/browse/DAT-26) | Tarea | E3.3 · Pipeline PDF → texto | — | DAT-27 |
| [DAT-27](https://aura360-team.atlassian.net/browse/DAT-27) | Tarea | E3.4 · Chunking + embeddings + pgvector | DAT-26 | DAT-19 |

- [ ] DAT-24 — arXiv adapter
- [ ] DAT-25 — Scholar adapter
- [ ] DAT-26 — PDF extraction
- [ ] DAT-27 — Embeddings + upsert

---

## E4 · Frontend esqueleto (handoff Lovable) 🟡

Owner: **Valentina Pérez** 👤 · **Dani Montoya** 🤝 · Timebox: Día 1-2.

| Key | Tipo | Título | Bloqueado por | Bloquea |
|---|---|---|---|---|
| [DAT-8](https://aura360-team.atlassian.net/browse/DAT-8) | Epic | E4 · Frontend esqueleto | — | — |
| [DAT-28](https://aura360-team.atlassian.net/browse/DAT-28) | Tarea | E4.1 · Layout shell + rutas | DAT-14 | — |
| [DAT-29](https://aura360-team.atlassian.net/browse/DAT-29) | Historia | E4.2 · Contratos API (OpenAPI/Zod) | DAT-15 | DAT-30 |
| [DAT-30](https://aura360-team.atlassian.net/browse/DAT-30) | Tarea | E4.3 · Tipos TS canonicales | DAT-29 | DAT-31 |
| [DAT-31](https://aura360-team.atlassian.net/browse/DAT-31) | Tarea | E4.4 · Handoff Lovable | DAT-30 | — |

- [ ] DAT-28 — Layout + rutas
- [ ] DAT-29 — OpenAPI/Zod
- [ ] DAT-30 — Tipos TS
- [ ] DAT-31 — Handoff docs

---

## E5 · Evaluation Harness & Guardrails 🔴

Owner: **Gabriel Cardona** · Timebox: Día 2 mañana.

| Key | Tipo | Título | Bloqueado por | Bloquea |
|---|---|---|---|---|
| [DAT-9](https://aura360-team.atlassian.net/browse/DAT-9) | Epic | E5 · Eval harness & Guardrails | — | — |
| [DAT-32](https://aura360-team.atlassian.net/browse/DAT-32) | Tarea | E5.1 · Métricas (groundedness / faithfulness / citation accuracy) | DAT-17 | DAT-35 |
| [DAT-33](https://aura360-team.atlassian.net/browse/DAT-33) | Tarea | E5.2 · Dataset de validación | — | DAT-35 |
| [DAT-34](https://aura360-team.atlassian.net/browse/DAT-34) | Tarea | E5.3 · Guardrail citation-required | DAT-22 | — |
| [DAT-35](https://aura360-team.atlassian.net/browse/DAT-35) | Tarea | E5.4 · Runner de eval | DAT-32, DAT-33 | DAT-36 |

- [ ] DAT-32 — Métricas
- [ ] DAT-33 — Dataset golden
- [ ] DAT-34 — Guardrail
- [ ] DAT-35 — Runner

---

## E6 · Pitch & Entregables 🔴

Owner: **Dani Montoya** 👤 · **Valentina Pérez** 🤝 · Timebox: Día 2 tarde.

| Key | Tipo | Título | Bloqueado por | Bloquea |
|---|---|---|---|---|
| [DAT-10](https://aura360-team.atlassian.net/browse/DAT-10) | Epic | E6 · Pitch & Entregables | — | — |
| [DAT-36](https://aura360-team.atlassian.net/browse/DAT-36) | Tarea | E6.1 · Slides pitch (5 min) | DAT-35 | DAT-40 |
| [DAT-37](https://aura360-team.atlassian.net/browse/DAT-37) | Tarea | E6.2 · Guion con timings | — | DAT-40 |
| [DAT-38](https://aura360-team.atlassian.net/browse/DAT-38) | Tarea | E6.3 · Grabar demo video (backup) | — | — |
| [DAT-39](https://aura360-team.atlassian.net/browse/DAT-39) | Tarea | E6.4 · Empaquetar .zip (≤ 100 MB) | — | DAT-41 |
| [DAT-40](https://aura360-team.atlassian.net/browse/DAT-40) | Tarea | E6.5 · Ensayo completo | DAT-36, DAT-37 | DAT-41 |
| [DAT-41](https://aura360-team.atlassian.net/browse/DAT-41) | Tarea | **E6.6 · Envío formulario (DEADLINE)** ⚠️ | DAT-39, DAT-40 | — |

- [ ] DAT-36 — Slides
- [ ] DAT-37 — Guion
- [ ] DAT-38 — Demo video
- [ ] DAT-39 — .zip suplementario
- [ ] DAT-40 — Ensayo
- [ ] DAT-41 — **Envío antes de 23 abr 11:59 AM**

---

## E7 · HPC BRAVO (OPCIONAL) 🟢

Owner: **Gabriel Cardona** · Timebox: Día 1 tarde — decisión go/no-go al cierre.

| Key | Tipo | Título | Bloqueado por | Bloquea |
|---|---|---|---|---|
| [DAT-11](https://aura360-team.atlassian.net/browse/DAT-11) | Epic | E7 · HPC BRAVO (opcional) | — | — |
| [DAT-42](https://aura360-team.atlassian.net/browse/DAT-42) | Tarea | E7.1 · Setup VPN + Open OnDemand | — | DAT-43 |
| [DAT-43](https://aura360-team.atlassian.net/browse/DAT-43) | Tarea | E7.2 · Notebook embeddings Tesla T4 | DAT-42 | DAT-44 |
| [DAT-44](https://aura360-team.atlassian.net/browse/DAT-44) | Tarea | E7.3 · Exportar parquet a pgvector | DAT-43 | — |

- [ ] DAT-42 — VPN + OOD
- [ ] DAT-43 — Notebook GPU
- [ ] DAT-44 — Parquet load

---

## Camino crítico (critical path)

```
DAT-12 → DAT-15 → DAT-17 → DAT-22 → DAT-34 ─┐
                ↓                             │
                DAT-32 → DAT-35 → DAT-36 ─┐   │
                                           ↓   ↓
DAT-37 ────────────────────────────────→ DAT-40 → DAT-41 (ENVÍO)
                                           ↑
DAT-39 ───────────────────────────────────┘
```

**Longitud mínima del camino crítico: 7 hops.** Cualquier retraso en uno de esos issues mueve el deadline completo.

## Paralelizable en Día 1

Una vez DAT-12 esté listo (monorepo), pueden arrancar en paralelo:
- **Gabriel:** DAT-13 → DAT-15 → DAT-23 → DAT-17 (camino crítico backend/agents)
- **Isabella:** DAT-24 + DAT-25 + DAT-26 (independientes entre sí)
- **Valentina:** DAT-14 → DAT-28 (layout); DAT-29 espera a DAT-15
- **Dani:** DAT-37 (guion — no depende de código) + DAT-33 (dataset eval)

## Decisión go/no-go HPC (E7)

Al cierre del Día 1 (21 abr ~22:00), revisar:
- ✅ Si DAT-27 ya corrió con Voyage → **skip E7**, usar API.
- ⚠️ Si hay margen y el adapter de embeddings funciona local → **activar E7** como respaldo.
- ❌ Si DAT-27 no terminó → **descartar E7**, priorizar destrabar E3.

## Señales de alarma

- **Día 1, 18:00:** si DAT-17 (Orchestrator) no pasa healthcheck con un agente dummy, **cortar scope**: reducir a 3 agentes (Discovery, Reader, Synthesizer con citas inline simples).
- **Día 2, 10:00:** si DAT-35 (eval runner) no tiene datos, **cambiar pitch**: mostrar métricas cualitativas + screenshots en lugar de métricas duras.
- **Día 2, 16:00:** si el demo en vivo aún falla, **priorizar DAT-38** (video grabado) como plan B.

---

## Stack acordado

- **LLM:** Claude (Anthropic).
- **Orquestación:** LangGraph con patrón Master Agent jerárquico.
- **Vector DB:** pgvector (Docker local o Supabase).
- **Embeddings:** Voyage-3 (fallback) o BGE en HPC (opcional).
- **Cloud:** AWS Bedrock/Lambda/OpenSearch (si hay tiempo; no es requisito del MVP).
- **Frontend:** Next.js + shadcn/ui + Tremor + Lovable (iteración visual).
- **Fuentes:** arXiv API + Google Scholar (SerpAPI).

## Referencias internas

- `CLAUDE.md` — guía para futuras sesiones de Claude Code.
- `softserve-analisis-reto3.md` — análisis del sponsor y estrategia de pitch.
- `miro-research-phase.md` — consolidado del research de Miro.
- `docs/Reto 3_ Instrucciones Detalladas.docx`, `docs/Rúbrica de evaluación DataHack.docx`, `docs/Recomendaciones para presentaciones (pitch).docx`.
