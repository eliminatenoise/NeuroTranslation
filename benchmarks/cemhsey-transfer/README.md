# Changing the pinch target

The original forearm model learned a two-finger pinch at 30% of maximum voluntary contraction. Here the participants saw 10%, 30% or 50% on the screen. Their task was to follow that target while a gauge recorded the force between the opposing fingers.

We keep the trained point model fixed. The first comparison lets it use the change the cue will ask for during the next 24 force samples. The second gives it one practice repeat to estimate how much that change should affect the forecast. All methods then face the same second repeat at each target. Four people contribute one recording day each. Performance can change with the prescribed force, the second attempt, or the way the person follows the cue. [Prespecified methods and comparisons](PROTOCOL.md) · [Study design](DESIGN.json) · [Original recording study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12354741/)

## What changed on the second pinch?

At the 50% target, adding the scheduled change to the current gauge reading gave the lowest whole-trial error of the nine forecasts. Its mean absolute error was 0.5721 percentage points of maximum voluntary contraction (MVC). The five-grid model reached 0.6987 after one practice attempt. The simple forecast beat that model in all four people.

The cue helped the five-grid model itself. Adjusting its frozen forecast for the stronger target reduced mean absolute error by 0.0485 percentage points of MVC. All four people gained. Learning one more coefficient from the practice attempt changed the average by only 0.0008 percentage points. Two people gained and two lost. Timing mattered. Practice reduced error by 0.0779 percentage points during the rise and increased it by 0.0737 during release. Both directions held in every participant.

Whole-trial mean absolute error follows, in percentage points of MVC. Each value gives equal weight to the four participants. The downloadable tables retain fractions of MVC and the full nine-arm comparison.

| Target | Current force + scheduled change | History adjusted | History after practice | Five grids adjusted | Five grids after practice |
|---|---:|---:|---:|---:|---:|
| 10% | 0.3693 | 0.5639 | 0.5635 | 0.5737 | 0.5734 |
| 30% | 0.4480 | 0.4265 | 0.4274 | 0.4299 | 0.4306 |
| 50% | 0.5721 | 0.7095 | 0.7085 | 0.6995 | 0.6987 |

At 10%, current force plus the scheduled change also beat the adjusted and practice-fitted models for all four people. At 30%, the cue adjustment is exactly zero by construction. Force history plus phase performed better there than current force plus cue change. Each target contributed four second repeats and 2,368 overlapping forecast cutoffs. Those repeats came from one indexed day per person, always after practice. The comparison leaves open what would happen on a different day, in a different order or with a new group.

The protocol uses the phrase “absolute mean error” once. The intended metric, the implemented metric and the metric independently reproduced were all mean absolute error, the average absolute difference between forecast and gauge.

[Explore the measured results](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/results/) · [Compare two local recordings](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/) · [Download the offline reader](../../docs/cemhsey-transfer/CEMHSEY-Pinch-Transfer.zip) · [Complete aggregate](RESULTS.json)
