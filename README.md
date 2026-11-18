# ParkPlan-S

*Data: [TouringPlans.com](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes) historical wait times and park hours.*

Does changing the ride order after each stop save time? ParkPlan-S replays 165 days at Disney’s Animal Kingdom. Five planners start with the same six rides in the same order. One sticks to that order; the other four can change the remaining route after a ride ends.

[Study results](experiments/algorithm_study_20261019/REPORT.md) · [Run the demo](experiments/week12_demo_20261115/README.md) · [Reproduce the full study](RUNNING.md)

## Results

| Comparison | Days both plans finished | Average difference in trip time |
|---|---:|---|
| Basic replanning vs. fixed order | 105 | Replanning was 15.48 minutes faster. |
| Eight-scenario rollout vs. basic replanning | 118 | Rollout was 6.36 minutes slower. |

Across all 165 days, the fixed plan finished all six rides on 120 days, the basic replanner on 126, and rollout on 128. The two rows cover different sets of days. The uncertainty interval for rollout includes zero, so we found no clear time advantage over basic replanning. These are simulated trip times based on posted waits and assumed walking and ride times, not times measured from visitors.

## Try it

From the repository root, use Python 3.10 or later. The planner needs no third-party packages. To run the engine tests without downloading data:

```bash
python3 -m unittest discover -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

For a one-day replay, follow the [demo instructions](experiments/week12_demo_20261115/README.md) to download the [exact data version](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes/tree/933161b8bebb7cd50e0d54bcb3578484875487fa). To inspect results without running code, open the [daily results](experiments/algorithm_study_20261019/evaluation/per_day.csv) or the [full comparison](experiments/algorithm_study_20261019/REPORT.md).

## Project files

- [Planner and experiments](experiments/algorithm_study_20261019/) — the five route-planning methods, tests, and saved results.
- [Park inputs](data/verified_inputs/) — historical park hours and sources for the walking and ride-time assumptions.
- [Reproduction scripts](scripts/) — rerun the comparisons or check saved results against the source data.
- [ADAPT reproduction](reproduction/week11/) — a separate experiment with a routing paper that informed the project. The park planner does not run the drone software.

Jesse Zhang and Yongqi Sheng developed ParkPlan-S for DS 340W. AI tools assisted with code, editing, and checks.

## Data-use terms

You're free to use these data however you see fit, subject to the following:

1. Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.
2. Any redistributions include these license terms.

See [sources and licenses](experiments/algorithm_study_20261019/SOURCES-AND-LICENSE.md) for details.
