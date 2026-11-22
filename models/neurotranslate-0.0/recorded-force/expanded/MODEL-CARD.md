# Model card for the NeuroTranslate 0.0 force-plate preview

Release `0.0.0-expanded-force-preview.1` contains two small numerical models and an offline program that runs both. They use 200 milliseconds of recorded muscle voltage and force to estimate the next 100 milliseconds on one instrumented plate. The first output estimates the chance of a new load. The second estimates signed vertical impulse, the accumulated force over that time. Start with the [example and setup instructions](README.md).

## Results on the fitting recordings

These results replay 1,728 forecast cases from 36 walks by 12 people. The models were already fit on these people and walks. Nearby forecast windows overlap. The replay shows what the models did on this material and leaves performance on new people open.

| Method | New-load Brier score | Signed impulse mean absolute error |
| --- | ---: | ---: |
| Extend the last force reading | 0.03472 | 3.42 N·s |
| Earlier NeuroTranslate 0.0, six training updates | 0.25312 | 11.30 N·s |
| Expanded, attention core kept fixed | 0.03329 | 10.81 N·s |
| Expanded, attention core also trained | 0.03296 | 10.20 N·s |

Lower values are better. The Brier score is the mean squared difference between a predicted probability and the recorded outcome, scored as either 0 or 1. Mean absolute error measures how far the predicted impulse was from the recorded impulse in newton-seconds. The simple force control extends the last 20 ms force average for the next 100 ms and predicts no new load.

All four methods had the same 1,647 cases for the load event and the same 1,728 cases for impulse. The load cases include 58 positive windows around 25 distinct crossings. Scores average plates within a forecast time, times within a walk, walks within a person, then people equally. When impulse is scored only on the 1,647 cases that also have an event label, the four impulse errors in table order are 3.44, 11.34, 10.83 and 10.20 N·s.

## How the checkpoints were trained

The first checkpoint keeps the starting attention core fixed and trains 546 input and output parameters for the force task. The second also trains the attention core, for 9,122 trainable parameters. The two start from the same weights and use the same data, input scaling and loss. Each receives 48 AdamW updates at a learning rate of 0.001. Each update uses all fitting cases and gives the two prediction targets equal weight. Fitting used 9,586 eligible plate windows, including 9,150 with a load label. Loss weighting keeps each person equally represented on each endpoint and retains the recorded balance of positive and negative labels. The two saved checkpoints each cover this one force task.

## What was measured

Surface electromyography, or EMG, records voltage at the skin over a muscle. This experiment uses six named channels recorded at 1,000 samples per second. Each history ends at the last available sample and uses ten consecutive 20-sample summaries of voltage magnitude and calibrated signed vertical force. The forecast concerns the following 100 samples on the same plate.

A plate must first record 20 samples between −10 and +10 newtons to count as unloaded. New loading begins at a rising crossing of +20 newtons that is followed by 19 more samples at or above that force. The future event label can therefore require samples past the forecast horizon to verify a late crossing. The impulse target sums the signed force of the next 100 samples and multiplies by 0.001 seconds. The model receives the earlier history only.

The recordings came from healthy adults walking on a single instrumented walkway. The analysis used two calibrated plates. The forecasts describe those plates and cannot identify steps on other parts of the walkway, determine what an individual muscle contributed, or establish timing on a live sensor system. This release is for offline research.

## Sources and reuse

Tamaya Van Criekinge, Wim Saeys, Steven Truijen, Luc Vereeck, Lizeth H. Sloot and Ann Hallemans collected and published the walking recordings. This experiment used the healthy walking files from the first Figshare release under CC0. NeuroTranslate reduced the original voltages and calibrated vertical force to timed bins, fit two checkpoints and calculated the aggregate comparison. [Versioned dataset](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Acquisition paper](https://doi.org/10.1038/s41597-023-02767-y)

The code, original documentation, invented inputs and their example outputs use the included [CC0 dedication](LICENSE). The starting shared core came from the published NeuroTranslate joint alpha model. Retain its data and licence notices with reusable copies of the weights, and identify any further changes. [Inherited source credits](INHERITED-CREDITS.md) · [Original joint alpha release](https://github.com/eliminatenoise/NeuroTranslation/tree/8d79659461244952789d074c4f50382a4bf43060/models/neurotranslate-0.0/joint_alpha)
