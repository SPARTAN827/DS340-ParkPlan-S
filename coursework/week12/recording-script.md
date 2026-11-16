# Week 12: Modified Implementation

Prepared for a real two-person recording; not evidence that recording or team agreement occurred.

About 5-6 minutes including a live run. This is a rehearsal estimate; the assignment states no video-length limit.

Roles below are suggested. Both students must understand, rehearse and perform their own parts. Read only spoken paragraphs. Screen notes are not spoken.

## Jesse Zhang | 0:00-0:40 | Our question and parent-paper connection

Screen action (not spoken): Show the team repository, then the paper's Contribution subsection. The Week 11 drone results and Week 12 park results are separate experiments.

Hi, I'm Jesse, and this is Yongqi. ParkPlan-S asks whether changing the remaining ride order can reduce the time needed to finish six rides in Animal Kingdom. Our parent paper, ADAPT, updates a drone's route when new information arrives. We borrow that repeated-decision idea. Our park implementation uses different predictions, data, and route-scoring methods. We are not claiming that the drone algorithm was directly transferred into the park.

## Jesse Zhang | 0:40-1:30 | What we changed

Screen action (not spoken): Show engine.py and the comparison table and Contribution subsection in the revised paper. Point to D0, C, R and S.

The existing dynamic method, D-zero, already considers arrival times and searches every remaining ride order. We tested three changes around it. C changes how quickly a current waiting-time observation loses influence. R tests each possible next ride across eight historical-day scenarios. Within each scenario, it lets D-zero make later decisions using information available at that simulated time. S uses the same scenarios but scores one shared remaining order. Comparing R with S helps us examine whether modeling later feedback is useful. All methods start with the same initial order and first ride.

## Jesse Zhang | 1:30-2:30 | Fresh execution

Screen action (not spoken): Run the exact command in DEMO-AND-SUBMISSION.md. Wait for all five policies. Show the new output folder, completion/failure reasons and verification. Keep any genuine failures visible.

This command runs all five methods on the first date of our evaluation period. We chose the date by its position in the calendar, not because a particular method wins. The program uses the pinned historical data and writes new output. This is a one-date demonstration, separate from the saved comparison across one hundred sixty-five dates. A failed trip means that the replay could not finish under its stated rules. It must stay in the results. The actual terminal output shows what happened in this run.

## Yongqi Sheng | 2:30-3:25 | Comparison results

Screen action (not spoken): Show the paper's comparison table, including the paired sample sizes, block intervals and completion counts.

I'm Yongqi. The saved study does not establish an improvement over D-zero. On the one hundred eighteen dates when both methods completed all six rides, rollout took about six point three six minutes longer on average. Time saved means D-zero minus rollout, so positive values favor rollout. Its uncertainty interval runs from minus thirteen point seven three to plus zero point three six minutes. Rollout completed one hundred twenty-eight of one hundred sixty-five dates, compared with one hundred twenty-six for D-zero. Those successes occur on partly different dates, so we cannot call the small completion difference a time-saving result.

## Yongqi Sheng | 3:25-4:10 | Other techniques and interpretation

Screen action (not spoken): Point to C and S rows, then F versus D0. Do not compare averages from different paired subsets as if they used identical dates.

Calibration looked promising on validation data, but its advantage did not carry over. It was about two point eight two minutes slower than D-zero on their shared successful dates. The shared-order control was about one point three six minutes slower. Their intervals also include zero. The existing dynamic method did beat the fixed plan by about fifteen point four eight minutes on their shared successful dates. That result belongs to the existing baseline. It is not evidence that our new rollout method improved it.

## Yongqi Sheng | 4:10-5:10 | Limits and next step

Screen action (not spoken): Show limitations, reproducibility commands and repository commit. Confirm both speakers have finished; upload and test actual Kaltura access afterward.

These are modeled trip times using posted waits, not measured visitor journeys. Walking and ride-service inputs are assumed, and the evaluation dates had already been examined in earlier work. The six input settings reuse the same waiting-time records; they are not six independent datasets. Our contribution is the implemented comparison and its evidence, including the negative result. We keep D-zero as the working comparator. A next study should improve the prediction of which next ride actually saves time and test a frozen method on genuinely unused dates. The repository includes the code, saved comparisons, and instructions for checking them.
