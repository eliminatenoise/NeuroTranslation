# What do the words add to a walking forecast?

Tell someone to walk “as usual” or “fast but not running”. Once you’ve seen their last 200 milliseconds of movement, do those words help you predict the next 100?

A small Transformer read the motion of the pelvis and right heel, the time since the right foot struck the ground and one of those two instructions. On 60 walks by ten people held out of fitting, it missed the future pelvis position by **5.02 mm** and the heel by **5.74 mm** on average. Giving the same model the opposite instruction made both forecasts worse. A second model trained with the instruction withheld scored **5.12 mm** and **5.68 mm**. Neither landmark showed a clear gain from giving the model the instruction once it had seen the movement.

## Try a forecast

Extract the whole package and open **forecast.html**, or use the launcher for Windows, macOS or Linux. The page runs on your device and starts with an invented history. Change the instruction while keeping those 21 frames fixed, or load your own local JSON window. A negative forward value means movement backwards from that landmark’s own position at cutoff. Left and up use the same signed convention.

With Node.js you can run the same exported weights from a terminal in this directory.

```sh
node forecast.cjs example.json "fast but not running"
node forecast.cjs example.json null
```

Each input has three fields. `history_mm` contains 21 frames at 100 Hz, each with the pelvis XYZ followed by right-heel XYZ. Both positions use the cutoff pelvis as origin. Forward points along the horizontal path from the first observed pelvis position to the last. A 90-degree rotation to the left gives the second axis. The third points up. `offset` is 10, 20, 30 or 40 frames since the first annotated right strike. `instruction` is either of the exact phrases above, the equivalent integer 4 or 5, or `null` to use the separately trained model. These two phrases select the same two numeric codes as their condition numbers. Each phrase applied to a whole walk. The source gives no word timings, arbitrary-language training or neural recording.

```js
const {orient, predict} = require("./predict.js");
const weights = require("./weights.json");
const example = require("./example.json");
const pelvisAndHeelDelta = predict(weights, example.input);
// For 21 laboratory frames containing pelvis and heel coordinates:
const convertToWalkingCoordinates = laboratoryHistory => orient(laboratoryHistory);
```

The result is two signed XYZ displacements in millimetres. Each starts at its landmark’s position at the end of the history. If the pelvis travels less than 10 mm horizontally over the history, its heading is insufficient for this model. A laboratory history must be rotated with `orient` before prediction. On the browser, `WalkingForecast` exposes both functions. The `permuted` third argument selects the model trained on shuffled trial instructions.

## What happened on the recorded walks?

Each error below is the length of the three-dimensional prediction error, averaged within repeat, condition and person so that each person counts equally. All methods saw the same 216 windows. Changing the model’s cue leaves the measured future exactly where it was. That comparison measures sensitivity to the cue. It cannot show where the same person would have stepped under a different instruction.

| Forecast on the ten historical participants | Pelvis error (mm) | Right-heel error (mm) |
|---|---:|---:|
| Correct instruction and marker history | 5.022 | 5.742 |
| History model trained with instruction withheld | 5.116 | 5.677 |
| Opposite instruction, correct-instruction weights | 5.491 | 6.265 |
| Trial instructions shuffled within each training person | 5.217 | 5.980 |
| Mean training displacement for the instruction and time since strike | 14.370 | 14.262 |
| Linear history, timing and observed-pace model with cue | 5.762 | 8.514 |
| Same linear model family without cue | 6.186 | 8.789 |
| Repeat the last 100 ms change | 23.239 | 20.726 |
| Extend the last 50 ms velocity | 19.022 | 19.294 |
| Keep each landmark still | 140.743 | 24.795 |

The correct cue reduced pelvis error by 0.094 mm relative to withholding it. The paired 95% interval for correct minus withheld ran from −0.229 to +0.020 mm. Heel error increased by 0.066 mm, with an interval from −0.129 to +0.255 mm. Against the swapped cue, the differences were −0.469 mm for the pelvis (−0.708 to −0.252) and −0.523 mm for the heel (−0.796 to −0.224). A cue benefit required both paired intervals for a landmark to lie below zero. Intervals resample ten whole participants 5,000 times, with seed 1207 and no multiplicity adjustment.

The trained Transformer did improve on the cue-aware linear forecast. Its error fell by 0.740 mm at the pelvis (paired difference −1.170 to −0.322 mm) and 2.772 mm at the heel (−3.325 to −2.214 mm). Eight of ten participants improved at the pelvis and all ten at the heel. This comparison changes the forecasting method while keeping the instruction. The experiment above changes the instruction while holding the model family constant. [Paired architectural comparison](linear-comparison.json)

Under “as usual”, the correct-cue model scored 4.055 mm at the pelvis and 3.142 mm at the heel. Under “fast but not running”, those values rose to 5.989 and 8.343 mm. Mean signed errors across both instructions were −0.412, +0.460 and +0.337 mm at the pelvis and −1.279, +0.331 and −0.693 mm at the heel, in forward, left and up order. A signed mean can conceal errors that point in opposite directions. [Assessment results, including both instructions](assessment-summary.json)

Three participant-held-out development folds gave 5.783 mm and 6.906 mm for the correct cue, 5.639 and 6.804 mm with the cue withheld, and 6.210 and 7.277 mm with it swapped. Neither development endpoint passed both cue tests. The final weights then used all 30 development people. Their folds shared training people across fits, so the development intervals describe this cohort. [Development results](development-summary.json)

## Which measurements counted?

Céline Schreiber and Florent Moissenet recorded barefoot walks on a level walkway. The pelvis estimate averages four skin markers, and a fifth skin marker sits over the right heel. The first three repeats of each instruction supplied 180 development walks and 60 assessment walks. Of 360 proposed development windows for each instruction, 323 usual and 322 fast windows qualified. In assessment, 112 usual and 104 fast windows qualified out of 120 each. All exclusions came from an insufficient history in the cropped recording at the earliest cutoff. Every person contributed both instructions. Ten further people remained in reserve. [Dataset and licence](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Recording methods](https://doi.org/10.1038/s41597-019-0124-4)

The first repeat of both conditions from one development person had been inspected before design freeze. The ten assessment people had appeared in earlier movement studies. Eight supplied eligible original walks to an earlier slow C2 heel-and-force analysis, and six supplied eligible later repeats. Their movements in the two present conditions did not enter fitting. The authors processed the optical data offline, including gap repair and forward–backward filtering. The strict cutoff applies to frames in that processed recording. A live sensor would require a separate test. [Selection, signal processing and reconstruction](source/README.md)

## How did the model learn?

Seven successive groups of three frames preserve all 21 observations. Each group supplies its final six positions and the six changes over each of its two preceding frame intervals. Appending elapsed phase and instruction gives 20 inputs. A learned linear projection maps each group to 24 features. Seven learned position vectors preserve the order. One three-head self-attention block reads the history, followed by a 48-unit tanh feed-forward block. Both blocks have residual connections and layer normalization. The final token predicts six residuals on top of each landmark’s previous 100 ms change. All six components are free to change sign and magnitude.

Each fit has 5,694 trainable parameters. Coordinate scales and residual scales came from the fitting people. PyTorch updated the whole network 180 times using full-batch AdamW with learning rate 0.003, weight decay 0.01, seed 7319 and no dropout or model selection. The loss averages squared standardized error across axes and landmarks. Each person counts equally, then each condition, repeat and window within that person. The correct-cue model, withheld-cue model and shuffled-training-cue model have the same capacity, initialization and optimizer. The shuffle used seed 7081, kept every trial together and preserved each person’s label counts. It changed the instruction for 90 of the 180 final training walks. In the correct-cue fit, both landmark losses produced nonzero gradients in the shared layers at the first update, and the shared weights moved over training.

## Rebuild the fits and scores

Use the version 8 source reader in `source/` to prepare the two splits. Its requirements belong in a separate environment. For model fitting the recorded environment used Python 3.14.8, NumPy 2.5.3 and PyTorch 2.14.0+rocm10.1.0 executing on CPU. Use a clean output directory. The training command recreates all three held-person folds, the final weights and the invented fixture. The assessment command refuses people present in the fitted set. Both commands hash-check their prepared arrays.

```sh
python -m pip install -r requirements.txt
python train.py train prepared/development.npz rebuild --threads 2 --data-sha256 30e584890531eb9576c10581839e48244961d0bf98ad767470cff67755f1e735
python train.py assess prepared/historical.npz rebuild --threads 2 --fit-dir rebuild --weights-sha256 bb6b1847e6ac0ba273dc9e4c79ba8d509da30e0df094aecf0f06d6b317da16e2 --data-sha256 c8acd32db57449fbc8fb0c354d4950d836f44313ba28b39e49deed8901008b64
```

To score the distributed weights directly after preparing the arrays, run `python score_release.py prepared scored`. This path recreates the historical assessment without refitting.

Different library builds or CPU kernels may change numerical rounding. The published JSON contains the precise weights used for the reported results. Rebuilding creates participant identifiers, measured futures and per-person scores under `rebuild/private/`. Keep those files local. To regenerate the self-contained model data in the browser page, run `python build_browser.py`. Attribution and licence terms accompany the code. [Source and reuse](NOTICE.md)
