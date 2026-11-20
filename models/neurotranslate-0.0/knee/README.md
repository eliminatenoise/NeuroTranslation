# Can an earlier movement model help predict a knee bend?

Watch both knees for four seconds while someone walks on a treadmill. Find the earlier stride that looks most like the current one and use it to predict how far each knee will bend 15 frames later. That gives a starting answer. Can the pattern of the past four seconds tell us how to correct it? [Try a walk](https://eliminatenoise.github.io/NeuroTranslation/knee-stride/)

NeuroTranslate already had a component that learned patterns in tracked wrist and rat movement. We kept its learned weights fixed. We divided each walk into four one-second pieces, describing each knee by its average angle, final angle and recent change. A new calculation learned to correct the stride forecast using those summaries, the match to the earlier stride and the patterns the existing component picked out.

| Four-second forecast | Average error in degrees |
| --- | ---: |
| Replay the previous stride | 3.535 |
| Correct the replay using the summaries and stride match | 3.460 |
| Also use the existing movement model | 3.465 |
| Use one copy of the existing model with its learned numbers scrambled | 3.422 |

The existing model improved on replay for nine of 12 walkers. Across all 12, its average error was 0.070° lower. The 95% interval for that change ran from −0.170° to +0.039° when resampling whole people. The scrambled version had the smaller error for nine walkers. These comparisons give no evidence here that the earlier training helped. A separate Transformer trained specifically to correct knee forecasts did better, at 2.679°. Its inputs describe the detailed motion around the stride match. Comparing those two models changes both the input representation and the training. [Specialist model and controls](../../knee-stride/) · [Shared-model errors by walker and knee](results.json) · [Frozen methods](protocol.json)

Thirty-nine people supplied training data. We fitted the corrections on every sixth eligible cutoff within each person's walk, giving each person the same weight. The evaluation used all 40,201 eligible cutoffs from 12 different people whose earlier forecast results were already known. Adjacent cutoffs overlap. The belt speed was 0.5 m/s. Both the inputs and the later reference angles come from Xsens's reconstruction of body-worn sensor measurements. Some reconstructions used the whole recording. The forecast advances 15 stored frames at 60 Hz. A live sensing deadline would need a separate test.

## Run one forecast

From the parent model folder, run this command with Python and NumPy.

```sh
python predict.py knee/example.json
```

The example contains invented right and left knee angles for 240 consecutive frames. Set `mode` to `stride`, `raw`, `shared` or `scrambled` to repeat the four comparisons in the table. The output lists the two angles in right/left order and the matched stride length in frames. The same model file runs the earlier distance, wrist-angle and population-firing examples.

## Reproduce the fit

Download the exact parent weights from the linked earlier edition. Use the joint-angle extraction instructions in the original knee study to obtain the licensed files with their recorded checksums. Pass the directory containing the individual IMU_S folders as `INPUTS`. The fit verifies the original weight and source hashes. The score uses the separate evaluation people. It writes per-person errors and paired comparisons. [Frozen parent weights](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/b5b642110ed3734b434830e1bd477d269749aa4a/models/neurotranslate-0.0/movement-weights.npz) · [Original extraction instructions](../../knee-motion/REPRODUCE.md)

```sh
python knee/study.py fit INPUTS parent.npz rebuilt.npz
python knee/study.py score INPUTS rebuilt.npz rebuilt-results.json
```

Rateb Katmah, Aamna AlShehhi, Doua Kosaji, Nour Al-Rahmani, Muhammad Abdullah, Abdul Aziz Vaqar Hulleck and Kinda Khalaf (2026) released the original PhysioNet dataset (version 1.0.0) under CC BY 4.0. The knee corrections and derived results retain that attribution. The new source code carries the repository's CC0 dedication. The earlier checkpoint also carries its original data terms. [Original data](https://doi.org/10.13026/r0ea-7161) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Checkpoint notices](../NOTICE.md)
