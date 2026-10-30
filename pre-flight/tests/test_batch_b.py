import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("handoff_checker", ROOT / "scripts/check_handoff.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BatchBTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "assets/examples/batch-b-handoff.example.json").read_text(encoding="utf-8"))

    def test_example(self):
        self.assertEqual([], module.validate(self.data))

    def test_tier(self):
        self.data["routing"]["tier"] = "Lite"
        self.assertTrue(module.validate(self.data))

    def test_unknown_impact(self):
        self.data["routing"]["unknown_impact"] = True
        self.assertTrue(module.validate(self.data))
        self.data["routing"]["tier"] = "Strict"
        self.assertEqual([], module.validate(self.data))

    def test_missing_scope(self):
        del self.data["handoff"]["scope"]
        self.assertTrue(module.validate(self.data))

    def test_unverified_pass(self):
        self.data["handoff"]["verification"]["status"] = "PASS"
        self.assertTrue(module.validate(self.data))

    def test_side_effect(self):
        self.data["handoff"]["side_effect_state"] = "unknown"
        self.assertTrue(module.validate(self.data))
        self.data["handoff"]["next_action"] = "read_only_reconcile"
        self.assertEqual([], module.validate(self.data))

    def test_accepted_pass(self):
        v = self.data["handoff"]["verification"]
        v.update({"status": "PASS", "evidence_level": "E0", "evidence_ref": "run/1"})
        self.assertEqual([], module.validate(self.data))

    def test_downgrade(self):
        self.data["routing"]["downgraded"] = True
        self.assertTrue(module.validate(self.data))
        self.data["routing"]["downgrade_reason"] = "reviewed"
        self.assertEqual([], module.validate(self.data))


intent_spec = importlib.util.spec_from_file_location("intent_delta", ROOT / "scripts/check_intent_delta.py")
intent = importlib.util.module_from_spec(intent_spec)
intent_spec.loader.exec_module(intent)


class IntentDeltaTests(unittest.TestCase):
    def setUp(self):
        self.record = {"changed_fields": ["bugfix"], "intent_confirmed": True,
                       "confirmation_ref": "review/1", "within_accepted_spec": True}

    def test_reuse_confirmed(self):
        self.assertEqual("reuse-confirmed-intent", intent.classify(self.record)[0])

    def test_material_delta(self):
        self.record["changed_fields"] = ["success_criteria"]
        self.assertEqual("await-intent-confirmation", intent.classify(self.record)[0])

    def test_unconfirmed(self):
        self.record["intent_confirmed"] = False
        self.assertEqual("await-intent-confirmation", intent.classify(self.record)[0])

    def test_outside_spec(self):
        self.record["within_accepted_spec"] = False
        self.assertEqual("needs-clarification", intent.classify(self.record)[0])

    def test_permission_change(self):
        self.record["changes_authorization"] = True
        self.assertEqual("separate-authorization", intent.classify(self.record)[0])

    def test_l1_change(self):
        self.record["changes_basic_law"] = True
        self.assertEqual("basic-law-amendment", intent.classify(self.record)[0])
