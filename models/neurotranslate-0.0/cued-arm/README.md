# What does an arm instruction tell us about the next movement?

One seated participant saw a cue to perform one of six actions with the supported right arm, or to rest. A sensor in the support followed the elbow, a second followed forearm rotation, and a glove followed the base of the index finger. This model predicts how each reading changes half a second, one second and one and a half seconds after its last input. The reader accepts a short list of phrases for the seven study categories. [Try an instruction](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#cued-arm)

## The cue alone gave the closest average forecast

We used three runs of 42 trials from the same person. Each run took a turn as the test run. The model fitted on the other two runs never saw the target readings from that test run. All 126 trials were eligible. To compare instruments that use different scales, we divided each error by the variation in that instrument's target in the two fitting runs. A smaller number means the model placed the future reading closer to the measurement. Each of the seven tasks and each run counts equally.

| What supplied the forecast? | Average scaled error |
| --- | ---: |
| No change from the last reading | 0.556 |
| Action cue only | **0.525** |
| Earlier mechanical readings, linear fit | 0.717 |
| Action cue and mechanical readings, linear fit | 0.607 |
| Earlier mechanical readings, shared movement encoder | 0.751 |
| Action cue and readings, shared movement encoder | 0.641 |
| Same cue and readings, shuffled encoder weights | 0.632 |

The shared encoder’s error fell in all three runs when it received the correct cue. The average reduction was 14.7% compared with withholding the cue and 21.0% compared with giving it incorrect task labels on those same histories. That met the study’s test for useful cue information. Reusing the trained encoder gave higher average error than both the simpler cue-and-motion fit and the control that shuffled the encoder weights. The test for an encoder advantage failed. The cue-only model had the lowest average across the three runs; keeping the last reading was closer in run one. The pooled evidence covers one participant. [Per-run, per-task and native-scale results](results.json) · [Prespecified comparisons](PROTOCOL.md)

## Use your own four bins

With Python and NumPy installed, open the parent model folder and run:

```sh
python predict.py cued-arm/example.json
```

The example uses invented sensor bins around rounded training averages. It returns three signed changes for each of three future times. The order in each row is elbow, forearm rotation, then index finger. The starting readings come from the last bin. The files do not establish a physical unit or anatomical sign convention for these channels. A predicted change of +6 in the elbow sensor cannot be read as six degrees of flexion.

Enter one of the seven canonical labels for methods that use the cue: `elbow flexion`, `elbow extension`, `supination`, `pronation`, `hand close`, `hand open` or `rest`. The web reader also recognizes the listed everyday phrases, such as “bend my right elbow.” The record identifies the investigator’s cue category. Verbatim words displayed or spoken to the participant are unavailable.

For the motion methods, supply four bins ending a quarter second after the cue. Each bin covers eight readings at 64 Hz. Its first three numbers are the three sensor medians. The next three numbers are the median of the last four readings minus the median of the first four, for the same sensors. `cue` needs only the cue, `motion` and `shared_motion` need only bins, and `still` needs neither. `cue_motion`, `shared_cue_motion` and `shuffled_cue_motion` need both. [Expected outputs for the invented example](example-results.json)

## Reproduce the study

The code uses the 2017 release from Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz. Use the previous shared model for the frozen encoder and the supplied source reader for the three original GDF files. The reader checks complete file hashes and the channels before allowing analysis. No imagery data or other participants are needed. Python 3.12, NumPy 2.5.5 and one OpenBLAS thread were used for the reference run. The prediction method uses the native input clocks without a resampling step. Display-to-sensor delay and physical synchronization remain unmeasured. [Data release](https://doi.org/10.5281/zenodo.834976) · [Acquisition paper](https://doi.org/10.1371/journal.pone.0182578) · [Parent checkpoint](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/c41fcf3b8763a403db9305fe0877a95b64e014ef/models/neurotranslate-0.0/movement-weights.npz)

```sh
python cued-arm/ofner_source.py fetch path/to/source-cache
python cued-arm/study.py path/to/source-cache previous-weights.npz reproduced-weights.npz reproduced-results.json
```

The data-derived coefficients and numerical results retain the source CC BY 4.0 attribution. This reanalysis selects the three execution runs, computes time bins, fits new readouts and compares the forecasts with observed values. Credit the authors and identify further changes. The project supplies its original code and invented example under CC0. [Authors, channel map and original data](SOURCE.md) · [Data licence](CC-BY-4.0.txt) · [Original project code dedication](../LICENSE)
