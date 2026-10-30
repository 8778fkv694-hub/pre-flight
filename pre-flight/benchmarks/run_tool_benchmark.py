#!/usr/bin/env python3
"""Reproducible *tool-level* benchmark. Does not claim an Agent/LLM run."""
import importlib.util
import json
import platform
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


intent = load("check_intent_delta")
handoff = load("check_handoff")


def run_case(item, template):
    cid = item["id"]
    if cid in ("C-001", "C-002", "C-003"):
        decision, reasons = intent.classify(item["structured_input"])
        passed = decision == item["expected_decision"]
        observed = {"decision": decision, "reasons": reasons}
    elif cid in ("C-004", "C-005"):
        payload = deepcopy(template)
        for key, value in item["mutation"].items():
            if key == "verification":
                payload["handoff"]["verification"].update(value)
            else:
                payload["handoff"][key] = value
        issues = handoff.validate(payload)
        passed = item["expected_issue"] in issues
        observed = {"issues": issues}
    elif cid == "C-006":
        payload = deepcopy(template)
        payload["routing"] = item["routing"]
        issues = handoff.validate(payload)
        passed = (not issues) == item["expected_valid"]
        observed = {"issues": issues}
    else:
        raise ValueError("unsupported case " + cid)
    return {"id": cid, "status": "PASS" if passed else "FAIL",
            "observed": observed, "expected": item.get("expected_decision",
            item.get("expected_issue", item.get("expected_valid")))}


def run():
    manifest_path = ROOT / "benchmarks/v2-executable-cases.json"
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))["scenarios"]
    fixture = json.loads((ROOT / "assets/examples/batch-b-handoff.example.json").read_text(encoding="utf-8"))
    results = [run_case(item, fixture) for item in cases]
    return {"schema": 1, "benchmark": "tool-level", "agent_behavior_validated": False,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "cases": len(results), "passed": sum(x["status"] == "PASS" for x in results),
            "failed": sum(x["status"] == "FAIL" for x in results), "results": results,
            "limitations": ["Structured inputs supplied directly: no autonomous Agent decisions",
                            "No LLM/host runtime, tool selection, context retrieval, or permissions actually exercised",
                            "Do not interpret 6/6 tool-case pass as Agent adherence or cross-model benchmark"]}


def main():
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
