# Forecast a worn sensor’s next turn

A sensor on a person’s back records how its orientation changes. This model sees a tenth of a second of earlier motion and two arrays of skin electrodes during instructed walking or standing. It predicts the size of the sensor’s turn during the next tenth of a second. The answer is an unsigned angle in degrees. A sensor turning two degrees to the left and one turning two degrees to the right both give a two-degree answer. [Open the model](https://eliminatenoise.github.io/NeuroTranslation/shared-back-rotation/) · [See where the measurements came from](https://eliminatenoise.github.io/Interoceptomics/back-rotation/)

## Try the model

Open **index.html** in a browser and change one row of the invented example. To use the Python model, open a terminal in the package directory containing `predict.py` and run the following command with NumPy installed.

```sh
python predict.py back_rotation/example.json
```

Choose `back_rotation` as the domain. The forecast uses the current instruction, `walking` or `standing`. The field `recent_angle_deg` is the unsigned change across the full 100 ms of history. Each of the four rows covers a consecutive 25 ms. List features in the order below, omitting voltage columns that a chosen method does not use.

| Input columns | What they mean |
| --- | --- |
| Two motion values | Endpoint change and total length along the measured rotation path (degrees). |
| Two upper-back values | Typical voltage variation and typical adjacent-sample change across the upper-back electrodes (µV). |
| Two lower-back values | The same two measures at the lower back (µV). |

`linear_motion` and `shared_motion` use the two motion columns. `shared_upper` or `shared_lower` adds only the two columns for its chosen region. `linear_full`, `shared_full` and `random_full` use all six. All these methods take the recent angle and instruction. `zero` requires only the domain and mode, `recent` adds the recent angle, and `task_median` adds only the instruction. The output field `unsigned_rotation_deg` carries the forecast.

## Did the electrical measurements help?

Four people supplied two trials each for fitting. Model comparisons during development left one person out at a time. Four other people were set aside before the fit. In both trials from one of them, the file lists three numbered orientation components and a buffer channel. An angle requires four verified components. The three people whose files passed that check supplied 2,304 windows. These results describe those three. Error was measured separately in each trial and task, then averaged equally across tasks and people.

The shared movement encoder’s mean absolute error was 0.376° from motion alone, 0.385° with both electrode regions, and 0.385° with electrical readings taken instead from another trial of the same person following the same instruction. Repeating the last rotation gave 0.445°. The planned four-person test remains incomplete. The trained and untrained encoders scored 0.385° and 0.382°, respectively, with the same inputs and readout-fitting method. [Results and paired comparisons](assess-summary.json) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/back-rotation/)

The existing movement encoder retains its original weights. The new readouts fit the difference between the forecast and recent rotation on a logarithmic scale. The linear comparisons receive the same input quantities without the encoder. The untrained encoder comparison uses a fixed random initialization and a fitted readout. The companion Transformer learns its own representation. The two studies also use different wrong-pair controls. [Try the task-trained Transformer](https://eliminatenoise.github.io/NeuroTranslation/back-rotation/)

## Reproduce the fit

Use the [original acquisition reader](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/back-rotation) to obtain the two source MAT files and source receipts per selected person in a local data directory. With NumPy and SciPy installed, run `python back_rotation/study.py fit DATA_DIRECTORY FIT_OUTPUT` here. The original four-person assessment stops when the input labels fail validation. Use the complete study package’s documented `qualified.py` command to reproduce the separate three-person description. The shared checkpoint is shipped in the parent folder. The optional `make_random.py` recreates the untrained control with PyTorch. [Frozen design](DESIGN.md) · [Development results](fit-summary.json)

The raw signals are voltages at the skin. They can contain contributions from muscles, the heart and movement of the electrodes. The orientation reading belongs to a strapped-on sensor. These measurements give no direct joint trajectory, force or transcript of someone’s intent. Desirée Irene Gracia Laso, Eduardo Iáñez, Mario Ortiz and José M. Azorín released the recordings under CC BY 4.0. This package contains fitted parameters, aggregate results and an invented input. [Source recordings and licence](https://doi.org/10.5281/zenodo.19065545) · [Original paper](https://doi.org/10.1038/s41597-026-07592-7)
