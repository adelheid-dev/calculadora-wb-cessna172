"""
Dados de referência da aeronave: Cessna 172S Skyhawk SP (TCDS 3A12).

Unidades nativas do POH (mantidas para conferência direta com o manual):
    Peso ....... lb (libras)
    Braço ...... in (polegadas a partir do Datum — face frontal da parede de fogo)
    Momento .... lb·in

Fontes: POH/AFM Cessna 172S, Seção 2 (Limitações) e Seção 6 (Peso e Balanceamento).

⚠️  O Peso Básico Vazio (BEW) e seu braço MUDAM DE AVIÃO PARA AVIÃO.
    Substitua-os pelos valores da Ficha de Pesagem da SUA aeronave.
    Este software é uma ferramenta de estudo/conferência e não substitui o POH.
"""
from __future__ import annotations

from dataclasses import dataclass, field

LB_TO_KG = 0.45359237
IN_TO_M = 0.0254


@dataclass(frozen=True)
class StationSpec:
    """Estação de carga definida no POH."""

    key: str
    label: str
    arm: float                               # braço padrão
    default_weight: float = 0.0
    max_weight: float | None = None          # limite estrutural da estação
    arm_range: tuple[float, float] | None = None  # bancos ajustáveis
    is_fuel: bool = False


@dataclass(frozen=True)
class CombinedLimit:
    """Limite de peso que se aplica à soma de várias estações."""

    keys: tuple[str, ...]
    max_weight: float
    label: str


@dataclass(frozen=True)
class CategorySpec:
    """Categoria de certificação: envelope geométrico e restrições."""

    name: str
    max_takeoff_weight: float
    max_ramp_weight: float
    envelope: tuple[tuple[float, float], ...]       # vértices (CG, Peso)
    empty_stations: tuple[str, ...] = ()            # estações que devem estar vazias
    notes: str = ""


@dataclass(frozen=True)
class AircraftSpec:
    name: str
    weight_unit: str
    arm_unit: str
    bew: float                    # Peso Básico Vazio
    bew_arm: float
    fuel_density: float           # lb/gal
    usable_fuel_gal: float
    taxi_fuel_gal: float          # partida, táxi e run-up
    stations: tuple[StationSpec, ...]
    combined_limits: tuple[CombinedLimit, ...]
    categories: dict[str, CategorySpec] = field(default_factory=dict)

    @property
    def moment_unit(self) -> str:
        return f"{self.weight_unit}·{self.arm_unit}"

    def station(self, key: str) -> StationSpec:
        for s in self.stations:
            if s.key == key:
                return s
        raise KeyError(key)


# --------------------------------------------------------------------------- #
#  CESSNA 172S
# --------------------------------------------------------------------------- #
CESSNA_172S = AircraftSpec(
    name="Cessna 172S Skyhawk SP",
    weight_unit="lb",
    arm_unit="in",
    # Exemplo típico de BEW (inclui óleo e combustível inutilizável).
    # >>> SUBSTITUA pelos dados da ficha de pesagem da sua aeronave <<<
    bew=1663.0,
    bew_arm=40.6,
    fuel_density=6.0,             # AVGAS 100LL ≈ 6,0 lb/gal US
    usable_fuel_gal=53.0,         # tanques padrão (56 gal total)
    taxi_fuel_gal=1.1,            # POH: 1,1 gal para partida/táxi/run-up
    stations=(
        StationSpec("front", "Piloto + passageiro dianteiro", 37.0, 340.0,
                    arm_range=(34.0, 46.0)),
        StationSpec("rear", "Passageiros traseiros", 73.0, 170.0),
        StationSpec("bag_a", "Bagagem Área A (1)", 95.0, 40.0, max_weight=120.0),
        StationSpec("bag_b", "Bagagem Área B (2)", 123.0, 0.0, max_weight=50.0),
        StationSpec("fuel", "Combustível utilizável", 48.0, 40 * 6.0,
                    max_weight=53.0 * 6.0, is_fuel=True),
    ),
    combined_limits=(
        CombinedLimit(("bag_a", "bag_b"), 120.0, "Bagagem A + B combinada"),
    ),
    categories={
        "normal": CategorySpec(
            name="Normal",
            max_takeoff_weight=2550.0,
            max_ramp_weight=2558.0,
            # Dianteiro: 35,0 in até 1950 lb, reta até 41,0 in a 2550 lb.
            # Traseiro: 47,3 in em todos os pesos.
            # (1500 lb é a borda inferior do gráfico do POH, não uma limitação.)
            envelope=(
                (35.0, 1500.0),
                (35.0, 1950.0),
                (41.0, 2550.0),
                (47.3, 2550.0),
                (47.3, 1500.0),
            ),
        ),
        "utility": CategorySpec(
            name="Utilidade",
            max_takeoff_weight=2200.0,
            max_ramp_weight=2208.0,
            # Dianteiro: 35,0 in até 1950 lb, reta até 37,5 in a 2200 lb.
            # Traseiro: 40,5 in em todos os pesos.
            envelope=(
                (35.0, 1500.0),
                (35.0, 1950.0),
                (37.5, 2200.0),
                (40.5, 2200.0),
                (40.5, 1500.0),
            ),
            empty_stations=("rear", "bag_a", "bag_b"),
            notes="Na categoria Utilidade, o banco traseiro e o bagageiro devem estar vazios.",
        ),
    },
)

AIRCRAFT = CESSNA_172S
