# When eye and scalp signals move together

A person walking along a narrow beam sees the virtual scene rotate. Two markers record how the head and the sacrum, a bone at the back of the pelvis, move. Electrodes record voltage at the scalp, beside the eyes, and over muscles in the neck and legs. How well do these readings forecast the next 125 milliseconds of marker travel? [Change an invented signal](index.html) · [See an actual recording in the Interoceptomics atlas](https://eliminatenoise.github.io/Interoceptomics/visual-balance/)

## Try the model

Open **index.html** in a browser. The green trace shows the invented eye signal. Add part of that pattern to the scalp trace, then compare a forecast with scalp voltage, one without it, and one that subtracts the part predicted from the eye and muscle signals. The example runs offline. The slider values do not measure how much an actual electrode picks up from the eyes.

From the directory containing `predict.py`, install NumPy and run:

```sh
python predict.py visual_balance/example.json
```

The `visual_balance` input takes the direction of the visual rotation, `clockwise` or `counterclockwise`. All forecasts give displacement in millimetres for the sacrum and head, along the recorded mediolateral, superior–inferior and anterior–posterior axes. We did not establish which anatomical direction corresponds to the positive sign of each axis.

The full model takes 160 consecutive samples in `motion_mm` (at 256 Hz, sacrum first). For the electrical signals, supply eight successive 20-sample bins. `eeg_mean_uv` and `eeg_rms_uv` contain the mean voltage and root-mean-square amplitude in microvolts from each of the 128 cap sites, in A1 through D32 source order. `nuisance_mean_uv` and `nuisance_rms_uv` contain the same summaries for two neck channels, three eye channels and eight leg channels. See the [source reader](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/visual-balance/source) for their order. `eeg_good` and `nuisance_good` flag available, good channels. Supply finite placeholders at unavailable sites; their values do not enter the estimate. Use histories and a cutoff admitted by the source reader for comparisons to the reported study. Custom input cannot establish its own tracking quality or sensor clock.

Choose `linear_motion` for the simple motion-plus-direction model. Its only measurement input is `motion_mm`. The `shared_full` model also uses the electrical signals and their masks, and `shared_nuisance` omits scalp voltages while retaining the same mask. `shared_residual` subtracts a training-fitted estimate of scalp voltage predictable from eye and muscle signals. The source groups eight scalp labels for each feature. Such a group is a computational input; assigning it a cortical function would require other measurements.

## Which model should I compare first?

Start with recent motion and rotation direction. The fitted linear model using these inputs averaged **7.37 mm** error at the sacrum and **6.62 mm** at the head on 880 qualifying events from six people held out of fitting. The more complex shared model that also saw scalp, eye and muscle signals averaged **8.58 mm** and **7.74 mm**. With scalp voltage withheld it scored **8.11 mm** and **7.43 mm**. Replacing the scalp signal with one from a different event for the same person, direction and part of the walk gave **8.63 mm** and **7.98 mm**. Neither landmark met both adjusted tests for an incremental benefit from scalp voltage.

The [separately trained Transformer](https://eliminatenoise.github.io/NeuroTranslation/visual-balance/) reached **7.80 mm** and **7.18 mm** with scalp input. It also missed both criteria. The simple model is a useful first comparison on these stored recordings. These errors do not establish that a scalp signal caused later movement. [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/visual-balance/) · [Historical scores](historical.json) · [Between-model differences](historical-model-comparison.json)

## Reproduce the comparisons

Regenerate the development and assessment NumPy files with the source reader. The following commands use the parent folder containing `predict.py`. Individual row predictions and fitting-fold weights go to your own `results` directory when `--private` is supplied.

```sh
python visual_balance/study.py fit prepared/development.npz fitted.json development.json --private results
python visual_balance/study.py score prepared/assessment.npz fitted.json historical.json --private results
python visual_balance/neighbors.py prepared/assessment-qc.json prepared/assessment.npz results/historical-rows.npz neighbors.json
python visual_balance/directions.py prepared/assessment.npz results/historical-rows.npz directions.json
```

Seventeen of eighteen development participants supplied 2,430 usable events. In one person the recorded head coordinates stayed at zero. All six assessment people supplied usable events. Source motion tracking gaps can appear as zeros, so they were excluded even where the stored numbers were finite. The scalp voltage can include eye and muscle activity. The movement stream has already been interpolated onto the EEG clock. The six reserve EEG recording files remained unopened.

Steven M. Peterson and Daniel P. Ferris prepared these open recordings. Source metadata lists CC0. [Study](https://doi.org/10.1016/j.dib.2021.107635) · [Dataset version 1.0.3](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Original balance analysis](https://doi.org/10.1523/ENEURO.0207-18.2018) · [Prespecified output-layer comparison](DESIGN.md)
