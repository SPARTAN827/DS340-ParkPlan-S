"""Adversarial checks for the independent auditor (no runner imports)."""
import copy
import math
from pathlib import Path
import tempfile
import unittest

import verify_results as verifier


def rounded(values):
    return [float(format(value, ".6g")) for value in values]


class IndependentAuditTests(unittest.TestCase):
    def setUp(self):
        self.config = {"simulation": {"eta_ipt": 0.4, "eta_chrg": 0.9}}
        self.sensors = [[0., 0., 0., 0.], [0., 0., 0., 0.], [100., 0., 0., 30.]]
        self.edges = {(0, 2): [0., 2., 10., 5.], (2, 1): [2., 1., 10., 5.],
                      (0, 1): [0., 1., 10., 5.]}
        self.prize = 8.82 - (4.5 - 2.19444e-6 * 10)
        self.arrival_voltage = math.sqrt(200 * (4.5 - 2.19444e-6 * 10))
        self.charge_t = 10 * (42 - self.arrival_voltage) / 0.825 / 0.9

    def success_fixture(self):
        mission = [[0., 0., 0., 0., 0., 0., 100., 0.]]
        mission.append(rounded([100., 0., 0., 10., 95., 10 + self.charge_t,
                                95 - self.prize / 0.4, self.prize]))
        mission.append(rounded([0., 0., 0., mission[-1][5] + 10,
                                mission[-1][6] - 5, -1., -1., 0.]))
        after = copy.deepcopy(self.sensors)
        after[2][3] = 42.
        final = copy.deepcopy(after)
        final[2][3] = float(format(math.sqrt(200 * (8.82 - 2.19444e-6 * 10)), ".6g"))
        return [mission, [[0., 0., 0., 0., 0., 2., 1.], [0., 0., 0., 0., 2., 1.]],
                [0, 1], [self.sensors, after, final], self.edges, self.config]

    def test_success_recomputed_from_raw_rows(self):
        result = verifier.audit_trajectory(*self.success_fixture())
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["serviced_nodes"], 1)
        self.assertEqual(result["visited_path"], [0, 2, 1])
        self.assertAlmostEqual(result["charged_energy_kj"], 4.32002)
        self.assertAlmostEqual(result["consumed_energy_kj"], 20.8001)

    def test_forged_charge_rejected(self):
        args = self.success_fixture()
        args[0][1][7] += 0.1
        with self.assertRaisesRegex(verifier.AuditError, "E_chrg"):
            verifier.audit_trajectory(*args)

    def test_nonfinite_mission_rejected(self):
        args = self.success_fixture()
        args[0][1][7] = float("nan")
        with self.assertRaisesRegex(verifier.AuditError, "non-finite"):
            verifier.audit_trajectory(*args)

    def test_bad_sensor_state_rejected(self):
        args = self.success_fixture()
        args[3][1][2][3] = 40.
        with self.assertRaisesRegex(verifier.AuditError, "sensor 2 voltage"):
            verifier.audit_trajectory(*args)

    def test_missing_command_rejected(self):
        args = self.success_fixture()
        args[2].pop()
        with self.assertRaisesRegex(verifier.AuditError, "transition count"):
            verifier.audit_trajectory(*args)

    def test_depot_label_without_depot_rejected(self):
        args = self.success_fixture()
        args[2][0] = 1
        with self.assertRaisesRegex(verifier.AuditError, "exit 1"):
            verifier.audit_trajectory(*args)

    def test_service_failure_actual_code_255(self):
        mission = [[0., 0., 0., 0., 0., 0., 6., 0.],
                   rounded([100., 0., 0., 10 + self.charge_t, 1 - self.prize / 0.4, -1., -1., 0.])]
        after = copy.deepcopy(self.sensors)
        after[2][3] = float(format(self.arrival_voltage, ".6g"))
        args = [mission, [[0., 0., 0., 0., 0., 2., 1.]], [255],
                [self.sensors, after], self.edges, self.config]
        result = verifier.audit_trajectory(*args)
        self.assertEqual(result["status"], "service_failure")
        self.assertEqual(result["serviced_nodes"], 0)
        args[2][0] = 254
        with self.assertRaisesRegex(verifier.AuditError, "expected 255"):
            verifier.audit_trajectory(*args)

    def test_visit_and_return_failures_are_not_success(self):
        for target, code, status in [(2, 254, "visit_failure"), (1, 253, "return_failure")]:
            mission = [[0., 0., 0., 0., 0., 0., 4., 0.],
                       [*self.sensors[target][:3], 10., -1., -1., -1., 0.]]
            result = verifier.audit_trajectory(mission, [[0., 0., 0., 0., 0., float(target)]],
                                               [code], [self.sensors, self.sensors], self.edges, self.config)
            self.assertEqual(result["status"], status)
            self.assertFalse(result["success"])

    def test_reading_nan_csv_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.csv"
            path.write_text("0,1,nan\n")
            with self.assertRaisesRegex(verifier.AuditError, "non-finite"):
                verifier.number_rows(path)

    def test_local_serialization_tolerance_not_percent_tolerance(self):
        verifier.near(1000.01, 1000.006, "rounded")
        with self.assertRaises(verifier.AuditError):
            verifier.near(1000.1, 1000.006, "changed")


if __name__ == "__main__":
    unittest.main()
