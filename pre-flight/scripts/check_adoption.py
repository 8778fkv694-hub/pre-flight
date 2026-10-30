#!/usr/bin/env python3
"""Read-only incremental adoption inspector. Never initializes or rewrites a project."""
import argparse
import json
from pathlib import Path

from check_project_contract import inspect as inspect_contract

ARTIFACTS = ("AGENT.md", "STATUS.md", "docs/sdlc/plan/intent.md",
             "docs/sdlc/design/spec.md", "docs/sdlc/build/plan.md")
MODES = ("observe", "warn", "enforce")


def inspect(root):
    if not root.is_dir():
        return [{"severity": "ERROR", "code": "PROJECT_NOT_FOUND", "path": str(root)}]
    findings = []
    for rel in ARTIFACTS:
        if not (root / rel).is_file():
            findings.append({"severity": "INFO", "code": "OPTIONAL_ARTIFACT_ABSENT", "path": rel})
    return findings


def evaluate(root, mode, approved=False, contract=False):
    findings = inspect(root)
    if mode == "enforce" and not approved:
        findings.append({"severity": "ERROR", "code": "ENFORCE_NOT_APPROVED",
                         "path": "explicit --approved-enforce required"})
    if contract and root.is_dir():
        required = ("docs/sdlc/plan/intent.md", "docs/sdlc/design/spec.md",
                    "docs/sdlc/build/plan.md", "docs/sdlc/test/verification.md")
        missing = [rel for rel in required if not (root / rel).is_file()]
        if missing:
            findings.append({"severity": "INFO", "code": "CONTRACT_NOT_APPLICABLE",
                             "path": ", ".join(missing)})
        else:
            for severity, where, message in inspect_contract(root):
                findings.append({"severity": severity, "code": "CONTRACT_" + where.upper(),
                                 "path": message})
    # Absent artifacts never fail adoption; existing projects may have equivalent structures.
    failed = any(x["severity"] == "ERROR" for x in findings)
    return findings, (1 if failed and (mode == "enforce" or
                                       any(x["code"] == "PROJECT_NOT_FOUND" for x in findings)) else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--mode", choices=MODES, default="observe")
    ap.add_argument("--approved-enforce", action="store_true")
    ap.add_argument("--contract-check", action="store_true")
    args = ap.parse_args()
    findings, code = evaluate(Path(args.project), args.mode, args.approved_enforce, args.contract_check)
    print(json.dumps({"mode": args.mode, "findings": findings, "exit_code": code},
                     ensure_ascii=False, indent=2))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
