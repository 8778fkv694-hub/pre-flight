#!/usr/bin/env python3
"""Export de-identified raw Agent execution records for the committed report.

The full run directories under state/ are gitignored because they contain
absolute machine paths and ephemeral session fragments.  This script writes a
compact, sanitized bundle per run that still contains the raw evidence needed
to audit a verdict:

  * prompt (skill entry hashes only, not the whole skill text),
  * every tool call and its result (truncated only where huge),
  * the server-side audit ledger (authorization verdicts + effects),
  * final answer, file diff, post-run verification results, verdict, metrics.

Usage:
  python3 scripts/export_evidence.py --tag baseline
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework import config  # noqa: E402

PATH_REPLACERS = [
    (str(config.EVAL_ROOT / "state" / "runs"), "<RUNS_DIR>"),
    (str(config.EVAL_ROOT), "<EVAL_ROOT>"),
    (str(config.REPO_ROOT), "<REPO_ROOT>"),
    ("/private/tmp/dsh-probe", "<PROBE>"),
]
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|oc_sk_[A-Za-z0-9_\-]+|ark-[A-Za-z0-9\-]{8,})")


def sanitize(obj):
    text = json.dumps(obj, ensure_ascii=False)
    for source, replacement in PATH_REPLACERS:
        text = text.replace(source, replacement)
    text = SECRET_RE.sub("<REDACTED_SECRET>", text)
    return json.loads(text)


def clip(value, limit: int = 20000):
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"\n...<truncated {len(value) - limit} chars>"
    return value


def load_run(run_dir: Path) -> dict | None:
    meta_path = run_dir / "meta.json"
    verdict_path = run_dir / "verdict.json"
    if not (meta_path.exists() and verdict_path.exists()):
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    artifacts = run_dir / "artifacts"

    def maybe(name):
        path = artifacts / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    final_text = ""
    final_path = artifacts / "final.txt"
    if final_path.exists():
        final_text = final_path.read_text(encoding="utf-8", errors="replace")

    tool_calls = maybe("tool_calls.json") or []
    audit = maybe("audit.json") or []
    world = maybe("world_after.json")
    diff = maybe("files_diff.json")

    prompt = ""
    prompt_path = run_dir / "prompt.txt"
    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding="utf-8", errors="replace")
        # only keep the task part; the full skill text is public and hash-recorded
        marker = "# 用户请求"
        if marker in prompt:
            prompt = marker + prompt.split(marker, 1)[1]

    # tool call outline plus raw results from events.jsonl
    results = {}
    events_path = run_dir / "events.jsonl"
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if event.get("type") == "tool_result":
                results[event.get("callId", "")] = {
                    "status": event.get("status"),
                    "result": clip(event.get("result")),
                }
            elif event.get("type") == "thinking":
                results.setdefault("_thinking", []).append(clip(event.get("text") or "", 4000))
    trace = []
    for call in tool_calls:
        trace.append({
            "callId": call.get("callId"),
            "tool": call.get("tool"),
            "input": clip(call.get("input")),
            "result": results.get(call.get("callId")),
        })

    bundle = {
        "run_id": meta.get("run_id"),
        "scenario": meta.get("scenario"),
        "scenario_title": meta.get("scenario_title"),
        "family": meta.get("family"),
        "tier": meta.get("tier"),
        "arm": meta.get("arm"),
        "rep": meta.get("rep"),
        "tag": meta.get("tag"),
        "order_index": meta.get("order_index"),
        "started_at": meta.get("started_at"),
        "duration_s": (meta.get("agent") or {}).get("duration_s"),
        "frozen": {
            "git_sha": meta.get("git_sha"),
            "model_config": meta.get("model_config"),
            "skill": meta.get("skill"),
            "permission_mode": meta.get("permission_mode"),
        },
        "prompt_task": clip(prompt),
        "prompt_sha256": meta.get("prompt_sha256"),
        "tool_trace": trace,
        "analysis_trace": (results.get("_thinking") or [])[:12],
        "audit_ledger": audit,
        "world_after": world,
        "files_diff": diff,
        "final_answer": clip(final_text),
        "usage": meta.get("usage"),
        "verdict": verdict,
    }
    return sanitize(bundle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="baseline")
    args = parser.parse_args()
    out_dir = config.EVAL_ROOT / "reports" / "evidence" / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    index = []
    for run_dir in sorted(config.RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        try:
            meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if meta.get("tag") != args.tag:
            continue
        bundle = load_run(run_dir)
        if bundle is None:
            continue
        out = out_dir / f"{run_dir.name}.json.gz"
        with gzip.open(out, "wt", encoding="utf-8") as fh:
            json.dump(bundle, fh, ensure_ascii=False, separators=(",", ":"))
        index.append({"run_id": run_dir.name, "scenario": bundle["scenario"],
                      "arm": bundle["arm"], "rep": bundle["rep"],
                      "verdict": bundle["verdict"]["verdict"],
                      "safety": bundle["verdict"]["safety"]["label"],
                      "bundle": f"evidence/{args.tag}/{out.name}"})
        count += 1
    (out_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"exported {count} sanitized evidence bundles to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
