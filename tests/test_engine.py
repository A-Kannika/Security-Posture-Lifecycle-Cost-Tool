import numpy as np
import pytest

from secposture.engine import (Case, Financials, ItemAdjustment, LineItem, Scenario,
                               is_replacement_year, run_case)
from secposture.scenarios import example_scenario, load_json, save_json
from secposture.uncertainty import monte_carlo, tornado


# --- Replacement-buffer rule: reproduces the documented "cooling fan" examples ---

def replacement_years(lifetime, timeline, buffer, inclusive=True):
    return [y for y in range(1, timeline + 1)
            if is_replacement_year(y, lifetime, timeline, buffer, inclusive)]


def test_fan_18pct_buffer_replaced_at_9_and_18():
    # threshold = 9 * 0.18 = 1.62; year 18 has 2 years left -> replace
    assert replacement_years(9, 20, 0.18) == [9, 18]


def test_fan_25pct_buffer_replaced_only_at_9():
    # threshold = 9 * 0.25 = 2.25; year 18 has 2 years left -> inside buffer
    assert replacement_years(9, 20, 0.25) == [9]


def test_buffer_equality_edge_case():
    # 10-yr asset, 20-yr project, buffer 0.2 -> threshold 2.0.
    # Year 10 is replaced either way; year 20 has 0 years left -> never.
    # Construct a true tie: lifetime 6, timeline 20, buffer 1/3 -> threshold 2, year 18 leaves 2.
    assert 18 in replacement_years(6, 20, 1 / 3, inclusive=True)
    assert 18 not in replacement_years(6, 20, 1 / 3, inclusive=False)


def test_final_year_replacement_depends_on_buffer():
    # Any positive buffer blocks a purchase in the very last year...
    assert 20 not in replacement_years(10, 20, 0.01)
    # ...but a zero buffer with the inclusive (>=) rule buys an asset that is
    # never used. This edge case is why a small positive buffer is recommended.
    assert 20 in replacement_years(10, 20, 0.0, inclusive=True)
    assert 20 not in replacement_years(10, 20, 0.0, inclusive=False)


# --- Cost and NPV mechanics ---

def one_item(kind="capex", **fin):
    it = LineItem("C.1.1", "Fan", kind, 1000, 2, 9 if kind == "capex" else 0)
    return Scenario(Financials(**{"wacc": 0.0, **fin}), [it], [Case("base")])


def test_capex_timeline_with_zero_wacc():
    scn = one_item(replacement_buffer=0.18, maintenance_rate=0.05)
    r = run_case(scn, scn.cases[0])
    c = r.costs[0]
    assert c[0] == 2000 and c[9] == 2000 and c[18] == 2000
    assert c[1] == pytest.approx(100)                # 5% maintenance
    # 3 purchases + 18 maintenance years
    assert -r.npv == pytest.approx(3 * 2000 + 18 * 100)


def test_labor_uses_wrap_rate_every_year_including_year0():
    scn = one_item("labor", wrap_rate=2.0, timeline=5)
    r = run_case(scn, scn.cases[0])
    assert np.allclose(r.costs[0], 4000)
    assert -r.npv == pytest.approx(6 * 4000)


def test_discounting():
    scn = one_item("labor", wrap_rate=1.0, timeline=1, wacc=0.10)
    r = run_case(scn, scn.cases[0])
    assert -r.npv == pytest.approx(2000 + 2000 / 1.1)


def test_case_adjustments_apply_correctly():
    scn = one_item(replacement_buffer=0.18, maintenance_rate=0.05)
    case = Case("adj", adjustments={"C.1.1": ItemAdjustment(units_add=1, cost_mult=2.0,
                                                           maint_add=-0.05, lifetime_add=1)})
    r = run_case(scn, case)
    c = r.costs[0]
    assert c[0] == 6000                       # 3 units x $2000
    assert c[10] == 6000 and c[9] == 0         # lifetime 10, zero maintenance
    assert c[20] == 0                          # no buy in last year


def test_attribution_sums_to_npv():
    scn = example_scenario()
    for case in scn.cases:
        r = run_case(scn, case)
        assert sum(r.attribution.values()) == pytest.approx(r.npv)
        assert r.capex_npv + r.labor_npv == pytest.approx(r.npv)
        assert r.cnpv[-1] == pytest.approx(r.npv)


def test_attributability_validation():
    with pytest.raises(ValueError):
        LineItem("C.9.9", "Bad", "capex", 1, 1, 5, 0.5, 0.5, 0.5)


def test_maintenance_profiles_change_cost():
    scn = example_scenario()
    flat = run_case(scn, scn.cases[0]).npv
    scn.financials.maint_profile = "escalating"
    assert run_case(scn, scn.cases[0]).npv < flat      # more negative = costlier


def test_json_roundtrip(tmp_path):
    scn = example_scenario()
    p = tmp_path / "s.json"
    save_json(scn, p)
    again = load_json(p)
    assert run_case(again, again.cases[1]).npv == pytest.approx(run_case(scn, scn.cases[1]).npv)


def test_monte_carlo_bands_are_ordered_and_reproducible():
    scn = example_scenario()
    m1 = monte_carlo(scn, scn.cases[0], n=60, seed=1)
    m2 = monte_carlo(scn, scn.cases[0], n=60, seed=1)
    assert np.allclose(m1.npv_samples, m2.npv_samples)
    assert np.all(m1.band(10) <= m1.band(90))


def test_tornado_sorted_by_swing():
    scn = example_scenario()
    rows = tornado(scn, scn.cases[0])
    swings = [abs(h - l) for _, l, h in rows]
    assert swings == sorted(swings, reverse=True)
