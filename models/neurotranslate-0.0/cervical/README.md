# From the last neck reading to the next one

Someone lies still. The same timed event repeats while electrodes record from the neck, axilla, scalp, thumb and chest. Give the model the readings up to 8 milliseconds after the event. It estimates what the neck electrode will read from 12 to 14 milliseconds, relative to its baseline before the event. A different model in the same study makes that forecast using a Transformer. [Open the robust model](https://eliminatenoise.github.io/NeuroTranslation/neck-voltage/) · [Open the Transformer](https://eliminatenoise.github.io/NeuroTranslation/cervical-forecast/)

## Try it on your computer

Open **index.html** in a browser. The invented example works offline. Change one of the three late numbers in the axilla row, then choose **Calculate forecasts**. The model using the axilla gets a new input. The other methods still have their original information.

To run the same example with Python 3 and NumPy, start in the package folder containing `predict.py`.

```sh
python predict.py cervical/example.json
```

The input uses the domain `cervical_voltage` and names its method in `mode`. Each input channel has eight averages in microvolts. The first five cover consecutive milliseconds from −15 to −10 ms and the last three cover +5 to +8 ms. Each interval includes its starting sample. Supply exactly the named channels that the method needs.

| Method | Required channels |
| --- | --- |
| `event_median` | Empty readings object |
| `persistence`, `median_innovation`, `neck` | SC6 |
| `other_sites` | SC6, Thumb, CP4, ECG |
| `with_axilla` | Biceps, SC6, Thumb, CP4, ECG |

The output `mean_change_uV` is the predicted mean voltage over the later two milliseconds minus the mean of the five baseline bins. The recording labelled Biceps comes from a pair of electrodes at the axilla used to record the median nerve response. SC6 records at the back of the neck relative to an electrode over the back at T6. The chest electrode records heart activity. Each signal has its own reference. [Original research](https://doi.org/10.1371/journal.pbio.3002828) · [Dataset and licence](https://doi.org/10.18112/openneuro.ds004388.v1.0.0)

## What the added recording contributed

Four people contributed 80 events each to training. The development comparisons fit only three people at a time. After training on all four, the fixed models saw 480 events from six other people in the same study. Each person carries equal weight in the summary.

The four-site model missed by 7.77 µV on average in the six new people. Adding the paired axillary recording gave 9.65 µV. Feeding the same model an axillary record from a different event gave 10.05 µV. Carrying the most recent neck voltage forward gave 8.09 µV. The prespecified axillary test did not pass. The target records electrical variation at the skin. It does not establish where in the nervous system that variation began. [Complete paired comparisons](assessment-summary.json) · [Illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/cervical-forecast/)

## Reproduce the calculation

The shared command dispatches this measurement to its own trained readout in `cervical/model.json`. Each method subtracts the five-bin baseline on each electrode and predicts the remaining change after the last neck reading. The fitting method limits the influence of large errors. The accompanying movement weights serve their original movement tasks.

Use the study package’s acquisition script to prepare the four development files and matching receipts from the original CC0 dataset. Run `python cervical/study.py DEVELOPMENT_DIRECTORY OUTPUT_DIRECTORY` from the folder containing `predict.py`. That writes the four development folds to `results.json` and the final all-four fit to `model.json`. The fixed selection, units, time windows and scoring rule are in [design.json](design.json). The [complete model package](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/cervical-forecast) includes the original input reader and the outside assessment. The example numbers are invented. The package contains fitted coefficients and aggregate errors.
