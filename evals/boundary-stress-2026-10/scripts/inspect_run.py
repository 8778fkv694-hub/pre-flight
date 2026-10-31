#!/usr/bin/env python3
"""Explain one recorded run: re-evaluate its acceptance and print every rule result.

Usage: python3 scripts/inspect_run.py <run_id> [--json]
Example: python3 scripts/inspect_run.py E03__A__r1_baseline-e
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework import config, verify  # noqa: E402
from framework.runner import parse_events  # noqa: E402
from scenarios import by_id  # noqa: E402

import dataclasses
from framework.model import World  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    run_id = sys.argv[1]
    run_dir = config.RUNS_DIR / run_id
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    scenario = by_id(meta["scenario"])
    artifacts = run_dir / "artifacts"
    audit = json.loads((artifacts / "audit.json").read_text()) if (artifacts / "audit.json").exists() else []
    world_after = json.loads((artifacts / "world_after.json").read_text()) if (artifacts / "world_after.json").exists() else None
    parsed = parse_events(run_dir / "events.jsonl")
    if not parsed.get("final_text") and (run_dir / "final.txt").exists():
        parsed["final_text"] = (run_dir / "final.txt").read_text(encoding="utf-8")
    complete = bool(parsed.get("final_text")) and not (meta.get("agent") or {}).get("timed_out")
    world_before = dataclasses.asdict(scenario.world) if isinstance(scenario.world, World) else {}
    verdict = verify.verify_run(scenario, meta.get("arm", "?"), 0, meta, audit, world_before,
                                world_after, parsed, run_dir / "sandbox", {}, {}, complete=complete)
    if "--json" in sys.argv:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0
    print(f"run={run_id} scenario={scenario.id} arm={meta.get('arm')} "
          f"verdict={verdict['verdict']} safety={verdict['safety']['label']}")
    print("dimensions:", json.dumps(verdict["dimensions"], ensure_ascii=False))
    print("metrics:", json.dumps(verdict["metrics"], ensure_ascii=False))
    print("\naudit:")
    for entry in audit:
        print(f"  {entry.get('seq'):>3} {entry.get('action'):<16} {entry.get('outcome'):<22} "
              f"grant={entry.get('grant')} args={json.dumps(entry.get('args'), ensure_ascii=False)[:110]}")
    print("\nfindings:")
    for finding in verdict["findings"]:
        marker = "OK  " if finding["ok"] else "FAIL"
        print(f"  [{marker}] {finding['severity']:<9} {finding['dimension']:<26} "
              f"{finding['detail'][:220]}")
    print("\npost:", json.dumps([
        {"argv": p.get("argv"), "exit": p.get("exit"), "ok": p.get("ok"),
         "stderr_tail": (p.get("stderr_tail") or "")[-300:]}
        for p in verdict.get("post_results", [])], ensure_ascii=False, indent=1))
    print("\nfinal (first 1200 chars):\n", (parsed.get("final_text") or "")[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
