#!/usr/bin/env python3
"""Conservative structured Intent change triage; not semantic intent inference."""
import argparse
import json
from pathlib import Path

SIGNIFICANT = {"goal", "audience", "scope", "success_criteria", "constraints"}
ALLOWED = SIGNIFICANT | {"implementation", "bugfix", "tests", "documentation", "performance"}


def classify(record):
    if not isinstance(record, dict):
        return "needs-clarification", ["record must be object"]
    changed = record.get("changed_fields")
    if not isinstance(changed, list) or not changed or any(x not in ALLOWED for x in changed):
        return "needs-clarification", ["changed_fields must be nonempty known-field list"]
    if record.get("changes_authorization") is True:
        return "separate-authorization", ["authorization changes require explicit permission"]
    if record.get("changes_basic_law") is True:
        return "basic-law-amendment", ["protected clauses require amendment process"]
    if not record.get("intent_confirmed") or not record.get("confirmation_ref"):
        return "await-intent-confirmation", ["existing Intent confirmation not evidenced"]
    if any(x in SIGNIFICANT for x in changed):
        return "await-intent-confirmation", ["substantive Intent delta requires human confirmation"]
    if record.get("within_accepted_spec") is not True:
        return "needs-clarification", ["cannot prove work is inside accepted Spec"]
    return "reuse-confirmed-intent", ["implementation-level change; retain verification evidence"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--mode", choices=("audit", "check"), default="audit")
    args = ap.parse_args()
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        decision, reasons = classify(data)
    except (OSError, UnicodeError, ValueError) as exc:
        decision, reasons = "needs-clarification", [str(exc)]
    print(json.dumps({"decision": decision, "reasons": reasons}, ensure_ascii=False))
    if args.mode == "check" and decision != "reuse-confirmed-intent":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
