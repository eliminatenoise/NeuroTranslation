# From one person's arm to another

Give the model the instruction shown to a seated person, together with four short measurements from their right arm. It forecasts changes at three instruments: an elbow sensor, a forearm rotation sensor and a glove sensor near the base of the index finger. Each forecast looks half a second, one second and one and a half seconds ahead. [Try the group model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#arm-transfer)

## What happened in five other people?

Seven people supplied 882 fitting trials. The five assessment participants supplied 630 trials across 15 runs. On those five people, the pooled shared model averaged **0.505** units of standardized error. The same encoder fitted on only one person averaged **0.793**. All five people improved with the broader fit. Supplying the correct task reduced the group's error from 0.561 without the cue and 0.682 with the wrong cue. The group median for each cue reached **0.435**, lower than the shared encoder for every assessment participant.

The first-run correction was tested on 420 later trials. It reduced average error from 0.521 to 0.484, with all five people improving. A simpler forecast using the person's own first-run median for that cue did better, at **0.429**. The correction therefore missed the specified requirement to beat all three comparisons. Removing absolute starting levels reduced the linear model's error by 2.15% and the shared model's by 1.84%. Both missed the 5% threshold.

Errors here are absolute changes divided by the fitting group's standard deviation for each target. Each person, run and cue counts equally at its own level. For the actual size of errors on the instruments, see the native-scale table in the results. Only five people supplied independent assessment units. [Native errors, paired intervals and all comparisons](results.json) · [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/arm-transfer/)

## What the model sees

The seven source cues include bending or straightening the elbow, turning the palm up or down, closing or opening the hand, and resting. An event in the recording identifies which visual task was shown. The web reader accepts a matching study term or a listed everyday phrase. The dataset supplies the intended task category. It does not supply a transcript of speech or the person's private intention.

There are three levels and three changes in each of four input rows. The levels are the eight-sample medians over consecutive 125 ms intervals on the stored 64 Hz sensor clock. The changes within each interval are its last-four-sample median minus its first-four-sample median. The input stops a quarter second after the cue on the stored event clock. Every output is a median of eight later readings minus the cutoff-bin median for the same instrument. A positive number means that a sensor’s value increased. The files do not establish a conversion into anatomical angles or the source of a change in a scalp voltage. The forecast uses mechanical measurements and the known cue.

## Test the downloadable model

From the parent model folder, with Python and NumPy installed, run:

```sh
python predict.py arm-transfer/example.json
```

`domain` is `group_arm_change`. The cue-only methods (`cue` and `cue_median`) take a named action. The first fits a linear readout to cue indicators. The second uses the typical sensor changes for that cue across the fitting participants. The motion-only methods (`motion` and `shared_motion`) take only `bins`. The methods `cue_motion`, `shared_cue_motion` and `shuffled_cue_motion` take both. The `still` method predicts zero change. The two `offset_free_linear` and `offset_free_shared` methods also take cue and bins, but learn from changes without using the three absolute starting levels. [Exact method](PROTOCOL.md) · [Additional offset comparison](OFFSET-CHECK.md)

## Correct a forecast using an earlier run

A population model can be consistently high or low for a particular person's sensor setup. The optional correction uses measured changes from that person's earlier run. For each earlier trial, subtract the pooled shared forecast from the observed 3-by-3 array of changes. Take the median difference separately for each cue. With six earlier observations of a cue, the final forecast uses half that correction: the multiplier is the count divided by the count plus six. A cue with no earlier examples retains the original group forecast.

Prepare a JSON list of trials. Each item has `cue`, `bins` and `observed_change_native_units` measured at the same three future times. Run this command in the parent folder:

```sh
python arm-transfer/calibrate.py earlier-trials.json > my-profile.json
```

Paste the resulting JSON into the group reader, or supply it as the `calibration` field with method `calibrated_shared`. Keep profiles with their original person and sensor setup. The file binds the correction to its fitted group model. For practice, the reader offers an invented correction. Neither the download nor the webpage includes a test person's profile.

## Reproduce the fitting and assessment

Ofner, Schwarz, Pereira and Müller-Putz (2017) published the recording files under CC BY 4.0. Download motor-execution runs 1–3 from numeric participants S1–S7 for fitting. For reproduction after the fit is sealed, obtain the same runs from S8–S12. Keep the original GDF filenames in a local cache. The reader verifies the publisher’s full-file byte counts and MD5 digests, the file layout and clock. The final three participants remain reserved. Use the frozen one-person model as the parent; its existing readouts are preserved. Python 3.12 and NumPy are sufficient. [Original data](https://doi.org/10.5281/zenodo.834976) · [Acquisition paper](https://doi.org/10.1371/journal.pone.0182578) · [Parent checkpoint](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/e350e86c84f44b23417d5698da884ca67fd5f1fc/models/neurotranslate-0.0/movement-weights.npz)

```sh
python arm-transfer/download_originals.py fitting path/to/private-cache
python arm-transfer/study.py fit path/to/private-cache earlier-model.npz group-model.npz fit-receipt.json
python arm-transfer/download_originals.py assessment path/to/private-cache
python arm-transfer/study.py assess path/to/private-cache group-model.npz fit-receipt.json reproduced-scores.json
```

The reanalysis selects the named right-arm execution runs, calculates time bins, fits new readouts and compares forecasts. The source recordings, derived weights and results retain CC BY 4.0 attribution. The project dedicates its original software and invented examples to the public domain under CC0. Retain the original credits and identify further changes. [Data licence](CC-BY-4.0.txt) · [Project dedication](../LICENSE)
