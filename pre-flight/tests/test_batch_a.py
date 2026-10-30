#!/usr/bin/env python3
"""Batch A deterministic smoke tests. Run: python3 -m unittest discover -s pre-flight/tests -v"""
import importlib.util
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


law = load("check_basic_law")
contract = load("check_project_contract")


class BatchATests(unittest.TestCase):
    def test_multiline_protected_clause_hash(self):
        a = "## 项目基本法\n受保护条款\n- [BL-001] 第一行\n  第二行\n"
        b = a.replace("第二行", "另一行")
        self.assertNotEqual(law.parse(a, 2), law.parse(b, 2))
        # Legacy format only hashes the first line: explicit migration closes that gap.
        self.assertEqual(law.parse(a, 1), law.parse(b, 1))

    def test_duplicate_clause_rejected(self):
        with self.assertRaises(SystemExit):
            law.parse("## 项目基本法\n受保护条款\n- [BL-001] one\n- [BL-001] two\n", 2)

    def test_legacy_hash_compatible(self):
        sample = "## 项目基本法\n受保护条款\n- [BL-001] one\n"
        self.assertEqual(law.parse(sample, 1), law.parse(sample, 2))

    def test_amendment_rejects_unapproved_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / law.AMENDMENTS
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"amendments": [{
                "id": "BA-01", "state": "accepted", "base_version": 1,
                "confirmed_by": "human", "confirmation_source": "review/1",
                "confirmed_at": "2026-10-30", "scope": "BL-001",
                "changes": {"BL-001": {"old": "a", "new": "b"}}
            }]}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                law.amendment(root, "BA-01", {"BL-001": "a"}, {"BL-001": "c"}, 1)

    def test_contract_detects_version_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, content in {
                "docs/sdlc/plan/intent.md": "# INTENT-001\n版本：2；状态：accepted\n",
                "docs/sdlc/design/spec.md": "# SPEC-001\n版本：1；状态：frozen；依据：INTENT-001 v1\n",
                "docs/sdlc/build/plan.md": "# PLAN-001\n版本：1；状态：draft；输入：SPEC-001 v1\n",
                "docs/sdlc/test/verification.md": "# verification\n",
            }.items():
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content, encoding="utf-8")
            findings = contract.inspect(root)
            self.assertTrue(any(level == "WARN" and where == "spec" and "pinned" in msg for level, where, msg in findings))

    def test_future_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, content in {
                "docs/sdlc/plan/intent.md": "# INTENT-001\n版本：1；状态：accepted\n",
                "docs/sdlc/design/spec.md": "# SPEC-001\n版本：2；状态：frozen；依据：INTENT-001 v9\n",
                "docs/sdlc/build/plan.md": "# PLAN-001\n版本：1；状态：draft；输入：SPEC-001 v2\n",
                "docs/sdlc/test/verification.md": "# verification\n",
            }.items():
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content, encoding="utf-8")
            findings = contract.inspect(root)
            self.assertTrue(any(level == "ERROR" and "future" in msg for level, _, msg in findings))

    def test_contract_draft_template_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, content in {
                "docs/sdlc/plan/intent.md": "# 候选 INTENT-001\n版本：1；状态：draft\n",
                "docs/sdlc/design/spec.md": "# SPEC-001\n版本：1；状态：draft；依据：INTENT-001 v1\n",
                "docs/sdlc/build/plan.md": "# PLAN-001\n版本：1；状态：draft；输入：SPEC-001 v1\n",
                "docs/sdlc/test/verification.md": "# verification\n",
            }.items():
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content, encoding="utf-8")
            self.assertEqual([], contract.inspect(root))


    def test_cli_new_lock_amend_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = root / "AGENT.md"
            agent.write_text("## 项目基本法\n受保护条款\n- [BL-001] initial\n  detail A\n", encoding="utf-8")
            runner = ROOT / "scripts" / "check_basic_law.py"

            def call(*args):
                return subprocess.run([sys.executable, str(runner), "--project", str(root), *args],
                                      capture_output=True, text=True)

            self.assertEqual(0, call("--freeze", "--note", "approved initial").returncode)
            self.assertEqual(0, call("--check").returncode)
            old = law.parse(agent.read_text(encoding="utf-8"), 2)
            agent.write_text(agent.read_text(encoding="utf-8").replace("detail A", "detail B"), encoding="utf-8")
            self.assertEqual(1, call("--check").returncode)
            new = law.parse(agent.read_text(encoding="utf-8"), 2)
            record = root / law.AMENDMENTS
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text(json.dumps({"amendments": [{
                "id": "BA-T01", "state": "accepted", "base_version": 1,
                "confirmed_by": "fixture-user", "confirmation_source": "fixture/ack",
                "confirmed_at": "2026-10-30T12:00:00+08:00", "scope": "BL-001",
                "changes": {"BL-001": {"old": old["BL-001"], "new": new["BL-001"]}}
            }]}), encoding="utf-8")
            self.assertEqual(2, call("--freeze", "--note", "amend").returncode)
            self.assertEqual(0, call("--freeze", "--force", "--amend", "BA-T01",
                                     "--note", "approved change").returncode)
            self.assertEqual(0, call("--check").returncode)
            self.assertEqual(2, law.lock_read(root / law.LOCK)["version"])

    def test_cli_legacy_to_schema2_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = root / "AGENT.md"
            agent.write_text("## 项目基本法\n受保护条款\n- [BL-001] initial\n  legacy unprotected detail\n",
                             encoding="utf-8")
            previous = law.parse(agent.read_text(encoding="utf-8"), 1)
            current = law.parse(agent.read_text(encoding="utf-8"), 2)
            lock = root / law.LOCK
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(json.dumps({"schema": 1, "version": 1, "clauses": previous}), encoding="utf-8")
            amendments = root / law.AMENDMENTS
            amendments.write_text(json.dumps({"amendments": [{
                "id": "BA-M01", "state": "accepted", "base_version": 1,
                "confirmed_by": "fixture-user", "confirmation_source": "fixture/ack",
                "confirmed_at": "2026-10-30T12:00:00+08:00", "scope": "BL-001",
                "changes": {"BL-001": {"old": previous["BL-001"], "new": current["BL-001"]}}
            }]}), encoding="utf-8")
            runner = ROOT / "scripts" / "check_basic_law.py"

            def call(*args):
                return subprocess.run([sys.executable, str(runner), "--project", str(root), *args],
                                      capture_output=True, text=True)

            self.assertEqual(0, call("--check").returncode)
            self.assertEqual(0, call("--migrate", "--force", "--amend", "BA-M01",
                                     "--note", "explicit migration").returncode)
            self.assertEqual(0, call("--check").returncode)
            self.assertEqual(2, law.lock_read(lock)["schema"])
            self.assertEqual(2, law.lock_read(lock)["version"])
            agent.write_text(agent.read_text(encoding="utf-8").replace("legacy unprotected detail",
                                                                      "changed detail"), encoding="utf-8")
            self.assertEqual(1, call("--check").returncode)


if __name__ == "__main__":
    unittest.main()
