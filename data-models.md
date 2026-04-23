# STARK-VIX — Modelo de datos

> Diseño del esquema PostgreSQL + pgvector para el backend FastAPI.
> Alineado con las 5 capacidades núcleo del MVP: descubrir, resumir, comparar, detectar tendencias, Q&A con citas.
>
> **Stack:** PostgreSQL 16 + `pgvector` + SQLAlchemy 2 (async) + Alembic + Pydantic v2 + FastAPI.

---

## 1. Dual-track de modelos de IA

El sistema soporta dos modos de ejecución, seleccionables por agente y por query.

### Track 1 · Ejecución local (lo que corre en la competencia)

Sin dependencias de red externa, sin costo monetario. Los modelos exponen **tok/s reales** (leídos de la API de Ollama o `sentence-transformers`).

### Track 2 · Frontera con mock de coste (para pitch)

No se invoca la API real durante el reto — se **simula** latencia y tok/s plausibles, y se calcula el **costo estimado** multiplicando tokens × `cost_per_1m_tokens`. Se muestra en UI con un badge claro "(mock)".

### Propósito

- **UX del frontend:** tok/s y costo visibles por evento de agente → diferenciador visual.
- **Pitch:** argumento de FinOps + escalabilidad. "Hoy corre en local a 0 $, en producción con Haiku cuesta 0.003 $ por query."
- **Rúbrica:** cubre "viabilidad" (#7) y "potencial de escalamiento" (#8).

---

## 2. Diagrama ER

```
 ┌──────────┐         ┌──────────────────┐
 │  models  │◀────────│  agent_events    │
 └──────────┘   FK    └──────────────────┘
                              │
                              │ FK
 ┌──────────┐         ┌───────▼────────┐
 │ projects │─────────│    queries     │
 └─────┬────┘ 1:N     └───┬────────────┘
       │                  │ 1:1
       │ N:M              ▼
       │         ┌────────────────┐
       │         │    reports     │
       │         └───────┬────────┘
       │                 │ 1:N
       │                 ▼
       │         ┌────────────────┐
 ┌─────▼──────┐  │   citations    │
 │  papers    │──└───────┬────────┘
 └─────┬──────┘    FK    │
       │ 1:N              │
       ▼                 │
 ┌──────────┐             │
 │  chunks  │◀────────────┘   (pgvector 1024d)
 └──────────┘

 ┌──────────┐         ┌──────────┐
 │ projects │─────────│  notes   │
 └──────────┘   1:N   └──────────┘

 ┌──────────┐         ┌──────────────┐
 │ queries  │─────────│  eval_runs   │
 └──────────┘   0..1  └──────────────┘
```

## 3. Tablas (11 total)

| # | Tabla | Rol | PK | Relaciones clave |
|---|---|---|---|---|
| 1 | `models` | Catálogo de LLMs y embeddings (local + frontier mock) con precios | `id TEXT` | referenciada por `agent_events.model_id` |
| 2 | `projects` | Una investigación completa del usuario | `id UUID` | 1:N → queries, notes, project_papers |
| 3 | `papers` | Catálogo global de artículos (deduplicados por DOI/arxiv_id) | `id TEXT` | 1:N → chunks, N:M ← project_papers |
| 4 | `chunks` | Fragmentos con embedding pgvector | `id BIGSERIAL` | N:1 ← paper_id |
| 5 | `project_papers` | N:M entre projects y papers | `(project_id, paper_id)` | — |
| 6 | `queries` | Pregunta/búsqueda dentro de un proyecto | `id UUID` | 1:1 → report, 1:N → agent_events |
| 7 | `agent_events` | Stream de pensamiento (persistido) con telemetría de tok/s y costo | `id BIGSERIAL` | N:1 ← query_id, N:1 ← model_id |
| 8 | `reports` | Respuesta sintetizada markdown editable + structured_output JSONB | `id UUID` | 1:1 ← query_id, 1:N → citations |
| 9 | `citations` | Anchor trazable paper + chunk + página/figura con flag `verified` | `id BIGSERIAL` | N:1 ← report_id, N:1 ← paper_id, N:1 ← chunk_id |
| 10 | `notes` | Notas libres del usuario por proyecto | `id UUID` | N:1 ← project_id |
| 11 | `eval_runs` | Scores de groundedness/faithfulness/citation_accuracy | `id UUID` | 0..1 ← query_id |

## 4. Modelos precargados en `seed.sql`

### Frontier mocks (Track 2 — solo demo)

| Provider | Model ID | Kind | Input $/1M | Output $/1M | Embedding dim | Notas |
|---|---|---|---|---|---|---|
| openai | `gpt-4o` | llm | 2.50 | 10.00 | — | LLM premium de referencia |
| openai | `gpt-4o-mini` | llm | 0.15 | 0.60 | — | LLM barato |
| openai | `gpt-4.1` | llm | 2.00 | 8.00 | — | Mid-tier |
| openai | `gpt-4.1-mini` | llm | 0.40 | 1.60 | — | Balance precio/calidad |
| openai | `o3-mini` | llm | 1.10 | 4.40 | — | Razonamiento |
| openai | `text-embedding-3-small` | embedding | 0.02 | — | 1536 | Embedding económico |
| openai | `text-embedding-3-large` | embedding | 0.13 | — | 3072 | Embedding premium |
| anthropic | `claude-opus-4-7` | llm | 15.00 | 75.00 | — | Premium flagship |
| anthropic | `claude-sonnet-4-6` | llm | 3.00 | 15.00 | — | **Default para síntesis** |
| anthropic | `claude-haiku-4-5` | llm | 1.00 | 5.00 | — | Agentes rápidos |
| anthropic | `voyage-3` | embedding | 0.06 | — | 1024 | **Drop-in local swap** |
| google | `gemini-2.5-pro` | llm | 1.25 | 5.00 | — | Alternativa premium |
| google | `gemini-2.5-flash` | llm | 0.075 | 0.30 | — | Más barato del mercado |

### Local (Track 1 — ejecución real)

| Provider | Model ID | Kind | Runtime | Embedding dim | Notas |
|---|---|---|---|---|---|
| local | `bge-large-en-v1.5` | embedding | sentence-transformers | 1024 | **Default embedding**, drop-in con voyage-3 |
| local | `nomic-embed-text-v1` | embedding | sentence-transformers | 768 | Alternativa más ligera |
| local | `llama3.1:8b-instruct` | llm | ollama | — | Agentes simples |
| local | `qwen2.5:7b-instruct` | llm | ollama | — | **Default síntesis** (buen JSON) |
| local | `mistral:7b-instruct` | llm | ollama | — | Fallback |

## 5. Decisiones de diseño

1. **Dimensión embedding = 1024.** `bge-large-en-v1.5` (local) y `voyage-3` (frontera) comparten dimensión → **drop-in swap** sin re-ingesta. Es el argumento de escalabilidad para el pitch.
2. **`papers.id` es texto (DOI o arxiv_id)**, no UUID. Permite upsert idempotente desde adaptadores arXiv/Scholar sin lookup previo.
3. **`agent_events.payload JSONB`** libre por agente. No fuerza un shape rígido que nos frene en hackathon.
4. **Comparativas en `reports.structured_output` JSONB**, no tabla propia. Formato dinámico según el usuario.
5. **`citations.verified`** lo marca Citation-Guard. El frontend filtra `verified=true` antes de renderizar.
6. **Sin tabla `users`** en MVP. Todo en tenant único. Añadir `user_id nullable` después es barato.
7. **`ivfflat` index con `lists = 100`** adecuado para 5k–50k chunks. Re-evaluar a `hnsw` si pasamos 100k.
8. **`tokens_per_second` como valor real** (local) o **plausible estimado** (mock) — mismo campo, diferenciable por `model_id`.
9. **Borrado físico**, no soft-delete. El timebox no justifica recycle bin.
10. **`updated_at` triggers** en projects, reports, notes para auditoría visual.

## 6. Flujo de telemetría (tok/s + costo)

```
Agent (Reader) invoca LLM
  ↓
[Ollama response]
  total_duration=2_500_000_000ns
  eval_count=340 tokens
  eval_duration=1_800_000_000ns
  ↓
backend computa tokens_per_second = 340 / 1.8 = 188.89
backend computa cost = 0 (local)  |  340 * cost_per_1m_tokens / 1_000_000 (mock)
  ↓
INSERT INTO agent_events (..., model_id, input_tokens, output_tokens, tokens_per_second, latency_ms, cost_estimated_usd)
  ↓
emit SSE: { agent, action, status, tok_per_sec, cost_usd }
  ↓
Frontend muestra badge (local · 189 t/s · 0 $) o (mock · 140 t/s · 0.003 $)
```

## 7. Archivos relacionados

- `db/schema.sql` — DDL completo listo para `psql` o Alembic.
- `db/seed.sql` — datos iniciales (modelos + proyecto + papers demo).
- `backend/app/db/models.py` — SQLAlchemy 2 ORM.
- `backend/app/db/schemas.py` — Pydantic v2 (Create/Read/Update).

## 8. Estrategia de migraciones

Para el MVP: **ejecutar `schema.sql` + `seed.sql` directos en Docker pgvector**. Alembic queda listo para cuando se estabilice el esquema (post-hackathon).

```bash
# Docker local (DAT-16)
docker run -d --name stark-pg \
  -e POSTGRES_PASSWORD=stark \
  -e POSTGRES_DB=starkvix \
  -p 5432:5432 \
  ankane/pgvector

# Aplicar esquema
psql postgres://postgres:stark@localhost:5432/starkvix -f db/schema.sql
psql postgres://postgres:stark@localhost:5432/starkvix -f db/seed.sql
```

## 9. Scope consciente fuera de MVP

- Auth + multi-tenancy (añadir `user_id` nullable después).
- Versionado de reports (sobrescritura directa por ahora).
- Full-text search sobre abstracts (solo semántico).
- Normalización de autores (TEXT[] por ahora).
- Soft delete / audit log.
- Alembic desde día 1 (schema.sql directo por velocidad).
