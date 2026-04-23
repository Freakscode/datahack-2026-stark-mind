# STARK-VIX · Backend

FastAPI + SQLAlchemy 2 (async) + pgvector.

## Setup

```bash
# 0. Prerequisitos (una sola vez)
#    - Docker con pgvector corriendo (ver db/ en la raíz del workspace)
#    - uv 0.8+ (brew install uv)

# 1. Configuración
cp .env.example .env

# 2. Dependencias
uv sync

# 3. Dev server
uv run uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /` · metadata del servicio
- `GET /docs` · Swagger UI
- `GET /health` · liveness
- `GET /ready` · readiness (verifica DB + pgvector)
- `GET /projects` · lista proyectos
- `GET /projects/{id}` · un proyecto
- `GET /projects/{id}/papers` · papers asociados
- `GET /projects/{id}/notes` · notas
- `GET /models` · catálogo de modelos (LLM + embeddings)

## Estructura

```
app/
├── main.py              # FastAPI app + CORS + routers
├── core/
│   ├── config.py        # Settings (Pydantic, lee .env)
│   └── db.py            # Engine async + SessionLocal
├── api/
│   ├── deps.py          # SessionDep
│   └── routers/
│       ├── health.py
│       ├── projects.py
│       └── models.py
└── db/
    ├── models.py        # SQLAlchemy ORM (11 tablas)
    └── schemas.py       # Pydantic v2 (Create/Read/Update)
```
