"""Paths and frozen configuration for the boundary stress evaluation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EVAL_ROOT.parents[1]
STATE_DIR = EVAL_ROOT / "state"
RUNS_DIR = STATE_DIR / "runs"
DSH_HOME = STATE_DIR / "dsh-home"
ADMIN_TOKEN_FILE = STATE_DIR / "service-admin-token"
SERVICE_URL = os.environ.get("PF_SERVICE_URL", "http://127.0.0.1:18891")
MODEL_PATCH = EVAL_ROOT / "config" / "headless-opencode.yml"
RUNS_INDEX = EVAL_ROOT / "state" / "runs-index.jsonl"

APP_BINARY = Path("/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness")
CLI_JS = Path("/Applications/DeepSeek Harness.app/Contents/Resources/app.asar/dsh/"
              "node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js")

# Arm definition: which skill tree is loaded.  The base arm must not see the
# enhanced tree (and vice versa the enhanced arm must not see base-arm results;
# run isolation provides that).
ARM_SKILLS = {
    "A": {
        "name": "pre-flight",
        "trees": ["pre-flight"],
        "entry": "skill/pre-flight/SKILL.md",
        "reference_root": "skill/pre-flight/",
    },
    "B": {
        "name": "pre-flight-enhanced",
        "trees": ["pre-flight", "pre-flight-enhanced"],
        "entry": "skill/pre-flight-enhanced/SKILL.md",
        "reference_root": "skill/pre-flight-enhanced/",
    },
}

BASE_SKILL_FILES = [
    "SKILL.md",
    "references/basic-law-change.md",
    "references/bootstrap.md",
    "references/change-control.md",
    "references/context-and-harness.md",
    "references/host-wiring.md",
    "references/intent-confirmation.md",
    "references/method-basis.md",
    "references/safety-baseline.md",
    "references/v2-batch-b-routing-and-handoff.md",
    "references/v2-batch-c-adoption-and-benchmark.md",
    "references/workflow.md",
    "assets/project-template/AGENT.md",
]

# Operational files copied into the tested Agent's context for arm B.
ENHANCED_SKILL_FILES = [
    "SKILL.md",
]

# Evaluator-only documents shipped in the same Skill directory but withheld
# from the tested Agent so the hidden acceptance key cannot leak into a run:
# the behavior rubric and the boundary-case answer key.
ENHANCED_EVALUATOR_FILES = [
    "references/behavior-evaluation.md",
    "evaluations/2026-10-31-boundary-cases.md",
    "evaluations/2026-10-31-extended-executed-check.md",
    "evaluations/2026-10-31-static-audit.md",
]

EXCLUDED_ANSWER_KEY_FILES = [f"pre-flight-enhanced/{rel}"
                             for rel in ENHANCED_EVALUATOR_FILES]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def skill_pack_manifest() -> dict:
    """Deterministic manifest of every file the frozen skill version ships."""
    files: dict[str, str] = {}
    for rel in BASE_SKILL_FILES:
        path = REPO_ROOT / "pre-flight" / rel
        files[f"pre-flight/{rel}"] = sha256_file(path)
    for rel in ENHANCED_SKILL_FILES + ENHANCED_EVALUATOR_FILES:
        path = REPO_ROOT / "pre-flight-enhanced" / rel
        files[f"pre-flight-enhanced/{rel}"] = sha256_file(path)
    aggregate = hashlib.sha256()
    for name in sorted(files):
        aggregate.update((name + "\0" + files[name] + "\n").encode())
    return {"files": files, "sha256": aggregate.hexdigest(),
            "git_sha": git_head(), "repo_root": str(REPO_ROOT),
            "excluded_answer_key_files": EXCLUDED_ANSWER_KEY_FILES}


def git_head() -> str:
    head = REPO_ROOT / ".git"
    try:
        if head.is_file():  # worktree: .git is a file pointing at gitdir
            return _read_head_from_gitfile(head)
        return _read_head_from_dir(head)
    except Exception:
        return "unknown"


def _read_head_from_gitfile(gitfile: Path) -> str:
    content = gitfile.read_text(encoding="utf-8").strip()
    if not content.startswith("gitdir:"):
        return "unknown"
    gitdir = Path(content.split(":", 1)[1].strip())
    if not gitdir.is_absolute():
        gitdir = (gitfile.parent / gitdir).resolve()
    return _read_head_from_dir(gitdir)


def _read_head_from_dir(gitdir: Path) -> str:
    head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        common = gitdir
        if (gitdir / "commondir").exists():
            common = (gitdir / (gitdir / "commondir").read_text().strip()).resolve()
        ref_path = common / ref
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip()
        packed = common / "packed-refs"
        if packed.exists():
            for line in packed.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0]
        return "unknown"
    return head


def model_config() -> dict:
    patch_text = MODEL_PATCH.read_text(encoding="utf-8")
    return {
        "provider": "opencode-go",
        "model": "deepseek-v4.1-flash",
        "profile": "headless",
        "permission_mode": "workspace-write",
        "approval_policy": "ask (fails closed in headless)",
        "patch_file": str(MODEL_PATCH.relative_to(EVAL_ROOT)),
        "patch_sha256": hashlib.sha256(patch_text.encode()).hexdigest(),
        "cli": str(CLI_JS),
    }


def ensure_dirs() -> None:
    for path in (STATE_DIR, RUNS_DIR, DSH_HOME / "profiles"):
        path.mkdir(parents=True, exist_ok=True)
    if not (DSH_HOME / "profiles" / "headless").exists():
        source = Path(os.path.expanduser("~/.dsh/profiles/headless"))
        import shutil
        shutil.copytree(source, DSH_HOME / "profiles" / "headless")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
