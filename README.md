# STARK-MIND · DataHack 2026 · Reto 3

> **Asistente Inteligente multi-agente para Artículos de Investigación.**
> Descubre, resume, compara, detecta tendencias y responde con **citas trazables** sobre literatura científica.

Repositorio del equipo para el **Reto 3** del DataHack 2026, sponsor **SoftServe**. Incluye el backend FastAPI del MVP (STARK-VIX), el frontend en React + Vite (stark-insight-forge, como submódulo), el schema de base de datos con pgvector, el research consolidado y el dossier de pitch.

---

## Tabla de contenido

- [Stack](#stack)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Requisitos previos](#requisitos-previos)
- [Clonar el proyecto (con submódulos)](#clonar-el-proyecto-con-submódulos)
- [Setup paso a paso](#setup-paso-a-paso)
  - [1. Base de datos — Postgres + pgvector](#1-base-de-datos--postgres--pgvector)
  - [2. Backend — FastAPI (STARK-VIX)](#2-backend--fastapi-stark-vix)
  - [3. Frontend — Vite + React (stark-insight-forge)](#3-frontend--vite--react-stark-insight-forge)
- [Ejecutar en desarrollo](#ejecutar-en-desarrollo)
- [Variables de entorno](#variables-de-entorno)
- [Dossier de pitch y research](#dossier-de-pitch-y-research)
- [Trabajar con el submódulo](#trabajar-con-el-submódulo)
- [Solución de problemas](#solución-de-problemas)

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Pydantic v2 · `uv` |
| Agentes (opcional) | LangGraph · LangChain · Anthropic Claude · OpenAI · Google GenAI · Ollama |
| Base de datos | PostgreSQL 16 · pgvector · pgcrypto · pg_trgm |
| Frontend | Vite · React · TypeScript · Tailwind CSS · Bun |
| Tests | pytest · pytest-asyncio · Vitest |
| Lint | Ruff (Python) · ESLint (TS) |

---

## Estructura del repositorio

```
datahack-2026-stark-mind/
├── backend/                           FastAPI + SQLAlchemy + pgvector (STARK-VIX)
│   ├── app/                           Código de la API
│   ├── scripts/                       Fixtures y utilidades
│   ├── pyproject.toml                 Dependencias (manejadas por uv)
│   ├── uv.lock
│   └── .env.example
├── db/                                Schema SQL + seed
│   ├── schema.sql                     Tablas, extensiones, índices
│   └── seed.sql                       Datos iniciales
├── stark-insight-forge/               Frontend Vite + React (submódulo)
│   └── ...
├── docs/                              Documentos oficiales del hackathon
├── data-models.md                     Modelo de datos del MVP
├── backlog.md                         Backlog priorizado
├── miro-research-phase.md             Research consolidado del tablero Miro
├── softserve-analisis-reto3.md        Análisis estratégico del sponsor
├── pitch-stark-mind-demo-y-qa.md      Dossier de pitch (fuente)
├── pitch-stark-mind-demo-y-qa.pdf     Dossier de pitch (PDF final)
├── CLAUDE.md                          Instrucciones del proyecto
└── .mcp.json                          Configuración MCP Miro
```

---

## Requisitos previos

Antes de empezar, instala:

- **Git** con soporte para submódulos (cualquier versión reciente).
- **Docker** (o PostgreSQL 16 local con pgvector).
- **Python 3.12+**.
- **`uv`** — gestor moderno de dependencias Python. Instalación:
  ```bash
  brew install uv             # macOS
  curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux / WSL
  ```
- **Bun** para el frontend:
  ```bash
  curl -fsSL https://bun.sh/install | bash
  ```
  (También funciona con `npm` si prefieres — hay `package-lock.json`.)

Opcionales según el modo de ejecución:

- **Ollama** si vas a correr LLMs locales: https://ollama.com
- **Claves de API** para Anthropic / OpenAI / Google / Voyage si usarás los proveedores cloud.

---

## Clonar el proyecto (con submódulos)

Este repositorio incluye `stark-insight-forge` como **submódulo Git**. Para clonar todo de una sola vez:

```bash
git clone --recurse-submodules git@github.com:Freakscode/datahack-2026-stark-mind.git
cd datahack-2026-stark-mind
```

Si ya lo clonaste sin `--recurse-submodules`, inicializa los submódulos ahora:

```bash
git submodule update --init --recursive
```

---

## Setup paso a paso

### 1. Base de datos — Postgres + pgvector

La forma más rápida es correr Postgres 16 con pgvector en Docker:

```bash
docker run -d \
  --name starkvix-db \
  -e POSTGRES_PASSWORD=stark \
  -e POSTGRES_DB=starkvix \
  -p 5434:5432 \
  pgvector/pgvector:pg16
```

Cargar el schema y el seed:

```bash
# Schema (extensiones, tablas, índices)
docker exec -i starkvix-db psql -U postgres -d starkvix < db/schema.sql

# Datos de ejemplo (opcional pero recomendado)
docker exec -i starkvix-db psql -U postgres -d starkvix < db/seed.sql
```

Verificar que `pgvector` esté disponible:

```bash
docker exec -it starkvix-db psql -U postgres -d starkvix -c "SELECT extname, extversion FROM pg_extension;"
```

Deberías ver `vector`, `pgcrypto` y `pg_trgm` listadas.

> Si prefieres un Postgres local sin Docker, instala la extensión `pgvector` siguiendo las instrucciones de https://github.com/pgvector/pgvector y crea la base `starkvix` en el puerto `5434` con usuario `postgres` y contraseña `stark`, o ajusta `DATABASE_URL` en el `.env` del backend.

### 2. Backend — FastAPI (STARK-VIX)

```bash
cd backend

# 1) Variables de entorno
cp .env.example .env
# Edita .env: agrega tus API keys si vas a usar agentes cloud.

# 2) Dependencias base (FastAPI + SQLAlchemy + pgvector)
uv sync

# 3) (Opcional) Dependencias de agentes — LangGraph, Anthropic, OpenAI, Google, Ollama
uv sync --extra agents
```

Verifica que el backend levanta:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Visita:

- http://127.0.0.1:8000 — metadata del servicio
- http://127.0.0.1:8000/docs — Swagger UI con todos los endpoints
- http://127.0.0.1:8000/ready — readiness (verifica DB + pgvector)

### 3. Frontend — Vite + React (stark-insight-forge)

```bash
cd stark-insight-forge

# 1) Variables de entorno
cp .env.example .env
# .env apunta por default a VITE_API_BASE_URL=http://127.0.0.1:8000

# 2) Dependencias
bun install
# (o: npm install)

# 3) Dev server
bun run dev
# (o: npm run dev)
```

El frontend queda en http://localhost:8080 (o el puerto que Vite asigne).

---

## Ejecutar en desarrollo

Flujo típico con las tres partes corriendo en paralelo, en terminales distintas:

```bash
# Terminal 1 — Base de datos (solo la primera vez, luego queda corriendo)
docker start starkvix-db

# Terminal 2 — Backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 3 — Frontend
cd stark-insight-forge && bun run dev
```

### Tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd stark-insight-forge && bun run test
```

### Lint y formato

```bash
# Backend
cd backend && uv run ruff check . && uv run ruff format .

# Frontend
cd stark-insight-forge && bun run lint
```

---

## Variables de entorno

### `backend/.env`

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | Sí | Conexión async a Postgres. Default: `postgresql+asyncpg://postgres:stark@localhost:5434/starkvix` |
| `ANTHROPIC_API_KEY` | No | Requerida si usas agentes con Claude |
| `OPENAI_API_KEY` | No | Requerida si usas agentes con GPT |
| `GOOGLE_API_KEY` | No | Requerida si usas agentes con Gemini |
| `VOYAGE_API_KEY` | No | Requerida para embeddings Voyage |
| `OLLAMA_BASE_URL` | No | Default `http://localhost:11434` (solo si corres Ollama local) |
| `SERPAPI_KEY` | No | Para búsqueda web en el Discovery Agent |
| `ARXIV_RATE_LIMIT` | No | Default `3` (segundos entre requests) |
| `LOG_LEVEL` | No | Default `INFO` |
| `CORS_ORIGINS` | No | Default `http://localhost:8080,http://localhost:8081` |
| `DEFAULT_EXECUTION_MODE` | No | `local` o `cloud`. Default `local` |

### `stark-insight-forge/.env`

| Variable | Obligatoria | Descripción |
|---|---|---|
| `VITE_API_BASE_URL` | Sí | URL del backend. Default `http://127.0.0.1:8000` |

---

## Dossier de pitch y research

| Archivo | Contenido |
|---|---|
| `pitch-stark-mind-demo-y-qa.pdf` | Dossier consolidado del pitch: contexto estratégico, script de demo minuto a minuto y banco de 46 preguntas IA/ML con respuestas. Distribuir a los pitchers 48h antes del ensayo. |
| `miro-research-phase.md` | Research consolidado del tablero Miro: plan maestro, benchmarking de 7 productos competidores, arquitectura multi-agente, user journeys de 3 personas, framework de 8 decisiones UX. |
| `softserve-analisis-reto3.md` | Análisis estratégico del sponsor: servicios alineados con el reto, dog whistles técnicos, diferenciadores. Base del pitch. |
| `data-models.md` | Modelo de datos del MVP. |
| `backlog.md` | Backlog priorizado. |
| `docs/` | Documentos oficiales del hackathon (reglamento, rúbrica, instrucciones del reto, recomendaciones de pitch). |

---

## Trabajar con el submódulo

`stark-insight-forge` vive en https://github.com/danielita2508/stark-insight-forge y se consume como submódulo. Comandos útiles:

```bash
# Actualizar el submódulo al último commit del remote
git submodule update --remote stark-insight-forge

# Tras actualizar, registra el nuevo puntero en este repo
git add stark-insight-forge
git commit -m "Bump stark-insight-forge submodule"
git push

# Clonar submódulos si se te olvidó al hacer clone inicial
git submodule update --init --recursive
```

> **Importante:** el submódulo apunta a un commit específico del repo externo. Los cambios que hagas dentro de `stark-insight-forge/` deben commitearse y pushearse **en ese repo aparte**, no en este.

---

## Solución de problemas

**`connection refused` al backend en el puerto 5434.**
Verifica que el contenedor Postgres esté corriendo: `docker ps | grep starkvix-db`. Si no, arranca con `docker start starkvix-db`.

**`extension "vector" does not exist`.**
La imagen de Postgres no tiene pgvector. Usa `pgvector/pgvector:pg16` tal como en el paso 1, no `postgres:16`.

**`uv: command not found`.**
Instala `uv`: `brew install uv` en macOS o el instalador oficial de astral.sh. Asegúrate de que `~/.local/bin` esté en tu `PATH`.

**El frontend no conecta con el backend.**
Revisa que `VITE_API_BASE_URL` en `stark-insight-forge/.env` apunte al backend real, y que `CORS_ORIGINS` en `backend/.env` incluya el puerto del frontend (por default `http://localhost:8080`).

**Cambios en `stark-insight-forge/` no aparecen en este repo.**
El submódulo referencia un commit específico. Debes: (1) commitear y pushear los cambios en el repo de `stark-insight-forge`; (2) en este repo, correr `git submodule update --remote stark-insight-forge && git add stark-insight-forge && git commit -m "Bump submodule"`.

**`uv sync` falla al instalar `asyncpg` o `pgvector`.**
Verifica que tienes Python 3.12+ disponible: `python3 --version`. Si no, instala con `brew install python@3.12`.

---

## Licencia y equipo

Proyecto desarrollado en el marco de **DataHack 2026 — Reto 3** (sponsor SoftServe), por el equipo de la IU Pascual Bravo.

Para dudas sobre el pitch o el producto, consultar `pitch-stark-mind-demo-y-qa.pdf`.
