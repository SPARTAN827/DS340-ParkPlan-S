"""Focused engine invariants and a constructed value-of-recourse example.

Run: python3 -m unittest discover -s experiments/algorithm_study_20261019 -p test_engine.py -v
The toy is a mechanism test, not evidence of superiority on park data.
"""
from __future__ import annotations

import bisect
import importlib.util
import itertools
import math
from pathlib import Path
import sys
import unittest

import engine as e


class Day:
    def __init__(self, events):
        self.events = [e.Obs(*v) for v in sorted(events)]
        self.times = [v.minute for v in self.events]
        self.queries = []

    def asof(self, now):
        self.queries.append(now)
        i = bisect.bisect_right(self.times, now + 1e-9) - 1
        if i < 0 or now - self.events[i].minute > 15 + 1e-9:
            return None
        return self.events[i]


def constant_curves(value=20):
    return {r: [float(value)] * 56 for r in e.RIDES}


def current(value=20, now=600):
    return {r: e.Obs(now, value) for r in e.RIDES}


def training_constant(value=20, dates=("train-a", "train-b")):
    return {r: {d: Day([(t, value) for t in range(585, 1441, 5)]) for d in dates}
            for r in e.RIDES}


class LegacyParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "tie_preserving_pilot/replay.py"
        spec = importlib.util.spec_from_file_location("legacy_for_engine_test", path)
        cls.old = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.old
        spec.loader.exec_module(cls.old)

    def test_predictor_and_order_match_legacy(self):
        curves = {r: [float((j * 7 + i * 11) % 65) for j in range(56)]
                  for i, r in enumerate(e.RIDES)}
        predictor = e.Predictor(curves)
        for now in (600.0, 683.12345, 1195.0):
            for closure in (False, True):
                snapshot = {r: (None if i == 2 else e.Obs(now - i / 3,
                             -999 if closure and i == 0 else i * 9))
                            for i, r in enumerate(e.RIDES)}
                oldday = {r: self.old.DayRide([] if obs is None else
                          [self.old.Observation(obs.minute, obs.value)])
                          for r, obs in snapshot.items()}
                for ride in e.RIDES:
                    for horizon in (0.0, 10.0, 15.0, 15.000001, 78.126, 900.0):
                        self.assertEqual(predictor.predict(ride, now + horizon, now, snapshot),
                            self.old.predicted_wait(ride, now + horizon, now, oldday, curves))
                incumbent = tuple(reversed(e.RIDES))
                oldorder, oldfinish = self.old.best_route(incumbent, now, oldday, curves, 10, 10)
                incfinish = self.old.route_prediction(incumbent, now, oldday, curves, 10, 10)
                expected = (oldorder, oldfinish) if oldfinish < incfinish - 1e-9 else (incumbent, incfinish)
                self.assertEqual(e.base_order(incumbent, "GATE", now, snapshot,
                                             e.Config.uniform(), predictor), expected)

    def test_ties_retain_incumbent_and_infinite_does_not_crash(self):
        curves = constant_curves(0)
        predictor = e.Predictor(curves)
        reverse = tuple(reversed(e.RIDES))
        self.assertEqual(e.base_order(reverse, "GATE", 600, current(0),
                                     e.Config.uniform(), predictor)[0], reverse)
        closed = current(-999)
        order, score = e.base_order(reverse, "GATE", 600, closed,
                                    e.Config.uniform(), predictor)
        self.assertEqual(order, reverse)
        self.assertTrue(math.isinf(score))
        # Less than the prescribed epsilon is not an improvement.
        cfg = e.Config.uniform(0, 0)
        a, b = e.RIDES[:2]
        cfg.walk["GATE"][b] = 5e-10
        self.assertEqual(e.base_order((b, a), "GATE", 600, current(0), cfg, predictor)[0], (b, a))

    def test_fractional_times_are_not_rounded(self):
        cfg = e.Config.uniform(0.123456789, 0.234567891)
        finish = e.route_finish(e.RIDES, "GATE", 600.123456789, current(0),
                                cfg, e.Predictor(constant_curves(0)))
        self.assertAlmostEqual(finish, 600.123456789 + 6 * (0.123456789 + 0.234567891), places=11)
        self.assertNotEqual(finish, round(finish, 3))


class ScenarioInvariants(unittest.TestCase):
    def test_selection_current_only_no_test_stream_and_deterministic(self):
        curves = constant_curves(20)

        class Poison:
            def asof(self, when):
                raise AssertionError("Evaluation-day future stream must never be read")

        byride = {r: {"a": Day([(600, 20)]), "b": Day([(600, 20)]),
                      "evaluation": Poison()} for r in e.RIDES}
        bank = e.ScenarioBank(byride, ["b", "a"], curves, k=1)
        selected = bank.select(600, current(20))
        self.assertEqual([s.date for s in selected], ["a"])
        for ride in e.RIDES:
            self.assertNotIn("evaluation", bank.by_ride[ride])
            for date in ("a", "b"):
                self.assertTrue(all(t == 600 for t in byride[ride][date].queries))
        # No training future-coverage filter: a has no later data but still wins.
        self.assertEqual(bank.select(600, current(20))[0].date, "a")

    def test_normalized_distance_omits_closed_and_missing_current(self):
        curves = constant_curves(20)
        data = training_constant(20)
        r0, r1 = e.RIDES[:2]
        data[r0]["train-a"] = Day([(600, 10)])
        data[r0]["train-b"] = Day([(600, 30)])
        data[r1]["train-a"] = Day([(600, 1000)])
        snap = {r: None for r in e.RIDES}
        snap[r0], snap[r1] = e.Obs(600, 10), e.Obs(600, -999)
        scenarios = e.ScenarioBank(data, ["train-a", "train-b"], curves).select(600, snap)
        self.assertEqual([s.date for s in scenarios], ["train-a", "train-b"])
        self.assertEqual(scenarios[0].distance, 0)
        self.assertEqual(scenarios[1].distance, 1)

    def test_anchor_zero_closure_expiry_and_no_future_closure_prediction(self):
        curves = constant_curves(20)
        data = training_constant(30, dates=("train",))
        r = e.RIDES[0]
        data[r]["train"] = Day([(600, 30), (620, -999)])
        snap = current(0)
        scenario = e.ScenarioBank(data, ["train"], curves).select(600, snap)[0]
        self.assertEqual(scenario.wait(r, 600), 0)
        # Historical future closure is curve-imputed, not a predictive closure.
        self.assertTrue(math.isfinite(scenario.wait(r, 620)))
        self.assertGreater(scenario.audit["historical_closure_curve_imputation_queries"], 0)
        closed = current(20)
        closed[r] = e.Obs(590, -999)
        scenario = e.ScenarioBank(data, ["train"], curves).select(600, closed)[0]
        self.assertTrue(math.isinf(scenario.wait(r, 605)))
        self.assertTrue(math.isfinite(scenario.wait(r, 605.000001)))
        self.assertEqual(scenario.snapshot(604)[r].minute, 590)
        self.assertIsNone(scenario.snapshot(605.000001)[r])
        self.assertNotEqual(scenario.snapshot(610)[r].value, -999)
        self.assertEqual(scenario.wait(r, 1500), 20)

    def test_snapshots_never_reveal_next_grid_or_future_observation(self):
        curves = constant_curves(20)
        data = training_constant(20)
        scenario = e.ScenarioBank(data, ["train-a"], curves).select(600.125, current(20, 600.125))[0]
        snap = scenario.snapshot(610.12499999)
        self.assertTrue(all(obs.minute <= 610.12499999 for obs in snap.values()))
        self.assertTrue(all(obs.minute == 605.125 for obs in snap.values()))
        # Issuance information stays exactly as supplied before the first new
        # model-grid observation; missing data must not appear retroactively.
        initial = current(20, 590)
        initial[e.RIDES[0]] = None
        early = e.ScenarioBank(data, ["train-a"], curves).select(600, initial)[0]
        self.assertIsNone(early.snapshot(601)[e.RIDES[0]])
        self.assertEqual(early.snapshot(601)[e.RIDES[1]].minute, 590)
        with self.assertRaises(ValueError):
            e.Predictor(curves).predict(e.RIDES[0], 610, 600, current(20, 601))

    def test_whole_day_cross_ride_pairing_preserved(self):
        curves = constant_curves(20)
        data = {r: {d: Day([(600, 20), (610, 10 + i + 100 * j)])
                    for j, d in enumerate(("a", "b"))}
                for i, r in enumerate(e.RIDES)}
        scenarios = e.ScenarioBank(data, ["a", "b"], curves).select(600, current(20))
        for j, scenario in enumerate(scenarios):
            for i, ride in enumerate(e.RIDES):
                self.assertEqual(scenario.wait(ride, 610), 10 + i + 100 * j)


class RolloutMechanism(unittest.TestCase):
    def test_deterministic_model_reproduces_d0_and_ties(self):
        curves = constant_curves(20)
        predictor, cfg, snap = e.Predictor(curves), e.Config.uniform(), current(20)
        bank = e.ScenarioBank(training_constant(20), ["train-a", "train-b"], curves)
        incumbent = tuple(reversed(e.RIDES))
        base, finish = e.base_order(incumbent, "GATE", 600, snap, cfg, predictor)
        scenarios = bank.select(600, snap)
        self.assertEqual(e.simulate_dynamic(base, "GATE", 600, scenarios[0], cfg, predictor), finish)
        for policy in ("rollout", "scenario_open_loop"):
            order, meta = e.plan(policy, incumbent, "GATE", 600, snap, cfg, predictor, bank)
            self.assertEqual(order, base)
            self.assertEqual(meta["chosen_next"], base[0])
            self.assertTrue(all(v == 240 for v in meta["predicted_costs"].values()))

    def test_constructed_adaptive_recourse_beats_shared_open_loop(self):
        # A takes 10 min; then observations reveal which of B/C has a short
        # temporary queue.  Both become short after 620.  No policy can see
        # the branch before A finishes.  Shared open-loop must use one order.
        a, b, c = e.RIDES[:3]
        curves = constant_curves(0)
        curves[b] = curves[c] = [20.0] * 56
        data = training_constant(0, ("left", "right"))
        for ride in (b, c):
            for date in ("left", "right"):
                high = (ride == c and date == "left") or (ride == b and date == "right")
                data[ride][date] = Day([(600, 20), (610, 60 if high else 0), (620, 0)])
        snap = current(0)
        snap[b] = snap[c] = e.Obs(600, 20)
        cfg, predictor = e.Config.uniform(5, 5), e.Predictor(curves)
        bank = e.ScenarioBank(data, ["left", "right"], curves)
        # The legacy point forecasts are tied, so D0 preserves incumbent B,A,C.
        # The scenario method can instead value observing the branch after A.
        incumbent = (b, a, c)
        base, _ = e.base_order(incumbent, "GATE", 600, snap, cfg, predictor)
        self.assertEqual(base, incumbent)
        d0_finishes = [e.simulate_dynamic(base, "GATE", 600, scenario, cfg, predictor)
                       for scenario in bank.select(600, snap)]
        self.assertEqual(e._mean_elapsed(d0_finishes, 600), 50)
        order, rollout = e.plan("rollout", incumbent, "GATE", 600, snap, cfg, predictor, bank)
        _, static = e.plan("scenario_open_loop", incumbent, "GATE", 600, snap, cfg, predictor, bank)
        self.assertEqual(order[0], a)
        self.assertEqual(rollout["predicted_costs"][a], 30)
        self.assertEqual(min(static["predicted_costs"].values()), 50)
        continuations = []
        for scenario in bank.select(600, snap):
            trace = []
            finish = e.simulate_dynamic((a, b, c), "GATE", 600, scenario, cfg, predictor, trace)
            self.assertEqual(finish, 630)
            continuations.append([step["ride"] for step in trace])
        self.assertEqual(continuations, [[a, b, c], [a, c, b]])

    def test_no_failed_sample_dropping_and_fallback(self):
        self.assertTrue(math.isinf(e._mean_elapsed([650, math.inf], 600)))
        curves = constant_curves(20)
        cfg, predictor = e.Config.uniform(), e.Predictor(curves)
        bank = e.ScenarioBank(training_constant(20), ["train-a"], curves)
        for policy in ("rollout", "scenario_open_loop"):
            order, meta = e.plan(policy, e.RIDES, "GATE", 600, current(-999), cfg, predictor, bank)
            self.assertEqual(order, e.RIDES)
            self.assertTrue(meta["fallback"])
            self.assertEqual(meta["fallback_reason"], "all_actions_unsupported")
        _, empty = e.plan("rollout", e.RIDES, "GATE", 600, current(20), cfg, predictor,
                          e.ScenarioBank({}, [], curves))
        self.assertTrue(empty["fallback"])

    def test_no_deadline_penalty_in_predictive_model(self):
        curves = constant_curves(200)
        predictor, cfg = e.Predictor(curves), e.Config.uniform()
        snap = current(200, 1400)
        bank = e.ScenarioBank(training_constant(200), ["train-a"], curves)
        order, meta = e.plan("rollout", e.RIDES[:2], "GATE", 1400, snap, cfg, predictor, bank)
        self.assertFalse(meta["fallback"])
        self.assertTrue(all(v == 440 for v in meta["predicted_costs"].values()))


if __name__ == "__main__":
    unittest.main()
