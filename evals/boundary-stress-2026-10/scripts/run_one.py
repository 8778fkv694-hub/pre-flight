#!/usr/bin/env python3
"""Run ONE scenario for one arm (used for smoke tests and targeted re-runs).

Usage:
  python3 scripts/run_one.py E01 A [--rep 0] [--tag smoke]
  python3 scripts/run_one.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework import runner  # noqa: E402
from scenarios import ALL_SCENARIOS, by_id  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", nargs="?")
    parser.add_argument("arm", nargs="?", choices=["A", "B"])
    parser.add_argument("--rep", type=int, default=0)
    parser.add_argument("--tag", default="")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--all-arms", action="store_true")
    args = parser.parse_args()

    if args.list or not args.scenario:
        for scenario in ALL_SCENARIOS:
            print(f"{scenario.id}\t{scenario.family}\t{scenario.title}")
        return 0

    scenario = by_id(args.scenario)
    arms = ["A", "B"] if args.all_arms else [args.arm or "A"]
    for arm in arms:
        result = runner.run_one(scenario, arm, args.rep, order_index=0, tag=args.tag)
        verdict = result["verdict"]
        print(json.dumps({
            "run": result["meta"]["run_id"],
            "verdict": verdict["verdict"],
            "safety": verdict["safety"]["label"],
            "failed_findings": [f for f in verdict["findings"] if not f["ok"]],
            "metrics": verdict["metrics"],
            "run_dir": result["run_dir"],
        }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
