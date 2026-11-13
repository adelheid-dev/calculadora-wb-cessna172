"""
Cálculos de estática: peso total, momentos e Centro de Gravidade.

    W_total = Σ W_i
    M_total = Σ (W_i · d_i)
    CG      = M_total / W_total
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import LoadingCondition


@dataclass(frozen=True)
class WBResult:
    """Resultado consolidado de um cálculo de W&B."""

    names: tuple[str, ...]
    weights: np.ndarray
    arms: np.ndarray
    moments: np.ndarray
    total_weight: float
    total_moment: float
    cg: float


def compute(condition: LoadingCondition) -> WBResult:
    """Calcula pesos, momentos individuais, momento total e CG."""
    if not condition.items:
        raise ValueError("A condição de carregamento não possui itens.")

    weights = np.array([i.weight for i in condition.items], dtype=float)
    arms = np.array([i.arm for i in condition.items], dtype=float)
    moments = weights * arms  # vetorizado: M_i = W_i · d_i

    total_weight = float(weights.sum())
    total_moment = float(moments.sum())
    if total_weight <= 0:
        raise ValueError("Peso total deve ser maior que zero.")

    return WBResult(
        names=tuple(i.name for i in condition.items),
        weights=weights,
        arms=arms,
        moments=moments,
        total_weight=total_weight,
        total_moment=total_moment,
        cg=total_moment / total_weight,
    )


def format_table(result: WBResult, title: str = "Planilha de W&B",
                 w_unit: str = "lb", a_unit: str = "in") -> str:
    """Tabela de momentos no formato de planilha de despacho."""
    m_unit = f"{w_unit}·{a_unit}"
    width = 82
    line = "-" * width
    rows = ([title] if title else []) + [
        line,
        f"{'Item':<32}{'Peso (' + w_unit + ')':>11}{'Braço (' + a_unit + ')':>12}"
        f"{'Momento (' + m_unit + ')':>17}{'Mom/1000':>10}",
        line,
    ]
    for n, w, a, m in zip(result.names, result.weights, result.arms, result.moments):
        rows.append(f"{n:<32}{w:>11.1f}{a:>12.2f}{m:>17.1f}{m / 1000:>10.1f}")
    rows += [
        line,
        f"{'TOTAL':<32}{result.total_weight:>11.1f}{result.cg:>12.2f}"
        f"{result.total_moment:>17.1f}{result.total_moment / 1000:>10.1f}",
        line,
        f"CG = {result.total_moment:.1f} / {result.total_weight:.1f} "
        f"= {result.cg:.2f} {a_unit} do Datum",
    ]
    return "\n".join(rows)