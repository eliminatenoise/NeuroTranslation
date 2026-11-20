# What will the neck electrode read four milliseconds later?

A brief stimulus at the left wrist left a trace in electrodes over the neck, at the upper arm, on the scalp, over a thumb muscle and on the chest. Give the Transformer the early readings and it forecasts one number in microvolts. That number is the mean neck voltage from 12 to just before 14 milliseconds after the stimulus, relative to the neck voltage averaged 15 to 10 milliseconds before it. The last input sample arrived at 7.9 milliseconds. The neck electrode, SC6, measured voltage relative to an electrode on the back, TH6. A surface voltage can mix contributions from several tissues.

## Did the arm reading help?

Four people supplied the training data. Six others supplied the assessment, 80 events per person in the same recording study. The matching arm signal improved the Transformer's mean absolute error compared with leaving the arm signal out. Giving that same fit the arm reading from a *different* stimulus did better still. One of six people improved against both controls. Simply carrying the last one-millisecond neck reading forward gave 8.09 µV mean absolute error.

| Six-person assessment | Matching arm | Arm omitted | Wrong event, same fit | People better than both controls |
|---|---:|---:|---:|---:|
| Transformer | 23.28 µV | 24.67 µV | 22.36 µV | 1 of 6 |
| Robust linear correction | 9.65 µV | 7.77 µV | 10.05 µV | 3 of 6 |

Errors are averaged within each person first. The improved matching for one comparison in each model does not establish that a particular nerve or spinal pathway caused the forecast. The participants lay still. Movement, therapy and stimulation control were outside this experiment. [All assessment errors and sign tests](assessment.json) · [Assessment rules](ASSESSMENT.md) · [Earlier development scores](development.json) · [Illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/cervical-forecast/)

## Make one forecast

Extract the model ZIP. With Python 3 and NumPy installed, run the launcher for Windows, macOS or Linux in the extracted folder. It evaluates an invented input using both fitted Transformers. To supply another input, pass its path to the launcher, or run the example in a terminal from this folder.

```sh
python forward.py example.json
```

The JSON accepts `baseline` (50 time samples by five channels), `early` (30 by five) and `event_index` (an integer from 0 to 79). Both windows use the native 10 kHz grid. In each row the order is Biceps, SC6, Thumb, CP4 and ECG, all in microvolts. The output keys `eng` and `noneng` identify independently fitted Transformers with and without the early arm signal. The package keeps the source channel names. “Biceps” is the label for a **surface nerve recording at the axilla**, paired with BicepsN. “Thumb” is a surface muscle recording at abductor pollicis brevis. CP4 is scalp voltage relative to the right mastoid. The ECG records a chest voltage difference. [Channel names and reference electrodes](CHANNELS.md) · [Try the browser reader](https://eliminatenoise.github.io/NeuroTranslation/cervical-forecast/) · [Compare electrode sites](https://eliminatenoise.github.io/Interoceptomics/cervical-signals/)

## Reproduce the comparison

Use Python 3.10 or later with NumPy for acquisition, inference and assessment. The acquisition program fetches the pinned original metadata and byte ranges from OpenNeuro's public dataset. Give it an output directory outside the extracted package. It checks the native channel order, event clock and source object identity. Each output gets a matching receipt. [Source selection, attribution and checks](source/README.md)

```sh
python source/acquire.py --group development --output ../development
python source/acquire.py --group assessment --output ../assessment
python assess.py ../assessment ../six-person-results.json
```

To repeat fitting, install CPU PyTorch. The reference Transformer fit used Python 3.11.16, NumPy 1.26.4 and PyTorch 2.8.0+cpu with two intra-op threads and one inter-op thread. Four rounds each leave one person out. A final fit uses all 320 development events. Every Transformer uses 100 full-batch updates, with a fixed seed and no early stopping. The following commands use fresh output folders. Fitting writes local trial predictions for checking the cross-validation calculations. The download contains fitted weights and summary statistics only, alongside synthetic software examples.

```sh
python fit.py --development-dir ../development --out ../transformer-fit
python robust/study.py ../development ../robust-fit
```

The robust readout fits a correction to the last one-millisecond neck reading. Its three fitted variants use neck data alone, the other electrode sites without the upper arm, or every site. The same readout is available in NeuroTranslate 0.0. It has its own coefficients. [Try the robust forecast](https://eliminatenoise.github.io/NeuroTranslation/neck-voltage/) · [Transformer architecture](PROTOCOL.md) · [Data selection](ACQUISITION-CLARIFICATION.md) · [Robust model design](robust/design.json)

Birgit Nierula, Tilman Stephani, Merve Kaptan, André Moruaux, Burkhard Maess, Gabriel Curio, Vadim V. Nikulin and Falk Eippert released the original data under CC0. This package contains the separate analysis, fitted coefficients and invented inputs. [OpenNeuro ds004388 v1.0.0](https://doi.org/10.18112/openneuro.ds004388.v1.0.0) · [CC0 dedication](CC0.txt)
