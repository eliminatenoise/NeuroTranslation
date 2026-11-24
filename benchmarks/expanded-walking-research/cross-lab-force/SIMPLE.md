# Predicting the force on a treadmill belt

A follow-up tests whether training a small force forecast on recordings from a second lab helps. [One-lab and two-lab comparison](source-mix/SIMPLE.md)

In this earlier comparison, a simple rule that continues the recent rise or fall in force made the closest force predictions. Its average miss was **9.64 newton-seconds**. The best NeuroTranslate setting missed by **10.69 newton-seconds**. NeuroTranslate did slightly better on a different question, the chance that a belt would start taking a new load. One pass through the model had the lowest error for that prediction. [Exact scores](results.json) · [Technical edition](TECHNICAL.md)

## What we measured

Each belt in the study had a force plate underneath it. The two plates measured how hard the belts pushed upward, 1,000 times a second. Each measurement belongs to a belt. We used eight people walking at the study’s published speed of 4 km/h. For this test we used the early recordings, before the study applied its force filter. [Study, Tables 1 and 2](https://doi.org/10.1038/s41597-026-07445-3) · [Archive](https://doi.org/10.17605/OSF.IO/KCQTF)

We used the three-minute section of the trial that begins after the warm-up and pause. We picked 24 moments per person, one in each of 24 seven-second intervals. A fixed calculation using the archive labels and interval numbers chose the moments before we looked at the later readings. At each moment, we predicted what both belts would measure. That gave each method 192 prediction times and 384 belt forecasts. [Exact schedule](results.json)

For each belt, the model received the preceding fifth of a second in ten groups of 20 readings. It saw the average force in each group. The test supplied no muscle voltage readings. The earlier training recordings had both force and muscle voltage. We used the same model saved after 547 training updates. The middle 12 layers repeated their calculations one, three, five, seven or nine times. The values learned during training stayed fixed. [Training recordings](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Checkpoint](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)

We also used three simple rules. The first carries the latest force average forward. The second looks at the latest two averages and continues the force at the same rate of rise or fall. Both use the frequency of new loads in the training recordings as their estimate of the chance of one happening. The third keeps force steady and gives a new load zero chance. All predictions were saved before we requested the later readings. At shutdown the monitor missed a reading after the prediction files had been saved. An independent check confirmed that the worker exited normally and that the files contained every prediction.

## How we compared the forecasts

The first forecast adds the upward force measured over the next tenth of a second. This total is called *impulse*. A belt pushing upward at 300 newtons for one tenth of a second produces 30 newton-seconds. We keep the direction of the measured force and average the size of each forecast’s miss.

The second forecast gives the chance of a new load starting during that same tenth of a second. A belt counts as quiet after 20 readings within 10 newtons of zero. A new load begins when the force reaches 20 newtons and stays at or above that level for 20 readings. We use a full second of earlier force to establish the previous state. The model still sees only the last fifth of a second. If a load starts within the forecast window, readings through 119 milliseconds can confirm it.

For the probability score, we compare the predicted chance with zero if no new load starts and one if it does. We square the difference. A smaller score means the chances were closer to what happened. We could score force on all 384 belt forecasts. For new loading, we left out 71 cases where the earlier readings did not establish the belt’s state and ten where a rise in force was still awaiting confirmation. The remaining 303 included 22 different loading events and 281 cases without a new load. Every method used the same eligible rows, and each person received equal weight.

| Method | Average impulse miss (N·s) | New-load probability error |
| --- | ---: | ---: |
| Keep force steady and use the training rate | 11.18824 | 0.07075751 |
| Continue the force trend and use the training rate | **9.64445** | 0.07075751 |
| Keep force steady and predict no new load | 11.18824 | 0.07495471 |
| NeuroTranslate, 1 pass | 11.00871 | **0.06997673** |
| NeuroTranslate, 3 passes | 10.69183 | 0.07072176 |
| NeuroTranslate, 5 passes | 10.85810 | 0.07177581 |
| NeuroTranslate, 7 passes | 10.75955 | 0.07165146 |
| NeuroTranslate, 9 passes | 10.72045 | 0.07155924 |

Three passes improved on the steady-force rule for six of the eight people and beat the trend rule for two. When we limited the force comparison to the 303 rows where both predictions could be checked, the trend rule still led at 9.31074 newton-seconds. Nine passes was the best model setting on those rows at 10.28250. One pass stayed first on the loading prediction and beat the training-rate rule for all eight people. The average probability score fell by 0.00078, a small change on a scale from zero to one.

These results apply to a tenth of a second of walking at one speed with recent measured belt force available. We used the existing model and kept the separately reserved final test sealed. [Earlier comparison with force and muscle readings](../pass-count/SIMPLE.md)
