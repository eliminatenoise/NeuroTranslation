# Where will the heel go?

A walker steps onto a floor plate. Here a camera system follows the right heel and forefoot, electrodes record eight right-leg muscle signals, and a plate measures the upward force during the same step. The model estimates heel travel along the three laboratory axes in millimetres and the plate reading in newtons 100 milliseconds later. [Try the model](index.html) · [Replay a recorded step in the Interoceptomics atlas](https://eliminatenoise.github.io/Interoceptomics/heel-and-force/)

## Try an invented step

Open **index.html** in a browser. Change the heel travel, strength of the shin signal or time since foot strike. Each change runs the selected method on the new history. The browser includes all the weights and works offline. In the package directory containing `predict.py`, install NumPy and run `python predict.py heel_force/example.json` to get the full-precision forecast.

Each input contains 24 consecutive 100 Hz frames in `markers_mm`. In each frame put the XYZ positions of the heel first and the forefoot second, in the same laboratory axes as the source. Set `offset_frames` to 14, 24, 34 or 44 frames after right foot strike. Supply four consecutive rows of eight skin-electrode amplitudes in microvolts as `emg_rms_uv` for a method that uses muscle signals. Each amplitude is the root mean square of 90 stored samples. The source protocol gives their order. The motion-only methods require just markers and time. The two methods using earlier plate force require `prior_plate_n` containing the two trailing averages, most recent first.

## Which forecast held up?

The movement encoder stays fixed. The compressed output layer learns two combinations of its inputs to predict all four numbers. The unrestricted layer can learn a separate correction for every output. Both use the same input measurements. On the original assessment repeats from eight people, the compressed model missed the heel by **1.85 mm** and the plate by **89.8 N** on average. The unrestricted model missed by **1.23 mm** and **91.8 N**. On later repeats from six of those people the corresponding pairs were **1.46 mm and 110.2 N**, and **1.12 mm and 106.9 N**. Compression missed the prespecified requirement. The recordings also gave no consistent evidence that matched muscle readings improved both forecasts. [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/heel-and-force/) · [Try the separately trained Transformer](https://eliminatenoise.github.io/NeuroTranslation/heel-and-force/)

The eight people supplied 16 original repetitions and 53 paired observations. Six of them supplied ten later repetitions and 31 observations. Results give equal weight to each person, then each repetition. The authors processed signals using samples on both sides of each instant. The clock belongs to the stored recordings. A skin marker can shift relative to the bone, and force under the foot cannot tell us how much force came from any one muscle.

## Reproduce the output layers

Use the [source reader](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/heel-and-force) to regenerate the three NumPy archives. The following commands use the same names as that reader. From the directory containing `predict.py`, with NumPy installed, run:

```sh
python heel_force/study.py fit prepared/development-v1.npz fitted.json development.json
python heel_force/study.py score prepared/historic-assessment-v1.npz fitted.json historical.json
python heel_force/study.py score prepared/later-repeats-v1.npz fitted.json additional.json
```

The first command fits on 25 people, first leaving whole participants out for comparison and then fitting one final model. The other two commands use those final weights without updating them. `--private DIRECTORY` also saves row-level predictions locally. [Prespecified methods](DESIGN.md) · [Development](fit-summary.json) · [Original assessment repeats](historic-assessment-summary.json) · [Additional repeats](later-repeats-summary.json)

Schreiber and Moissenet released the source recordings under CC BY 4.0. [Source recordings, version 8](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Study and Supplementary Table 2](https://doi.org/10.1038/s41597-019-0124-4) · [Licence](CC-BY-4.0.txt)
