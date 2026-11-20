[The studies](../README.md) › Study 21 · Pinch at new targets

# At a new pinch target, a one-line rule beat the fitted model for all four people

The five-grid model of [study 19](../cemhsey-arrays/README.md) learned a two-finger pinch at 30% of the hardest squeeze. Here four people followed targets of 10%, 30% and 50% on a screen while a gauge recorded the force between their fingers. At 50%, the rule "take the current reading and add the change the on-screen schedule calls for" forecast the gauge 120 ms ahead with an average miss of **0.5721%**, the lowest of the nine forecasts. The fitted five-grid model, given one practice pinch, missed by **0.6987%**: 0.1266% worse, and worse for all four people, by 0.0502% to 0.1938%.

Every error here is the plain average miss (mean absolute error) over the whole trial, in % of the person's hardest squeeze that day (their maximum voluntary contraction, MVC), with the four people counting equally. The forearm signal is surface EMG, electrical activity of muscle picked up on the skin.

The cue did help the five-grid model itself. Adjusting its fixed forecast for the stronger target lowered its average miss by 0.0485%, and all four people gained. Learning one more weight from the practice pinch changed the average by only 0.0008%: two people gained and two lost, because timing mattered. Practice lowered the error by 0.0779% during the rise and raised it by 0.0737% during the release, in every person both times.

Average miss over the whole trial, in % of the hardest squeeze:

| Target | Current force plus scheduled change | Force history, adjusted | Force history, after practice | Five grids, adjusted | Five grids, after practice |
|---|---:|---:|---:|---:|---:|
| 10% | 0.3693 | 0.5639 | 0.5635 | 0.5737 | 0.5734 |
| 30% | 0.4480 | 0.4265 | 0.4274 | 0.4299 | 0.4306 |
| 50% | 0.5721 | 0.7095 | 0.7085 | 0.6995 | 0.6987 |

At 10% the one-line rule also beat the adjusted and practised models for all four people. At 30%, the level the model was fitted at, the target adjustment is zero by construction, and the fit on force history and cue stage beat the one-line rule. The model was not broken; it had learned one target.

## What was done

The fitted model stayed fixed. The first comparison let it use the change the cue would ask for over the next 24 force samples; the second gave it one practice repeat to learn how much that change should move the forecast. Every method then faced the same second repeat at each target. Four people gave one recording day each; none of them was in the original fit, though earlier studies had used other days from the same four. Each target gave four second repeats and 2,368 overlapping forecasts. The repeats came from one recording day per person, always after the practice pinch.

## What it does not show

Performance can change with the prescribed force, with the second attempt, or with the way a person follows the cue, and here they changed together. What would happen on another day, in another order or with another group is open. No group was set aside for this study.

## The plan

The plan fixed the average miss at the 50% target as the main result, the 10% target as its companion and 30% as a check; it set no pass rule. It uses the phrase "absolute mean error" once: the measure intended, the measure computed and the measure checked independently were all the mean absolute error, the average gap between forecast and gauge. [The plan and its comparisons](PROTOCOL.md) · [Study design](DESIGN.json) · [Original recording study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12354741/)

[Explore the measured results](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/results/) · [Compare two recordings on your computer](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/) · [Download the offline reader](../../docs/cemhsey-transfer/CEMHSEY-Pinch-Transfer.zip) · [Results file](RESULTS.json)

The next study brings the same saved corrections back on a new recording day: [Study 22 · Pinch, next day](../cemhsey-carry/README.md).
