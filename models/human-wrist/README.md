# Where will the wrist go on another recording day?

A camera tracks two wrists, two elbows and two shoulders. Eight electrodes measure electrical activity at the surface of the brain. Given half a second of both signals just before a recorded right-wrist movement, can a model predict where either wrist will appear eight or fifteen camera frames later?

The experiment fits one recording from AJILE12 and tests the next recording of the same person. The public example uses invented movement and voltage. You can change its inputs, train fresh models on the fictional recordings, or repeat the clinical analysis in a private directory.

## Open a forecast

Extract the full download. Open [the reader](reader/index.html) in a recent browser. Choose an example, move either wrist or adjust the voltage gain. The change in the model’s guess is measured in camera pixels. Eight frames take about 267 milliseconds at 30 frames per second. Fifteen take half a second.

The reader opens with four simulated motions and their own simulation-trained weights. To try a case from the full training workflow, use **Open a private case → Model and case (.json)** and pick [fictional-example.json](fictional-example.json). Every coordinate, voltage value and fitted parameter in this file comes from the artificial arm in [fictional.py](study/fictional.py). The file contains earlier inputs and the weights for both wrists. A future reference appears only if you explicitly include it during export.

## Train the fictional example

Use Python 3.12 or 3.13 in a virtual environment. The following commands run from the directory containing this file. Activate the environment for your operating system, then install the dependencies once. PyTorch’s CPU build is sufficient. Package installation needs access to the package index. The practice commands run offline.

```sh
python -m venv .venv
```

On macOS or Linux, run `source .venv/bin/activate`. In Windows Command Prompt, run `.venv\Scripts\activate.bat`.

```sh
python -m pip install -r requirements.txt
python study/run.py practice --work wrist-practice
```

The generator constructs shoulders, elbows and wrists from two rotating segments in an imaginary camera plane. It makes 60 fitting examples and 58 separate test examples. It also inserts missing measurements into a few test examples so you can see exactly where a forecast becomes unavailable. These counts exercise the scientific workflow. The artificial movement does not model this person’s physiology.

Open `wrist-practice/predict/case.json` in the reader. The two weight archives and the coefficients for the camera-only fits are in `wrist-practice/fit/`. The full table of 110 forecasts is in `wrist-practice/predict/predictions.npz`, and their errors are in `wrist-practice/score/scores.json`. To add the fictional measured endpoint to an exported case, run the following after scoring.

```sh
python study/run.py case --work wrist-practice --row 0 --with-reference --output fictional-with-reference.json
```

## Reproduce the recording-day study

Choose a private output directory outside the public package. Keep the recordings, cache, trained weights, predictions and exported case on your own computer. The browser reads a case locally. Nothing in the study software sends your case or your results anywhere.

The source is participant 01, sessions 3 and 4, in AJILE12 release 0.220127.0436. The original NWB files are about 15.9 GB each. With both files on disk, substitute their actual paths in this command. [Versioned dataset](https://doi.org/10.48324/dandi.000055/0.220127.0436) · [Session 3 NWB](https://api.dandiarchive.org/api/assets/7b9e2ca1-9097-488a-b4e9-ac407fb31457/download/) · [Session 4 NWB](https://api.dandiarchive.org/api/assets/f47baec3-984b-419c-998e-b47414f9aa4c/download/)

```sh
python study/run.py clinical --train-nwb "/path/to/sub-01_ses-3_behavior+ecephys.nwb" --held-nwb "/path/to/sub-01_ses-4_behavior+ecephys.nwb" --work private-wrist
```

To retrieve only the parts needed for the analysis, use the command below. This is the only study option that enables an external request. It reads clock and event metadata, then fetches native compressed chunks holding eligible measurements. The physical chunks may include neighbouring frames. Only the specified measurements enter the arrays. The program checks the immutable object identifier, byte range and response length, and checks each resulting measurement array against the frozen original. The cap counts requested HTTP payload bytes, including unsuccessful requests. It defaults to 384 MiB per recording. Four workers handle disjoint reads by default. Choose one to six with `--workers` or lower the cap with `--cap-mib`. With this edition and the tested HDF5 reader, the workflow requested 133.89 MiB for session 3 and 136.96 MiB for session 4. Verified chunks are cached in the private directory.

```sh
python study/run.py clinical --download-ranges --work private-wrist
```

To stop immediately after fitting or predicting, add `--through fit` or `--through predict`. Repeat the command with the same working directory through a later stage to continue. A completed stage is reused after its software, inputs and outputs pass checksum checks. Use a fresh directory for a different source, fit recipe or software edition. The local-file route keeps the network disabled. Either local file can also be supplied alongside the explicit ranged-download option.

| Stage | What is opened | What you can inspect |
| --- | --- | --- |
| `fit/` | Earlier camera and voltage measurements plus the future wrists from session 3 only | `training.npz`, bilateral `weights.npz`, historical right-wrist `legacy.npz` and camera-only `geometry.json` |
| `predict/` | Frozen fitted parameters and earlier measurements from session 4 | `inputs.npz`, all 110 predictions, eligibility and donor checks, and a target-free `case.json` |
| `score/` | Saved predictions and the two future wrist positions from session 4 | `targets.npz`, `scores.json` and `comparison.json`, which compares every aggregate section with the original at five decimal places |

Load `private-wrist/predict/case.json` under **Open a private case**. It contains the first eligible bilateral example in chronological order and all twelve seed-17 network branches used by the reader. To choose another example, run the following with its zero-based held row. The exporter requires finite earlier measurements for both arms and valid voltage. It creates a new file and leaves existing files intact.

```sh
python study/run.py case --work private-wrist --row 0 --output my-private-case.json
```

After scoring, `--with-reference` also includes both finite observed endpoints for that row. Future positions are omitted by default. All coordinates use the original camera axes. The reader draws each wrist relative to its own last known position.

## What the recording actually tests

The authors detected right-wrist reaches retrospectively from tracked video. Each chosen onset has an independent reach-table time within the archive’s 2-millisecond event resolution. This agreement checks the stored clocks. It does not establish a hardware synchronization error of 2 milliseconds. Electrodes were filtered and rereferenced offline. No instructions were given at these onsets.

The first 16 hours of session 3 supplied 60 eligible right-wrist events. The first 16 event histories also recreate the smaller fits. Each retained half-second on either side of the onset had to lie within one two-minute block, under allowed activity labels, with at least 30 seconds between retained events. Session 4 contributed the first twelve eligible events in each four-hour interval where available. The six intervals supplied **3, 7, 12, 12, 12 and 12** events. Input and outcome quality were applied after selecting those 58 events. No excluded measurement led to selection of a replacement.

Each example contains 250 earlier samples at 500 Hz from eight grid channels, and fifteen earlier camera frames at 30 Hz for each of six landmarks. The archive stored a volts-per-unit conversion of one millionth for the electrical signal. The numbers used here are microvolts. The pose field is labelled metres with an undefined conversion. The original authors describe the numbers as image pixels. The analysis keeps these signed, projected image coordinates, without a depth or physical-distance calibration. Grid region rows 0, 9, 18, 27, 36, 45, 54 and 63 supply the same montage on both recordings. Two retained channels, 0 and 36, carry author quality flags. All eight remain in their original positions. A window needs finite voltage, at least one varying channel and no time sample with all eight channels zero. Each arm needs fifteen finite frames of all three of its landmarks. Each target needs two finite image coordinates.

### Which models competed?

- **82 new outputs.** One set uses the full 60-event training roster with separately fitted wrists. A second set uses the first 16 events and forecasts the right wrist only. Each set has five simple forecasts and 36 combinations of linear regression, small causal Transformers, pose alone, pose plus voltage and earlier-event voltage controls. All Transformers read five chronological blocks. Each block holds ten pose features and sixteen voltage features. Width is eight, the hidden layer has twelve units, and three fixed initializations (17, 37, 73) each receive 48 full-batch AdamW updates in double precision. The direct model learns a whole displacement. The two bounded models limit each learned correction to one quarter of the per-axis training scale. One adds the correction to a still wrist, the other to scaled recent wrist velocity. The fitted velocity and scales come entirely from the training session.
- **5 camera-only outputs.** Two project a still wrist or its recent velocity. Three fit bounded mixtures of slopes estimated over four, eight and fifteen earlier frames. The fits compare movement of the whole wrist with movement separated into shoulder translation, upper-arm and forearm components. The component fits either share coefficients between sides or fit each side separately.
- **23 historical right-wrist outputs.** The first 16 right-wrist examples refit the earlier still, mean and velocity controls, three frequency-band or pose regressions, four linear temporal models and twelve seeded temporal Transformers. The voltage bands are 8–32 and 76–100 Hz. The residual model starts from half the observed wrist velocity. All historical and new fitted coefficients are created locally from the selected training recording.

### Reading a held score

An endpoint error is the straight-line distance between a forecast and the camera’s later wrist estimate, in pixels. `absolute` reports count, mean, median and x/y root-mean-square error for each method, wrist and horizon. `pairs` contains 172 matched comparisons. A negative difference favours the first named method. Each comparison includes the six individual four-hour intervals, their equal-weight average across occupied intervals, and six estimates that each leave out one interval.

The primary comparison pairs true pose-plus-voltage forecasts with both pose-only fits and forecasts using voltage from the most recent eligible event in an earlier two-minute block. The recipient keeps its own pose. The first event has no earlier donor. Thus 58 events can contribute ordinary endpoint errors and **57** can contribute the common-donor comparison. `primary_common` retains the same eligible examples for both controls. `all_bilateral_common` requires both wrists at one horizon. `all_four_heads_common` requires both wrists at both horizons.

| Mean error in pixels across 58 held events | Right +8 | Right +15 | Left +8 | Left +15 |
| --- | ---: | ---: | ---: | ---: |
| Seed-17 Transformer, velocity plus learned correction, pose and voltage | 29.68 | 48.83 | 46.43 | 53.12 |
| Same treatment, separately fitted on pose alone | 30.03 | 50.00 | 46.46 | 53.13 |
| Fitted fraction of earlier velocity | 31.02 | 50.31 | 45.59 | 51.79 |

Adding voltage to pose lowered the right-wrist mean error at both horizons in all three fits on the common 57 events. Voltage from a different event sometimes performed as well or better. Neither wrist met the prespecified requirement to beat both controls at both horizons in every fit. The simpler fitted-velocity forecast had lower left-wrist mean error than the illustrated seed-17 model. All three seeds share one training recording and one test recording. The left-wrist estimates describe what happened during selected **right**-wrist movements. Generalization to another person, an online onset detector and a causal effect of one arm’s cortical activity require different evidence. [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/human-wrist/)

## Files, sources and rights

The names, byte lengths and cryptographic digests of the original NWB assets are documented in [assets.json](study/assets.json). The [reference checks](study/expected.json) contain hashes of complete source arrays and rounded aggregate sections. The frozen fitted weights and individual event values stay out of this distribution. The bundled worked case and its weights come exclusively from the fictional generator. The original software and invented example have a [CC0 dedication](LICENSE.txt). DANDI lists the clinical dataset under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Steven M. Peterson, Satpreet H. Singh, Benjamin Dichter, Micheal Scheid, Rajesh P. N. Rao and Bingni W. Brunton (2022). *AJILE12: Long-term naturalistic human intracranial neural recordings and pose*, version 0.220127.0436, DANDI Archive. This analysis selects event windows and contacts, fits forecasts and calculates held errors. [Original data](https://doi.org/10.48324/dandi.000055/0.220127.0436) · [Dataset paper](https://doi.org/10.1038/s41597-022-01280-y) · [Original movement-detection methods](https://doi.org/10.1523/ENEURO.0007-21.2021)

[Online wrist reader](https://eliminatenoise.github.io/NeuroTranslation/human-wrist/) · [Recording-day paper](https://eliminatenoise.github.io/NeuroTranslation/papers/human-wrist/) · [Electrode atlas](https://eliminatenoise.github.io/Interoceptomics/human-wrist/)
