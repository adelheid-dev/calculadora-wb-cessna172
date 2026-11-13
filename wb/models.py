"""
Modelos de dados do problema de Peso e Balanceamento (W&B).

Os modelos são agnósticos de unidade: basta usar o mesmo sistema
(lb/in ou kg/m) em todos os itens.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class LoadItem:
    """Um item de carga posicionado em uma estação da aeronave."""

    name: str
    weight: float
    arm: float
    is_fuel: bool = False
    key: str = ""

    def __post_init__(self) -> None:
        for label, v in (("peso", self.weight), ("braço", self.arm)):
            if not math.isfinite(v):
                raise ValueError(f"{label} não finito em '{self.name}': {v}")
        if self.weight < 0:
            raise ValueError(f"Peso negativo em '{self.name}': {self.weight}")

    @property
    def moment(self) -> float:
        """Momento estático M = W · d."""
        return self.weight * self.arm


@dataclass
class LoadingCondition:
    """Conjunto de itens de carga que define uma condição de carregamento."""

    items: list[LoadItem] = field(default_factory=list)

    def add(self, item: LoadItem) -> None:
        self.items.append(item)

    def weight_of(self, key: str) -> float:
        return sum(i.weight for i in self.items if i.key == key)

    def without_fuel(self) -> "LoadingCondition":
        """Condição de Peso Zero Combustível (ZFW)."""
        return LoadingCondition([i for i in self.items if not i.is_fuel])

    def burn_fuel(self, amount: float) -> "LoadingCondition":
        """Nova condição com `amount` (unid. de peso) a menos de combustível."""
        out: list[LoadItem] = []
        for i in self.items:
            if i.is_fuel:
                burned = min(amount, i.weight)
                amount -= burned
                i = replace(i, weight=i.weight - burned)
            out.append(i)
        return LoadingCondition(out)
