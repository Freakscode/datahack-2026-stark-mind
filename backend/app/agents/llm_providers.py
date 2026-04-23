"""Factory agnóstica de LLM providers sobre LangChain.

Diseño:
  - El extractor no sabe qué provider usa: llama a `get_chat_model(config)`.
  - `config` se construye desde: (a) args del CLI, (b) env vars, (c) defaults.
  - El usuario final puede mezclar providers por nodo (ej. classify con
    gemma2:2b rápido + extraer columnas con gemma2:27b) — el `ExtractorConfig`
    lo soporta pero el MVP usa un solo modelo para todos los nodos.

Providers soportados en este primer commit:
  - ollama        (default — local, gemma2:27b)
  - anthropic     (claude-opus-4-7 / claude-sonnet-4-6 / claude-haiku-4-5)
  - openai        (gpt-4o / gpt-4o-mini)
  - google_genai  (gemini-1.5-pro / gemini-1.5-flash)

Cada import es lazy para que instalar `--extra agents` cargue todo pero el
backend base (sin extra) siga arrancando sin LangChain.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

Provider = Literal["ollama", "anthropic", "openai", "google_genai"]


@dataclass(frozen=True)
class LLMConfig:
    """Configuración completa de un LLM para un nodo del grafo."""

    provider: Provider = "ollama"
    model: str = "gemma4:26b"
    temperature: float = 0.1
    # Thinking models (gemma4, deepseek-r1, qwen3-thinking) gastan tokens en
    # el bloque de reasoning antes de emitir la respuesta final. Para un
    # prompt de ~5k tokens in, el thinking puede consumir 2500-4000 tokens
    # antes de llegar al JSON. 4500 deja margen cómodo.
    max_tokens: int = 4500
    # num_ctx: context window efectivo en Ollama. Gemma 4 soporta hasta 262K
    # pero con esa KV cache consume >40 GB RAM y fuerza CPU offload en M-series.
    # 16384 cubre cualquier prompt del extractor y mantiene inferencia en GPU.
    num_ctx: int = 16384
    # reasoning: si el modelo es "thinking" (gemma4, deepseek-r1, qwen3-thinking),
    # True separa el razonamiento en `additional_kwargs['reasoning_content']`
    # dejando el `content` limpio con solo el JSON final. None = comportamiento
    # default del modelo; para thinking models deja `<think>...</think>` inline.
    reasoning: bool | None = True
    # Provider-specific options (ej. ollama_base_url, top_p, etc.)
    extras: dict = field(default_factory=dict)


def _require_env(var: str, provider: str) -> str:
    val = os.environ.get(var)
    if not val:
        raise RuntimeError(
            f"{provider} requiere la variable de entorno {var}. "
            f"Setéala en backend/.env o exporta en tu shell."
        )
    return val


def get_chat_model(cfg: LLMConfig) -> "BaseChatModel":
    """Resuelve el provider y devuelve un ChatModel ya configurado.

    Raises:
        RuntimeError: si el provider pide env vars ausentes.
        ImportError: si no se instaló el extra `agents` o falta algún provider.
    """
    if cfg.provider == "ollama":
        from langchain_ollama import ChatOllama

        base_url = cfg.extras.get("base_url") or os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        return ChatOllama(
            model=cfg.model,
            temperature=cfg.temperature,
            num_predict=cfg.max_tokens,
            num_ctx=cfg.num_ctx,
            reasoning=cfg.reasoning,
            base_url=base_url,
            # format="json" deja el output del modelo directamente parseable,
            # reduce la necesidad de regex cleanup. Se aplica por prompt, no aquí.
        )

    if cfg.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        _require_env("ANTHROPIC_API_KEY", "anthropic")
        return ChatAnthropic(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    if cfg.provider == "openai":
        from langchain_openai import ChatOpenAI

        _require_env("OPENAI_API_KEY", "openai")
        return ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    if cfg.provider == "google_genai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        _require_env("GOOGLE_API_KEY", "google_genai")
        return ChatGoogleGenerativeAI(
            model=cfg.model,
            temperature=cfg.temperature,
            max_output_tokens=cfg.max_tokens,
        )

    raise ValueError(f"provider desconocido: {cfg.provider}")


def check_ollama_health(base_url: str = "http://localhost:11434", model: str | None = None) -> None:
    """Verifica que Ollama corre y opcionalmente que el modelo está pulled.

    Usado como primer paso del CLI. Si falla, imprime la instrucción `ollama pull`.
    """
    import httpx

    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(
            f"Ollama no responde en {base_url}. Arráncalo con `ollama serve` o "
            f"instala Ollama desde https://ollama.com. Detalle: {e}"
        ) from e

    if model:
        tags = [m["name"] for m in resp.json().get("models", [])]
        if model not in tags and model.split(":")[0] not in {t.split(":")[0] for t in tags}:
            raise RuntimeError(
                f"Modelo '{model}' no está disponible en Ollama. Pull con:\n"
                f"    ollama pull {model}\n"
                f"Modelos actuales: {tags or '(ninguno)'}"
            )


DEFAULT_CONFIG = LLMConfig(provider="ollama", model="gemma4:26b")


__all__ = [
    "DEFAULT_CONFIG",
    "LLMConfig",
    "Provider",
    "check_ollama_health",
    "get_chat_model",
]
