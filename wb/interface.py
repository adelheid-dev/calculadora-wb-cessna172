"""
Entrada interativa via terminal, à prova de valores inválidos.

Política de validação:
  - Valores sem sentido físico são BLOQUEADOS na entrada e pedidos de novo:
    texto, vazio inválido, NaN/infinito, negativos, braço fora do trilho do
    banco, combustível acima da capacidade dos tanques.
  - Valores fisicamente possíveis mas acima de uma LIMITAÇÃO (ex.: bagagem
    acima de 120 lb) são ACEITOS e depois reportados como violação — o
    piloto precisa ver o problema, não ser impedido de digitá-lo.
  - Ctrl+C / Ctrl+D (ou fim da entrada) geram UserAbort, tratado no main.
"""
from __future__ import annotations

import math
from typing import Callable

from .config import AircraftSpec
from .models import LoadingCondition, LoadItem

MAX_ATTEMPTS = 5


class UserAbort(Exception):
    """O usuário cancelou a entrada de dados."""


def _read(prompt: str, input_fn: Callable[[str], str]) -> str:
    try:
        return input_fn(prompt)
    except (KeyboardInterrupt, EOFError) as exc:
        raise UserAbort from exc


def parse_number(raw: str) -> float:
    """Converte texto em float aceitando vírgula decimal. Rejeita NaN/inf."""
    text = raw.strip().replace(" ", "")
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    value = float(text)  # pode levantar ValueError
    if not math.isfinite(value):
        raise ValueError("valor não finito")
    return value


def ask_float(prompt: str, default: float, min_value: float | None = None,
              max_value: float | None = None,
              input_fn: Callable[[str], str] = input,
              print_fn: Callable[..., None] = print) -> float:
    """Pergunta um número até receber um valor válido (Enter = padrão)."""
    rng = ""
    if min_value is not None and max_value is not None:
        rng = f" ({min_value:g}–{max_value:g})"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = _read(f"  {prompt}{rng} [{default:g}]: ", input_fn)
        if raw.strip() == "":
            return default
        try:
            value = parse_number(raw)
        except ValueError:
            print_fn(f"    ✗ '{raw.strip()}' não é um número válido. Ex.: 170 ou 37,5")
            continue
        if min_value is not None and value < min_value:
            print_fn(f"    ✗ O valor deve ser ≥ {min_value:g}.")
            continue
        if max_value is not None and value > max_value:
            print_fn(f"    ✗ O valor deve ser ≤ {max_value:g}.")
            continue
        return value
    print_fn(f"    ! {MAX_ATTEMPTS} tentativas inválidas — usando o padrão ({default:g}).")
    return default


def ask_choice(prompt: str, options: dict[str, str], default: str,
               input_fn: Callable[[str], str] = input,
               print_fn: Callable[..., None] = print) -> str:
    keys = list(options)
    menu = "  ".join(f"[{i}] {options[k]}" for i, k in enumerate(keys, 1))
    for _ in range(MAX_ATTEMPTS):
        raw = _read(f"{prompt}\n  {menu}  [{keys.index(default) + 1}]: ", input_fn).strip().lower()
        if raw == "":
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(keys):
            return keys[int(raw) - 1]
        for k, label in options.items():
            if raw in (k.lower(), label.lower()):
                return k
        print_fn("    ✗ Opção inválida.")
    print_fn(f"    ! Usando o padrão: {options[default]}.")
    return default


def read_loading_interactive(ac: AircraftSpec,
                             input_fn: Callable[[str], str] = input,
                             print_fn: Callable[..., None] = print) -> tuple[LoadingCondition, str]:
    """Coleta categoria e carregamento. Retorna (condição de RAMPA, categoria)."""
    wu, au = ac.weight_unit, ac.arm_unit
    sanity_max = 2 * max(c.max_ramp_weight for c in ac.categories.values())

    category = ask_choice("Categoria de operação:",
                          {k: c.name for k, c in ac.categories.items()}, "normal",
                          input_fn, print_fn)

    print_fn(f"\nInforme os pesos ({wu}) e braços ({au} do Datum). Enter = padrão.\n")
    cond = LoadingCondition()

    print_fn("▸ Peso Básico Vazio (da ficha de pesagem)")
    bew = ask_float(f"Peso ({wu})", ac.bew, 1.0, sanity_max, input_fn, print_fn)
    bew_arm = ask_float(f"Braço ({au})", ac.bew_arm, 0.0, 200.0, input_fn, print_fn)
    cond.add(LoadItem("Peso Básico Vazio (BEW)", bew, bew_arm, key="bew"))

    for st in ac.stations:
        print_fn(f"▸ {st.label}")
        if st.is_fuel:
            gal = ask_float("Combustível utilizável (gal US)",
                            st.default_weight / ac.fuel_density,
                            0.0, ac.usable_fuel_gal, input_fn, print_fn)
            weight = gal * ac.fuel_density
            print_fn(f"    → {gal:g} gal × {ac.fuel_density:g} {wu}/gal = {weight:.1f} {wu}")
            arm = st.arm
        else:
            weight = ask_float(f"Peso ({wu})", st.default_weight, 0.0, sanity_max,
                               input_fn, print_fn)
            if st.arm_range:
                arm = ask_float(f"Braço ({au})", st.arm, *st.arm_range,
                                input_fn=input_fn, print_fn=print_fn)
            else:
                arm = st.arm  # estação fixa no POH
        cond.add(LoadItem(st.label, weight, arm, st.is_fuel, st.key))
    return cond, category


def default_loading(ac: AircraftSpec) -> LoadingCondition:
    cond = LoadingCondition([LoadItem("Peso Básico Vazio (BEW)", ac.bew, ac.bew_arm, key="bew")])
    for st in ac.stations:
        cond.add(LoadItem(st.label, st.default_weight, st.arm, st.is_fuel, st.key))
    return cond
