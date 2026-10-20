"""TouringPlans.com credited public-distribution preservation checks.

This adapter checks a narrowly scoped subset. It never returns a fictitious
31-artifact pass and never changes the frozen study or its original manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments/algorithm_study_20261019"
MANIFEST_PATH = "experiments/tie_preserving_pilot/preserved_artifacts_sha256.json"
MANIFEST_SHA256 = "c5634a39e1e494035e61e9ae7994e22c19af803aaf5f75ed590c30ad144be2c2"
RUNNER_SHA256 = "a8ed8bd340c66f6be7106d58f6098df01d112cc2407cc986bcce4059fed94cd0"
VERIFIER_SHA256 = "a4543d18222785bdc9ce4a1054a4b987ea6d4ccda6ea7f5bfef9997a5eea508d"
OMITTED_PATHS = frozenset({
    "deliverables/ParkPlan-S-Oct14-Plain-Language-and-Evidence-v2.zip",
    "meeting-notes/2026-10-14-professor-v2/01-先把项目讲明白-中文.html",
    "meeting-notes/2026-10-14-professor-v2/01-先把项目讲明白-中文.md",
    "meeting-notes/2026-10-14-professor-v2/01-先把项目讲明白-中文.pdf",
    "meeting-notes/2026-10-14-professor-v2/02-Professor-Progress-Plain-English.html",
    "meeting-notes/2026-10-14-professor-v2/02-Professor-Progress-Plain-English.md",
    "meeting-notes/2026-10-14-professor-v2/02-Professor-Progress-Plain-English.pdf",
    "meeting-notes/2026-10-14-professor-v2/03-两分钟英文讲稿与重点.html",
    "meeting-notes/2026-10-14-professor-v2/03-两分钟英文讲稿与重点.md",
    "meeting-notes/2026-10-14-professor-v2/03-两分钟英文讲稿与重点.pdf",
    "meeting-notes/2026-10-14-professor-v2/READ-FIRST-zh.md",
})


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_public_preservation(root: Path = ROOT) -> dict:
    """Verify exactly 20 included legacy files; reject unlisted omissions.

    The 11 omitted files must be absent from a public copy. Their historical
    hashes remain in the original manifest but are NOT verified by this check.
    """
    root = Path(root).resolve()
    manifest_path = root / MANIFEST_PATH
    require(digest(manifest_path) == MANIFEST_SHA256, "Original preservation manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    omissions = json.loads((root / "scripts/public-omissions.json").read_text(encoding="utf-8"))
    require(len(manifest) == 31, "Original manifest must contain exactly 31 artifacts")
    require(omissions["original_manifest_sha256"] == MANIFEST_SHA256,
            "Omission record does not identify the original manifest")
    require(omissions["original_artifact_count"] == 31
            and omissions["included_legacy_artifact_count"] == 20
            and omissions["omitted_legacy_artifact_count"] == 11,
            "Omission record count mismatch")
    require(set(omissions["omitted"]) == OMITTED_PATHS,
            "Omission record must contain exactly the declared 11 meeting/archive paths")
    require(omissions["omitted"] == {p: manifest[p] for p in OMITTED_PATHS},
            "Omitted historical hashes differ from the original manifest")
    included = {p: h for p, h in manifest.items() if p not in OMITTED_PATHS}
    require(len(included) == 20 and all(p.startswith("experiments/") for p in included),
            "Included legacy artifact set differs from the declared 20 files")
    for relative, expected in included.items():
        path = root / relative
        require(path.is_file(), f"Required public legacy artifact missing: {relative}")
        require(digest(path) == expected, f"Required public legacy artifact changed: {relative}")
    for relative in OMITTED_PATHS:
        require(not (root / relative).exists(),
                f"Public copy contains an intentionally excluded artifact: {relative}")
    return {
        "status": "PASS",
        "scope": "Public distribution: 20 included legacy hashes checked; 11 omitted historical artifacts not checked.",
        "original_preservation_manifest_sha256": MANIFEST_SHA256,
        "included_legacy_artifacts_verified": 20,
        "historical_artifacts_intentionally_not_distributed": 11,
        "included_paths": sorted(included),
        "omitted_paths": sorted(OMITTED_PATHS),
        "historical_31_artifact_certificate_reissued": False,
    }


def check_frozen_entrypoints(root: Path = ROOT) -> None:
    study = Path(root) / "experiments/algorithm_study_20261019"
    require(digest(study / "run.py") == RUNNER_SHA256, "Frozen scientific runner changed")
    require(digest(study / "verify_results.py") == VERIFIER_SHA256,
            "Original independent verifier changed")
