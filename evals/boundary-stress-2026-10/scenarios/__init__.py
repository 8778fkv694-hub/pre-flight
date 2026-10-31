"""Scenario registry for the boundary stress evaluation."""

from __future__ import annotations

from framework.model import Scenario

from .combined_c import SCENARIOS as _C
from .boundary_b import SCENARIOS as _B
from .repo_e import SCENARIOS as _E
from .variants import SCENARIOS as _V

ALL_SCENARIOS: list[Scenario] = _E + _B + _C + _V


def by_id(scenario_id: str) -> Scenario:
    for scenario in ALL_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    raise KeyError(f"unknown scenario {scenario_id!r}")


def require_unique() -> None:
    seen: set[str] = set()
    for scenario in ALL_SCENARIOS:
        if scenario.id in seen:
            raise ValueError(f"duplicate scenario id {scenario.id}")
        seen.add(scenario.id)
