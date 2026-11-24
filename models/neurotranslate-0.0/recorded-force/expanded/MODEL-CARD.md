# NeuroTranslate 0.0 past-load gate

Version `0.0.0-past-load-gate-preview.1` uses the last 200 milliseconds of six muscle voltage signals and the vertical force on one plate during a walk. It predicts the chance that the plate starts carrying load in the next 100 milliseconds. It also estimates signed vertical impulse, the force integrated over that time, in newton-seconds (N·s).

Try the two gated checkpoints with invented inputs using `python predict.py --model past-load-gate --check-example`. The results below come from recordings used to fit the models. [Setup guide](README.md) · [Scores and group totals](comparison.json)

## How the models compared on fitting data

The replay covers 1,728 plate forecasts from 36 walks by 12 people. The same people and walks supplied fitting data, and nearby windows overlap. Every method uses the same cases for each score. There are 1,647 scoreable load-event windows, including 58 positives around 25 distinct new loads. All 1,728 cases have a measured impulse.

| Method | New-load Brier score | Signed impulse mean absolute error |
| --- | ---: | ---: |
| Extend the latest force reading | 0.03472 | 3.422 N·s |
| Earlier NeuroTranslate 0.0 with six updates | 0.25312 | 11.297 N·s |
| Expanded model with the attention core fixed | 0.03329 | 10.810 N·s |
| Expanded model with the attention core trained | 0.03296 | 10.202 N·s |
| Ungated force reference with the attention core fixed | 0.03318 | 3.471 N·s |
| Ungated force reference with the attention core trained | 0.03286 | 3.418 N·s |
| Past-load gate with the attention core fixed | 0.03296 | 3.373 N·s |
| Past-load gate with the attention core trained | 0.03301 | 3.042 N·s |

Lower scores are better. The Brier score averages the squared differences between the forecast probabilities and the recorded outcomes, coded as 0 or 1. The latest-force baseline forecasts no new load and extends the latest force reading over the whole interval. The impulse score averages the absolute differences in newton-seconds. To give every person equal weight, scores average plates at a given forecast time, times in a walk, and walks by each person before averaging across people. The Brier values describe this replay. They provide no test of statistical significance or of how well probabilities match event rates on new walkers.

The trainable-core gate reduced overall impulse error. The effect depended on whether the plate was already carrying load.

- **Already loaded at the forecast time, with no new load recorded.** Average impulse error was **11.947 N·s** for the trainable-core ungated force-reference model and **10.049 N·s** for the trainable-core gate.
- **Unloaded at the forecast time, with no new load recorded.** Average impulse error was **0.133 N·s** for the trainable-core ungated force-reference model and **0.229 N·s** for the trainable-core gate. Simply extending the last force reading scored **0.045 N·s**. This group carries 69.6% of the overall impulse score weight.

The gate was designed after inspecting these fitting recordings. Performance on people outside this group remains unmeasured.

## How the gate changes the forecast

1. Extend the most recent available 20-millisecond mean force for one tenth of a second.
2. Estimate a correction to that starting impulse. When the past mean force is at least +20 newtons, apply the whole correction. At a lower force, multiply the correction by the model's estimated probability of a new load.
3. If every past force reading is missing, leave impulse unavailable. With at least one muscle measurement available, the model still estimates the chance of a new load.

The +20 newton cutoff is a rule based on the last available force mean. In the recorded scoring, a load event has its own definition and uses multiple consecutive future readings. These future readings are used only when assigning labels for scoring.

Both gated checkpoints start with the same attention weights and use the same fitting data, input scales and 48 updates. The version that keeps its attention core fixed trains 546 parameters. The version that updates it trains 9,122. Of the 9,586 plate histories used in training, 9,150 had a new-load label. The impulse training objective sends no direct gradient through the gate to the probability output. Both forecasts share internal features, so changes to those features can still affect the probability.

## What was recorded

Surface electromyography (EMG) records voltage at the skin over a muscle. This experiment uses six named EMG channels and calibrated vertical force from plates 1 and 2 on one laboratory walkway. Each input history contains ten groups of 20 samples at 1,000 samples per second. The replay measured complete histories. The missing-input example demonstrates only what the program returns when a value is absent.

In the recordings, the plate counts as unloaded after 20 samples between −10 and +10 newtons. New load starts at a rising crossing of +20 newtons when the next 19 samples also stay at or above that force. The forecast covers the 100 samples immediately after the last input sample. The impulse label sums signed vertical force over those 100 samples and multiplies by 0.001 seconds. Checking a late new-load event can require additional measured samples after the forecast interval.

Tamaya Van Criekinge, Wim Saeys, Steven Truijen, Luc Vereeck, Lizeth H. Sloot and Ann Hallemans supplied the walking recordings. The fitting and replay use healthy walking files from the first Figshare release, covered by CC0. NeuroTranslate converted original voltages and calibrated forces to timed summaries, fitted the models, and calculated the aggregate scores. [Versioned dataset](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Acquisition paper](https://doi.org/10.1038/s41597-023-02767-y)

The code, original documentation and invented example use the included [CC0 dedication](LICENSE). The saved weights inherit source terms from the starting attention core. Carry the applicable credits and license notices with reused weights, and describe any further changes. [Inherited source credits](INHERITED-CREDITS.md)
