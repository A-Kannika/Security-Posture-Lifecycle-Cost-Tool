"""Lifecycle cost engine for physical-protection-system (PPS) security postures.

Computes year-by-year expenditures, net present value (NPV) and cumulative NPV
(CNPV) for up to N security-posture cases, and attributes cost to the three
security functions: detection, delay and response.

Cost rules (one line item, one case, year y in 0..T):
  * Year 0 (construction): capital items are purchased; labor is paid.
  * Years 1..T, capital items:
      - if y is a multiple of the asset lifetime AND the asset is outside the
        end-of-project replacement buffer -> full replacement CAPEX;
      - otherwise -> maintenance (a % of the item's CAPEX, shaped by a profile).
  * Years 1..T, labor items: paid every year, multiplied by the wrap rate,
    never incur maintenance.
  * Replacement buffer: replace in year y only if
        (T - y) >= lifetime * buffer      (inclusive, the default)
    or  (T - y) >  lifetime * buffer      (strict, `buffer_inclusive=False`).
  * All values are expenditures, so NPV and CNPV are reported as negatives.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

import numpy as np

Kind = Literal["capex", "labor"]
MaintProfile = Literal["flat", "escalating", "bathtub"]


@dataclass
class Financials:
    wacc: float = 0.07                 # weighted average cost of capital
    wrap_rate: float = 1.8             # labor burden multiplier
    maintenance_rate: float = 0.03     # annual maintenance as fraction of CAPEX
    replacement_buffer: float = 0.18   # fraction of lifetime (see module doc)
    timeline: int = 20                 # operating years (year 0 is construction)
    buffer_inclusive: bool = True      # ">=" (True) or ">" (False)
    maint_profile: MaintProfile = "flat"
    maint_escalation: float = 0.04     # per year of asset age, for "escalating"


@dataclass
class LineItem:
    id: str
    name: str
    kind: Kind
    unit_cost: float                   # per-unit CAPEX or annual salary
    units: float
    lifetime: int = 0                  # years; ignored for labor
    detection: float = 1 / 3
    delay: float = 1 / 3
    response: float = 1 / 3

    def __post_init__(self) -> None:
        s = self.detection + self.delay + self.response
        if not np.isclose(s, 1.0, atol=1e-3):
            raise ValueError(f"{self.id}: attributability must sum to 1 (got {s:.3f})")
        if self.kind == "capex" and self.lifetime <= 0:
            raise ValueError(f"{self.id}: capital items need a positive lifetime")


@dataclass
class ItemAdjustment:
    units_add: float = 0.0       # U.x  (added to units)
    cost_mult: float = 1.0       # E.x  (multiplies cost)
    maint_add: float = 0.0       # M.x  (added to maintenance rate)
    lifetime_add: int = 0        # LT.x (added to lifetime)


@dataclass
class Case:
    name: str
    financial_overrides: dict[str, float] = field(default_factory=dict)
    adjustments: dict[str, ItemAdjustment] = field(default_factory=dict)

    def adj(self, item_id: str) -> ItemAdjustment:
        return self.adjustments.get(item_id, ItemAdjustment())


@dataclass
class Scenario:
    financials: Financials
    items: list[LineItem]
    cases: list[Case]

    def case_financials(self, case: Case) -> Financials:
        return replace(self.financials, **case.financial_overrides)


@dataclass
class CaseResult:
    case: str
    years: np.ndarray                 # 0..T
    item_ids: list[str]
    costs: np.ndarray                 # [items, years] nominal cost
    discounted: np.ndarray            # [items, years] present value
    npv: float                        # negative
    cnpv: np.ndarray                  # [years], negative, cumulative
    capex_npv: float
    labor_npv: float
    attribution: dict[str, float]     # detection/delay/response NPV (negative)


# ---------------------------------------------------------------------------

def is_replacement_year(year: int, lifetime: int, timeline: int,
                        buffer: float, inclusive: bool = True) -> bool:
    """True if a capital asset is repurchased in `year`."""
    if year <= 0 or lifetime <= 0 or year > timeline or year % lifetime:
        return False
    remaining = timeline - year
    threshold = lifetime * buffer
    return remaining >= threshold if inclusive else remaining > threshold


def maintenance_factor(age: int, lifetime: int, fin: Financials) -> float:
    """Multiplier on the base maintenance rate for an asset of a given age.

    flat       -> 1
    escalating -> (1 + g)^(age-1)
    bathtub    -> higher in early life (infant mortality) and late life (wear-out)
    """
    if fin.maint_profile == "flat":
        return 1.0
    if fin.maint_profile == "escalating":
        return (1 + fin.maint_escalation) ** max(age - 1, 0)
    if fin.maint_profile == "bathtub":
        x = min(age / max(lifetime, 1), 1.0)    # 0..1 through the asset's life
        return 0.6 + 1.6 * (2 * x - 1) ** 2     # 2.2 at both ends, 0.6 mid-life
    raise ValueError(f"unknown maintenance profile {fin.maint_profile}")


def run_case(scn: Scenario, case: Case) -> CaseResult:
    fin = scn.case_financials(case)
    T = int(fin.timeline)
    years = np.arange(T + 1)
    disc = (1 + fin.wacc) ** -years.astype(float)

    costs = np.zeros((len(scn.items), T + 1))
    for i, it in enumerate(scn.items):
        a = case.adj(it.id)
        units = max(it.units + a.units_add, 0)
        unit_cost = it.unit_cost * a.cost_mult
        if it.kind == "labor":
            costs[i, :] = unit_cost * units * fin.wrap_rate
            continue
        life = max(it.lifetime + a.lifetime_add, 1)
        capex = unit_cost * units
        maint_rate = max(fin.maintenance_rate + a.maint_add, 0.0)
        costs[i, 0] = capex
        last_purchase = 0
        for y in range(1, T + 1):
            if is_replacement_year(y, life, T, fin.replacement_buffer, fin.buffer_inclusive):
                costs[i, y] = capex
                last_purchase = y
            else:
                age = y - last_purchase
                costs[i, y] = capex * maint_rate * maintenance_factor(age, life, fin)

    discounted = costs * disc
    per_year = discounted.sum(axis=0)
    kinds = np.array([it.kind for it in scn.items])
    attr = {
        k: -float(sum(discounted[i].sum() * getattr(it, k) for i, it in enumerate(scn.items)))
        for k in ("detection", "delay", "response")
    }
    return CaseResult(
        case=case.name,
        years=years,
        item_ids=[it.id for it in scn.items],
        costs=costs,
        discounted=discounted,
        npv=-float(per_year.sum()),
        cnpv=-np.cumsum(per_year),
        capex_npv=-float(discounted[kinds == "capex"].sum()),
        labor_npv=-float(discounted[kinds == "labor"].sum()),
        attribution=attr,
    )


def run_all(scn: Scenario) -> list[CaseResult]:
    return [run_case(scn, c) for c in scn.cases]
