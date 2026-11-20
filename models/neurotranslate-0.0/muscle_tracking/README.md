# Tracking a muscle as it shortens and lengthens

An ultrasound probe on the front of the shin records a bundle of muscle fibres while a seated volunteer lifts the forefoot. The software estimates the length of that bundle in the image and its angle relative to nearby connective tissue. Give the model 21 original tracking rows. It predicts the change in length over the next ten tracking steps. Negative values mean shortening. [Try the model](https://eliminatenoise.github.io/NeuroTranslation/shared-muscle-tracking/) · [Explore the anatomy](https://eliminatenoise.github.io/Interoceptomics/muscle-tracking/)

## Use the model

Open **index.html** to change the invented length and angle histories and see what each method predicts. The diagram uses your last length and angle. It shows what would happen if the bundle kept the same span across the tissue while its longitudinal span continued its recent change. A real muscle need not obey that assumption. The diagram represents a line in the image plane.

The Python entry point runs the same calculations. From the package folder containing `predict.py`, with NumPy installed, run:

```sh
python predict.py muscle_tracking/example.json
```

Use `muscle_tracking` as the domain. Supply 21 consecutive `length_mm` values in chronological order. Methods that use angles also need 21 corresponding `angle_deg` values, from the same source rows. All methods return the signed change and the predicted later length in millimetres. The horizon is ten original tracking steps; files with different tracking density need not represent the same elapsed time.

| Methods | Inputs and calculation |
| --- | --- |
| `hold`, `recent`, `typical` | Length. Hold the last value, continue its previous ten-step change, or add the typical change seen during training. |
| `geometry` | Length and angle. Hold the transverse span fixed and continue the recent change in longitudinal projection. |
| `linear_length`, `shared_length` | Length. Fit a correction to the recent change, using either a linear model or the shared movement encoder. |
| `linear_both`, `shared_both`, `random_both` | Length and angle. Compare a linear readout, the trained movement encoder with a new readout, and an untrained encoder of the same size with a fitted readout. |

## What the recorded tracks showed

Four people supplied the original fitting recordings. Each development comparison left a whole person out. The separate evaluation used 776 forecasts in 4 new people from the same dataset. The shared encoder averaged 0.226 mm absolute error from length history and 0.219 mm after adding angle history. Keeping the length history but supplying angles from a different trial of the same person gave 0.241 mm. The simple geometric estimate gave 0.249 mm. The full model fell short of its registered paired-angle test. Forecast errors weight people equally and the two trials within each person equally. [Group results and paired comparisons](assess-summary.json) · [Research supplement](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-tracking/)

The angle and length estimates share the same images. The tracking software can smooth the traces or carry forward errors. A relationship between two features of one tracked line cannot establish independent muscle activation. The original files also contain electrical and motion records; the particular ultrasound frame belonging to each electrical timestamp has yet to be verified. No muscle force is measured by this model.

## Reproduce the comparison

Use the [study acquisition program](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/muscle-tracking) to create the qualified tracking files and their matching source receipts. Then run `python muscle_tracking/study.py fit DATA_DIRECTORY FIT_OUTPUT` in the main CPU package. To score a complete independent cohort, run `python muscle_tracking/study.py assess DATA_DIRECTORY TEST_OUTPUT --model FIT_OUTPUT/model.json`. The published study specifies any source qualifications needed before using a physical measurement. The movement checkpoint and the untrained comparison encoder are already in the package. The new fitted readouts are stored in `muscle_tracking/model.json`. [Frozen comparison design](DESIGN.md) · [Development scores](fit-summary.json)

Qiang Zhang, Noor Hakam, Oluwasegun Akinniyi, Ashwin Iyer, Xuefeng Bao and Nitin Sharma released the AnkleImage data under CC BY 4.0. This reader contains trained coefficients, error summaries and an invented example. The geometry drawing is computed from that example or the values you supply. [Original dataset and licence](https://doi.org/10.6019/S-BIAD1482) · [Original research article](https://doi.org/10.1038/s41597-024-04285-x)
