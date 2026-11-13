import math

import pytest

from wb import FlightEnvelope, LoadingCondition, LoadItem, Status, analyze, compute
from wb.config import CESSNA_172S as AC
from wb.interface import UserAbort, ask_float, default_loading, parse_number, read_loading_interactive
from wb.report import build_report, export_report

SQUARE = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)]


# ---------------- Estática ---------------- #
def test_cg_simple_lever():
    r = compute(LoadingCondition([LoadItem("A", 100, 1.0), LoadItem("B", 100, 3.0)]))
    assert r.total_moment == pytest.approx(400)
    assert r.cg == pytest.approx(2.0)


@pytest.mark.parametrize("w,a", [(-1, 1.0), (math.nan, 1.0), (1.0, math.inf)])
def test_invalid_item_rejected(w, a):
    with pytest.raises(ValueError):
        LoadItem("X", w, a)


def test_burn_fuel():
    c = LoadingCondition([LoadItem("E", 1000, 40), LoadItem("F", 100, 48, is_fuel=True)])
    assert compute(c.burn_fuel(30)).total_weight == pytest.approx(1070)
    assert compute(c.burn_fuel(999)).total_weight == pytest.approx(1000)


# ---------------- Geometria ---------------- #
@pytest.mark.parametrize("pt,expected", [
    ((5, 5), Status.INSIDE), ((10, 5), Status.ON_BOUNDARY),
    ((0, 0), Status.ON_BOUNDARY), ((11, 5), Status.OUTSIDE),
])
def test_envelope_strict(pt, expected):
    assert FlightEnvelope("sq", SQUARE).check(*pt).status is expected


def test_self_intersecting_envelope_rejected():
    with pytest.raises(ValueError):
        FlightEnvelope("bowtie", [(0, 0), (1, 1), (1, 0), (0, 1)])


def test_c172_forward_limit_interpolation():
    env = FlightEnvelope("n", AC.categories["normal"].envelope)
    # 2250 lb: limite dianteiro = 35 + 6*(300/600) = 38,0 in
    assert env.check(38.0, 2250).status is Status.ON_BOUNDARY
    assert env.check(38.1, 2250).status is Status.INSIDE
    assert env.check(37.9, 2250).status is Status.OUTSIDE


def test_path_check():
    env = FlightEnvelope("sq", SQUARE)
    assert env.check_path((2, 2), (8, 8))
    assert not env.check_path((2, 2), (12, 8))


# ---------------- C172S / limitações ---------------- #
def test_default_loading_approved_normal():
    a = analyze(AC, default_loading(AC), "normal")
    assert a.approved, a.violations
    assert a.takeoff.result.total_weight == pytest.approx(a.ramp.result.total_weight - 6.6)


def test_default_loading_rejected_utility():
    a = analyze(AC, default_loading(AC), "utility")
    assert not a.approved
    assert any("deve estar vazia" in v for v in a.violations)


def test_baggage_limits():
    c = default_loading(AC)
    c.items = [i if i.key != "bag_b" else LoadItem(i.name, 90, i.arm, key="bag_b")
               for i in c.items]
    v = analyze(AC, c, "normal").violations
    assert any("Área B" in x for x in v) and any("combinada" in x for x in v)


# ---------------- Interface robusta ---------------- #
def _feeder(answers):
    it = iter(answers)
    return lambda _prompt: next(it)


@pytest.mark.parametrize("raw,val", [("37,5", 37.5), (" 170 ", 170.0), ("1.5", 1.5)])
def test_parse_number(raw, val):
    assert parse_number(raw) == val


@pytest.mark.parametrize("raw", ["abc", "nan", "inf", "1,2,3", ""])
def test_parse_number_rejects(raw):
    with pytest.raises(ValueError):
        parse_number(raw)


def test_ask_float_retries_until_valid():
    msgs = []
    v = ask_float("x", 10, 0, 100, _feeder(["abc", "nan", "-5", "500", "42"]),
                  lambda *a: msgs.append(a))
    assert v == 42 and len(msgs) == 4


def test_ask_float_falls_back_to_default():
    v = ask_float("x", 10, 0, 100, _feeder(["x"] * 10), lambda *a: None)
    assert v == 10


def test_eof_raises_user_abort():
    def boom(_):
        raise EOFError
    with pytest.raises(UserAbort):
        ask_float("x", 1, input_fn=boom)


def test_full_interactive_with_garbage():
    answers = ["zzz", "1",              # categoria: inválida, depois normal
               "", "",                  # BEW
               "abc", "350", "99",      # front peso (inválido, ok); braço fora do trilho
               "40",                    # braço válido
               "", "", "",              # rear, bag A, bag B
               "999", "30"]             # combustível acima da capacidade, depois 30 gal
    cond, cat = read_loading_interactive(AC, _feeder(answers), lambda *a: None)
    assert cat == "normal"
    front = next(i for i in cond.items if i.key == "front")
    assert (front.weight, front.arm) == (350, 40)
    assert cond.weight_of("fuel") == pytest.approx(180)


# ---------------- Relatório ---------------- #
def test_report_export(tmp_path):
    a = analyze(AC, default_loading(AC), "normal")
    p = export_report(a, tmp_path / "sub" / "r.txt")
    txt = p.read_text(encoding="utf-8")
    for key in ("TABELA DE MOMENTOS", "Decolagem", "Zero Combustível (ZFW)",
                "Shapely", "APROVADO PARA VOO"):
        assert key in txt
    assert "NÃO APROVADO" not in build_report(a)
