"""Monte Carlo uncertainty and one-at-a-time sensitivity (tornado) analysis."""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from .engine import Case, ItemAdjustment, Scenario, run_case


@dataclass
class Uncertainty:
    """Spreads used for sampling. Triangular(low, mode=1, high) multipliers."""
    wacc_range: tuple[float, float] = (0.05, 0.10)          # absolute WACC
    capex_mult: tuple[float, float] = (0.85, 1.30)          # cost overrun skew
    labor_mult: tuple[float, float] = (0.95, 1.15)
    maint_rate_range: tuple[float, float] = (0.02, 0.05)
    lifetime_shift: tuple[int, int] = (-2, 2)                # years


@dataclass
class MCResult:
    case: str
    years: np.ndarray
    cnpv_samples: np.ndarray          # [n, years]
    npv_samples: np.ndarray           # [n]

    def band(self, q: float) -> np.ndarray:
        return np.percentile(self.cnpv_samples, q, axis=0)


def _perturbed(scn: Scenario, case: Case, u: Uncertainty, rng: np.random.Generator) -> tuple[Scenario, Case]:
    s = copy.deepcopy(scn)
    c = copy.deepcopy(case)
    c.financial_overrides = dict(c.financial_overrides)
    c.financial_overrides["wacc"] = rng.uniform(*u.wacc_range)
    c.financial_overrides["maintenance_rate"] = rng.uniform(*u.maint_rate_range)
    for it in s.items:
        base = c.adj(it.id)
        lo, hi = u.labor_mult if it.kind == "labor" else u.capex_mult
        mult = rng.triangular(lo, 1.0, hi)
        shift = 0 if it.kind == "labor" else int(rng.integers(u.lifetime_shift[0], u.lifetime_shift[1] + 1))
        c.adjustments[it.id] = ItemAdjustment(
            units_add=base.units_add,
            cost_mult=base.cost_mult * mult,
            maint_add=base.maint_add,
            lifetime_add=base.lifetime_add + shift,
        )
    return s, c


def monte_carlo(scn: Scenario, case: Case, n: int = 500,
                u: Uncertainty | None = None, seed: int = 0) -> MCResult:
    u = u or Uncertainty()
    rng = np.random.default_rng(seed)
    runs = [run_case(*_perturbed(scn, case, u, rng)) for _ in range(n)]
    return MCResult(case.name, runs[0].years,
                    np.array([r.cnpv for r in runs]),
                    np.array([r.npv for r in runs]))


def tornado(scn: Scenario, case: Case, swing: float = 0.2, top: int = 8) -> list[tuple[str, float, float]]:
    """Change each line item's cost by ±swing; return (label, low_npv_delta, high_npv_delta),
    sorted by impact. Also includes WACC ±swing."""
    base = run_case(scn, case).npv
    out = []
    for it in scn.items:
        deltas = []
        for f in (1 - swing, 1 + swing):
            c = copy.deepcopy(case)
            a = c.adj(it.id)
            c.adjustments[it.id] = ItemAdjustment(a.units_add, a.cost_mult * f, a.maint_add, a.lifetime_add)
            deltas.append(run_case(scn, c).npv - base)
        out.append((f"{it.id} {it.name}", *deltas))
    w = scn.case_financials(case).wacc
    deltas = []
    for f in (1 - swing, 1 + swing):
        c = copy.deepcopy(case)
        c.financial_overrides = {**c.financial_overrides, "wacc": w * f}
        deltas.append(run_case(scn, c).npv - base)
    out.append(("WACC", *deltas))
    out.sort(key=lambda t: abs(t[2] - t[1]), reverse=True)
    return out[:top]
