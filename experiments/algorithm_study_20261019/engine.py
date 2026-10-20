"""Small, nonanticipative scenario-rollout planning engine (standard library only).

The real executor is deliberately outside this module.  Planners receive a current
snapshot, never the evaluation day's future stream.  Each model scenario is one
training day shared across all rides.  Its future can be read by the simulator to
realize a leg, but the continuation policy sees only an as-of simulated snapshot.

Model limitations are intentional and reported in plan metadata: historical
missing/closed values are curve-imputed; future closures are NOT forecast; known
current closures expire at their ORIGINAL timestamp + 15 minutes; model scoring
does not impose a closing deadline; beyond midnight the curve's tail is used.
The five-minute simulated observation grid starts at scenario issuance.  This is
a model assumption, not a claim about source observation frequency.

Rollout here estimates the cost of forcing one action then following D0.  It is
not an optimal stochastic policy, and finite historical scenarios plus model
misspecification do not imply improvement on real or held-out days.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import itertools
import math
from typing import Any, Mapping, Sequence


RIDES = ("AK07", "AK11", "AK14", "AK18", "AK85", "AK86")
EPS = 1e-9
START = 600.0
MAX_AGE = 15.0
SLOT = 15.0
GRID = 5.0


@dataclass(frozen=True)
class Obs:
    minute: float
    value: float


Snapshot = Mapping[str, Any | None]


@dataclass
class Config:
    start: float = START
    walk: dict[str, dict[str, float]] = field(default_factory=lambda: {
        a: {b: 10.0 for b in RIDES} for a in ("GATE",) + RIDES})
    service: dict[str, float] = field(default_factory=lambda: {r: 10.0 for r in RIDES})

    @classmethod
    def uniform(cls, walk: float = 10.0, service: float = 10.0) -> "Config":
        if walk < 0 or service < 0:
            raise ValueError("Travel and service time must be nonnegative")
        return cls(walk={a: {b: float(walk) for b in RIDES}
                         for a in ("GATE",) + RIDES},
                   service={r: float(service) for r in RIDES})


def historical(ride: str, minute: float,
               curves: Mapping[str, Sequence[float]]) -> float:
    values = curves[ride]
    slot = max(0, min(len(values) - 1, int((minute - START) // SLOT)))
    return float(values[slot])


def _observable(snapshot: Snapshot, ride: str, now: float) -> Any | None:
    obs = snapshot.get(ride)
    if obs is not None and obs.minute > now + EPS:
        raise ValueError("Snapshot contains a future observation")
    # Mirrors DayRide.asof; callers need not manually discard stale values.
    if obs is not None and now - obs.minute > MAX_AGE + EPS:
        return None
    return obs


@dataclass
class Predictor:
    curves: Mapping[str, Sequence[float]]
    decay: float = 60.0

    def __post_init__(self) -> None:
        if self.decay <= 0:
            raise ValueError("Prediction decay must be positive")

    def predict(self, ride: str, arrival: float, now: float,
                snapshot: Snapshot) -> float:
        """Exact legacy residual-decay predictor, including closure boundary."""
        current = _observable(snapshot, ride, now)
        baseline = historical(ride, arrival, self.curves)
        if current is not None and current.value == -999:
            return math.inf if arrival - current.minute <= MAX_AGE + EPS else baseline
        if current is None:
            return baseline
        residual = current.value - historical(ride, current.minute, self.curves)
        return max(0.0, baseline + residual * math.exp(-(arrival - now) / self.decay))


def route_finish(order: Sequence[str], location: str, now: float,
                 snapshot: Snapshot, config: Config, predictor: Predictor) -> float:
    finish = now
    for ride in order:
        arrival = finish + config.walk[location][ride]
        wait = predictor.predict(ride, arrival, now, snapshot)
        if not math.isfinite(wait):
            return math.inf
        finish = arrival + wait + config.service[ride]
        location = ride
    return finish


def base_order(incumbent: Sequence[str], location: str, now: float,
               snapshot: Snapshot, config: Config,
               predictor: Predictor) -> tuple[tuple[str, ...], float]:
    """D0 exhaustive forecast optimizer, preserving incumbent on tied scores.

    Starting from sorted RIDES reproduces the legacy initial lexical tie rule.
    All-infinite predictions retain the incumbent and return infinity.
    """
    incumbent = tuple(incumbent)
    incumbent_finish = route_finish(incumbent, location, now, snapshot, config, predictor)
    best, best_finish = incumbent, math.inf
    for order in itertools.permutations(sorted(incumbent)):
        finish = route_finish(order, location, now, snapshot, config, predictor)
        if finish < best_finish - EPS:
            best, best_finish = order, finish
    if best_finish < incumbent_finish - EPS:
        return best, best_finish
    return incumbent, incumbent_finish


class Scenario:
    """A training-day template anchored using current observable values only."""

    def __init__(self, date: str, streams: Mapping[str, Any],
                 curves: Mapping[str, Sequence[float]], now: float,
                 snapshot: Snapshot, distance: float = 0.0):
        self.date, self.streams, self.curves = date, streams, curves
        self.now, self.distance = float(now), float(distance)
        self.initial = {r: _observable(snapshot, r, now) for r in RIDES}
        self.audit: Counter = Counter()
        self.offset = {}
        for ride, obs in self.initial.items():
            self.offset[ride] = (obs.value - self._template(ride, now)
                                 if obs is not None and obs.value >= 0 else 0.0)

    def _template(self, ride: str, minute: float) -> float:
        if minute >= 1440.0:
            self.audit["beyond_midnight_curve_queries"] += 1
            return historical(ride, minute, self.curves)
        stream = self.streams.get(ride)
        obs = stream.asof(minute) if stream is not None else None
        if obs is None:
            self.audit["missing_curve_imputation_queries"] += 1
            return historical(ride, minute, self.curves)
        if obs.value < 0:
            self.audit["historical_closure_curve_imputation_queries"] += 1
            return historical(ride, minute, self.curves)
        return float(obs.value)

    def wait(self, ride: str, minute: float) -> float:
        """Realize model wait; only simulator, not continuation planner, calls this."""
        if minute < self.now - EPS:
            raise ValueError("Scenario cannot realize before issuance")
        obs = self.initial.get(ride)
        if obs is not None and obs.value == -999 and minute - obs.minute <= MAX_AGE + EPS:
            return math.inf
        return max(0.0, self._template(ride, minute) +
                   self.offset[ride] * math.exp(-(minute - self.now) / 60.0))

    def snapshot(self, minute: float) -> dict[str, Obs | None]:
        if minute < self.now - EPS:
            raise ValueError("Scenario cannot observe before issuance")
        if abs(minute - self.now) <= EPS:
            return dict(self.initial)
        # Never round up: even fractions immediately below a grid boundary must
        # not expose the next model observation.
        observed_at = self.now + math.floor((minute - self.now) / GRID) * GRID
        if observed_at <= self.now:
            # The issuance grid point is the actual supplied snapshot.  Do not
            # retroactively replace missing/stale issuance data with new values.
            return {r: _observable(self.initial, r, minute) for r in RIDES}
        result = {}
        for ride in RIDES:
            original = self.initial.get(ride)
            if original is not None and original.value == -999:
                if observed_at - original.minute <= MAX_AGE + EPS:
                    result[ride] = (original if minute - original.minute <= MAX_AGE + EPS
                                    else None)
                    continue
            value = self.wait(ride, observed_at)
            result[ride] = Obs(observed_at, value)
        return result


class ScenarioBank:
    """Stores ONLY supplied training dates, with no test-day future reference.

    Selection queries historical templates at the current decision time only;
    there is no future-coverage filtering.  Missing/closed historical current
    states use the historical curve.  Current closed/missing rides are omitted
    from the distance.  Date ordering resolves exact distance ties.
    """

    def __init__(self, by_ride: Mapping[str, Mapping[str, Any]],
                 train_dates: Sequence[str], curves: Mapping[str, Sequence[float]],
                 k: int = 8):
        if k < 1:
            raise ValueError("Scenario count must be positive")
        self.train_dates = tuple(sorted(set(train_dates)))
        self.curves = {r: tuple(curves[r]) for r in RIDES}
        self.k = k
        # Filter at construction, even if the caller supplied a full archive.
        self.by_ride = {r: {d: by_ride.get(r, {}).get(d) for d in self.train_dates}
                        for r in RIDES}

    def select(self, now: float, snapshot: Snapshot) -> list[Scenario]:
        observable = {r: o for r in RIDES
                      if (o := _observable(snapshot, r, now)) is not None and o.value >= 0}
        distances = []
        for date in self.train_dates:
            terms = []
            for ride, current in observable.items():
                stream = self.by_ride[ride][date]
                obs = stream.asof(now) if stream is not None and now < 1440 else None
                prior = historical(ride, now, self.curves)
                template = obs.value if obs is not None and obs.value >= 0 else prior
                terms.append(((current.value - template) / max(15.0, prior)) ** 2)
            distance = math.fsum(terms) / len(terms) if terms else 0.0
            distances.append((distance, date))
        chosen = sorted(distances)[:self.k]
        return [Scenario(date, {r: self.by_ride[r][date] for r in RIDES},
                         self.curves, now, snapshot, distance)
                for distance, date in chosen]


def simulate_dynamic(order: Sequence[str], location: str, now: float,
                     scenario: Scenario, config: Config, predictor: Predictor,
                     trace: list[dict] | None = None) -> float:
    """Execute first action, then D0 after each model completion.

    A continuation receives scenario.snapshot(finish), never scenario itself.
    This allows recourse without choosing an entire route with future knowledge.
    """
    remaining = tuple(order)
    while remaining:
        ride, remaining = remaining[0], remaining[1:]
        arrival = now + config.walk[location][ride]
        wait = scenario.wait(ride, arrival)
        if not math.isfinite(wait):
            return math.inf
        finish = arrival + wait + config.service[ride]
        if trace is not None:
            trace.append({"ride": ride, "depart": now, "arrival": arrival,
                          "wait": wait, "finish": finish})
        now, location = finish, ride
        if remaining:
            remaining, _ = base_order(remaining, location, now,
                                      scenario.snapshot(now), config, predictor)
    return now


def _open_loop_finish(order: Sequence[str], location: str, now: float,
                      scenario: Scenario, config: Config) -> float:
    for ride in order:
        arrival = now + config.walk[location][ride]
        wait = scenario.wait(ride, arrival)
        if not math.isfinite(wait):
            return math.inf
        now = arrival + wait + config.service[ride]
        location = ride
    return now


def _mean_elapsed(finishes: Sequence[float], now: float) -> float:
    # Failed samples cannot be dropped.  One nonfinite result rejects the action.
    if not finishes or any(not math.isfinite(value) for value in finishes):
        return math.inf
    return math.fsum(value - now for value in finishes) / len(finishes)


def plan(policy: str, incumbent: Sequence[str], location: str, now: float,
         snapshot: Snapshot, config: Config, predictor: Predictor,
         bank: ScenarioBank | None = None) -> tuple[tuple[str, ...], dict]:
    if policy not in {"fixed", "dynamic", "rollout", "scenario_open_loop"}:
        raise ValueError(f"Unknown policy: {policy}")
    incumbent = tuple(incumbent)
    meta: dict = {"policy": policy, "predicted_costs": {}, "scenario_ids": [],
                  "fallback": False, "fallback_reason": None,
                  "predicted_cost_unit": "remaining_minutes"}
    if not incumbent:
        meta.update(chosen_next=None, base_next=None)
        return incumbent, meta
    if policy == "fixed":
        meta.update(chosen_next=incumbent[0], base_next=incumbent[0])
        return incumbent, meta
    base, base_finish = base_order(incumbent, location, now, snapshot, config, predictor)
    meta.update(base_next=base[0], chosen_next=base[0], base_predicted_finish=base_finish)
    if policy == "dynamic":
        return base, meta
    scenarios = bank.select(now, snapshot) if bank is not None else []
    meta.update(scenario_ids=[s.date for s in scenarios],
                scenario_distances={s.date: s.distance for s in scenarios},
                scenario_model={"template": "whole_training_day_all_rides",
                    "historical_missing_and_future_closures": "training_curve_imputation",
                    "forecast_future_closures": False, "snapshot_grid_minutes": GRID,
                    "current_closure_expiry": "original_observation_plus_15_minutes",
                    "beyond_midnight": "training_curve_tail",
                    "closing_deadline_in_model": None,
                    "aggregation": "uniform_mean_no_failed_sample_dropping"})
    if not scenarios:
        meta.update(fallback=True, fallback_reason="no_training_scenarios")
        return base, meta
    actions = [r for r in sorted(base)
               if math.isfinite(predictor.predict(r, now + config.walk[location][r],
                                                  now, snapshot))]
    costs = {ride: math.inf for ride in base}
    best_orders: dict[str, tuple[str, ...]] = {}
    if policy == "rollout":
        for action in actions:
            forced_order = (action,) + tuple(r for r in base if r != action)
            finishes = [simulate_dynamic(forced_order, location, now, s, config, predictor)
                        for s in scenarios]
            costs[action] = _mean_elapsed(finishes, now)
    else:
        # One shared full order per comparison, NOT a per-scenario optimal order.
        for order in itertools.permutations(sorted(base)):
            if order[0] not in actions:
                continue
            finishes = [_open_loop_finish(order, location, now, s, config) for s in scenarios]
            cost = _mean_elapsed(finishes, now)
            if cost < costs[order[0]] - EPS:
                costs[order[0]], best_orders[order[0]] = cost, order
    meta["predicted_costs"] = costs
    meta["scenario_query_audit"] = {s.date: dict(s.audit) for s in scenarios}
    finite = [a for a in actions if math.isfinite(costs[a])]
    if not finite:
        meta.update(fallback=True, fallback_reason="all_actions_unsupported")
        return base, meta
    best_cost = min(costs[a] for a in finite)
    tied = [a for a in finite if abs(costs[a] - best_cost) <= EPS]
    chosen = base[0] if base[0] in tied else min(tied)
    meta["chosen_next"] = chosen
    if policy == "scenario_open_loop":
        meta["shared_best_order"] = list(best_orders[chosen])
    # Only the first action is committed.  Keep the D0 tail as the incumbent for
    # the next real decision, exactly as in the rollout simulations.
    return (chosen,) + tuple(r for r in base if r != chosen), meta
