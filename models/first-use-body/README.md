# Forecast a moving set of landmarks

Give the forecaster a series of points on an animal seen by a camera. Each point keeps its identity within that recording. A fly can have 13 landmarks and a worm can have 49. Neither needs to borrow a mouse skeleton. The output is the predicted position of each visible point in the same camera plane.

Run the fictional seven-point example with Python and NumPy.

```sh
python first_use.py
python check.py mixed-weights.json
```

On the first frame, the example predicts that each visible point will stay where it is (`last_position`). A missing point stays unknown (`unobserved`). After five natural frames, a point becomes eligible for the trained predictor (`learned`) when it is visible now and has at least three observations within those five frames. A recently seen point with insufficient history keeps its last-position estimate if it is visible now. No calibration gesture or fit on the new animal is required.

```python
from first_use import predict
from forecaster import read_weights

weights = read_weights("mixed-weights.json")
# xy has shape (frames, landmarks, 2); missing points have NaN coordinates.
# t gives elapsed seconds, with one increasing timestamp per frame.
future_xy, method_for_each_point = predict(xy, t, horizon_s=0.12, weights=weights)
```

The two supplied fits use the same architecture. The **mammal fit** learned from a mouse recording and a gerbil recording. The **mixed fit**, used in the example, also saw a fly and two worms. The example runs offline. Python and NumPy suffice for inference. PyTorch is needed to repeat training.

## What does body shape contribute?

Over five frames each point has a recent direction of travel. Other points in the same image may move with it. A shared network learns how much to trust local and collective motion. Its inputs include each point’s distance from the center, the spread of nearby landmarks, and how closely the point moves with its neighbors. The calculation estimates the size and proportions of the *visible projected configuration*. Posture, missing points and camera perspective can all change that configuration.

The network assigns six weights to staying still, the point’s latest velocity, its three- and five-frame velocities, and the corresponding two pooled velocities. Its output is their weighted sum in camera coordinates. A matched network trained with the seven geometry features set to zero tests how much the geometry contributes. All models retain elapsed time. Neither learned model uses species names, point names, fixed anatomy or a lookup for animal identity. Reordering points, translating, rotating or reflecting the whole scene, and changing coordinate units preserve the corresponding output up to rounding. The calculation assumes a common 2-D view with persistent point identities. A change of camera perspective falls outside those symmetries. Pairwise distances require memory proportional to the square of the number of visible landmarks.

## What happened on other animals?

Each forecast was compared with the same point in a later optical tracker frame. Error is the distance between those two positions divided by the root-mean-square distance of eligible points from their center in the observed frame. Smaller values are better. In the table, each recording has equal weight. Co-recorded animals, overlapping landmarks and nearby frames share information and do not count as independent experiments.

| Fit and test set | Recordings | Scored points | With geometry | Without geometry | Stay still | Last velocity | Half velocity | Rigid motion |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mammal fit, original holdout near 120 ms | 13 | 23,535 | 0.1320 | 0.1391 | 0.1690 | 0.2745 | 0.1833 | 0.1444 |
| Mammal fit, common holdout near 120 ms | 10 | 17,943 | 0.1397 | 0.1475 | 0.1959 | 0.2601 | 0.1844 | 0.1570 |
| Mixed fit, same ten recordings | 10 | 17,943 | 0.1563 | 0.1490 | 0.1959 | 0.2601 | 0.1844 | 0.1570 |
| Mammal fit, locust at 200 ms | 1 | 1,680 | 0.1608 | 0.1846 | 0.2339 | 0.1670 | 0.1753 | 0.1502 |
| Mixed fit, same locust recording | 1 | 1,680 | 0.1464 | 0.1487 | 0.2339 | 0.1670 | 0.1753 | 0.1502 |

Adding fly and worm recordings improved the locust result and worsened the mean on the ten common short-horizon recordings. On those ten, the mixed fit without geometry also beat the mixed fit with geometry. The comparison changed both the training examples and their taxonomic weights. It cannot identify a causal benefit from greater diversity. The 200 ms comparison comes from a single recording with different acquisition timing.

The mammal fit saw two recordings, nine tracker IDs and 13,816 landmark examples. Its test set included a separate mouse acquisition, two fly layouts, a bee recording, a locust recording and nine worm acquisitions spanning three strains. The mixed fit saw five recordings in three phyla, twelve tracker IDs and 32,763 examples. Its holdout contained eleven recordings. The dumpy worm strain remained wholly held. Across both stages the sources cover six species in three phyla. Camera views, tracking pipelines and taxon vary together. The source includes five to 49 landmarks per track, with two-dimensional pixel coordinates for insects and rodents and micrometres for the worms. In worm and locust midline exports, a point can denote an ordered sample along a segmented body outline or midline. The same index need not follow the same piece of tissue. The optical trackers supply the comparison endpoints. Their own measurement error was not independently measured here.

**First use.** On the first visible frame, staying still gave mean normalized error 0.1956 on the original 13 short-horizon recordings (539 points). A learned forecast first became possible after five observed frames. For that first eligible short-horizon forecast per track, the mammal fit scored 0.1319 across 543 point endpoints. The predictions begin at different instants and can cover different points. On the held clips, the first eligible five-frame forecast occurred 27–510 ms after the short-horizon recordings began, or 800 ms for the slower locust recording. Each animal could simply keep moving.

**Missing measurements.** Randomly hiding 20% of input point observations reduced scorable short-horizon endpoints in the original evaluation from 23,535 to 17,380. Mammal-fit error on the remaining points was 0.1331. Each perturbation uses the same clock and unmodified target. The error denominator uses the original observed radius for a comparable unit. The descriptive 90% error radius uses only the points visible to the predictor in that condition. Its training cutoff came from leaving out whole training recordings in turn. For the geometry head, multiply the current eligible-point radius by 0.5425 for the mammal fit or 0.4604 for the mixed fit. The cutoffs and sampling definition are in `error-radii.json`. Across the mixed short-horizon holdout, unperturbed coverage averaged 90.5% by recording and ranged from 53.0% to 100%. Those intervals do not guarantee 90% coverage in a new recording.

**Speed.** In five fresh Python processes on an AMD Ryzen AI Max+ 395 CPU, median import took 35.3 ms and loading weights took 0.35 ms. The first learned forecast took 0.81 ms. The warmed median took 0.193 ms for a fictional seven-point, five-frame event. Operating-system file caches were uncontrolled. These times exclude camera acquisition, point detection, association and transport. None of those stages is implemented in the forecaster.

The saved results give per-record native-unit and normalized errors, equal-record, equal-phylum and pooled estimates, worst-record error, origins and exclusions, and the first and later forecast results. The whole-record origin subsample uses timestamps and tracker availability to distribute evaluation windows across a clip. A single forecast uses only its five-frame prefix and the requested future time. At least three observations including the origin are required per predicted landmark. At least two distinct eligible locations are needed for a positive scoring radius. Inference can run on one landmark, but the normalized score is undefined in that case. This experiment does not establish performance for humans, other phyla, arbitrary sensing systems, forces, nerve activity or intent.

## Files and reproduction

- `forecaster.py` and `first_use.py` implement the trained forecaster and first-observation fallback. `check.py` uses entirely fictional geometry.
- `mammal-weights.json` and `mixed-weights.json` each contain both trained heads as portable arrays. `protocol.json` contains the frozen clocks, seed, sampling, objective and comparison rules. No held recording guided hyperparameter selection.
- `mammal-scores.json`, `mixed-scores.json`, `matched-comparison.json` and `cold-start-results.json` contain the detailed evaluations. Rigid motion fits translation and rotation of points matched between the oldest and latest frame, then extrapolates at constant rates.
- `study.py fit`, `study.py predict` and `score.py` reproduce the stages. `mixed-split.json` lists the secondary allocation. Run the included `sources/fetch_tracks.py --output bodyplan-data` with Python 3.11 or newer, NumPy and h5py to reconstruct the 16 acquisitions. Supply its manifest, with one `.npz` file containing `xy[T,K,2]` and `seconds[T]` per track. The per-track manifest fields are `id`, `path`, `split`, `group`, `species`, `phylum`, `units` and an optional `sha256`. Use the same manifest for forecasting and scoring. The original run used NumPy 2.5.3 and PyTorch 2.14.0, one PyTorch and one BLAS thread, seed 1729.
- Acquisition credits and terms are in `SOURCES.md`. Frame extraction and tracker quality remain part of the measurement. No source animal coordinates are distributed here.

```sh
python study.py fit path/to/manifest.json fitted
python study.py predict path/to/manifest.json fitted predictions
python score.py path/to/manifest.json fitted predictions scores.json
python study.py fit path/to/manifest.json mixed-fit --mixed mixed-split.json
python study.py predict path/to/manifest.json mixed-fit mixed-predictions --mixed mixed-split.json
python score.py path/to/manifest.json mixed-fit mixed-predictions mixed-scores-local.json --mixed mixed-split.json
```

The original code and fictional example are dedicated under CC0. Source-specific attribution and license notices accompany the trained arrays and results. The accompanying licenses retain their own scope.
