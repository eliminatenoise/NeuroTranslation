# The elbow after the cue

A visual cue asks a seated person to bend or straighten the supported right elbow. At a quarter of a second after the cue, the model has an instruction and four short snapshots of recent sensor activity. Can it predict how much the elbow sensor will change during the next three quarters of a second?

Extract the whole ZIP, then open **index.html** or the launcher for your operating system. The interactive experiment runs directly in your browser, including offline. On a system that restricts downloaded scripts, opening index.html uses the same reader.

1. Select **Bend** or **Straighten**. These are the two task classes in the source codebook. The wording here describes them in everyday English.
2. Try **Cue + elbow history**, then **Cue + elbow + scalp**. The diamond gives a single future sensor reading. The large signed figure gives the change from the last early reading. The model predicts no intervening path.
3. Open **Edit sensor readings** to change the four invented bins. **Add an invented later reading** lets you score the result yourself. That later reading is withheld from all forecasts. Inputs far from the training examples can produce implausible outputs.
4. Under **Did scalp activity help?**, compare the same methods on recorded trials. Switch between the two cue groups to see what the overall mean hides.

## What the recorded comparison found

Six bend cues and six straighten cues appeared in each of three execution runs from participant S1. On each rotation the model fitted two whole runs (24 trials) and predicted the remaining run (12 trials). Every run was held once. The final interactive coefficients use all 36 trials. The error table comes from the separate three rotations. One bend trial in run 1 was already known from an earlier source check before the forecast protocol was fixed. The shared participant and small trial count limit generalization.

Adding scalp electrode C3 to the cue and recent elbow history raised the balanced mean absolute error from 0.07237 to 0.07859 native sensor units. Error fell in one of three runs and neither cue group. Giving the fitted C3 model scalp input from another trial with the same cue yielded 0.07780. Replacing the scalp features with eye-channel features yielded 0.09082. The protocol required an improvement against all three controls, both cue groups and at least two runs.

The exploratory attention calculation had a lower aggregate error (0.07122) and a higher error than cue plus elbow history on the flexion trials. It uses a fixed rule to pool four scalp summaries before fitting a linear output. It had no attention-specific pairing or eye replacement control. Twenty-five of 36 observed changes were at most 0.1 native units in magnitude. Seventeen changes had a sign opposite to the median for their cue in the two training runs. A cue tells us which movement was requested. Sensor measurements tell us how the supported elbow responded.

## How the reading was built

The recording clock counts 512 ticks per second. Take the cue tick as zero. The last permitted input is at +128 ticks. Scalp (C3) and eye (EOG) summaries each use four chronological means of 64 readings, covering ticks −127 through +128. Eye summaries average channels 62, 63 and 64. The outer two eye labels disagree in order between the header and the codebook. Symmetric averaging avoids assigning laterality and can cancel activity of opposite polarity. Signal amplitudes remain on the stored scale.

The elbow sensor has 64 readings per second. At each threshold take the last sample on or before that tick. Split the 32 elbow readings through the cutoff into four chronological groups of eight and take their medians. The chart places each median at its nominal bin end. The last elbow sample can precede that threshold by up to seven EEG ticks. Subtract the last early median from the median of the eight most recent readings at +512 ticks. A positive difference means the stored value rose. These numbers have no verified conversion to anatomical angle or displacement in space.

The regression uses the cue code, final elbow median and three successive changes. The C3 and EOG regressions each add three respective signal changes relative to the first bin. Each fold learns means, scales, coefficients, cue medians and attention scale from its two training runs. Ridge regression uses a fixed penalty of 6. The swapped control substitutes the following trial's four scalp means within the same held-out run and cue group, wrapping at the last trial. This offline control needs another trial and is available only in the recorded-run results. The experiment contains no participant trace or trial-level predictions. This design gives no spatial brain map, direct muscle or nerve measurement, causal decoding of intent, or validation on a new participant. [Frozen protocol](method/protocol.json) · [Aggregate scores](method/scores.json)

## Reproduce

Python 3.10+ with the standard library handles the browser build and example forecast. From the extracted elbow-cue folder:

```sh
python build.py --zip ../elbow-cue-offline.zip
python method/check_example.py
python method/infer.py --input method/example.json --method cue_mechanics_c3
```

The page embeds the fitted weights and aggregate results so no network request supplies a forecast. The build packs an explicit inventory with fixed timestamps and executable bits for macOS and Linux. SHA256SUMS identifies every member apart from the checksum list itself.

To refit, install NumPy in a suitable Python 3.10+ environment and obtain the three source files from Zenodo. The included reader can fetch roughly 270 MB into a directory you select. Keep source recordings outside the distributed experiment. The fit writes new aggregate output into a separate directory.

```sh
python method/ofner_source.py fetch ../ofner-cache
python method/ofner_source.py verify ../ofner-cache
python method/fit.py --cache ../ofner-cache --out ../elbow-refit
```

Compare the refit model and score files with the originals in method/. The hashes bind the shipped scientific material. Different numerical libraries can differ in their last digits. Match all labels and counts exactly and numerical leaves within an absolute and relative tolerance of 1e-10. [Original recordings and codebook](https://doi.org/10.5281/zenodo.834976) · [Acquisition paper](https://doi.org/10.1371/journal.pone.0182578) · [Authors, modifications and licence](NOTICE.md)
