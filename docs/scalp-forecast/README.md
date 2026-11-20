# An arm forecast from the first quarter-second

A person sees a cue to bend the elbow. By the time a quarter of a second has passed, a few movement readings may already hint at what comes next. Six scalp channels give the model another source of evidence. Does it make a closer forecast when the person who moves has never supplied any of the fitting data?

Extract the whole ZIP. Open **index.html** in a browser or use **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh**. The reader computes every forecast locally and works offline. Links to the acquisition study and dataset need a connection.

## Try a comparison

Start with **Cue + motion + scalp** and **Cue + motion**. Open **Edit the early readings**, select the scalp recording and change C3 in its final time bin. Only the first forecast can respond. Switch to **Eye alone** to give the model just the three eye channels. Selecting **Cue + motion + eye** supplies all three sources. The scalp-only and eye-only fits use a constant internal cue and a training-wide baseline. Selecting a different movement instruction does not change their results.

The starting values were invented near the scale of the fitting group’s aggregate readings. You can change the seven-way instruction, six scalp channels, three eye channels and both measurements from each of three movement sensors in each time bin. Clear a required number and the corresponding forecast disappears. Other models can continue with their own inputs. The model expects exactly the channels and time bins documented here. It scales inputs with fitting-group statistics and clips each standardized input at six standard deviations. Editing beyond that limit can leave a forecast unchanged. The editable example does not establish that a chosen combination of readings occurred in the source experiment.

## Which clocks count?

The cue is tick 0 on the 512 Hz event clock. Each electrical input is a mean of 64 stored samples. The inclusive bins cover −127 to −64, −63 to 0, +1 to +64 and +65 to +128 ticks. Bin two includes the cue. The last electrical reading is exactly 0.25 seconds after the cue. Scalp columns represent FC3, FC4, C3, C4, CP3 and CP4 in that order. Eye channels follow acquisition columns 62, 63 and 64 because header labels vary. Enter the native signal levels with the source recording reference. The predictor subtracts the first mean of each channel from all four of that channel’s means. There is no subsequent filtering or common rereferencing here.

Three mechanical sensors run at 64 Hz. The final permitted row is L = floor((cue tick + 128) / 8). Four bins span rows L−31 through L, eight consecutive rows per bin. Each input row contains the median levels of the elbow, forearm rotation and proximal index-finger glove, followed by the last-four minus first-four median for each sensor. The model uses the final levels as anchors. At each forecast horizon, the target is the later eight-row median minus that last early median, in native instrument units. The three horizon endpoints occur 0.5, 1.0 and 1.5 seconds after the cutoff (0.75, 1.25 and 1.75 seconds after the cue). The reader supplies no post-cutoff recording. Later measurements are available only to the study's scoring procedure.

## What the scores measure

The fitted models use the first three motor-execution runs from each of seven people. In development, a separate fit for each fold left one of those people out. The assessment applied the frozen final fit to a fourth execution run in each of five other people. Some earlier mechanical experiments used other runs from those five. The assessment concerns these specific recordings, instructions and instruments. These results do not establish transfer to new tasks, laboratories or uncalibrated physical angles. The model provides no medical control or actuation.

Choose an evaluation group and a sensor to inspect the three absolute errors in that sensor’s native units. The overall score divides each of the nine errors by its own fitting-group target standard deviation before averaging. Trials within a cue, cues within a run, runs within a person and people receive equal weight at their respective stages. The seven development folds have their own fitting scales. The 95% intervals resample whole people and summarize paired differences in overall error. They do not describe the uncertainty of an individual synthetic forecast. The assessment criterion for each comparison requires at least 5% lower average error and lower error in every assessment person. The full criterion for an advantage beyond measured eye signals also requires the prespecified practical and pairing checks. [Frozen protocol](method/PROTOCOL.md) · [Development cohort](method/development.json) · [Fourth-run cohort](method/assessment.json)

In the 210 assessment trials, adding scalp to cue and movement changed the overall error from 0.508530 to 0.508563. Three of five people had lower error. The paired difference averaged +0.0000335 and its exploratory 95% interval ran from −0.001048 to +0.001375. The cue median scored 0.492784 and predicting no change scored 0.564891. Of the prespecified individual comparisons, only the scalp model’s advantage over predicting no change passed. The full practical criterion and the criterion for added information beyond the measured eye channels both failed. [Assessment scores](method/assessment.json)

The physiology question is narrower than the forecasting question. An earlier check in the seven development people found a median absolute correlation of 0.327 between the central scalp mean and eye channel 63 during the quarter-second after the cue. Pairing scalp and eye recordings from adjacent trials of the same cue and run yielded 0.195. The central scalp mean averages C3 and C4. The statistic pools within-trial Pearson correlations by run, person and cohort. Shared variation can have several origins. The forecast comparison asks whether the extra scalp measurement predicts the later movement once the instruction and early movement are known. A direct comparison with the model given eye channels addresses one possible source of predictive information. Neither comparison localizes a cortical generator.

## Models and controls

The cue-plus-motion model receives the movement instruction, early movement summaries and final mechanical levels. Adding scalp or eye inputs changes which measurements the time bins contain. The combined Transformer takes both. **Scalp differences** uses three bilateral contrasts (FC3−FC4, C3−C4, CP3−CP4) so its electrical input has the same channel count as the eye comparison. Each Transformer mixes one cue/anchor token and four ordered time bins using two attention heads. Ridge models use regularized linear fits on the same selected measurements. The cue median and cue mean come from training people. **No change** predicts zero at every horizon.

The mismatched fit learned from a different scalp trial of the same person, run and cue during training. Its live row accepts the readings you supply. Rows labelled **shuffled** in the evidence table replace a recipient's scalp readings with each other same-cue, same-person, same-run trial at scoring time, keeping the recipient's other readings and target fixed. Those rows require a set of recorded trials. The model and scoring source use different names for these two operations.

## Reproduce a number

The offline page uses the same fitted weights as the NumPy predictor. The example request contains `cue`, `method`, `history` (4×6), `scalp` (4×6) and `eye` (4×3). Each method needs only the fields it uses. The result's `delta` array has one row per horizon and three columns ordered elbow, forearm rotation, index glove. To run it, install NumPy in your own Python environment and invoke these commands from the extracted folder. Rebuilding the reader and ZIP needs Python 3.10+ and its standard library.

```sh
python method/predict.py method/example.json
python build.py --zip ../scalp-forecast-offline.zip
```

All study hashes in the reader are recorded in the provenance file. The cohort projection preserves aggregate method scores, paired intervals and counts. The package omits trial trajectories and individual score profiles. [Weights](method/model.json) · [Synthetic input](method/example.json) · [NumPy implementation](method/predict.py) · [Browser implementation](src/predict.js) · [Source hashes](method/provenance.json) · [Credits](NOTICE.md) · [Full study and training code](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/scalp-forecast)
