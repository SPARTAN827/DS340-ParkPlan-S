"""Guard the demo's evidence boundaries; no raw dataset needed."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_demo as demo


class DemoIntegrityTests(unittest.TestCase):
    def test_missing_archive_fails_without_writing_a_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
                status = demo.main(["--archive", str(root / "missing.tar.gz"), "--output-root", str(root / "runs")])
            self.assertEqual(status, 2)
            self.assertIn("Pinned archive missing", errors.getvalue())
            self.assertFalse((root / "runs").exists())

    def test_first_date_rule_is_not_order_or_outcome_dependent(self):
        date, train = demo.select_demo_date({"fit": ["2017-01-01"], "validation": ["2018-01-01"], "evaluation": ["2018-08-02", "2018-07-26"]})
        self.assertEqual(date, "2018-07-26")
        self.assertEqual(len(train), 2)

    def test_future_training_and_overlap_are_rejected(self):
        for future in ("2018-07-26", "2018-07-27"):
            with self.subTest(future=future), self.assertRaises(ValueError):
                demo.select_demo_date({"fit": [future], "validation": [], "evaluation": ["2018-07-26"]})

    def test_frozen_dependency_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            study = root / "experiments/algorithm_study_20261019"
            study.mkdir(parents=True)
            archive = root / "source.tar.gz"
            archive.write_bytes(b"example archive")
            source = study / "engine.py"
            source.write_bytes(b"original code")
            lock = study / "evaluation_lock.json"
            expected = {source.relative_to(root).as_posix(): demo.digest(source)}
            lock.write_text(json.dumps({"files": expected}))
            with patch.object(demo, "SOURCE_SHA256", demo.digest(archive)), patch.object(demo, "LOCK_SHA256", demo.digest(lock)):
                self.assertEqual(demo.verify_inputs(root, archive), expected)
                source.write_bytes(b"changed code")
                with self.assertRaisesRegex(ValueError, "Frozen dependency changed"):
                    demo.verify_inputs(root, archive)
                source.write_bytes(b"original code")
                archive.write_bytes(b"newer dataset")
                with self.assertRaisesRegex(ValueError, "Dataset checksum mismatch"):
                    demo.verify_inputs(root, archive)

    def failure_rows(self):
        return [{"policy": policy, "initial_order": "a|b", "completed_order": "", "completed": 0,
                 "success": False, "elapsed_min": None, "failure": "closed_at_arrival", "events": []} for policy in demo.POLICIES]

    def test_failed_trip_cannot_get_zero_elapsed_time(self):
        rows = self.failure_rows()
        self.assertEqual(demo.check_outcomes(rows, {}, ("a", "b"))["policy_records_checked"], 5)
        rows[0]["elapsed_min"] = 0
        with self.assertRaisesRegex(ValueError, "Failure must retain"):
            demo.check_outcomes(rows, {}, ("a", "b"))

    def test_success_requires_all_rides_and_correct_arithmetic(self):
        rows = self.failure_rows()
        rows[0].update(success=True, failure="", completed=2, completed_order="a|b", elapsed_min=3.0,
                       total_walk_min=1., total_posted_wait_min=1., total_service_min=1.)
        demo.check_outcomes(rows, {}, ("a", "b"))
        bad = copy.deepcopy(rows)
        bad[0]["elapsed_min"] = 4.
        with self.assertRaisesRegex(ValueError, "arithmetic"):
            demo.check_outcomes(bad, {}, ("a", "b"))
        with self.assertRaisesRegex(ValueError, "same six rides"):
            demo.check_outcomes(rows, {}, ("a", "b", "c"))

    def test_future_or_stale_decision_observation_rejected(self):
        for timestamp in (601., 580.):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                rows = self.failure_rows()
                rows[1]["events"] = [{"type": "decision", "at": 600., "snapshot": {"a": {"minute": timestamp, "value": 20}}}]
                demo.check_outcomes(rows, {}, ("a", "b"))


if __name__ == "__main__":
    unittest.main()
