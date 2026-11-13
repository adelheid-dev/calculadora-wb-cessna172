"""Geração e exportação do relatório de W&B em arquivo .txt."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .analysis import Analysis, Condition
from .calculations import format_table
from .config import IN_TO_M, LB_TO_KG

WIDTH = 82


def _hdr(title: str) -> str:
    return f"\n{'=' * WIDTH}\n{title}\n{'=' * WIDTH}"


def _cond_line(c: Condition, wu: str, au: str) -> str:
    r = c.result
    return (f"{c.label:<24}{r.total_weight:>9.1f} {wu}{r.cg:>9.2f} {au}"
            f"{r.total_moment / 1000:>10.1f}   {c.check.status.value}")


def build_report(a: Analysis, generated_at: datetime | None = None) -> str:
    ac, cat = a.aircraft, a.category
    wu, au = ac.weight_unit, ac.arm_unit
    ts = (generated_at or datetime.now()).strftime("%d/%m/%Y %H:%M:%S")
    fwd, aft = a.envelope.cg_limits
    tk, zf = a.takeoff, a.zfw

    out: list[str] = [
        "=" * WIDTH,
        "RELATÓRIO DE PESO E BALANCEAMENTO (W&B)".center(WIDTH),
        "=" * WIDTH,
        f"Aeronave ........: {ac.name}",
        f"Categoria .......: {cat.name}",
        f"Gerado em .......: {ts}",
        f"Unidades ........: peso em {wu}, braço em {au}, momento em {ac.moment_unit}",
        f"MTOW / Rampa ....: {cat.max_takeoff_weight:.0f} / {cat.max_ramp_weight:.0f} {wu}",
        f"Limites de CG ...: {fwd:.1f} a {aft:.1f} {au} (dianteiro varia com o peso)",
        f"Combustível .....: {ac.fuel_density:g} {wu}/gal; táxi/run-up "
        f"{ac.taxi_fuel_gal:g} gal ({ac.taxi_fuel_gal * ac.fuel_density:.1f} {wu})",
        _hdr("1. TABELA DE MOMENTOS — CONDIÇÃO DE RAMPA"),
        format_table(a.ramp.result, "", wu, au),
        _hdr("2. CONDIÇÕES DE VOO"),
        f"{'Condição':<24}{'Peso':>12}{'CG':>12}{'Mom/1000':>10}   Envelope",
        "-" * WIDTH,
        _cond_line(a.ramp, wu, au),
        _cond_line(tk, wu, au),
        _cond_line(zf, wu, au),
        "-" * WIDTH,
        f"Deslocamento do CG na queima (Decolagem→ZFW): "
        f"{zf.result.cg - tk.result.cg:+.2f} {au}",
        f"Trajetória de queima inteira dentro do envelope: "
        f"{'SIM' if a.burn_path_ok else 'NÃO'}",
        "",
        "Equivalente SI (Decolagem): "
        f"{tk.result.total_weight * LB_TO_KG:.1f} kg | CG {tk.result.cg * IN_TO_M:.4f} m"
        if wu == "lb" and au == "in" else "",
        _hdr("3. VALIDAÇÃO GEOMÉTRICA DO ENVELOPE (Shapely + Matplotlib Path)"),
        f"{'Condição':<24}{'Shapely':>10}{'MPL Path':>10}{'Margem norm.':>14}   Resultado",
        "-" * WIDTH,
    ]
    for c in (tk, zf):
        k = c.check
        out.append(f"{c.label:<24}{str(k.shapely_inside):>10}{str(k.mpl_path_inside):>10}"
                   f"{k.margin:>+14.3f}   {k.status.value}")
    out.append("(margem > 0 = dentro; distância à borda no envelope normalizado 0–1)")

    out.append(_hdr("4. LIMITAÇÕES OPERACIONAIS"))
    if a.violations:
        out += [f"  ✗ {v}" for v in a.violations]
    else:
        out.append("  ✓ Nenhuma limitação de estação, combustível ou peso excedida.")
    if cat.notes:
        out.append(f"  ℹ {cat.notes}")

    verdict = "APROVADO PARA VOO" if a.approved else "NÃO APROVADO PARA VOO"
    out += [
        _hdr(f"5. STATUS FINAL: {verdict}"),
        "",
        "AVISO: ferramenta de estudo/conferência. Confirme sempre com o POH/AFM e a",
        "ficha de pesagem da aeronave. A responsabilidade é do piloto em comando.",
        "",
        "Piloto em comando: ______________________   Assinatura: ________________",
        "=" * WIDTH,
    ]
    return "\n".join(line for line in out if line is not None) + "\n"


def export_report(a: Analysis, path: str | Path | None = None,
                  directory: str | Path = "relatorios") -> Path:
    """
    Grava o relatório em UTF-8 e devolve o caminho.
    Sem `path`, cria relatorios/wb_<categoria>_<AAAAMMDD_HHMMSS>.txt.
    Erros de E/S são propagados como OSError para o chamador tratar.
    """
    now = datetime.now()
    if path is None:
        path = Path(directory) / f"wb_{a.category_key}_{now:%Y%m%d_%H%M%S}.txt"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_report(a, now), encoding="utf-8")
    return path
