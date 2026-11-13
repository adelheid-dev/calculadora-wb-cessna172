"""
Envelope de voo (CG × Peso) como polígono e verificação geométrica.

Usa duas abordagens independentes e compara os resultados:
    1. Shapely  -> Polygon.contains()  (interior estrito, borda NÃO conta)
    2. Matplotlib Path -> contains_point() (ray casting)

"Rigorosamente dentro" = ponto no interior do polígono, não sobre a borda.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from matplotlib.path import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.validation import explain_validity


class Status(Enum):
    INSIDE = "DENTRO DO ENVELOPE"
    ON_BOUNDARY = "SOBRE O LIMITE (não aprovado)"
    OUTSIDE = "FORA DO ENVELOPE"


@dataclass(frozen=True)
class EnvelopeCheck:
    status: Status
    margin: float          # distância (no espaço normalizado) até a borda
    shapely_inside: bool
    mpl_path_inside: bool

    @property
    def is_safe(self) -> bool:
        return self.status is Status.INSIDE


class FlightEnvelope:
    """
    Envelope definido por vértices (cg_m, peso_kg), em ordem (horário ou anti-horário).

    Como CG (~1 m) e Peso (~1000 kg) têm escalas muito diferentes, a margem
    é calculada num espaço normalizado [0,1]×[0,1] para ser significativa.
    """

    def __init__(self, name: str, vertices: list[tuple[float, float]]):
        if len(vertices) < 3:
            raise ValueError("O envelope precisa de pelo menos 3 vértices.")
        self.name = name
        self.vertices = np.asarray(vertices, dtype=float)

        self.polygon = Polygon(self.vertices)
        if not self.polygon.is_valid:
            raise ValueError(f"Envelope inválido: {explain_validity(self.polygon)}")

        # Path fechado para o matplotlib
        closed = np.vstack([self.vertices, self.vertices[0]])
        codes = [Path.MOVETO] + [Path.LINETO] * (len(self.vertices) - 1) + [Path.CLOSEPOLY]
        self.path = Path(closed, codes)

        # Normalização para cálculo de margem
        self._min = self.vertices.min(axis=0)
        self._span = self.vertices.max(axis=0) - self._min
        self._norm_poly = Polygon(self._normalize(self.vertices))

    # ------------------------------------------------------------------ #
    def _normalize(self, pts: np.ndarray) -> np.ndarray:
        return (np.asarray(pts, dtype=float) - self._min) / self._span

    @property
    def cg_limits(self) -> tuple[float, float]:
        return float(self.vertices[:, 0].min()), float(self.vertices[:, 0].max())

    @property
    def weight_limits(self) -> tuple[float, float]:
        return float(self.vertices[:, 1].min()), float(self.vertices[:, 1].max())

    # ------------------------------------------------------------------ #
    def check(self, cg: float, weight: float, tol: float = 1e-9) -> EnvelopeCheck:
        """Verifica geometricamente se o ponto (CG, Peso) está estritamente dentro."""
        pt = Point(cg, weight)

        shapely_inside = self.polygon.contains(pt)          # borda excluída
        on_boundary = self.polygon.boundary.distance(pt) <= tol
        # radius negativo encolhe o polígono -> pontos na borda ficam fora
        mpl_inside = bool(self.path.contains_point((cg, weight), radius=-tol))

        if on_boundary:
            status = Status.ON_BOUNDARY
        elif shapely_inside and mpl_inside:
            status = Status.INSIDE
        elif not shapely_inside and not mpl_inside:
            status = Status.OUTSIDE
        else:  # métodos discordam -> conservador
            status = Status.ON_BOUNDARY

        npt = Point(*self._normalize([cg, weight]))
        margin = self._norm_poly.boundary.distance(npt)
        if status is not Status.INSIDE:
            margin = -margin  # negativo = fora / sobre o limite

        return EnvelopeCheck(status, float(margin), shapely_inside, mpl_inside)

    def check_path(self, p0: tuple[float, float], p1: tuple[float, float],
                   samples: int = 200, tol: float = 1e-9) -> bool:
        """
        Verifica se TODO o segmento p0→p1 (ex.: trajetória do CG durante a
        queima de combustível) está estritamente dentro do envelope.

        Dupla validação:
            - Shapely: o segmento está contido e não toca a borda;
            - Matplotlib Path: amostragem de `samples` pontos ao longo do segmento.
        """
        line = LineString([p0, p1])
        shapely_ok = self.polygon.contains(line) and not line.intersects(self.polygon.boundary)
        t = np.linspace(0.0, 1.0, samples)[:, None]
        pts = (1 - t) * np.asarray(p0, float) + t * np.asarray(p1, float)
        mpl_ok = bool(self.path.contains_points(pts, radius=-tol).all())
        return shapely_ok and mpl_ok
