import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_adoption.py"
BENCHMARK = ROOT / "benchmarks/v2-batch-c-scenarios.json"


class BatchCTests(unittest.TestCase):
    def invoke(self, project, *flags):
        return subprocess.run([sys.executable, str(SCRIPT), "--project", str(project), *flags],
                              capture_output=True, text=True)

    def test_observe_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "existing.txt").write_text("untouched", encoding="utf-8")
            before = sorted(x.relative_to(root).as_posix() for x in root.rglob("*"))
            result = self.invoke(root)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(before, sorted(x.relative_to(root).as_posix() for x in root.rglob("*")))

    def test_warn_nonblocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.invoke(tmp, "--mode", "warn", "--contract-check")
            self.assertEqual(0, result.returncode)
            self.assertIn("CONTRACT_NOT_APPLICABLE", result.stdout)

    def test_enforce_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(1, self.invoke(tmp, "--mode", "enforce").returncode)
            self.assertEqual(0, self.invoke(tmp, "--mode", "enforce", "--approved-enforce").returncode)

    def test_missing_project_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(0, self.invoke(Path(tmp) / "missing").returncode)

    def test_canonical_contract_enforcement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("docs/sdlc/plan/intent.md", "docs/sdlc/design/spec.md",
                        "docs/sdlc/build/plan.md", "docs/sdlc/test/verification.md"):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("invalid metadata", encoding="utf-8")
            self.assertEqual(0, self.invoke(root, "--mode", "warn", "--contract-check").returncode)
            self.assertEqual(1, self.invoke(root, "--mode", "enforce", "--approved-enforce",
                                            "--contract-check").returncode)

    def test_benchmark_is_unexecuted(self):
        data = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        self.assertEqual("NOT_RUN", data["execution"]["status"])
        self.assertEqual(0, data["execution"]["repetitions"])
        self.assertEqual(6, len({x["id"] for x in data["scenarios"]}))
        self.assertFalse(data["execution"]["results"])
