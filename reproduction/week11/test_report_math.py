import unittest
from make_report import wilson


class WilsonIntervalTests(unittest.TestCase):
    def test_all_success_has_exact_upper_endpoint(self):
        lo, hi = wilson(50, 50)
        self.assertEqual(hi, 1.0)
        self.assertAlmostEqual(lo, 0.9286524, places=6)

    def test_no_success_has_exact_lower_endpoint(self):
        lo, hi = wilson(0, 50)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.0713476, places=6)

    def test_half_success_is_symmetric(self):
        lo, hi = wilson(25, 50)
        self.assertAlmostEqual(lo+hi, 1.0, places=12)
        self.assertAlmostEqual(lo, 0.3664451, places=6)


if __name__ == '__main__':
    unittest.main()
