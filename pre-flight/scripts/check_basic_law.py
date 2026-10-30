#!/usr/bin/env python3
"""Check protected basic-law clauses. No external dependencies.

Schema 1 locks remain readable in legacy mode; schema 2 protects multiline
clauses. Migration is explicit and must not silently rewrite the old lock.
Records are consistency evidence, NOT proof of a human's identity or approval.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LOCK = Path("docs/sdlc/maintain/basic-law.lock.json")
AMENDMENTS = Path("docs/sdlc/maintain/basic-law-amendments.json")
CLAUSE = re.compile(r"^- \[(BL-\d{3})\] (\S.*)$")
TOP_LEVEL = re.compile(r"^(?:#{1,6} |[-*+] |\d+\. |\S)")
LEGACY_CLAUSE = re.compile(r"^-\s+\[(BL-\d{3})\]\s*(.+?)\s*$")
SHA = re.compile(r"^[0-9a-f]{64}$")


def fail(message, code=1):
    print("FAIL:", message)
    raise SystemExit(code)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        fail("cannot read JSON %s: %s" % (path, exc), 2)


def parse(text, schema):
    if "## 项目基本法" not in text or "受保护条款" not in text:
        fail("missing basic-law heading or protected-clause marker")
    if schema == 1:
        # Exact V1 extraction: strip the line, match flexible whitespace, hash only the first line.
        # V1 deliberately did not protect continuation lines; migrating closes that gap.
        clauses = {}
        for line in text.splitlines():
            match = LEGACY_CLAUSE.match(line.strip())
            if match:
                if match.group(1) in clauses:
                    fail("duplicate clause " + match.group(1))
                clauses[match.group(1)] = digest(match.group(2).strip())
        if not clauses:
            fail("no protected clauses")
        return clauses
    result = {}
    active = None
    for line in text.splitlines():
        match = CLAUSE.fullmatch(line)
        if match:
            key, value = match.groups()
            if key in result:
                fail("duplicate clause " + key)
            result[key] = [value]
            active = key
        elif active is not None:
            if line.startswith(("  ", "\t")) and line.strip():
                result[active].append(line.strip())
            elif not line.strip():
                # A blank line may separate paragraphs inside the same L1 clause.
                # Keep the clause active until a non-indented boundary follows.
                continue
            elif TOP_LEVEL.match(line):
                active = None
            else:
                fail("ambiguous continuation near " + active)
    if not result:
        fail("no protected clauses")
    return {key: digest("\n".join(parts)) for key, parts in result.items()}


def lock_read(path):
    data = read_json(path)
    if not isinstance(data, dict) or data.get("schema", 1) not in (1, 2):
        fail("unsupported lock schema", 2)
    if type(data.get("version")) is not int or data["version"] < 1:
        fail("invalid lock version", 2)
    clauses = data.get("clauses")
    if not isinstance(clauses, dict) or not clauses or any(
        not isinstance(k, str) or not re.fullmatch(r"BL-\d{3}", k)
        or not isinstance(v, str) or not SHA.fullmatch(v)
        for k, v in clauses.items()
    ):
        fail("invalid lock clauses", 2)
    return data


def amendment(project, amend_id, old, new, version):
    data = read_json(project / AMENDMENTS)
    if not isinstance(data, dict) or not isinstance(data.get("amendments"), list):
        fail("invalid amendment registry", 2)
    records = [r for r in data["amendments"] if isinstance(r, dict) and r.get("id") == amend_id]
    if len(records) != 1:
        fail("amendment ID must occur exactly once")
    record = records[0]
    if record.get("state") != "accepted" or record.get("base_version") != version:
        fail("amendment not accepted for current lock version")
    for field in ("confirmed_by", "confirmation_source", "confirmed_at", "scope"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            fail("amendment missing " + field)
    changes = record.get("changes")
    if not isinstance(changes, dict):
        fail("amendment changes missing")
    actual = {}
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            actual[key] = {"old": old.get(key), "new": new.get(key)}
    if changes != actual:
        fail("amendment approved change set differs from actual protected-clause diff")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--migrate", action="store_true")
    mode.add_argument("--check", action="store_true", help="explicit check alias (also the default)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--amend")
    ap.add_argument("--note")
    args = ap.parse_args()
    project = Path(args.project).resolve()
    try:
        text = (project / "AGENT.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail("cannot read AGENT.md: " + str(exc), 2)
    path = project / LOCK
    previous = lock_read(path) if path.exists() else None
    schema = previous.get("schema", 1) if previous else 2

    if args.migrate:
        if previous is None or schema != 1:
            fail("migration requires existing schema 1 lock", 2)
        if not args.force or not args.amend or not args.note:
            fail("migration requires --force --amend and --note", 2)
        # Check the old clauses before changing the hashing semantics.
        legacy = parse(text, 1)
        if legacy != previous["clauses"]:
            fail("legacy baseline mismatch; resolve before migration")
        updated = parse(text, 2)
        amendment(project, args.amend, previous["clauses"], updated, previous["version"])
    elif args.freeze:
        if not args.note:
            fail("--freeze requires --note", 2)
        if previous:
            if not args.force or not args.amend:
                fail("re-freeze requires --force --amend", 2)
            updated = parse(text, schema)
            amendment(project, args.amend, previous["clauses"], updated, previous["version"])
        else:
            if args.force or args.amend:
                fail("initial freeze cannot use --force/--amend", 2)
            updated = parse(text, 2)
    else:
        if args.force or args.amend or args.note:
            fail("check mode does not accept freeze options", 2)
        if previous is None:
            fail("no lock: human must confirm basic law before first freeze", 2)
        updated = parse(text, schema)
        if updated != previous["clauses"]:
            fail("protected clauses differ from frozen baseline")
        print("PASS: basic law schema %s version %s (%s clauses)" %
              (schema, previous["version"], len(updated)))
        return

    payload = {
        "schema": 2 if args.migrate else (schema if previous else 2),
        "version": previous["version"] + 1 if previous else 1,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "note": args.note,
        "amend": args.amend or "",
        "clauses": updated,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)
    print("FROZEN: basic law schema %s version %s" % (payload["schema"], payload["version"]))


if __name__ == "__main__":
    main()
