"""
Calculadora de Peso, Balanceamento e CG — Cessna 172S.

Uso:
    python main.py                               # interativo + gráfico + relatório .txt
    python main.py --demo                        # valores padrão, sem perguntas
    python main.py --demo --categoria utility    # categoria Utilidade
    python main.py --relatorio saida/voo.txt     # caminho do relatório
    python main.py --sem-relatorio --no-show --save out/wb.png

Códigos de saída: 0 aprovado | 1 não aprovado | 2 erro | 130 cancelado
"""
from __future__ import annotations

import argparse
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Calculadora de W&B — Cessna 172S")
    p.add_argument("--demo", action="store_true", help="usa valores padrão, sem entrada")
    p.add_argument("--categoria", choices=["normal", "utility"], default=None,
                   help="categoria (no modo interativo é perguntada)")
    p.add_argument("--relatorio", metavar="ARQ.txt", help="caminho do relatório .txt")
    p.add_argument("--sem-relatorio", action="store_true", help="não gera o .txt")
    p.add_argument("--save", metavar="ARQ.png", help="salva o gráfico em arquivo")
    p.add_argument("--no-show", action="store_true", help="não abre a janela do gráfico")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")

    from wb.analysis import analyze
    from wb.calculations import format_table
    from wb.config import AIRCRAFT as ac
    from wb.interface import UserAbort, default_loading, read_loading_interactive
    from wb.plotting import plot_analysis
    from wb.report import export_report

    print("=" * 78)
    print(f"  CALCULADORA DE W&B — {ac.name}".center(78))
    print("=" * 78)

    try:
        if args.demo:
            loading, category = default_loading(ac), args.categoria or "normal"
        else:
            loading, category = read_loading_interactive(ac)
            if args.categoria:
                category = args.categoria
    except UserAbort:
        print("\n\nEntrada cancelada pelo usuário. Nada foi calculado.")
        return 130

    try:
        a = analyze(ac, loading, category)
    except ValueError as exc:
        print(f"\n✗ Erro nos dados de entrada: {exc}")
        return 2

    wu, au = ac.weight_unit, ac.arm_unit
    print()
    print(format_table(a.ramp.result, "TABELA DE MOMENTOS — RAMPA", wu, au))
    for c in (a.ramp, a.takeoff, a.zfw):
        r = c.result
        print(f"{c.label:<24} W = {r.total_weight:7.1f} {wu} | CG = {r.cg:6.2f} {au}"
              f" -> {c.check.status.value}")
    print(f"Trajetória de queima dentro do envelope: {'SIM' if a.burn_path_ok else 'NÃO'}")
    for v in a.violations:
        print(f"⚠  {v}")
    print("\n>>> " + ("APROVADO PARA VOO ✅" if a.approved else "NÃO APROVADO ❌"))

    if not args.sem_relatorio:
        try:
            path = export_report(a, args.relatorio)
            print(f"\nRelatório salvo em: {path}")
        except OSError as exc:
            print(f"\n✗ Não foi possível salvar o relatório: {exc}")

    try:
        plot_analysis(a, save_path=args.save, show=not args.no_show)
    except OSError as exc:
        print(f"✗ Não foi possível salvar o gráfico: {exc}")

    return 0 if a.approved else 1


if __name__ == "__main__":
   sys.exit(main())
