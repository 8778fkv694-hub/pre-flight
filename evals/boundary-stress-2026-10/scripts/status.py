#!/usr/bin/env python3
"""Summarize current baseline status from recorded verdicts.

Usage:
  python3 scripts/status.py --tags baseline-e,baseline-bc
  python3 scripts/status.py --tags baseline-e,baseline-bc --failures
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework import config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", default="baseline-e,baseline-bc")
    parser.add_argument("--failures", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    tags = {t.strip() for t in args.tags.split(",") if t.strip()}
    runs = []
    for meta_path in config.RUNS_DIR.glob("*/meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            verdict = json.loads((meta_path.parent / "verdict.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if tags and meta.get("tag") not in tags:
            continue
        runs.append((meta, verdict))
    runs.sort(key=lambda item: (item[0]["scenario"], item[0]["arm"], item[0]["rep"]))
    by_arm = defaultdict(Counter)
    by_scenario = defaultdict(lambda: defaultdict(Counter))
    for meta, verdict in runs:
        by_arm[meta["arm"]][verdict["verdict"]] += 1
        by_scenario[meta["scenario"]][meta["arm"]][verdict["verdict"]] += 1
    print(f"runs={len(runs)} tags={sorted(tags)}")
    for arm in sorted(by_arm):
        print(f"  arm {arm}: {dict(by_arm[arm])}")
    safety = [(m, v) for m, v in runs if v["safety"]["label"] == "SAFETY_HARD_FAIL"]
    print(f"  safety hard failures: {len(safety)}")
    if args.failures:
        print("\nnon-pass runs:")
        for meta, verdict in runs:
            if verdict["verdict"] == "PASS":
                continue
            bad = [f for f in verdict.get("findings", []) if not f["ok"]]
            print(f"  {meta['run_id']}: {verdict['verdict']} safety={verdict['safety']['label']} "
                  f"({verdict.get('status_reason') or ''})")
            for finding in bad[:5]:
                print(f"      [{finding['severity']}] {finding['dimension']}: "
                      f"{finding['detail'][:160]}")
        print("\nscenario totals (A/B):")
        for sid in sorted(by_scenario):
            print(f"  {sid:8} " + "  ".join(
                f"{arm}={dict(by_scenario[sid][arm])}" for arm in sorted(by_scenario[sid])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
