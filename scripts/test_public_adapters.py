"""TouringPlans.com credited tests of public packaging boundaries, not policies."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import types
import unittest

import public_integrity as integrity
import run_public_study as public_runner


class PublicPreservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="parkplan-public-adapter-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        manifest = json.loads((integrity.ROOT / integrity.MANIFEST_PATH).read_text(encoding="utf-8"))
        self.included = [p for p in manifest if p not in integrity.OMITTED_PATHS]
        for relative in self.included + [integrity.MANIFEST_PATH, "scripts/public-omissions.json"]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(integrity.ROOT / relative, target)

    def test_exact_twenty_pass_without_omitted_files(self):
        result = integrity.check_public_preservation(self.root)
        self.assertEqual(result["included_legacy_artifacts_verified"], 20)
        self.assertEqual(result["historical_artifacts_intentionally_not_distributed"], 11)
        self.assertFalse(result["historical_31_artifact_certificate_reissued"])

    def test_missing_included_file_fails(self):
        (self.root / self.included[0]).unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            integrity.check_public_preservation(self.root)

    def test_modified_included_file_fails(self):
        with (self.root / self.included[0]).open("ab") as stream:
            stream.write(b"\nmodified fixture\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            integrity.check_public_preservation(self.root)

    def test_original_manifest_change_fails(self):
        (self.root / integrity.MANIFEST_PATH).write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            integrity.check_public_preservation(self.root)

    def test_extra_omission_fails(self):
        path = self.root / "scripts/public-omissions.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["omitted"][self.included[0]] = "f" * 64
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "exactly the declared"):
            integrity.check_public_preservation(self.root)

    def test_accidentally_bundled_meeting_file_fails(self):
        path = self.root / sorted(integrity.OMITTED_PATHS)[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("A file that is explicitly excluded from this public distribution.")
        with self.assertRaisesRegex(ValueError, "contains an intentionally excluded"):
            integrity.check_public_preservation(self.root)


class RunnerAdapterTests(unittest.TestCase):
    def test_original_entrypoint_hashes(self):
        integrity.check_frozen_entrypoints()

    def test_only_bookkeeping_functions_replaced(self):
        writes, saves = [], []
        policy = object()
        module = types.SimpleNamespace(
            preserved=lambda: 31,
            write_rows=lambda folder, rows, metadata: writes.append((folder, rows, metadata)),
            save=lambda path, value: saves.append((path, value)),
            replay=policy,
        )
        public_runner.install_public_bookkeeping(module)
        self.assertIs(module.replay, policy)
        self.assertEqual(module.preserved(), 20)
        rows = [{"scientific_result": "unchanged"}]
        metadata = {"old_artifacts_unchanged": 20}
        module.write_rows("fixture-output", rows, metadata)
        self.assertIs(writes[0][1], rows)
        self.assertEqual(metadata, {"old_artifacts_unchanged": 20})
        self.assertEqual(writes[0][2]["public_distribution"]["included_legacy_artifacts_verified"], 20)
        self.assertEqual(writes[0][2]["public_distribution"]["historical_artifacts_intentionally_not_distributed"], 11)
        result = {"rows_matched": 330, "old_artifact_hashes": 20}
        module.save("reference-check", result)
        self.assertNotIn("public_distribution", result)
        self.assertIn("public_distribution", saves[-1][1])
        ordinary = {"selection": "scientific-fields"}
        module.save("selection", ordinary)
        self.assertIs(saves[-1][1], ordinary)


if __name__ == "__main__":
    unittest.main()
