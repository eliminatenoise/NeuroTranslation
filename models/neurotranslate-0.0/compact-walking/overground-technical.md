# Overground heel forecast evaluation

[Simple edition](overground-simple.md) · [Download the offline example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/neurotranslate-0.0/compact-walking/overground-preview.zip)

The complete-case mean error was **25.33 mm** with a causal pelvis-velocity correction and **67.54 mm** for the last-change baseline. The paired difference was **42.21 mm lower**, with a 95% participant bootstrap interval of **40.56 to 43.76 mm lower**. All 55 participants had lower error.

## Recordings and forecast times

Horst and colleagues released overground barefoot gait trials with 250 Hz optical coordinates. The run used all 1,104 named gait trials from 55 participants. Two separate participants supplied engineering checks. The recorded heel channels are `L HEEL` and `R HEEL`. The horizontal body velocity comes from the midpoint of `L ILIAC` and `R ILIAC`. Coordinates are millimetres, aligned as lab Y, negative lab X, and lab Z, giving left, backward, and up in model order. [Mainz raw C3D release](https://data.mendeley.com/datasets/svx74xcrjr/2) · [Study methods](https://doi.org/10.1038/s41598-019-38748-8)

Use one finite native point with a positive C3D residual every 20 ms. The residual records an error estimate from reconstructing the point. The archive omits the optional camera identity masks. Each forecast uses ten selected positions from a complete 200 ms native interval. The nominal issue is 10 ms after the last selected point. At 250 Hz the target falls 25 native frames after that point, exactly 100 ms after the last reading and 90 ms after nominal issue. Forecast starts are 320 ms apart, with a fixed initial phase from the first two bytes of the SHA-256 of the archive member name. The target and history rows are disjoint. [C3D marker and residual format](https://www.c3d.org/HTML/Documents/3ddatafloatingpointformat.htm)

Of 4,142 scheduled starts, 43 lacked a full native history interval and three lacked an observed heel in that history. The final **4,096** forecasts were frozen before target decoding. One of the 8,192 future heel points failed the residual gate. One additional start lacked a complete pelvis history, leaving **8,189** heel outcomes for the joint comparison.

## Frozen forecast methods

Subtract the first selected position independently from each heel's ten inputs. The physical baseline multiplies the difference between the final two positions by five. The released Compact model was fitted on treadmill recordings. This test averages seeds `2731` and `4119` coordinate by coordinate with the force inputs set to unavailable. [Frozen model and weights](https://github.com/eliminatenoise/NeuroTranslation/tree/2e6e3e4ac3caf3bcc5adde13ca5a5f48a3a63f46/models/neurotranslate-0.0/compact-walking)

Fit a straight line to each horizontal component of the ten earlier iliac midpoints. Subtract the resulting velocity times elapsed history time from both heel histories. Run the same frozen predictor and add 0.1 seconds of that velocity to the output. The separate pelvis-only comparator uses the restored translation alone. Error is the straight-line distance in millimetres from the forecast to each observed heel position. Average within each participant, then give all 55 participant means equal weight. The paired intervals use 10,000 participant resamples.

| Method on common pelvis support | Mean heel error |
| --- | ---: |
| Last position | 155.40 mm |
| Last-change baseline | 67.54 mm |
| Unchanged Compact | 88.62 mm |
| Iliac midpoint velocity alone | 154.45 mm |
| Compact with pelvis travel removed and restored | **25.33 mm** |

On the primary 8,191 heel outcomes the unchanged Compact error was 88.62 mm and the last-change error was 67.54 mm. The difference was 21.08 mm higher for Compact, with a 95% paired interval from 19.84 to 22.31 mm higher. The measured scope is barefoot walking with optical markers at one external lab.

The archive provides capture frame times. End-to-end latency for producing and receiving a marker reading in a live system remains unmeasured.

Fabian Horst, Sebastian Lapuschkin, Wojciech Samek, Klaus-Robert Müller and Wolfgang I. Schöllhorn released the Mainz recordings under CC BY 4.0. The scores above are aggregate calculations. [Dataset and licence](https://doi.org/10.17632/svx74xcrjr.2) · [Original study](https://doi.org/10.1038/s41598-019-38748-8)

## Run the frozen transform

With Node.js 18 or later, run an included launcher or enter `node overground.mjs overground-example.json` in the extracted folder. The example is invented. Input JSON uses `time_ms` for ten times exactly 20 ms apart and `heel_mm` and `pelvis_mm` for ten rows each. Each row gives the left and then the right marker in the same signed millimetre axes. All required observations must be present. Each output vector is a six-component displacement from the last observed heels.
