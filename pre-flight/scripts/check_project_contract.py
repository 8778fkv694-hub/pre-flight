#!/usr/bin/env python3
"""Read-only, deterministic cross-artifact contract audit.

audit (default) reports findings without failing; check exits nonzero on errors.
No semantic understanding, no automatic migration, no external dependencies.
"""
import argparse
import json
import re
from pathlib import Path

PATHS = {
    "intent": "docs/sdlc/plan/intent.md",
    "spec": "docs/sdlc/design/spec.md",
    "plan": "docs/sdlc/build/plan.md",
    "verification": "docs/sdlc/test/verification.md",
}
REF = re.compile(r"\b(INTENT|SPEC|PLAN)-\d{3}\s+v(\d+)\b", re.I)
STATE = re.compile(r"状态[：:]\s*([a-z][a-z-]*)", re.I)
VERSION = re.compile(r"版本[：:]\s*(\d+)")
HEADING = re.compile(r"^#\s+(?:(?:候选)\s*)?((?:INTENT|SPEC|PLAN)-\d{3})\b", re.I)
STATES = {
    "intent": {"draft", "awaiting-confirmation", "accepted", "in-progress", "closed", "cancelled"},
    "spec": {"draft", "frozen", "superseded"},
    "plan": {"draft", "ready", "in-progress", "completed", "cancelled"},
}


def inspect(root):
    issues = []
    docs = {}
    for kind, relative in PATHS.items():
        path = root / relative
        if not path.is_file():
            issues.append(("ERROR", kind, "missing file: " + relative))
            continue
        text = path.read_text(encoding="utf-8")
        heading = HEADING.search(text)
        version = VERSION.search(text[:1200])
        state = STATE.search(text[:1200])
        docs[kind] = {
            "text": text, "id": heading.group(1).upper() if heading else None,
            "version": int(version.group(1)) if version else None,
            "state": state.group(1).lower() if state else None,
        }
        if kind != "verification":
            if not heading or not version or not state:
                issues.append(("ERROR", kind, "missing ID/version/state metadata"))
            elif state.group(1).lower() not in STATES[kind]:
                issues.append(("ERROR", kind, "unknown state: " + state.group(1)))
    for kind, dependency in (("spec", "intent"), ("plan", "spec")):
        if kind not in docs or dependency not in docs:
            continue
        body = docs[kind]["text"][:1600]
        refs = [(m.group(0).split()[0].upper(), int(m.group(2))) for m in REF.finditer(body)]
        expected = (docs[dependency]["id"], docs[dependency]["version"])
        pinned = [r for r in refs if r[0].startswith(dependency.upper() + "-")]
        active = docs[kind]["state"] in {"frozen", "ready", "in-progress", "completed"}
        if not pinned:
            issues.append(("ERROR" if active else "WARN", kind,
                           "no explicit %s version reference" % dependency))
        elif expected[0] and expected[1]:
            for ref_id, ref_version in pinned:
                if ref_id == expected[0] and ref_version > expected[1]:
                    issues.append(("ERROR", kind, "references future %s v%s" %
                                   (ref_id, ref_version)))
                elif (ref_id, ref_version) != expected:
                    # Historical accepted versions may be valid. Inspect immutable history.
                    issues.append(("WARN", kind,
                                   "pinned %s v%s differs from current %s v%s; verify history" %
                                   (ref_id, ref_version, expected[0], expected[1])))
        if active and expected in pinned:
            permitted = ({"accepted", "in-progress", "closed"} if dependency == "intent"
                         else {"frozen"})
            if docs[dependency]["state"] not in permitted:
                issues.append(("ERROR", kind,
                               "active artifact depends on non-accepted current " + dependency))
    # Structured receipts are optional; validation checks the claim's shape, not its truth.
    receipt = root / "docs/sdlc/test/receipts.json"
    if receipt.exists():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("receipts"), list):
                raise ValueError("expected receipts array")
            for idx, item in enumerate(data["receipts"]):
                if not isinstance(item, dict):
                    raise ValueError("receipt %d not an object" % idx)
                for key in ("wp_id", "spec_id", "spec_version", "test_id", "implementation_ref", "environment", "status", "evidence"):
                    if key not in item or item[key] in ("", None):
                        issues.append(("ERROR", "receipt", "receipt %d missing %s" % (idx, key)))
                if item.get("status") not in ("PASS", "FAIL", "SKIP", "NOT_RUN"):
                    issues.append(("ERROR", "receipt", "receipt %d invalid status" % idx))
                spec = docs.get("spec")
                if spec and item.get("spec_id") == spec["id"] and item.get("spec_version") != spec["version"]:
                    issues.append(("WARN", "receipt", "receipt %d is for another Spec version; do not use as current proof" % idx))
        except (ValueError, UnicodeError) as exc:
            issues.append(("ERROR", "receipt", "invalid receipts.json: " + str(exc)))
    status = root / "STATUS.md"
    if status.exists() and "spec" in docs:
        # Optional strict machine-readable single-line marker; old STATUS is not broken by its absence.
        marker = re.search(r"^Current-Spec:\s*(SPEC-\d{3})\s+v(\d+)\s*$", status.read_text(encoding="utf-8"), re.M | re.I)
        if marker and (marker.group(1).upper(), int(marker.group(2))) != (docs["spec"]["id"], docs["spec"]["version"]):
            level = "WARN" if docs["spec"]["state"] == "draft" else "ERROR"
            issues.append((level, "status", "Current-Spec differs from Spec document; inspect active baseline"))
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--mode", choices=["audit", "check"], default="audit")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    try:
        issues = inspect(root)
    except (OSError, UnicodeError) as exc:
        print("ERROR: unable to read project:", exc)
        raise SystemExit(2)
    for severity, where, message in issues:
        print("%s [%s]: %s" % (severity, where, message))
    errors = sum(1 for severity, _, _ in issues if severity == "ERROR")
    print("CONTRACT: %d error(s), %d warning(s) [%s]" %
          (errors, len(issues) - errors, args.mode))
    if args.mode == "check" and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
