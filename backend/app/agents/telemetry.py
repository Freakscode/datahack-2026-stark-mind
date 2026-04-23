"""Telemetría: cálculo de tokens/s y costo estimado por evento.

Los modelos `local` devuelven cost=0. Los `frontier_mock` calculan con la fórmula
`tokens × cost_per_1m / 1_000_000`. Cuando el modelo no expone `default_tokens_per_second`
(p. ej. embedding models), el campo tok/s queda en None.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TypedDict

from app.db.models import Model


class Telemetry(TypedDict, total=False):
    model_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    tokens_per_second: Decimal | None
    latency_ms: int | None
    cost_estimated_usd: Decimal | None


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def compute_telemetry(
    model: Model | None,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    extra_latency_ms: int = 0,
) -> Telemetry:
    """Calcula telemetría realista a partir del catálogo `models`.

    - Para embedding/rerank models, latency viene de `extra_latency_ms`.
    - Para LLM, latency = output_tokens / default_tokens_per_second.
    - Cost = 0 si es local; cost formula con los rates si es frontier_mock.
    """
    if model is None:
        return {
            "model_id": None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens_per_second": None,
            "latency_ms": extra_latency_ms or None,
            "cost_estimated_usd": None,
        }

    tok_s = model.default_tokens_per_second
    latency_ms: int | None = extra_latency_ms or None
    if tok_s and output_tokens:
        latency_ms = int((float(output_tokens) / float(tok_s)) * 1000) + extra_latency_ms

    cost: Decimal | None
    if model.execution_mode == "local":
        cost = Decimal("0")
    elif (
        model.input_cost_per_1m_tokens is not None
        and model.output_cost_per_1m_tokens is not None
        and input_tokens is not None
        and output_tokens is not None
    ):
        in_cost = Decimal(input_tokens) * model.input_cost_per_1m_tokens / Decimal(1_000_000)
        out_cost = Decimal(output_tokens) * model.output_cost_per_1m_tokens / Decimal(1_000_000)
        cost = (in_cost + out_cost).quantize(Decimal("0.000001"))
    else:
        cost = None

    return {
        "model_id": model.id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tokens_per_second": tok_s,
        "latency_ms": latency_ms,
        "cost_estimated_usd": cost,
    }
