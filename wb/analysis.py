
"""
Orquestra a análise completa: Rampa → Decolagem (após táxi) → ZFW.
Reúne cálculos de estática, verificação geométrica e limitações.
"""
from __future__ import annotations

from dataclasses import dataclass

from .calculations import WBResult, compute
from .config import AircraftSpec, CategorySpec
from .envelope import EnvelopeCheck, FlightEnvelope
from .limits import check_limits
from .models import LoadingCondition


@dataclass(frozen=True)
class Condition:
    label: str
    result: WBResult
    check: EnvelopeCheck


@dataclass(frozen=True)
class Analysis:
    aircraft: AircraftSpec
    category_key: str
    category: CategorySpec
    envelope: FlightEnvelope
    ramp: Condition
    takeoff: Condition
    zfw: Condition
    burn_path_ok: bool
    violations: list[str]

    @property
    def approved(self) -> bool:
        return (self.takeoff.check.is_safe and self.zfw.check.is_safe
                and self.burn_path_ok and not self.violations)


def analyze(aircraft: AircraftSpec, ramp_loading: LoadingCondition,
            category_key: str = "normal") -> Analysis:
    category = aircraft.categories[category_key]
    envelope = FlightEnvelope(f"{aircraft.name} — Cat. {category.name}", category.envelope)

    taxi_fuel = aircraft.taxi_fuel_gal * aircraft.fuel_density
    takeoff_loading = ramp_loading.burn_fuel(taxi_fuel)

    def cond(label: str, loading: LoadingCondition) -> Condition:
        r = compute(loading)
        return Condition(label, r, envelope.check(r.cg, r.total_weight))

    ramp = cond("Rampa", ramp_loading)
    takeoff = cond("Decolagem", takeoff_loading)
    zfw = cond("Zero Combustível (ZFW)", ramp_loading.without_fuel())

    burn_ok = envelope.check_path(
        (takeoff.result.cg, takeoff.result.total_weight),
        (zfw.result.cg, zfw.result.total_weight),
    )
    violations = check_limits(aircraft, category, ramp_loading,
                              ramp.result.total_weight, takeoff.result.total_weight)
    return Analysis(aircraft, category_key, category, envelope,
                    ramp, takeoff, zfw, burn_ok, violations)
