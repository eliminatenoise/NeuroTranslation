# Where will the heel move, and what will the plate read?

Follow two skin markers on the right foot for 24 camera frames. Stop at the last frame. One tenth of a second later, where will the heel marker be, and how much upward force will the plate under that foot measure? Two outputs from the same step give us a direct test. Does learning to predict one help predict the other?

The models were frozen before scoring the original assessment walks. Eight people from that previously used cohort supplied 53 eligible instants in 16 recordings. The shared model missed the heel endpoint by **1.156 mm** and the plate load by **92.36 N**. The separately trained motion and load specialists missed by **1.183 mm** and **93.73 N**. Both point estimates favored the shared model. The 95% participant-bootstrap intervals for shared minus specialist error included zero on both outcomes, from −0.103 to +0.040 mm and from −6.08 to +2.90 N. The prespecified test required both intervals to fall below zero.

Six people from the same historical cohort supplied 31 more eligible instants in 10 later recordings. The shared predictor scored 1.024 mm and 103.28 N, against 1.026 mm and 103.90 N for the specialists. Both paired intervals included zero again. These later repeats test the same fitted weights on further walks from previously studied people. The ten reserved participants supplied no recordings to this work. Neither assessment met the prespecified test for added EMG value.

## What happened in development?

In participant-held-out development folds, the shared model missed the heel marker by an average of **1.365 mm**, and the plate load by **100.03 N**. The corresponding specialists missed by **1.364 mm** and **99.45 N**. The small differences favored the specialists. The participant-bootstrap intervals for shared minus specialist error ran from −0.055 to +0.061 mm and from −1.19 to +2.43 N. These overlapping training folds describe the development cohort.

| Model or rule | Mean 3D endpoint error (mm) | Mean absolute load error (N) |
|---|---:|---:|
| Shared Transformer, markers, timing and surface EMG | 1.365 | 100.03 |
| Two separate Transformers, same inputs | 1.364 | 99.45 |
| Shared Transformer, markers and timing | 1.251 | 89.87 |
| Three similar marker histories from different training people | 1.189 | 88.65 |
| Ridge regression, markers and timing | 1.256 | 83.31 |
| Keep the heel still | 1.457 | — |
| Average training load at this time since strike | — | 93.76 |
| Carry forward the most recent plate measurement | — | 78.48 |

The last row has a different advantage. It can read the force plate before the cutoff. The other methods cannot. The shared model's mean signed errors, in laboratory order X, Y, Z and upward load, were +0.051 mm, −0.150 mm, +0.072 mm and −7.99 N. Endpoint error measures the length of the displacement prediction error in three dimensions. It retains an error that would cancel in a signed average.

## Which steps counted?

Schreiber and Moissenet recorded barefoot walks, including a C2 condition paced for 0.4–0.8 m/s. Of 90 development recordings from 30 people, 28 lacked a distinct plate assignment for both feet and one failed the marker projection check at strike. The remaining 61 recordings came from 25 people. Four planned instants per recording gave 244 candidate histories. Forty-one fell outside the stored extent. The other 203 supplied both a heel displacement and an upward load from the assigned plate. The earliest cutoff contributed 20 pairs. Each of the other three contributed 61. Repeats count equally within a person, people count equally in the result, and several instants from the same footstep share their recording's weight. [Dataset](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Data descriptor and supplement](https://doi.org/10.1038/s41597-019-0124-4)

The heel marker sits on the posterior calcaneus and the forefoot marker over the second metatarsal head. Their relative motion, the heel height and the elapsed time since the annotated right strike enter four ordered bins. Each bin also takes the RMS surface EMG from eight muscles on the right. The last bin ends at the analog sample aligned with the camera cutoff. The future force value averages 15 samples centred 100 ms later. Joint angles, individual muscle forces and foot pressure distribution remain unmeasured here. Source preprocessing includes two-way filters, trial-wide EMG centring and marker gap repair. An offline prediction from those signals cannot establish prospective sensor latency. [Authors’ processing code](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/tree/e35dc90c1acd24da134897fd1b4241152cff6005)

What happens if we give the network the muscle activity from another walk? For 189 instants from 22 people, we could exchange the entire four-bin EMG history for one from a different repeat by the same person, at the same time since strike. With the correct history, the model scored 1.307 mm and 97.72 N on those same instants. With the exchanged history, it scored 1.339 mm and 97.77 N. A model trained on markers and timing alone scored 1.210 mm and 85.60 N there. Neither outcome met both prespecified tests of additional EMG value. The donor subset leaves out 14 instants, so its raw means cannot be compared to the full-cohort means in the table.

## What changed during training?

One 2-head attention block reads the four bins, and two linear heads convert the last token into three heel coordinates and one load. The shared trunk has 2,656 parameters. Both tasks supply gradients to it. On the first update of the final fit the heel gradient had norm 1.3302, the load gradient 3.9749. Their half-weighted sum reproduced the combined gradient to an L2 residual of 8.59 × 10⁻⁷. Across 12 steps the trunk moved 1.2516 in parameter-space L2 distance. This establishes that both tasks taught the same trainable trunk. Whether that helped is a separate empirical question answered by the errors above.

The shared model and each specialist got the same-width trunk, the same marker and EMG inputs, optimizer and the same three candidate training lengths. Each person appeared in just one outer evaluation fold. Each outer fold chose its training length on different people inside the remaining training set. All coordinate scales, load scale and input scales came from the fitting people for that split. Training each specialist independently uses two trunks overall. The frozen protocol gives the loss, weighting, cutoff times and control comparisons.

## Run the exported model

Load `predict.js` and parse `joint-model.json` as JSON. The local function needs no network connection.

```js
const forecast = GaitPair.predict(model, example.input);
console.log(forecast.heel_delta_mm, forecast.plate_up_N);
```

`example.json` contains an invented walking history and the expected Torch outputs under `expected.joint`. Ordered input shapes are 24 × 2 × 3 laboratory marker coordinates in millimetres and 4 × 8 muscle RMS values in microvolts. `offset_frames` is one of 14, 24, 34 and 44 frames after the annotated strike. Model metadata gives muscle and marker order. Heel displacement is signed future minus cutoff in laboratory XYZ, with Z upwards. Add the predicted displacement to the final heel coordinates to locate its predicted endpoint. The second output is the assigned plate’s upward load in newtons. Run `heel-model.json`, `force-model.json` and `marker-model.json` through the same function to obtain the separately trained comparisons. Each specialist returns its own outcome. The marker-only model accepts inputs without EMG.

The recordings are by Florent Moissenet and Céline Schreiber, from Figshare version 8 under CC BY 4.0. This experiment derives binned marker and muscle histories, 100-ms displacement and upward-load targets, fitted predictors and new evaluation results. [Source and licence](https://doi.org/10.6084/m9.figshare.7734767.v8) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Rebuild the final weights

The source reader’s train command produces `development-v1.npz`. With that file and the three Python files `rebuild_weights.py`, `records.py` and `network.py` in reach, run the command below with a fresh destination directory. The command verifies the development array archive, computes its feature and target scales, initializes four networks from seed 8347 and trains their selected configurations. It prints each resulting weight-file SHA-256. Our one-thread CPU reproduction with NumPy 2.5.3 and PyTorch 2.14.0+rocm10.1.0 recovered all four files byte for byte. Floating-point implementations on other builds may differ. Rebuilding these final fits uses the selected training lengths. The participant-grouped comparisons above used nested development folds.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python rebuild_weights.py source/prepared/development-v1.npz rebuilt
```

## Run an example locally

Extract the ZIP. Install Node.js if you need it, then use the Windows, macOS or Linux launcher. All three run the joint model on the invented history in `example.json`. From a terminal, run `node forecast.cjs`. Pass a model name and your own JSON file to change the input, for example `node forecast.cjs heel my-history.json`. The four model names are `joint`, `heel`, `force` and `marker`. The offline interactive reader runs these same weights in a browser. [Download the offline reader](https://eliminatenoise.github.io/NeuroTranslation/heel-and-force-offline.zip)

## Repeat the participant-held-out study

Run the source reader from its own directory first. In the model folder, the command below uses the resulting development arrays and their matching receipt to reconstruct the original three outer folds, the inner searches, the equal-person and equal-repeat weighting, and the 12-, 36- and 90-update comparisons. It refits each control on the corresponding training rows. Supply either or both optional assessment files to score every control after the development search. The output contains aggregate results, the selected settings and four fitted networks. A one-thread CPU run in the reference environment reproduces the full-precision published development and assessment summaries and all four weight files.

```sh
python develop.py source/prepared/development-v1.npz source/prepared/development-v1-receipt.json reproduced --assessment source/prepared/historic-assessment-v1.npz --later-repeats source/prepared/later-repeats-v1.npz
```

## Reproduce the assessments

First follow the [source reader](source/README.md) to rebuild the development arrays. Use a separate Python environment for the model scripts. The verified fitting environment used NumPy 2.5.3 and PyTorch 2.14.0; the original-source reader has its own pinned dependencies. Follow [the study protocol](METHODS.md) for the nested development comparison. The assessment reproduction below uses the four final networks and their saved scales.

To reconstruct either assessment, run the same source command with `--partition assessment` or `--partition later-repeats`. Add `--fit-seal ../PRETEST-SHA256.json --fit-seal-sha256 7f916b43b9dec19f3b12cb076a7445823fc6a45798464aa340334a05929e9222` when running it from the `source` folder. This public manifest identifies the four task-trained weights, the movement model readout and the original preassessment seal. Source receipts generated on your computer contain trial identifiers. The published results contain cohort summaries.

From the model folder, run the following on the prepared arrays. The scorer prints participant-weighted means and bootstrap intervals for each trained network, the wrong-repeat control and paired error differences. The [complete aggregate table](aggregate.json) also gives the separately fitted ridge and nearest-history comparisons, timing rules and force-history controls. The `exact_reference_floats` field compares the calculated summaries to the published values at full precision.

```sh
python assess.py source/prepared/historic-assessment-v1.npz
python assess.py source/prepared/later-repeats-v1.npz
```
