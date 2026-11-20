# How much load will the right foot’s platform record?

A person sets their right heel down on a force plate. We know where the heel and forefoot were during the last 240 milliseconds. We also have electrical recordings from eight muscles in that leg. Can those recordings tell us more about the upward force the platform will register ten camera frames later?

This experiment uses the platform that caught the right foot at its first recorded heel strike. The authors’ trial table had to identify two reliable, distinct platforms, one for each foot. The right heel and second-metatarsal markers also had to fall inside the assigned platform at that strike. We tested four fixed times after the strike, wherever the necessary history was available. The inputs follow the stored clock. The original signals were filtered in both time directions, so this experiment does not establish a live prediction lead time. [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-and-floor/)

## What the comparisons showed

Twenty-five people supplied 61 qualifying training trials and 203 input windows. Eight different people supplied 16 qualifying test trials and 53 windows. These were the assessment people designated for the companion two-platform study. Both fits excluded the reserved group. This question uses the source-assigned right platform and a different set of times.

| Forecast | Mean absolute error (N) |
| --- | ---: |
| Time since the strike | 93.08 |
| Linear fit to markers and strike timing | 93.40 |
| Linear fit also given muscle recordings | **82.04** |
| Markers, strike timing and the frozen movement encoder | 93.93 |
| Same encoder plus muscle recordings at the readout | 85.18 |
| Same design after shuffling the encoder weights once | 86.63 |

The fixed encoder is the part of NeuroTranslate that learned movement patterns in earlier tasks. A new readout uses its summary of the two foot markers. The electrical measurements enter the readout alongside that summary. Adding them reduced average error by 8.75 N against the marker-only shared model, with lower error in five of eight people. The 95% interval for the signed change in error ran from −28.99 to +9.03 N. The ordinary linear fit given both kinds of measurements did better on average than the shared model.

On the 44 windows with a comparable second trial, changing only the electrical input to that of another repeat at the same elapsed time gave 85.02 N error. Correctly paired input gave 83.26 N. Five of the six people had effectively identical mean errors after this swap. For them the individual errors on each side of the swap all had the same sign; permuting additive terms therefore left their average unchanged. Only one person contributed a substantial improvement. Neither the fixed test for added information from muscle activity nor the test for an advantage from earlier encoder training passed. If the current measured platform force was also available, simply carrying it forward gave 76.45 N across all 53 windows. [Per-person results, exclusions and paired comparisons](results.json)

## Run the model

In the parent model folder, use Python and NumPy:

```sh
python predict.py right-plate/example.json
```

The example is invented. Its four foot-marker rows list the heel’s laboratory x, y and z coordinates followed by the forefoot’s x, y and z, in metres relative to the assigned plate centre. The rows are the last point sample in each of four consecutive 60 ms bins. The cutoff is 14, 24, 34 or 44 point frames after the annotated strike. Optional electrical inputs are root-mean-square amplitudes in microvolts for the same bins. Give zero and a zero validity flag for an unavailable amplitude. The model estimates the mean force in a 10 ms block centred ten stored frames after the cutoff block. Outputs are in newtons and retain the regression’s sign.

Use `phase`, `marker_ridge` or `marker_shared` without electrical fields. Use `combined_ridge`, `combined_shared` or `scrambled_combined` with both `emg_uV` and `emg_valid`. The muscle order is tibialis anterior, soleus, medial gastrocnemius, vastus medialis, rectus femoris, semitendinosus, gluteus maximus and gluteus medius, all on the right. No current or future force value enters these six learned forecasts. [Example results](example-results.json) · [Frozen method](METHOD.md)

## Reproduce the comparison

Céline Schreiber and Florent Moissenet published the original overground recordings under CC BY 4.0. Download the version 8 walking ZIP and the original Supplemental Table 2 DOCX. The acquisition article describes the filtering and protocol. The prose states a 5 N force cutoff, while the authors’ versioned export uses 50 N. The export can contain zeros below that floor. The present analysis adds no threshold. [Versioned data](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Article and supplement](https://doi.org/10.1038/s41597-019-0124-4) · [Source licence](https://creativecommons.org/licenses/by/4.0/)

Use the source preparation instructions for the [two-platform study](../../walking-force/), or `python right-plate/prepare_source.py --help` from the parent directory. The preparation tool verifies the archive, reconstructs the fixed roster and writes one directory per partition with source contact codes. With Python 3.11+, ezc3d and NumPy installed, run:

```sh
python right-plate/study.py fit PRIVATE_DIR/train parent.npz rebuilt.npz
python right-plate/study.py score PRIVATE_DIR/assessment rebuilt.npz reproduced.json
```

The model checks the fixed method, the original parent weights and the source partitions. The readout was first trained and sealed before the right-platform assessment was run. The portable parent checkpoint is available from the preceding release. [Frozen parent weights](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/3db01687b3864633ec53fb44ee53f1dda47621f4/models/neurotranslate-0.0/movement-weights.npz) · [Shared checkpoint notices](../NOTICE.md)
