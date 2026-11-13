"""
Verificação de limitações operacionais que não são capturadas pelo envelope
geométrico: pesos máximos por estação, limites combinados, combustível,
peso de rampa/decolagem e restrições da categoria.
"""
from __future__ import annotations

from .config import AircraftSpec, CategorySpec
from .models import LoadingCondition


def check_limits(aircraft: AircraftSpec, category: CategorySpec,
                 ramp: LoadingCondition, ramp_weight: float,
                 takeoff_weight: float) -> list[str]:
    """Retorna a lista de violações (vazia = nenhuma)."""
    u = aircraft.weight_unit
    violations: list[str] = []

    for st in aircraft.stations:
        w = ramp.weight_of(st.key)
        if st.max_weight is not None and w > st.max_weight:
            violations.append(
                f"{st.label}: {w:.1f} {u} excede o máximo de {st.max_weight:.0f} {u} "
                f"(+{w - st.max_weight:.1f})")

    for lim in aircraft.combined_limits:
        w = sum(ramp.weight_of(k) for k in lim.keys)
        if w > lim.max_weight:
            violations.append(
                f"{lim.label}: {w:.1f} {u} excede o máximo de {lim.max_weight:.0f} {u}")

    for key in category.empty_stations:
        w = ramp.weight_of(key)
        if w > 0:
            violations.append(
                f"Categoria {category.name}: '{aircraft.station(key).label}' "
                f"deve estar vazia ({w:.1f} {u} carregados)")

    if ramp_weight > category.max_ramp_weight:
        violations.append(
            f"Peso de rampa {ramp_weight:.1f} {u} excede o máximo de "
            f"{category.max_ramp_weight:.0f} {u} (+{ramp_weight - category.max_ramp_weight:.1f})")
    if takeoff_weight > category.max_takeoff_weight:
        violations.append(
            f"Peso de decolagem {takeoff_weight:.1f} {u} excede o MTOW de "
            f"{category.max_takeoff_weight:.0f} {u} "
            f"(+{takeoff_weight - category.max_takeoff_weight:.1f})")
    return violations