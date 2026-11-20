# Which measurements went into the forecast?

The original study followed eight male Long–Evans rats learning to alternate between reward wells on a W-shaped track. Each recording ties the rat’s tracked position to the times when recorded neurons fired. This experiment used three rats to fit the models and three different rats to test them. The file catalogue, split, feature definitions, weights in the error calculation and rule for a positive result were fixed before reading their recorded positions or spike trains. ER1, JS15 and JS17 supplied the training data. JS21, JS34 and KL8 supplied the test data. The whole JS14 recording and both ZT2 files stayed outside the experiment. [Archive](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Frozen protocol](protocol.json)

## Pick a recording interval before seeing the result

We used the earliest epoch with at least 16 complete, nonoverlapping annotated trips, and took its first 16 trips. All six recordings had both brain regions. Each file’s unit table linked an individual sorted unit to an electrode row. We required that row’s group name to agree with the linked group and its location to match the group’s location. Every unit in the six files met both checks. The table shows how many units were available, how many candidate instants fell on the two-second schedule, and how many had enough data for the comparison.

| Rat | Role | Epoch | Trip IDs | CA1 units | PFC units | Scheduled | First trip, donor only | Camera/timing exclusions | In fit or score |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ER1 | Train | 1 | 0–15 | 82 | 40 | 357 | 26 | 21 | 310 |
| JS15 | Train | 1 | 0–15 | 45 | 36 | 263 | 29 | 16 | 218 |
| JS17 | Train | 1 | 0–15 | 36 | 42 | 328 | 32 | 0 | 296 |
| JS21 | Test | 1 | 0–15 | 26 | 46 | 179 | 25 | 2 | 152 |
| JS34 | Test | 1 | 0–15 | 53 | 49 | 154 | 23 | 1 | 130 |
| KL8 | Test | 3 | 15–30 | 69 | 22 | 289 | 22 | 0 | 267 |

A trip ID belongs to its animal. The first trip supplies possible earlier firing for the control. It contributes no scored or fitted target. In the other 15 trips, candidate cutoffs begin two seconds after the annotated start and repeat every two seconds. We require enough room in the trip for the 250 ms horizon, 50 ms target tolerance and a further 250 ms margin. We then check for stale frames, late or missing targets, gaps and nonfinite coordinates. This defines which recorded intervals can be scored retrospectively. Judging coverage requires the trip end and subsequent camera timestamps. The fitted predictor itself uses only the preceding observations. [Training coverage by trip and reason](coverage-fit.json) · [Test coverage by trip and reason](coverage-score.json)

## Read the camera and firing on one clock

The camera and sorted spikes use the same NWB recording clock in seconds. Each retained source timestamp and each XY coordinate come from the original track and carry its units. All motion inputs and the measured outcome are invariant under a common rotation, reflection or translation of XY. We work with straight-line displacements to avoid assuming the tracks face in the same direction.

At each cutoff, we take the latest camera frame at or before five instants spanning the preceding second in 250 ms steps. A frame can be no more than 75 ms old. From the five positions and their actual time differences we calculate four interval speeds in cm/s, net distances over the last two and four intervals, the cosines of the three successive turns, and the ages in seconds of the last four camera frames. Each turn with a zero-length step gets cosine zero. The archive’s supplied speed column, absolute XY, trip label, animal ID and elapsed run time never enter a forecast.

We measure the target from the last available camera position to the first frame at or after cutoff + 250 ms. We discard a target more than 50 ms late or a history-to-target span crossing a camera gap longer than 100 ms. Across the held rats the target frame arrived 250.0–290.8 ms after cutoff. The actual interval between the two position measurements ranged from 250.4 to 320.7 ms. The constant-speed comparison multiplies the most recent measured interval speed by the nominal 0.25 seconds. [Actual timing by rat](timing-and-pooled.json)

Each neuron belongs to one file. A unit number in ER1 supplies no identity link to a unit numbered the same way in JS21. Instead, we first pool spike counts by region in four consecutive 250 ms bins ending at cutoff. The left edge is excluded and the right edge included. We divide by that region’s file-local number of mapped sorted units and by 0.25 s, then take log(1 + rate). The resulting eight inputs always mean the same thing: four pairs of spikes per second per mapped unit in CA1 and PFC, after the log transform. The electrode samples, cell types and signal quality can still vary across animals. Unit counts come from retrospective sorting of the original session. There are no per-unit observation intervals in these files. A zero bin means zero archived events.

## Compare the same elapsed instants

The two fitted models use ridge regression. Both have the same movement features, fixed penalty 0.03 and unpenalized intercept. The combined model gets the eight firing features in addition. Each animal has equal total training weight, each eligible trip within that animal has equal weight, and each retained instant within that trip has equal weight. We standardize each feature using its weighted training mean and standard deviation, substituting one for standard deviations below 10⁻⁸. We fit the intercept to the weighted mean target and solve the weighted least-squares problem with the ridge penalty. Distances below zero are clipped to zero. The test animals contribute no training weights, fitted scale or outcome-based calibration.

For the timing control, we keep the combined model, current camera observations and true target fixed. We replace all eight firing features with firing measured during a completed earlier trip of the same rat and epoch. Choose the closest available nominal cutoff in time since trip start, preferring the most recent earlier trip and then the earlier cutoff on ties. Donor selection uses no camera outcome or error. This preserves the number of units, area identity and one-second joint activity history. A difference can still reflect motion-related state shared by firing and behaviour. It cannot establish cause or tell us what either region alone contributes.

The fixed test for a consistent contribution required the correctly aligned firing to beat both movement alone and earlier-trip firing on every held rat. Only KL8 cleared both comparisons. The primary averages weight trips and rats equally. A secondary calculation that weights every test instant equally gives 2.692 cm for movement alone, 2.654 cm with aligned firing, and 2.671 cm when earlier-trip firing replaces it. KL8 supplies 267 of 549 instants under that calculation. Three animals do not support a precise population estimate; repeated instants within a trip do not create additional independent animals. [Every prediction and control](predictions.csv) · [Fitted coefficients](weights.json)

## Reproduce the analysis

Python 3.12 with the versions in `requirements.txt` was used for the source reconstruction. `predict.py` needs only Python and NumPy. The packets, coefficients and example are included, so fitting, scoring and predicting from the existing files run offline.

```sh
python -m pip install -r requirements.txt
python study.py fit
python study.py score
python describe.py
python predict.py example-input.json
```

To rebuild the packets, first run `python catalogue.py` and then run the extractor once for each of ER1, JS15, JS17, JS21, JS34 and KL8, substituting its ID in the command below. Each request reads a small byte range with the published object ETag and checks the returned range. Digests bind each used block and derived packet. The analysis fetched 150,480,736 bytes from six objects totalling 205,600,335,712 bytes, including bytes adjacent to the required tables. The archive supplies the full-file SHA-256 digests. The local verification covers the downloaded ranges. The extraction retains camera rows and file-local flat-spike bounds for each trip. The retained event array follows the order of the accepted unit rows in its selection file. No continuous voltages or raw camera images were extracted. [Version, asset identifiers and archive digests](source/catalogue.json)

```sh
python extract.py JS21 --cache ./range-cache
```

`trace.json` retains all camera samples from the first eligible test trip, JS21 trip 1, plus counts in successive complete 250 ms bins from trip start and all 12 eligible forecast instants. Edges use the original NWB seconds. For each forecast it records the actual preceding camera positions, actual and donor regional counts, source row numbers, measured target and predictions. For a display of rates, divide each region's counts by its stated unit count and by 0.25 s. A distance forecast places no limit on which direction the rat might have turned.
