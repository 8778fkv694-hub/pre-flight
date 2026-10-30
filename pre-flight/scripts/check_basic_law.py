#!/usr/bin/env python3
"""Freeze and verify the protected clauses of a project's basic law.

The basic law lives in AGENT.md. Protected clauses are single-line list items
such as ``- [BL-001] intent: ...``. Freezing records a SHA-256 baseline; later
checks detect silent deletion, addition, or rewriting of clauses.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

AGENT_REL = Path("AGENT.md")
BASELINE_REL = Path("docs/sdlc/maintain/basic-law.lock.json")
LOG_REL = Path("docs/sdlc/maintain/basic-law-log.md")

HEADING = "## 项目基本法"
MARKER = "受保护条款"
CLAUSE_RE = re.compile(r"^-\s+\[(BL-\d{3})\]\s*(.+?)\s*$")


def die(msg, code=2):
    """Print a concise English failure line and exit."""
    print("FAIL: " + msg)
    sys.exit(code)


class Parser(argparse.ArgumentParser):
    """Argument parser that routes usage errors through die()."""

    def error(self, message):
        die(message, 2)


def read_text(path, what):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        die("cannot decode %s as UTF-8 (%s): %s" % (what, path, exc), 2)
    except OSError as exc:
        die("cannot read %s (%s): %s" % (what, path, exc), 2)


def extract_clauses(text):
    """Return (clauses, duplicate_ids) from AGENT.md text."""
    clauses = {}
    seen = []
    for line in text.splitlines():
        match = CLAUSE_RE.match(line.strip())
        if not match:
            continue
        clause_id = match.group(1)
        clauses[clause_id] = match.group(2).strip()
        seen.append(clause_id)
    duplicates = sorted({cid for cid in seen if seen.count(cid) > 1})
    return clauses, duplicates


def clause_hash(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def content_problems(text, clauses, duplicates):
    problems = []
    if HEADING not in text:
        problems.append("AGENT.md is missing required heading '%s'" % HEADING)
    if MARKER not in text:
        problems.append("AGENT.md is missing required marker '%s'" % MARKER)
    if not clauses:
        problems.append("no protected clauses (BL-xxx) found in AGENT.md")
    if duplicates:
        problems.append("duplicate clause ID(s): %s" % ", ".join(duplicates))
    return problems


def load_baseline(path):
    """Read and validate the baseline JSON, or exit 2."""
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        die("cannot decode baseline as UTF-8 (%s): %s" % (path, exc), 2)
    except OSError as exc:
        die("cannot read baseline (%s): %s" % (path, exc), 2)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        die("cannot parse baseline JSON (%s): %s" % (path, exc), 2)
    if not isinstance(data, dict):
        die("baseline structure invalid: top level must be an object (%s)" % path, 2)
    clauses = data.get("clauses")
    if not isinstance(clauses, dict) or not clauses:
        die("baseline structure invalid: missing or empty 'clauses' (%s)" % path, 2)
    for clause_id, digest in clauses.items():
        if not isinstance(clause_id, str) or not isinstance(digest, str):
            die("baseline structure invalid: clause entries must be strings (%s)" % path, 2)
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        die("baseline structure invalid: missing or non-integer 'version' (%s)" % path, 2)
    if data.get("schema") is not None and data.get("schema") != 1:
        die("unsupported baseline schema in %s" % path, 2)
    return data


def write_baseline(path, payload):
    """Atomically write the baseline JSON through <baseline>.tmp."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        die("cannot write baseline (%s): %s" % (path, exc), 2)


def check(project):
    agent_path = project / AGENT_REL
    if not agent_path.is_file():
        die("AGENT.md not found: %s" % agent_path, 2)
    text = read_text(agent_path, "AGENT.md")

    baseline_path = project / BASELINE_REL
    if not baseline_path.is_file():
        die("baseline not found (%s); run with --freeze first" % baseline_path, 2)
    data = load_baseline(baseline_path)

    clauses, duplicates = extract_clauses(text)
    problems = content_problems(text, clauses, duplicates)
    if problems:
        for problem in problems:
            print("VIOLATION: " + problem)
        print("CHECK FAILED: %d protected-clause violation(s)" % len(problems))
        sys.exit(1)

    baseline_clauses = data["clauses"]
    baseline_ids = set(baseline_clauses)
    current_ids = set(clauses)
    violations = []

    for clause_id in sorted(baseline_ids - current_ids):
        violations.append(
            "clause %s is in the baseline but missing from AGENT.md" % clause_id
        )
    for clause_id in sorted(current_ids - baseline_ids):
        violations.append(
            "new clause %s is not in the baseline; confirm it and re-freeze"
            % clause_id
        )
    for clause_id in sorted(baseline_ids & current_ids):
        if clause_hash(clauses[clause_id]) != baseline_clauses[clause_id]:
            violations.append(
                "clause %s changed since baseline; use the amendment "
                "procedure and re-freeze with --force --amend" % clause_id
            )

    if violations:
        for violation in violations:
            print("VIOLATION: " + violation)
        print("CHECK FAILED: %d protected-clause violation(s)" % len(violations))
        sys.exit(1)

    print(
        "PASS: %d protected clauses match baseline version %s (frozen %s)"
        % (len(clauses), data["version"], data.get("frozen_at", "unknown"))
    )


def freeze(project, note, force, amend):
    agent_path = project / AGENT_REL
    if not agent_path.is_file():
        die("AGENT.md not found: %s" % agent_path, 2)
    text = read_text(agent_path, "AGENT.md")
    clauses, duplicates = extract_clauses(text)
    problems = content_problems(text, clauses, duplicates)
    if problems:
        for problem in problems:
            print("VIOLATION: " + problem)
        print("FREEZE FAILED: %d protected-clause violation(s)" % len(problems))
        sys.exit(1)

    baseline_path = project / BASELINE_REL
    re_freeze = baseline_path.is_file()

    if re_freeze:
        amend = (amend or "").strip()
        if not force or not amend:
            die(
                "re-freezing requires both --force and --amend <amendment-id>",
                2,
            )
        log_path = project / LOG_REL
        if not log_path.is_file():
            die("amendment log not found: %s" % log_path, 2)
        log_text = read_text(log_path, "amendment log")
        if amend not in log_text:
            die(
                "amendment ID %r is not recorded in %s" % (amend, log_path),
                2,
            )
        data = load_baseline(baseline_path)
        version = data["version"] + 1
    else:
        if amend is not None:
            die("the first freeze must not use --amend (amend is recorded as '')", 2)
        version = 1
        amend = ""

    payload = {
        "schema": 1,
        "version": version,
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": note,
        "amend": amend,
        "clauses": {cid: clause_hash(body) for cid, body in clauses.items()},
    }
    write_baseline(baseline_path, payload)
    print(
        "FROZEN: %d protected clauses, baseline version %d written to %s"
        % (len(clauses), version, baseline_path)
    )


def main(argv=None):
    parser = Parser(
        description="Freeze or check the protected clauses in AGENT.md."
    )
    parser.add_argument(
        "--project",
        default=".",
        help="project root directory (default: .)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check clauses against the baseline (default action)",
    )
    parser.add_argument(
        "--freeze",
        action="store_true",
        help="write a new baseline for the current clauses",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow re-freezing an existing baseline (requires --amend)",
    )
    parser.add_argument(
        "--amend",
        metavar="ID",
        help="amendment ID recorded in docs/sdlc/maintain/basic-law-log.md",
    )
    parser.add_argument(
        "--note",
        metavar="TEXT",
        help="reason for freezing (required with --freeze)",
    )
    args = parser.parse_args(argv)

    if args.freeze and args.check:
        die("--freeze and --check are mutually exclusive", 2)

    project = Path(args.project).expanduser().absolute()
    if not project.is_dir():
        die("project directory not found: %s" % project, 2)

    if args.freeze:
        note = (args.note or "").strip()
        if not note:
            die("--freeze requires a non-empty --note", 2)
        freeze(project, note, args.force, args.amend)
    else:
        check(project)


if __name__ == "__main__":
    main()
