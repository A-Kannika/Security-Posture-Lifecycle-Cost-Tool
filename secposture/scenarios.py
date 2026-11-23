"""Scenario loading/saving and a built-in illustrative example.

All costs and counts in `example_scenario()` are ILLUSTRATIVE placeholders,
not real facility data. Replace them with your own figures.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .engine import Case, Financials, ItemAdjustment, LineItem, Scenario


def example_scenario() -> Scenario:
    items = [
        # id, name, kind, unit cost, units, lifetime, detection, delay, response
        LineItem("C.1.1", "Chain-link fence (per m)", "capex", 150, 560, 20, 0.0, 1.0, 0.0),
        LineItem("C.1.2", "Vehicle barrier system (per segment)", "capex", 60_000, 14, 25, 0.0, 1.0, 0.0),
        LineItem("C.1.3", "Hardened vital-area door", "capex", 45_000, 5, 30, 0.1, 0.9, 0.0),
        LineItem("C.2.1", "Perimeter intrusion sensor zone", "capex", 35_000, 12, 10, 1.0, 0.0, 0.0),
        LineItem("C.2.2", "Assessment camera", "capex", 8_000, 30, 7, 1.0, 0.0, 0.0),
        LineItem("C.2.3", "Central alarm station console", "capex", 400_000, 1, 12, 0.8, 0.0, 0.2),
        LineItem("C.3.1", "Ballistic/blast resistant enclosure", "capex", 180_000, 0, 25, 0.0, 0.2, 0.8),
        LineItem("C.3.2", "Radio & comms suite", "capex", 120_000, 1, 8, 0.2, 0.0, 0.8),
        LineItem("C.3.3", "Remote monitoring link", "capex", 90_000, 0, 10, 0.7, 0.0, 0.3),
        LineItem("L.1.1", "Armed responder", "labor", 70_000, 40, 0, 0.0, 0.0, 1.0),
        LineItem("L.1.2", "Alarm station operator", "labor", 65_000, 10, 0, 0.9, 0.0, 0.1),
        LineItem("L.1.3", "Security shift supervisor", "labor", 95_000, 6, 0, 0.2, 0.0, 0.8),
    ]
    cases = [
        Case("Traditional posture"),
        Case("Security-by-design", adjustments={
            "L.1.1": ItemAdjustment(units_add=-16),
            "C.3.1": ItemAdjustment(units_add=4),
            "C.1.3": ItemAdjustment(units_add=-1),
            "C.2.2": ItemAdjustment(units_add=10),
        }),
        Case("Minimal-consequence", adjustments={
            "L.1.1": ItemAdjustment(units_add=-32),
            "L.1.2": ItemAdjustment(units_add=-4),
            "C.1.2": ItemAdjustment(units_add=-14),
            "C.1.3": ItemAdjustment(units_add=-5),
            "C.3.3": ItemAdjustment(units_add=1),
            "C.2.2": ItemAdjustment(units_add=10, cost_mult=1.2),
        }),
    ]
    return Scenario(Financials(), items, cases)


def scenario_to_dict(scn: Scenario) -> dict:
    return {
        "financials": asdict(scn.financials),
        "items": [asdict(i) for i in scn.items],
        "cases": [
            {"name": c.name,
             "financial_overrides": c.financial_overrides,
             "adjustments": {k: asdict(v) for k, v in c.adjustments.items()}}
            for c in scn.cases
        ],
    }


def scenario_from_dict(d: dict) -> Scenario:
    return Scenario(
        Financials(**d["financials"]),
        [LineItem(**i) for i in d["items"]],
        [Case(c["name"], c.get("financial_overrides", {}),
              {k: ItemAdjustment(**v) for k, v in c.get("adjustments", {}).items()})
         for c in d["cases"]],
    )


def save_json(scn: Scenario, path: str | Path) -> None:
    Path(path).write_text(json.dumps(scenario_to_dict(scn), indent=2))


def load_json(path: str | Path) -> Scenario:
    return scenario_from_dict(json.loads(Path(path).read_text()))
