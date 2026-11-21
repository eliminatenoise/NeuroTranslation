# Can the next tenth of a second of arm movement improve a cortical spike forecast?

A macaque reached between targets with its hand on a handle. Electrodes in a patch of sensory cortex called area 2 recorded spikes, the brief electrical events produced by active neurons. This model estimates how many spikes each electrode will record over 100 milliseconds. It learned from 198 trials on September 7, 2017. The same animal returned on September 14. That second recording tests how far the forecast travels after one week. [Original study](https://doi.org/10.7554/eLife.48198) · [Chowdhury, Glaser and Miller’s CC0 recordings](https://doi.org/10.5061/dryad.nk98sf7q7)

## Follow one forecast

Run the example from this folder with Python 3.11 or newer and NumPy. It uses the published weights and an observed training reach. The first line shows a forecast of 3.220 spikes at contact 2 and an observed count of 5. A forecast can be fractional because it estimates the expected count.

```sh
python example.py
```

The example starts in trial 3 of the earlier recording. Its second go signal has already appeared. Call the forecast row *k*. Here *k* is 1006, five recording samples after the signal. Each sample spans 10 milliseconds. The first forecast uses the last known arm position, its recent velocity, counts from the preceding 200 ms and the cues already shown. Wait ten samples and the arm may be somewhere else entirely. The update gets to see how far the arm moved beyond the displacement that its earlier velocity predicted. Both forecasts then face the same ten unseen count bins, starting at *k* + 10. Every spike used by either fitted forecast came before *k*.

The camera measured the shoulder-relative positions of a hand marker and a marker near the elbow, each in three dimensions and in metres. The last two coordinates give the handle's planar position in centimetres. Let *p* be that eight-coordinate position and *s* the displacement per sample estimated from the last and first positions of the final five pre-forecast samples. The new information *r* is an eight-coordinate displacement, in the units of each source coordinate.

```text
s = (p[k−1] − p[k−5]) / 4
r = (p[k+9] − p[k−1]) − 10 × s
```

The 55 base inputs, in order, are the eight coordinates of *p[k−1]*, the eight components of *s*, the preceding 20-bin count totals on 37 contacts, the number of go cues strictly before *k*, and the seconds since the latest such cue. The update appends the eight components of *r*. Each fitted head subtracts its saved input means, divides by its saved scales, multiplies by its coefficients, adds its intercept and takes the exponential. The intercept occupies the first column of each coefficient table. Each row corresponds to the contact at the same row in its population's contact list.

## Which spikes count?

The source sorter assigned some extracellular spikes to local classes and left others unclassified. Sort zero denotes that residual class. The primary forecast predicts the sum of all exported classes on each of the 37 contacts with a sort-zero column in both sessions and both later recording blocks. Its two sensitivity analyses ask how the result changes when counting only sort zero on those 37 contacts, or only positive sorts on the 17 contacts carrying them throughout. All three use the same preceding history from the 37 primary contacts. The fitted coefficients differ for each endpoint.

Contact 67 carried sorted spikes on both days and lacked a sort-zero entry on September 7. It belongs in the positive analysis. Five earlier positive contacts lack positive coverage on the later day and 16 later positive contacts lack it on the earlier day. The full table identifies every local source column and its sort class. The sorter split two classes at contact 15 on the early day and at contact 53 on the later day. The recordings establish contact labels across days. Whether an individual neuron reappeared remains unknown. [CC0 source recording](https://doi.org/10.5061/dryad.nk98sf7q7)

## Fitting and scoring

The head for one contact minimizes the weighted mean of exp(η) − yη plus 0.005 times the sum of squared non-intercept coefficients. Here *y* is that contact's observed 100-ms total and η is its linear prediction. All 198 training trials have equal total weight. Each trial divides that weight equally over its eligible windows, yielding 519 windows. Means and population standard deviations use those same weights. Columns constant throughout training have scale one. The optimizer uses L-BFGS-B, a 1,000-iteration ceiling and a relative objective-change tolerance of 10⁻⁹. All 182 heads converged within 85 iterations. Independent Newton fits reached penalized objectives within 9.5 × 10⁻⁸ of the released fits.

The main comparison puts three forecasts on identical rows. The base forecast retains the original estimate, the update uses the measured residual, and the wrong-motion control gives the update a residual from a different reach. That donor is the latest eligible earlier *trial* in the same workspace and recording block, at the same go ordinal. Its trial must end before the recipient begins. Only its residual moves across trials. Across all three forecasts the recipient supplies its own earlier position, spike counts and cues.

A valid main row has finite coordinates at the two history positions used to calculate the slope, a finite endpoint displacement and two finite cue features. Every raw bin that contributes to a required count must hold a finite nonnegative integer on every selected local column. Each endpoint class gets its own mask. Three descriptive count references reuse the last 100-ms total before *k*, the 100-ms total ending at *k* + 9, or the training mean for that contact. Their table compares all six methods on the subset that supports both persistence counts. Later count availability does not affect primary donor selection. The second persistence baseline has seen more recent spikes than either fitted model.

For one observation the Poisson deviance equals 2 × [μ − y + y log(y/μ)], with μ floored at 10⁻⁶ and the log term set to zero when *y* is zero. Lower is better. Average contacts equally within a window, windows equally within an original trial, and supported trials equally within each workspace. For the two paired contrasts subtract the base score or wrong-motion score from the update score. Resample eight consecutive trials at a time within each physical block and workspace, from the entire chronological assigned roster, including trials with no usable windows. Draw overlapping stretches uniformly with replacement and trim to the original number of trials. The code uses 5,000 draws and seed 20261125 per workspace. It also reports intervals from resampling one original at a time within each block. Both paired moving-block upper bounds must fall below zero in each workspace for the primary improvement claim.

## Reproduce the fits and held scores

First use the companion source reconstruction instructions to obtain the train and two September 14 arrays from the public recordings. From this folder run the commands below, replacing the array directory with your own. The scorer uses the checked-in weights. Refitting needs SciPy as well as NumPy. The recorded environment used Python 3.13.15, NumPy 2.5.5 and SciPy 1.18.1. Different numerical libraries can change the last digits of an optimizer's result.

```sh
python -m pip install numpy scipy
python test_model.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python fit.py ../source/arrays/train.npz rebuilt.json diagnostics.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python score.py --metadata metadata --blocks ../source/arrays/block1.npz ../source/arrays/block2.npz --result scored.json --rows forecast-rows.npz
```

`forecast-rows.npz` retains the original row key, observed endpoint totals, expected counts, donor and support flags. For each endpoint, expected counts are in update, base, wrong motion, previous 100 ms through *k* + 9, previous 100 ms through *k* − 1, and training mean order. A donor index spans the two concatenated block archives, starting at zero. The value −1 means no earlier donor. The JSON score file includes exclusions, matched denominators, per-contact deviance and both interval estimates.

This is an offline comparison of one later day from one animal. Camera reconstruction, filtering and spike sorting can use processing unavailable at the nominal live sample time. A better forecast could reflect sensory input, motor-related activity, or both. The recordings do not establish a peripheral feedback pathway or a causal effect of these movements.
