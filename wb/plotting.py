"""Visualização do envelope de voo e das condições de carregamento."""
from __future__ import annotations

from pathlib import Path as FsPath

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon as MplPolygon

from .analysis import Analysis, Condition

SAFE = "#1a9e3f"
UNSAFE = "#d62728"
EDGE = "#1f4e9c"
FILL = "#cfe0f7"


def _c(cond: Condition) -> str:
    return SAFE if cond.check.is_safe else UNSAFE


def plot_analysis(a: Analysis, save_path: str | None = None, show: bool = True):
    ac = a.aircraft
    wu, au = ac.weight_unit, ac.arm_unit
    fig, ax = plt.subplots(figsize=(10, 7))

    # Outras categorias como referência (contorno tracejado)
    for key, cat in ac.categories.items():
        if key == a.category_key:
            continue
        v = np.asarray(cat.envelope)
        ax.add_patch(MplPolygon(v, closed=True, fill=False, ls="--", lw=1.2,
                                ec="gray", label=f"Envelope Cat. {cat.name} (ref.)", zorder=3))

    # Envelope ativo, em destaque
    v = a.envelope.vertices
    ax.add_patch(MplPolygon(v, closed=True, fc=FILL, ec=EDGE, lw=2.5, alpha=0.9,
                            label=f"Envelope Cat. {a.category.name} (área segura)", zorder=2))
    ax.plot(v[:, 0], v[:, 1], "s", color=EDGE, ms=5, zorder=3)
    ax.axhline(a.category.max_takeoff_weight, color=EDGE, lw=0.8, ls=":", zorder=2)

    tk, zf = a.takeoff, a.zfw
    ax.plot([tk.result.cg, zf.result.cg], [tk.result.total_weight, zf.result.total_weight],
            "--", color="gray" if a.burn_path_ok else UNSAFE, lw=1.5, zorder=4,
            label="Deslocamento do CG na queima de combustível")

    ax.scatter(zf.result.cg, zf.result.total_weight, s=110, marker="D", color=_c(zf),
               ec="black", zorder=5, label=f"ZFW: {zf.check.status.value}")
    ax.annotate(f"ZFW\n{zf.result.cg:.2f} {au} | {zf.result.total_weight:.0f} {wu}",
                (zf.result.cg, zf.result.total_weight), textcoords="offset points",
                xytext=(-14, -30), ha="right", fontsize=9,
                bbox=dict(boxstyle="round", fc="white", ec="none", alpha=0.8))

    ax.scatter(tk.result.cg, tk.result.total_weight, s=220, color=_c(tk), ec="black",
               lw=1.5, zorder=6, label=f"Decolagem: {tk.check.status.value}")
    ax.annotate(f"CG = {tk.result.cg:.2f} {au}\nW = {tk.result.total_weight:.1f} {wu}",
                (tk.result.cg, tk.result.total_weight), textcoords="offset points",
                xytext=(14, 10), fontsize=10, fontweight="bold",
                bbox=dict(boxstyle="round", fc="white", ec=_c(tk)))

    all_v = np.vstack([np.asarray(c.envelope) for c in ac.categories.values()])
    xs = [*all_v[:, 0], tk.result.cg, zf.result.cg]
    ys = [*all_v[:, 1], tk.result.total_weight, zf.result.total_weight]
    dx, dy = (max(xs) - min(xs)) * 0.22, (max(ys) - min(ys)) * 0.12
    ax.set_xlim(min(xs) - dx, max(xs) + dx)
    ax.set_ylim(min(ys) - dy, max(ys) + dy)

    verdict = "APROVADO PARA VOO" if a.approved else "NÃO APROVADO"
    title = f"{ac.name} — Peso × CG (Cat. {a.category.name})\n{verdict}"
    if a.violations:
        title += f" — {len(a.violations)} limitação(ões) excedida(s)"
    ax.set_title(title, fontsize=12, fontweight="bold", color=SAFE if a.approved else UNSAFE)
    ax.set_xlabel(f"Posição do CG a partir do Datum ({au})")
    ax.set_ylabel(f"Peso ({wu})")
    ax.grid(True, ls=":", alpha=0.7)
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.95)
    fig.tight_layout()

    if save_path:
        FsPath(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    if show:
        plt.show()
    return fig, ax