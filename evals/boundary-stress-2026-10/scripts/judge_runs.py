#!/usr/bin/env python3
"""Batch-run the arm-blind LLM judge over completed runs and aggregate agreement.

The deterministic verifier (``framework/verify.py``) is the primary acceptance
gate.  This script runs the second-layer semantic judge
(``framework/judge.py``) over runs that already have a verdict, then compares
the judge's ``PASS/PARTIAL/FAIL`` with the deterministic verdict and lists the
differences.

Usage (from ``evals/boundary-stress-2026-10``)::

  source ../../../.env.sh
  python3 scripts/judge_runs.py --tag baseline --workers 4
  python3 scripts/judge_runs.py --tag baseline --workers 4 --resume
  python3 scripts/judge_runs.py --tag baseline --ids E01 --limit 1
  python3 scripts/judge_runs.py --tag baseline --dry-run

Behaviour:
  * scans ``state/runs/*/meta.json`` for runs whose ``tag`` matches and that
    already have a ``verdict.json``;
  * skips ``NOT_RUN`` / ``BLOCKED`` verdicts by default (there is no Agent
    behaviour to review; pass ``--include-incomplete`` to override);
  * ``--resume`` skips runs that already have a usable ``state/judge/*.json``
    (parse failures are retried); resumed results are still included in the
    agreement summary;
  * ``--limit N`` caps how many *new* judge sessions this invocation starts;
  * runs ``--workers`` judge sessions concurrently; each judge is its own
    headless process with its own prompt/work directory (arm-blind);
  * writes ``state/judge-summary-<tag>.json`` with the confusion matrix,
    agreement rates and a findings/dimension difference list.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework import config, judge  # noqa: E402
from scenarios import by_id  # noqa: E402

PRINT_LOCK = threading.Lock()


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def _load_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def collect_tasks(args) -> tuple[list[dict], list[dict], list[dict], int]:
    """Return (tasks to judge, resumed tasks, skipped-without-verdict, matched)."""
    ids = {item.strip() for item in (args.ids or "").split(",") if item.strip()}
    tasks: list[dict] = []
    resumed: list[dict] = []
    skipped_verdict: list[dict] = []
    for meta_path in sorted(config.RUNS_DIR.glob("*/meta.json")):
        meta = _load_json(meta_path)
        if not isinstance(meta, dict):
            continue
        if meta.get("tag") != args.tag:
            continue
        run_id = str(meta.get("run_id") or meta_path.parent.name)
        scenario_id = str(meta.get("scenario") or "")
        if ids and scenario_id not in ids and run_id not in ids:
            continue
        verdict_path = meta_path.parent / "verdict.json"
        if not verdict_path.exists():
            skipped_verdict.append({"run_id": run_id, "scenario": scenario_id,
                                    "reason": "no verdict.json"})
            continue
        verdict = _load_json(verdict_path)
        if not isinstance(verdict, dict):
            skipped_verdict.append({"run_id": run_id, "scenario": scenario_id,
                                    "reason": "unreadable verdict.json"})
            continue
        verdict_label = str(verdict.get("verdict") or "")
        if verdict_label not in judge.VERDICTS and not args.include_incomplete:
            skipped_verdict.append({
                "run_id": run_id,
                "scenario": scenario_id,
                "reason": f"verdict={verdict_label or 'UNKNOWN'} "
                          "(no Agent behaviour to review; --include-incomplete "
                          "to judge anyway)",
                "verdict": verdict_label,
            })
            continue
        try:
            scenario = by_id(scenario_id)
        except KeyError:
            skipped_verdict.append({"run_id": run_id, "scenario": scenario_id,
                                    "reason": "scenario not in registry",
                                    "verdict": verdict_label})
            continue
        task = {"meta": meta, "verdict": verdict, "scenario": scenario,
                "run_dir": meta_path.parent}
        if args.resume and judge.result_is_usable(judge.result_path(run_id)):
            existing = judge.load_result(judge.result_path(run_id))
            task["resumed_result"] = existing
            resumed.append(task)
        else:
            tasks.append(task)

    tasks.sort(key=lambda item: (str(item["meta"].get("scenario") or ""),
                                 str(item["meta"].get("arm") or ""),
                                 int(item["meta"].get("rep") or 0),
                                 str(item["meta"].get("run_id") or "")))
    resumed.sort(key=lambda item: (str(item["meta"].get("scenario") or ""),
                                   str(item["meta"].get("arm") or ""),
                                   int(item["meta"].get("rep") or 0),
                                   str(item["meta"].get("run_id") or "")))
    matched = len(tasks) + len(resumed)
    if args.limit and args.limit > 0:
        tasks = tasks[:args.limit]
    return tasks, resumed, skipped_verdict, matched


def preflight() -> None:
    errors: list[str] = []
    if not config.MODEL_PATCH.exists():
        errors.append(f"missing model patch: {config.MODEL_PATCH}")
    if not config.APP_BINARY.exists():
        errors.append(f"missing app binary: {config.APP_BINARY}")
    # The headless CLI lives inside app.asar; Electron resolves that virtual
    # path, a normal Python stat() cannot.  Only check the archive itself.
    asar_path = Path("/Applications/DeepSeek Harness.app/Contents/Resources/app.asar")
    if not asar_path.exists() and not config.CLI_JS.exists():
        errors.append(f"missing app.asar and headless cli: {asar_path}")
    if not (os.environ.get("OPENCODE_GO_API_KEY")
            or os.environ.get("DEEPSEEK_API_KEY")):
        errors.append(
            "OPENCODE_GO_API_KEY / DEEPSEEK_API_KEY not set in this process; "
            "run `source /Users/yiliwen/开发/pre-flight-eval/.env.sh` "
            "(从 evals/boundary-stress-2026-10 目录是 `source ../../../.env.sh`) "
            "before this script")
    if errors:
        for message in errors:
            log(f"[preflight] {message}")
        raise SystemExit(2)


def run_judge_task(task: dict, args) -> dict:
    meta = task["meta"]
    run_id = str(meta.get("run_id") or task["run_dir"].name)
    started = time.time()
    try:
        result = judge.judge_run(task["run_dir"], task["scenario"],
                                 include_findings=args.include_findings,
                                 timeout_s=args.timeout)
        parsed = result.get("parsed") or {}
        log(f"  judged {run_id}: primary={task['verdict'].get('verdict')} "
            f"judge={parsed.get('overall') or result.get('status')} "
            f"conf={parsed.get('confidence')} "
            f"({time.time() - started:.0f}s)")
        return {"task": task, "result": result, "error": None}
    except Exception as exc:  # noqa: BLE001 - one run must not abort the batch
        message = f"{type(exc).__name__}: {exc}"
        log(f"  ERROR {run_id}: {message}")
        return {"task": task, "result": None, "error": message,
                "traceback": traceback.format_exc(limit=8)}


def _failure_item(task: dict, result: dict | None, error: str | None) -> dict:
    meta = task["meta"]
    return {
        "run_id": str(meta.get("run_id") or task["run_dir"].name),
        "scenario": meta.get("scenario"),
        "arm": meta.get("arm"),
        "status": (result or {}).get("status") or "error",
        "error": (result or {}).get("parse_error") or (result or {}).get("error") or error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Arm-blind LLM judge over completed runs (second-layer verify)")
    parser.add_argument("--tag", default="baseline",
                        help="run tag to select (meta.json tag), default baseline")
    parser.add_argument("--workers", type=int, default=4,
                        help="concurrent judge sessions (default 4)")
    parser.add_argument("--limit", type=int, default=0,
                        help="max number of NEW judge sessions this invocation (0 = all)")
    parser.add_argument("--ids", default="",
                        help="comma separated scenario ids (or exact run ids) to filter")
    parser.add_argument("--resume", action="store_true",
                        help="skip runs that already have a usable judge result")
    parser.add_argument("--include-incomplete", action="store_true",
                        help="also judge NOT_RUN / BLOCKED verdicts")
    parser.add_argument("--include-findings", action="store_true",
                        help="(experimental) show primary verifier findings to the judge")
    parser.add_argument("--timeout", type=int, default=judge.DEFAULT_TIMEOUT_S,
                        help=f"per judge session timeout seconds "
                             f"(default {judge.DEFAULT_TIMEOUT_S})")
    parser.add_argument("--dry-run", action="store_true",
                        help="list the runs that would be judged, then exit")
    args = parser.parse_args()

    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")
    preflight()
    config.ensure_dirs()
    judge.ensure_judge_dirs()

    tasks, resumed, skipped_verdict, matched = collect_tasks(args)
    if not tasks and not resumed:
        log(f"no completed runs found for tag={args.tag!r}"
            + (f" ids={args.ids!r}" if args.ids else ""))
        summary = judge.build_agreement_summary(
            tag=args.tag, records=[], matched=0, skipped_resume=[],
            skipped_verdict=skipped_verdict, failures=[],
            judge_meta=judge.judge_meta(args.timeout), elapsed_s=0.0)
        config.write_json(config.STATE_DIR / f"judge-summary-{args.tag}.json",
                          summary)
        return 1 if skipped_verdict else 0

    log(f"tag={args.tag} matched_completed={matched} "
        f"resume_skipped={len(resumed)} to_judge={len(tasks)} "
        f"workers={args.workers} timeout={args.timeout}s")
    if args.dry_run:
        for task in tasks:
            meta = task["meta"]
            log(f"  would judge {meta.get('run_id')} "
                f"primary={task['verdict'].get('verdict')}")
        for task in resumed:
            log(f"  would skip (resume) {task['meta'].get('run_id')}")
        return 0

    started = time.time()
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_judge_task, task, args) for task in tasks]
        for index, future in enumerate(concurrent.futures.as_completed(futures),
                                       start=1):
            outcome = future.result()
            results.append(outcome)
            log(f"[{index}/{len(tasks)}] done "
                f"{outcome['task']['meta'].get('run_id')}")

    records: list[dict] = []
    failures: list[dict] = []
    for outcome in results:
        task = outcome["task"]
        result = outcome["result"]
        if result is None:
            result = {"status": "error", "parsed": None, "error": outcome["error"]}
        records.append({"meta": task["meta"], "verdict": task["verdict"],
                        "result": result})
        if result.get("status") != "ok":
            failures.append(_failure_item(task, result, outcome.get("error")))
    for task in resumed:
        resumed_result = dict(task.get("resumed_result") or {})
        if "scenario_consistency" not in resumed_result:
            # Older judge results may predate the staleness check; derive it now.
            resumed_result["scenario_consistency"] = judge.scenario_consistency(
                task["meta"], task["verdict"], task["scenario"])
        records.append({"meta": task["meta"], "verdict": task["verdict"],
                        "result": resumed_result})

    summary = judge.build_agreement_summary(
        tag=args.tag,
        records=records,
        matched=matched,
        skipped_resume=[str(task["meta"].get("run_id")) for task in resumed],
        skipped_verdict=skipped_verdict,
        failures=failures,
        judge_meta=judge.judge_meta(args.timeout),
        elapsed_s=time.time() - started,
    )
    summary_path = config.STATE_DIR / f"judge-summary-{args.tag}.json"
    config.write_json(summary_path, summary)

    agreement = summary["agreement"]
    counts = summary["counts"]
    log(f"judged={counts['judged_ok']} failed={counts['judge_failed']} "
        f"exact_agree={agreement['exact_agree']}/{counts['judged_ok']} "
        f"({agreement['exact_rate']}) "
        f"fail_binary={agreement['fail_binary_agree']}/{counts['judged_ok']} "
        f"({agreement['fail_binary_rate']})")
    log(f"confusion matrix (rows=primary PASS/PARTIAL/FAIL, "
        f"cols=judge PASS/PARTIAL/FAIL): "
        f"{json.dumps(agreement['confusion_primary_rows_judge_cols'], ensure_ascii=False)}")
    if summary["findings_diff"]:
        log(f"differences to review: {len(summary['findings_diff'])} "
            f"{json.dumps(summary['findings_diff_priority_counts'], ensure_ascii=False)} "
            f"(see findings_diff in {summary_path})")
    stale = summary.get("scenario_consistency", {}).get("stale_runs") or []
    if stale:
        log(f"WARNING: {len(stale)} run(s) finished before the current scenario "
            f"definition (verdict/judge not directly comparable); re-run needed: "
            f"{[item['run_id'] for item in stale][:6]}")
    if failures:
        log(f"judge failures: {len(failures)} (see failures in summary)")
    elif skipped_verdict:
        log(f"skipped runs without a usable verdict: {len(skipped_verdict)}")
    log(f"summary written: {summary_path}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
