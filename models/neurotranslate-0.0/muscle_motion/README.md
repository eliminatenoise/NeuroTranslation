# From walking to standing

After a visual scene turns, a marker on the sacrum follows the movement of the pelvis. Eight skin electrodes record the electrical activity near four muscles in each lower leg. This model estimates the next 32 positions of the marker and the next 125 ms of muscle signal amplitude. One outcome is measured in millimetres, the other in microvolts. [Open the offline comparison](index.html) · [Explore two measured events](https://eliminatenoise.github.io/Interoceptomics/muscle-and-motion/)

## Try it

Open **index.html**, leave the invented history fixed and change the training recordings. One fit learned only from walking. Another adjusted its walking coefficients using the first third of each development participant’s standing event log. A third learned from exactly those standing examples starting from zero. The short green line shows the last part of the movement history. The dotted line shows the forecast. Muscles can have different voltage amplitudes even when the final marker position is the same.

To run the example in Python, install NumPy and run `python predict.py muscle_motion/example.json` from the folder containing `predict.py`. For your own data, set `domain` to `muscle_motion`. Supply `posture` as `standing` or `walking`, and `direction` as `clockwise` or `counterclockwise`. These are the actual task and visual scene labels. There was no spoken movement instruction in the archive.

Each of the 160 consecutive samples contains signed lower-leg surface voltages in `leg_uv` and one XYZ sacrum marker in `sacrum_mm`. Supply the four left channels followed by the four right channels. Each side uses tibialis anterior, soleus, medial gastrocnemius and peroneus longus, in that order. The position axes in the source are mediolateral, superior–inferior and anterior–posterior. Their anatomical positive directions are unverified. The model subtracts each history’s last marker position before computing the forecast. To compare measurements with the published study, use the original recorded clock, event definition and source quality checks.

| Method | Training or rule |
|---|---|
| `persistence`, `hold_position` | Retain the latest muscle amplitude and, respectively, repeat the preceding 32-sample path or stay at the last position |
| `velocity16`, `velocity32` | Retain muscle amplitude and extend the recent 16- or 32-sample velocity |
| `envelope_trend`, `context_mean` | Continue the amplitude change, or return the training average for the posture and cue |
| `pooled`, `pooled_no_posture` | Train on both postures, with or without the posture label |
| `motion_signal`, `muscle_signal` | Fit corrections from one signal family; both recent-value baselines are still supplied |
| `walk_only`, `stand_only` | Fit on all qualifying training events of just one posture |
| `stand_limited`, `adapted_walk` | Fit on the first third of the standing logs from zero slopes or around previously learned walking slopes |

The muscle outputs are the root mean square of a time-varying voltage over a future interval. They do not measure contraction length, force or the timing of a descending neural command. The position output gives all 32 future positions relative to cutoff (256 Hz, ending at 125 ms).

## Did walking training help?

On 879 standing events from six people outside training, the standing-only linear model trained on the early events missed the muscle amplitudes by **6.06 µV** and the sacrum path by **0.84 mm** on average. Starting from the walking coefficients and using those same standing examples gave **6.13 µV** and **0.87 mm**. The walking prior missed the prespecified improvement test. The model using all standing training events scored **5.34 µV** and **0.77 mm**, with more training observations.

Across standing and walking together, the pooled linear model scored **10.70 µV** and **2.12 mm**. Simply repeating the latest muscle amplitude and the recent path gave **10.27 µV** and **3.27 mm**. The separately trained [joint Transformer](https://eliminatenoise.github.io/NeuroTranslation/muscle-and-motion/) gave **9.50 µV** and **1.96 mm**. Its two specialist counterparts scored **9.45 µV** and **1.94 mm**. On these data the Transformer architecture improved on the pooled linear forecast, but sharing a single model between the outcomes did not establish an advantage over the specialists. [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-and-motion/) · [Historical paired comparisons](historical-model-comparison.json) · [Standing and walking tables](historical.json)

## Reproduce the fits

Use the [versioned source reader](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/muscle-and-motion/source) to prepare the original recordings. Run the commands below from the folder containing `predict.py`. A local `--private` output directory is optional and includes individual predictions.

```sh
python muscle_motion/study.py fit prepared/development.npz fitted.json development.json
python muscle_motion/study.py assess prepared/assessment.npz fitted.json historical.json
```

All fitting, including the posture transfer, used the 18 development participants. The test used six people outside the fit. Their prior walking recordings had appeared in an earlier study. Their standing records were newly assessed here. Another six participants’ recording files remained unopened. Standing preceded walking in the source design, so session order and posture cannot be cleanly separated here. The source used offline filters and optical interpolation. These forecasts establish performance on that stored clock. [Model specification](DESIGN.md) · [Original study by Peterson and Ferris](https://doi.org/10.1016/j.dib.2021.107635) · [CC0 dataset, version 1.0.3](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)
