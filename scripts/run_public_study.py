#!/usr/bin/env python3
"""TouringPlans.com credited public-distribution runner; no policy changes.

Run only in a reproduction copy: the frozen runner writes phase outputs.
The only substitutions are explicit preservation bookkeeping and annotations.
Scientific functions execute from the original, hash-guarded run.py.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from public_integrity import (
    ROOT, STUDY, check_frozen_entrypoints, check_public_preservation, digest,
)


def load_runner():
    check_frozen_entrypoints()
    sys.path.insert(0, str(STUDY))
    spec = importlib.util.spec_from_file_location("parkplan_public_frozen_runner", STUDY / "run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def install_public_bookkeeping(module):
    """Return checked scope; do not touch policy, inputs, selection, or hashes."""
    checked = check_public_preservation()
    original_write_rows = module.write_rows
    original_save = module.save

    def preserved():
        return check_public_preservation()["included_legacy_artifacts_verified"]

    def annotation():
        return {
            **check_public_preservation(),
            "adapter": "scripts/run_public_study.py",
            "adapter_sha256": digest(Path(__file__).resolve()),
            "scientific_runner": "experiments/algorithm_study_20261019/run.py",
            "scientific_runner_sha256": digest(STUDY / "run.py"),
            "note": "Only public preservation bookkeeping and provenance annotations differ; original frozen policy code is unchanged.",
        }

    def write_rows(folder, rows, metadata):
        public_metadata = dict(metadata)
        public_metadata["public_distribution"] = annotation()
        original_write_rows(folder, rows, public_metadata)

    def save(path, value):
        # The reference-only summary also reports preservation accounting.
        if isinstance(value, dict) and "old_artifact_hashes" in value and "rows_matched" in value:
            value = {**value, "public_distribution": annotation()}
        original_save(path, value)

    module.preserved = preserved
    module.write_rows = write_rows
    module.save = save
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["validate", "select", "reference", "evaluate", "sensitivity", "check"])
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    module = load_runner()
    checked = install_public_bookkeeping(module)
    print(json.dumps(checked, indent=2, ensure_ascii=False), flush=True)
    if args.phase == "check":
        return 0
    if args.phase == "select":
        module.select()
    else:
        module.run(args.phase, args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
