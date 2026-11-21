# Which retinal ganglion cell fires next?

A simple recency rule beat the rat-trained model in the salamander retina. Across three visual stimuli, a rule that favoured cells with both a high running count and recent activity assigned more probability to the next observed cell than the five fitted coefficients did. The fitted model still beat equal odds in every experiment. The comparison covers 34,490 resolved forecasts in 28 ten-second intervals. [Results](results.json)

The five coefficients came from spikes recorded while rat JS14 ran along a W-shaped track. That collection sampled dorsal hippocampal CA1 and prefrontal cortex. The salamander recordings sampled ganglion cells in isolated larval tiger salamander retinal tissue exposed to visual stimuli. Both studies used simultaneously recorded spike trains. For each new recording, predictions start with that recording’s own roster and empty counters. No salamander data entered the fit. [Rat recordings](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Retinal recordings](https://doi.org/10.5061/dryad.1f1rc) · [Retinal study](https://doi.org/10.1371/journal.pcbi.1005148)

## What transferred

Log loss measures the probability assigned to the cell that fired, in natural-log units. Lower is better. Each valid repeat has equal weight within its experiment. The last row gives each experiment equal weight. The model’s top choice shares credit equally among tied candidates.

| Stimulus | Valid repeats | Local candidate units | Resolved forecasts | Uniform | Running count | Count × recency | Rat-trained model | Model first choice |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Natural movie | 8 | 178 | 14,505 | 5.182 | 4.746 | **4.641** | 4.708 | 3.52% |
| Checkerboard | 10 | 155 | 10,213 | 5.043 | 4.414 | **4.298** | 4.412 | 6.24% |
| Moving bar | 10 | 140 | 9,772 | 4.942 | 4.365 | **4.318** | 4.401 | 6.30% |
| Equal experiment | 28 | varies | 34,490 | 5.056 | 4.508 | **4.419** | 4.507 | 5.36% |

On the second rat, ER1, the fitted model beat recency on equal-trip log loss, 3.380 to 3.484 nats. The ranking reversed for each salamander stimulus. The excess loss relative to recency was 0.067 nats for the movie (descriptive 95% repeat-bootstrap interval 0.065–0.070), 0.114 for the checkerboard (0.105–0.121) and 0.083 for the bar (0.073–0.096). Running count alone was a closer comparison. The model improved on it for the movie, came within 0.002 nats on the checkerboard and fell behind it on the bar. Different roster sizes, brain regions, tasks and recording methods affect the absolute scores. The archived files do not identify individual animals for each experiment. Repeat-level intervals describe the recorded samples. [Fitted coefficients](reference/weights.json) · [Result tables and intervals](results.json)

Rare cells expose a second limit. Among cells with one through ten resolved target spikes in each experiment, the model never ranked a correct cell first. For movie, checkerboard and bar respectively, there were 34, 43 and 36 such cells, accounting for 136, 231 and 172 forecasts. Their event-weighted model losses were 6.297, 5.747 and 5.672 nats. Uniform probabilities gave lower losses for all three groups. The complete tables also give equal-unit scores, ranks, a lower-quartile frequency check and results early and late in each replay. [Results](results.json)

## What the clock permits

The authors recorded on a 252-electrode array, sorted spikes offline and deposited event times in 10 kHz sample units. An electrode can pick up several cells. The candidates here are the deposited unit spike-train entries for one experiment. The archive provides no continuous per-unit availability intervals or online sorter latency.

At the close of each occupied millisecond the model assigns one probability to each candidate. The next occupied millisecond supplies the outcome. A bin with precisely one spike identifies one target. The 4,380 target bins with multiple spikes still update the history, and do not receive an identity score. The 28 last forecasts are censored. Three spikes fell in incomplete edge bins. This endpoint cannot locate a spike between two observed events on an unrecorded neuron. The experiment tests neither movie decoding nor movement control. [Frozen evaluation](protocol.json) · [Clock validation](clock-qc.json)

The selected material covers the first ten source-marked repeats long enough for a ten-second prefix in each experiment. In the movie, two of those prefixes contain out-of-order timestamps on one unit. The primary analysis rejected those packets without replacement. Sorting the original integer timestamps within each unit restores the two repeats. With all ten, model loss was 4.708 against 4.638 for recency. The movie file includes 178 spike trains and an author-specified subset of 170. Restricting the analysis to those 170 units gave 4.669 against 4.602 on the eight strict-valid repeats. The other eight deposited entries have no comparable inclusion endorsement from the authors. The checkerboard provided 69 repeat markers long enough for this test. The bar provided 108, alongside 130 shorter markers. All candidate rosters and boundaries remain local to their original recording. [Per-repeat metadata, exclusions and sensitivity checks](results.json)

## Reproduce the scores

Use Python 3.13. From this directory, install the pinned packages into a virtual environment, fetch the archive and evaluate it. The archive stays in the destination you choose. The last command independently recomputes all four methods’ per-repeat log losses, first choices and mean ranks using integer clock arithmetic.

```sh
python -m pip install -r requirements.txt
python acquire.py input
python evaluate.py input/error_robust_mode_data.zip reproduced.json
python check.py input/error_robust_mode_data.zip reproduced.json
```

Loback, Tkačik, Prentice and colleagues deposited the salamander data in Dryad under CC0. The official Zenodo preservation record serves the same file and DOI. Version 1 contains one archive of 87,524,253 bytes, with Dryad MD5 `f34c92b51f2abcc3ff965500176ff9fc` and verified SHA-256 `f5ffc42ef4db643c83c70ac3a3b727e3192478c1401bd796184d8856de8a6039`. The source manifest gives the names and hashes of the three MATLAB members. Palmer and colleagues' separate movie archive uses 16.667 ms bins, too coarse for the one-millisecond endpoint. [Source manifest](sources.json) · [Dryad data](https://doi.org/10.5061/dryad.1f1rc) · [Zenodo preservation record](https://zenodo.org/records/4976473) · [CC0](https://creativecommons.org/publicdomain/zero/1.0/) · [Palmer dataset](https://doi.org/10.5061/dryad.4qrfj6qm8)

The original rat recordings and their derived coefficients are attributed to Justin Shin and Shantanu Jadhav under CC BY 4.0. The archive preserves the fitted weights and the original reference implementation. This study adds the salamander source adapter, replay, comparisons and checks. The new evaluation code is dedicated to the public domain under CC0. Credit the source authors when reusing model-derived results. [Original model attribution](reference/NOTICE.md) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Code dedication](reference/LICENSE-CODE)
