# Can the shin signal predict the next pedal reading?

Try lifting your forefoot against a pedal that stays put. The effort changes even when the pedal does not move. In the AnkleImage experiment, a skin electrode over the tibialis anterior recorded the muscle’s electrical activity. A load cell under the pedal sent a signal through a conditioner. Can the muscle signal help predict where that second reading will go?

Give the model 201 consecutive readings from each channel and the pedal setting. It predicts the signed change in the load channel 100 acquisition rows ahead. The authors report 1,000 samples per second, so the horizon is nominally 100 milliseconds. Some files have a regular stored time vector. Others have only row positions, from which the extractor constructs a nominal clock. Three reserved files contain an original 10 kHz grid and the authors’ 1 kHz export. Their selected channel and time vectors match every tenth raw sample. Neither supplies independent hardware timestamps. The load stays in native conditioner units. Converting the reading to newtons or ankle torque would require separate calibration and geometry. The source calls the channel `loadcell_right`. That label does not establish which limb a participant used. [Source methods](https://doi.org/10.1038/s41597-024-04285-x) · [Data and licence](NOTICE.md)

## Try the forecast

Extract the complete folder. Install Python 3 and NumPy in the interpreter used by the launcher. Open **Launch-Windows.cmd**, **Launch-macOS.command** or **Launch-Linux.sh**. Alternatively, run the following from the extracted folder.

```sh
python -m pip install numpy
python -B forecast.py example.json
```

The example is invented. To try your own, supply two arrays of 201 finite numbers, `load` and `emg`, ordered from oldest to newest. Use `angle0` or `angle5` for `setting`. These are the exact archive categories. The sign of the five-degree setting relative to the ankle is unverified. An optional `donor_emg` array supplies the control from a second trial at the same setting. Omitting it removes the swapped-trial forecast.

The full Transformer divides the history into ten groups. It uses differences in the recent pedal signal, variations in muscle activity, their timing and the pedal setting. Three other Transformers take different subsets of those inputs. Six simpler forecasts include zero change, continuation of the last change, typical changes from the training data and linear fits. The eleventh forecast feeds the full model a muscle trace from the other trial. This comparison asks what the correct pairing adds.

## Reproduce the study

The original AnkleImage study enrolled ten people across five ankle tasks. Four gave fixed-pedal Task 1 recordings. Each underwent 21 standard trials, and two also underwent seven extra high-frequency ultrasound trials. This analysis selected four standard trials for each of the four people, two trials at each of two settings. Fit on two people, holding each entire person out in turn during development. Freeze the fit on both before opening eight trials from two other people. Seven trials qualify. In the eighth the right load field has two columns, with no verified choice of column or 1 kHz time grid. The planned two-person comparison remains incomplete. The qualified results describe the complete four trials for one person, a same-setting pair for the other, and that person’s single remaining trial. The single trial has no qualified partner for the swapped-muscle control. [Original study, Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC11680872/) · [Source and clock checks](source/README.md)

The following commands use Python 3.11 or later. Source retrieval needs NumPy, SciPy and internet access for uncached files. Training also needs PyTorch. Use a fresh output directory for training and a new filename for the assessment. For an exact CPU comparison use one PyTorch thread, one inter-op thread and one BLAS thread, as in the original run.

```sh
python -m pip install numpy scipy torch
python -B source/extract.py development --cache ../ankle-data
python -B source/extract_assessment.py --cache ../ankle-data
python -B test_model.py
python -B fit.py ../ankle-data ../new-fit --threads 1 --device cpu
python -B assess.py ../ankle-data ../new-assessment.json
```

Compare the fitted weights and artificial fixture with `model.json` and `fixture.json`. Compare the two result files with [development](development.json) and [assessment](assessment.json). Development mean absolute error pools trials within each person and setting and then gives both settings and both people equal weight. The separate descriptive assessment gives the available trials equal weight within each of its three groups. The seven qualified trials yield 446 windows. Only 388 have an eligible wrong-trial partner. The original strict scorer, `assess_strict.py`, cannot run the complete-roster test with this material. Adjacent forecasts reuse some of the same history. Window counts measure repeated observations within these four people. [Model and decision criteria](protocol.json) · [Original pre-assessment hashes](PRETEST-SHA256.json)
