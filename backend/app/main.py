"""STARK-VIX FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import extractions, health, latent, models, projects, queries
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: aquí van las conexiones y warmups futuros (Ollama, embeddings, etc.)
    yield
    # Shutdown


app = FastAPI(
    title="STARK-VIX API",
    description="Multi-agent research assistant backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(queries.router)
app.include_router(models.router)
app.include_router(extractions.router)
app.include_router(latent.router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "name": "stark-vix-api",
        "version": "0.1.0",
        "docs": "/docs",
    }
