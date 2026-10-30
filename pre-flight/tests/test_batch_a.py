#!/usr/bin/env python3
"""Batch A deterministic smoke tests. Run: python3 -m unittest discover -s pre-flight/tests -v"""
import importlib.util
import json
import tempfile
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


if __name__ == "__main__":
    unittest.main()
