"""Copy the frozen Skill tree for one arm into a run sandbox."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from . import config


def copy_skill_pack(root: Path, arm: str) -> dict:
    """Copy the arm's skill files under ``root/skill/`` and return a manifest."""
    if arm not in config.ARM_SKILLS:
        raise ValueError(f"unknown arm {arm!r}")
    spec = config.ARM_SKILLS[arm]
    dest_root = root / "skill"
    manifest: dict[str, str] = {}
    files: list[str] = []
    if "pre-flight" in spec["trees"]:
        files += [f"pre-flight/{rel}" for rel in config.BASE_SKILL_FILES]
    if "pre-flight-enhanced" in spec["trees"]:
        files += [f"pre-flight-enhanced/{rel}" for rel in config.ENHANCED_SKILL_FILES]
    for rel in files:
        src = config.REPO_ROOT / rel
        dst = dest_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest[rel] = hashlib.sha256(src.read_bytes()).hexdigest()
    aggregate = hashlib.sha256()
    for name in sorted(manifest):
        aggregate.update((name + "\0" + manifest[name] + "\n").encode())
    entry_path = root / spec["entry"]
    entry_text = entry_path.read_text(encoding="utf-8")
    return {
        "arm": arm,
        "skill_name": spec["name"],
        "trees": spec["trees"],
        "entry": spec["entry"],
        "entry_sha256": hashlib.sha256(entry_text.encode()).hexdigest(),
        "reference_root": spec["reference_root"],
        "files": manifest,
        "pack_sha256": aggregate.hexdigest(),
        "entry_text": entry_text,
    }
