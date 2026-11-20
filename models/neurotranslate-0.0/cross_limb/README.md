# A wrist and a pelvis on the same clock

Two studies tell us where a marker went and how the nearby muscles behaved. In one, the marker followed a wrist reaching for an object. In the other, a marker on the sacrum followed the lower back during standing or walking. A shared rule can read 625 ms of either recording and forecast the next 125 ms. The people and movements in the two studies are separate. [Open the offline comparison](index.html) · [See two original recordings](https://eliminatenoise.github.io/Interoceptomics/cross-limb-movement/)

## Change an invented recording

Choose a wrist or pelvis history in **index.html**. Turn the displayed axes or multiply the first muscle’s earlier amplitude by a known factor. The fitted rules use ratios to that muscle’s own past levels and combine previous movement vectors. Turning the axes should turn their forecast. Changing the voltage scale of an observed muscle should scale its forecast while preserving the other outputs. The task-average comparator uses its original coordinate system and amplitude scale.

Each input bin spans 31.25 ms. For the arm, a bin contains 125 native electrical samples; for the leg it contains eight. Both supply twenty consecutive bins. The wrist position is the latest available 500 Hz knot at each bin end. The archive’s wrist coordinates are in centimetres and were converted to millimetres using the measurement definition in the authors’ analysis. The future wrist path is interpolated onto the 32 display times. Its 125 ms endpoint lies between original samples at 124 and 126 ms. The sacrum is measured on an already processed 256 Hz grid. Neither stored sequence establishes live sensor latency.

## Run a forecast

From the directory with `predict.py`, install NumPy and run either command:

```sh
python predict.py cross_limb/grasp_lift-example.json
python predict.py cross_limb/balance-example.json
```

The `cross_limb` domain takes the study, method, context, available channel names, 20 rows of nonnegative `patch_rms` in source units, 20 rows of XYZ marker knots in mm and `age_s` in seconds. `patch_xyz_mm` ends at the origin and uses the source’s own axes. `repeat_path_mm` is the preceding 125 ms path at 32 equally spaced offsets, relative to its *earlier* start. It contains no future observation. Each muscle name goes with its own column; reordering both leaves the forecast for that muscle unchanged. Supply all eight lower-limb channels or three to five qualified upper-limb channels. The output contains only those named muscles. The leg input's context is `standing_cw`, `standing_ccw`, `walking_cw` or `walking_ccw`; the arm context is `led_grasp_lift`.

| Method | What it uses |
|---|---|
| `pooled` | One rule fitted across both studies |
| `leg`, `arm` | One study’s full training data, directly applicable to either example using history-based normalization |
| `leg_limited`, `arm_limited` | Only the first third of the selected target study's development logs |
| `arm_to_leg`, `leg_to_arm` | The same early target data, with coefficients adjusted from a prior fit in the other study |
| `hold_still`, `hold_repeat`, `hold_velocity` | Hold recent muscle amplitude; keep the position fixed, repeat the previous trajectory or extend its mean 125 ms velocity |
| `context_mean` | Return the typical fitting target for the corresponding study and task |

A recent muscle signal that stays completely silent has no history scale; the linear rule predicts zero for that channel. Unavailable sensors have no measurement to score. The movement rule can change frame without needing a correspondence between an anatomical wrist axis and the lower back.

## What did sharing improve?

With one pooled linear fit, the pelvis path missed by **3.39 mm** on average. Training the same rule only on balance gave **2.52 mm**. For the wrist, those two choices, pooled versus arm-only, scored **7.36 mm** and **7.70 mm**, respectively. The group muscle errors are reported separately because only the leg amplitudes have a verified microvolt scale. On the historical wrist records, none of the three participants had all five muscle channels qualified. The 882 lifts contributed three or four channels apiece. The sacrum comparison included 1,759 balance records from six people and all eight channels.

The [trained Transformer](https://eliminatenoise.github.io/NeuroTranslation/cross-limb-movement/) answered a different question about sharing learned temporal features. With equal arm-data exposure its shared wrist path scored **4.87 mm**, versus **5.10 mm** for the arm specialist. The arm specialist trained for the same *total* number of updates as the shared model scored **4.39 mm**. The shared model did not meet its prespecified advantage test across both tasks and outcomes. [Study and paper](https://eliminatenoise.github.io/NeuroTranslation/papers/cross-limb-movement/) · [Measured linear comparisons](historical.json) · [Matched models](historical-model-comparison.json)

## Reproduce the linear controls

The [data reader](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/cross-limb-movement/source) builds both source-specific histories, preserving their timing, sensors and original licences. From the package directory run:

```sh
python cross_limb/study.py fit prepared/development.npz coefficients.json development-full.json
python cross_limb/study.py assess prepared/assessment.npz coefficients.json historical-full.json
python cross_limb/public_summary.py historical-full.json historical-public.json
```

The fit uses only the prior fitting participants. Its development folds keep every event for a person in one fold. The historical participants remained outside the fit, although other studies in this programme had previously used their recordings. Three further arm and six further balance participants’ recording payloads remained unopened. The public channel error summaries require at least two contributing people for any particular channel. Full per-event values can be retained in your own local reproduction with the optional `--private` directory. [Prespecified linear comparison](DESIGN.md) · [Grasp measurements by Luciw, Jarocka and Edin](https://doi.org/10.1038/sdata.2014.47) · [Balance measurements by Peterson and Ferris](https://doi.org/10.1016/j.dib.2021.107635)
