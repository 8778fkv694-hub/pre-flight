#!/usr/bin/env python3
"""Re-verify already-recorded runs against the CURRENT frozen scenario definitions.

The raw artifacts collected during a run (server-side audit ledger, post-run
world snapshot, file diff, NDJSON tool trace, final answer) do not depend on
acceptance rules.  If a scenario's hidden acceptance was corrected while the
baseline was running (e.g. a regex that false-positived on a negation), the
original Agent behavior can be re-judged from the same raw evidence without
re-running the Agent.

This script writes ``verdict.reverified.json`` (keeping the original as
``verdict.original.json`` on first verification) and never touches raw
evidence or the Agent's files.  Reports should use the re-verified verdicts.

Usage:
  python3 scripts/reverify.py --tag baseline-e,baseline-bc
  python3 scripts/reverify.py --all --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework import config, verify  # noqa: E402
from framework.model import World  # noqa: E402
from scenarios import by_id  # noqa: E402
from framework.runner import contamination_scan, parse_events  # noqa: E402


def reverify_one(run_dir: Path, dry_run: bool = False) -> dict | None:
    meta_path = run_dir / "meta.json"
    verdict_path = run_dir / "verdict.json"
    if not (meta_path.exists() and verdict_path.exists()):
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    original = json.loads(verdict_path.read_text(encoding="utf-8"))
    scenario = by_id(meta["scenario"])
    artifacts = run_dir / "artifacts"

    audit = []
    if (artifacts / "audit.json").exists():
        audit = json.loads((artifacts / "audit.json").read_text(encoding="utf-8"))
    world_after = None
    if (artifacts / "world_after.json").exists():
        world_after = json.loads((artifacts / "world_after.json").read_text(encoding="utf-8"))
    parsed = parse_events(run_dir / "events.jsonl")
    if not parsed.get("final_text") and (run_dir / "final.txt").exists():
        parsed["final_text"] = (run_dir / "final.txt").read_text(encoding="utf-8")
    sandbox = run_dir / "sandbox"
    meta["contamination"] = contamination_scan(parsed.get("tool_calls") or [], sandbox)
    complete = bool(parsed.get("final_text")) and not (meta.get("agent") or {}).get(
        "timed_out")

    import dataclasses
    world_before = dataclasses.asdict(scenario.world) if isinstance(scenario.world, World) else {}
    new_verdict = verify.verify_run(
        scenario, meta.get("arm", "?"), meta.get("order_index") or 0, meta, audit,
        world_before, world_after, parsed, sandbox, {}, {}, complete=complete)

    changed = (new_verdict["verdict"] != original["verdict"]
               or [f for f in new_verdict.get("findings", []) if not f["ok"]]
               != [f for f in original.get("findings", []) if not f["ok"]])
    new_verdict["reverified"] = {
        "at": config_git_time(),
        "acceptance_source": "current scenario definitions in this commit",
        "original_verdict": original["verdict"],
        "changed": changed,
    }
    if not dry_run:
        original_path = run_dir / "verdict.original.json"
        if not original_path.exists():
            original_path.write_text(
                json.dumps(original, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        verdict_path.write_text(
            json.dumps(new_verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"run_id": meta["run_id"], "scenario": meta["scenario"],
            "arm": meta["arm"], "rep": meta.get("rep"),
            "original": original["verdict"], "reverified": new_verdict["verdict"],
            "changed": changed,
            "failed": [f["detail"] for f in new_verdict.get("findings", []) if not f["ok"]][:5]}


def config_git_time() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--ids", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    tags = {t.strip() for t in args.tag.split(",") if t.strip()}
    ids = {t.strip() for t in args.ids.split(",") if t.strip()}
    results = []
    for run_dir in sorted(config.RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        try:
            meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if tags and meta.get("tag") not in tags:
            continue
        if ids and meta.get("scenario") not in ids:
            continue
        result = reverify_one(run_dir, dry_run=args.dry_run)
        if result:
            results.append(result)
    changed = [r for r in results if r["changed"]]
    out = config.STATE_DIR / "reverify-latest.json"
    config.write_json(out, {"total": len(results), "changed": len(changed),
                            "dry_run": args.dry_run, "results": results})
    print(f"re-verified {len(results)} runs; {len(changed)} changed")
    for item in changed:
        print(f"  {item['run_id']}: {item['original']} -> {item['reverified']}"
              f" failed={item['failed'][:2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
