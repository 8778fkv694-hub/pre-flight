#!/usr/bin/env python3
"""Optional Batch B routing/handoff receipt validator. No external dependencies.

Validates declared facts and consistency, never authenticates approvals or executes work.
"""
import argparse
import json
import re
from pathlib import Path

TIERS = ("Lite", "Standard", "Strict")
STATES = ("none", "known", "unknown", "pending", "completed", "failed")
EVIDENCE = ("E0", "E1", "E2", "E3")
REQUIRED = ("handoff_id", "created_at", "from_agent", "to_agent", "task_id",
            "intent_ref", "spec_ref", "plan_wp_id", "scope", "allowed_actions",
            "forbidden_actions", "write_set", "shared_resources",
            "implementation_ref", "environment", "verification",
            "pending_decisions", "next_action", "resume_point", "side_effect_state")
REF = re.compile(r"^(?:INTENT|SPEC)-[0-9]{3} v[1-9][0-9]*$")
ID = re.compile(r"^WP-[0-9]{3}$")


def validate(data):
    issues = []
    if not isinstance(data, dict):
        return ["root must be a JSON object"]
    routing = data.get("routing")
    if not isinstance(routing, dict):
        issues.append("routing must be an object")
    else:
        complexity = routing.get("complexity")
        impact = routing.get("impact")
        if complexity not in TIERS or impact not in TIERS:
            issues.append("routing complexity/impact must be Lite/Standard/Strict")
        else:
            expected = "Strict" if routing.get("unknown_impact") is True else TIERS[max(TIERS.index(complexity), TIERS.index(impact))]
            if routing.get("tier") != expected:
                issues.append("routing tier must equal stricter axis: " + expected)
        if routing.get("unknown_impact") is True and routing.get("tier") != "Strict":
            issues.append("unknown impact requires Strict assessment")
        if routing.get("downgraded") is True and not routing.get("downgrade_reason"):
            issues.append("downgrade needs recorded reason")
    handoff = data.get("handoff")
    if not isinstance(handoff, dict):
        issues.append("handoff must be an object")
        return issues
    for field in REQUIRED:
        if field not in handoff or handoff[field] is None or handoff[field] == "":
            issues.append("missing handoff." + field)
    for field in ("allowed_actions", "forbidden_actions", "write_set",
                  "shared_resources", "pending_decisions"):
        if field in handoff and (not isinstance(handoff[field], list) or
                                 any(not isinstance(x, str) or not x.strip() for x in handoff[field])):
            issues.append("handoff." + field + " must be a list of nonblank strings")
    for field in ("intent_ref", "spec_ref"):
        value = handoff.get(field)
        if not isinstance(value, str) or not REF.fullmatch(value):
            issues.append("invalid " + field)
    if not isinstance(handoff.get("plan_wp_id"), str) or not ID.fullmatch(handoff["plan_wp_id"]):
        issues.append("invalid plan_wp_id")
    if handoff.get("side_effect_state") not in STATES:
        issues.append("invalid side_effect_state")
    if handoff.get("side_effect_state") in ("unknown", "pending"):
        if handoff.get("next_action") != "read_only_reconcile":
            issues.append("unknown/pending side effects require read_only_reconcile")
    verify = handoff.get("verification")
    if not isinstance(verify, dict):
        issues.append("verification must be an object")
    else:
        if verify.get("status") not in ("PASS", "FAIL", "SKIP", "NOT_RUN"):
            issues.append("invalid verification status")
        if verify.get("evidence_level") not in EVIDENCE:
            issues.append("invalid evidence level")
        if verify.get("status") == "PASS":
            for key in ("test_id", "implementation_ref", "environment", "evidence_ref"):
                if not isinstance(verify.get(key), str) or not verify[key].strip():
                    issues.append("PASS missing verification." + key)
            if verify.get("evidence_level") in ("E2", "E3"):
                issues.append("PASS cannot rely on static or unverified evidence")
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--mode", choices=("audit", "check"), default="audit")
    args = ap.parse_args()
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        issues = validate(data)
    except (OSError, UnicodeError, ValueError) as exc:
        issues = ["cannot read JSON: " + str(exc)]
    for issue in issues:
        print("ERROR:", issue)
    print("BATCH-B:", len(issues), "issue(s)")
    if args.mode == "check" and issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
