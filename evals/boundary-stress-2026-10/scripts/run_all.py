#!/usr/bin/env python3
"""Run the randomized A/B matrix (real independent Agent sessions).

Order is shuffled with a recorded seed so the two arms and the repetitions do
not run in a fixed sequence.  Every run is isolated:
  * its own sandbox and mock-production world,
  * its own fresh headless Agent session (no shared memory),
  * the other arm's artifacts are never mounted or referenced.

Usage examples:
  python3 scripts/run_all.py --tag baseline --reps 3 --workers 6
  python3 scripts/run_all.py --tag extra_b05 --ids B05-1d,B05-30d --reps 3
  python3 scripts/run_all.py --tag baseline --resume
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import sys
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework import config, runner  # noqa: E402
from scenarios import ALL_SCENARIOS, require_unique  # noqa: E402

PRINT_LOCK = threading.Lock()


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def select_scenarios(args) -> list:
    scenarios = list(ALL_SCENARIOS)
    if args.ids:
        wanted = {item.strip() for item in args.ids.split(",") if item.strip()}
        scenarios = [s for s in scenarios if s.id in wanted]
        missing = wanted - {s.id for s in scenarios}
        if missing:
            raise SystemExit(f"unknown scenario ids: {sorted(missing)}")
    if args.families:
        families = {item.strip() for item in args.families.split(",") if item.strip()}
        scenarios = [s for s in scenarios if s.family in families]
    if args.exclude:
        excluded = {item.strip() for item in args.exclude.split(",") if item.strip()}
        scenarios = [s for s in scenarios if s.id not in excluded]
    if not scenarios:
        raise SystemExit("no scenarios selected")
    return scenarios


def existing_runs(tag: str) -> dict[tuple[str, str, int, str], dict]:
    found: dict[tuple[str, str, int, str], dict] = {}
    for meta_path in config.RUNS_DIR.glob("*/meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if meta.get("tag") != tag:
            continue
        key = (meta["scenario"], meta["arm"], int(meta["rep"]), tag)
        if (meta_path.parent / "verdict.json").exists():
            found.setdefault(key, meta)
    return found


def run_task(task: dict) -> dict:
    scenario = task["scenario_obj"]
    started = time.time()
    try:
        result = runner.run_one(scenario, task["arm"], task["rep"],
                                order_index=task["order_index"], tag=task["tag"])
        verdict = result["verdict"]
        log(f"[{task['order_index']:03d}/{task['total']:03d}] {scenario.id} "
            f"{task['arm']} r{task['rep']} -> {verdict['verdict']} "
            f"({time.time() - started:.0f}s)")
        return {"task": {k: v for k, v in task.items() if k != "scenario_obj"},
                "ok": True, "run_dir": result["run_dir"],
                "verdict": verdict["verdict"]}
    except Exception as exc:  # noqa: BLE001
        log(f"[{task['order_index']:03d}] {scenario.id} {task['arm']} r{task['rep']} "
            f"-> INFRA_ERROR {exc}")
        return {"task": {k: v for k, v in task.items() if k != "scenario_obj"},
                "ok": False, "error": type(exc).__name__ + ": " + str(exc),
                "traceback": traceback.format_exc()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="baseline")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--rep-start", type=int, default=0)
    parser.add_argument("--arms", default="A,B")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20261031)
    parser.add_argument("--ids", default="")
    parser.add_argument("--families", default="")
    parser.add_argument("--exclude", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config.ensure_dirs()
    require_unique()
    scenarios = select_scenarios(args)
    arms = [arm.strip() for arm in args.arms.split(",") if arm.strip()]
    for arm in arms:
        if arm not in config.ARM_SKILLS:
            raise SystemExit(f"unknown arm {arm!r}")

    tasks = []
    for scenario in scenarios:
        for arm in arms:
            for rep in range(args.rep_start, args.rep_start + args.reps):
                tasks.append({"scenario": scenario.id, "scenario_obj": scenario,
                              "arm": arm, "rep": rep, "tag": args.tag,
                              "family": scenario.family, "tier": scenario.tier})
    rng = random.Random(args.seed)
    rng.shuffle(tasks)
    for index, task in enumerate(tasks):
        task["order_index"] = index
        task["total"] = len(tasks)

    done = existing_runs(args.tag) if args.resume else {}
    if done:
        tasks = [t for t in tasks
                 if (t["scenario"], t["arm"], t["rep"], t["tag"]) not in done]
        log(f"resume: {len(done)} runs already complete, {len(tasks)} remaining")

    config.write_json(config.STATE_DIR / f"order-{args.tag}.json", {
        "tag": args.tag, "seed": args.seed, "reps": args.reps, "arms": arms,
        "workers": args.workers, "total": len(tasks),
        "order": [{k: v for k, v in task.items() if k != "scenario_obj"}
                  for task in tasks],
    })
    log(f"tag={args.tag} scenarios={len(scenarios)} arms={arms} "
        f"reps={args.reps} tasks={len(tasks)} workers={args.workers} seed={args.seed}")
    if args.dry_run:
        for task in tasks[:10]:
            log(json.dumps({k: v for k, v in task.items() if k != "scenario_obj"}))
        return 0

    runner.ensure_service()
    started = time.time()
    results = []
    progress_path = config.STATE_DIR / f"progress-{args.tag}.jsonl"
    with open(progress_path, "w", encoding="utf-8") as progress:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_task, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                progress.write(json.dumps({
                    "run_id": result.get("task", {}).get("scenario"),
                    "arm": result.get("task", {}).get("arm"),
                    "rep": result.get("task", {}).get("rep"),
                    "verdict": result.get("verdict"),
                    "ok": result.get("ok"),
                    "error": result.get("error"),
                    "run_dir": result.get("run_dir"),
                }, ensure_ascii=False) + "\n")
                progress.flush()

    runner.finalize_index()
    counts: dict[str, int] = {}
    for result in results:
        key = result.get("verdict") or "INFRA_ERROR"
        counts[key] = counts.get(key, 0) + 1
    log(f"finished {len(results)} runs in {(time.time() - started) / 60:.1f} min: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
