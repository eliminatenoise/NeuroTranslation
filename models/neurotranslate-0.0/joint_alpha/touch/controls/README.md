# Can the force on a fingertip forecast its next nerve spikes?

A moving plate pressed against a supported fingertip while an electrode recorded impulses from one sensory nerve fibre. Can the force measured on the plate tell us how many impulses that fibre will send a little later? A repeated movement makes this question harder than it sounds. The clock alone can tell us when the plate usually moves.

Two controls use that repetition. One learns from elapsed time and earlier nerve impulses. Another also sees the force from the **previous** movement, at the same point in time, on the same material and in the same direction. Each competes with a model that sees the force from the **current** movement. The simplest comparison predicts the mean count across the seven training participants for every window.

## What happened in two new participants?

The models learned from 176,685 eligible windows in 529 trials from seven people. Development used 41,416 windows in 124 trials from two other people. Each supplied one recorded nerve fibre and 20,708 windows. The table gives mean Poisson negative log likelihood in nats per window. A smaller score assigns more probability to the counts that actually occurred.

| Development participant and recorded fibre | Training mean | Clock and spike history | Current force added | Previous movement’s force added |
| --- | ---: | ---: | ---: | ---: |
| U105, fast-adapting type I | 0.152431 | 0.112514 | 0.105419 | **0.105402** |
| U111, slowly adapting type I | 0.321159 | 0.306339 | **0.305323** | 0.305346 |

Adding current force improved on the clock and spike history for both people. But did the model need the force from *this* movement? The previous movement’s force scored slightly better for U105, and the current movement’s force scored slightly better for U111. These two people give no consistent answer in favour of trial-specific force.

The total counts show how a smaller likelihood score can coexist with large errors. The current-force model predicted 1,282 spikes for U105, whose electrode recorded 361. For U111 it predicted 1,725 and the electrode recorded 1,972. The two receptor classes each occur in one development person, so differences between the people cannot isolate a receptor-class effect. The aggregate results file gives the same comparisons by unit, material and direction.

## What each forecast uses

The input spans ten consecutive 20 ms bins. The last bin ends at time *t*. Count twenty milliseconds forward, then count the spikes in the following twenty milliseconds. This later count is the outcome.

Each regression uses ten evenly spaced Gaussian functions of elapsed trial time from 0 to 6.9 seconds, each one spacing wide. Earlier nerve activity contributes three spike counts over the last 20, 60 and 200 ms. Each force model adds six values measured at the plate, in newtons. Three are the latest 20 ms mean force along each axis. Three give the change since the preceding bin. The previous-movement model takes all six from the matched repetition. None of the regressions sees receptor identity or material as a predictor.

The three regressions estimate the expected count through a Poisson log link. Each fits its own feature means, population standard deviations, intercept and slopes on training windows alone. Standard deviations below 10⁻¹⁰ are replaced by one. The fit minimizes average Poisson negative log likelihood plus 0.005 times the sum of squared standardized slopes. The intercept is unpenalized. All windows have equal training weight. The reported likelihood includes the log-factorial term and uses natural logarithms. Smaller is better.

## Run the comparison

Use Python 3.11 or newer, NumPy for predictions, and SciPy for fitting or scoring. Use the accompanying Delhaye preparation script and its roster to create the training and development archives from the deposited recordings. The arguments below are paths to the resulting local files.

```sh
python refit.py train.npz refit-weights.json
python score_development.py pooled-weights.json development.npz reproduced-scores.json
```

To run the frozen predictor on any supported input arrays, load the JSON and call the NumPy function. A batch may contain one window.

```python
import json
from pathlib import Path
import numpy as np
from predict import predict_all

weights = json.loads(Path("pooled-weights.json").read_text())
with np.load("development.npz", allow_pickle=False) as archive:
    means = predict_all(archive["X"], archive["previous_repeat_force"], weights)
```

`X` has shape `[windows, 10, 5]`. Its channels are three mean plate-force axes in newtons, the nerve spike count for that bin, and elapsed seconds at the end of the bin. The donor array has shape `[windows, 10, 3]` and holds the matched earlier repetition’s three force axes. Each result is a one-dimensional array of expected spikes per future 20 ms.

## Source

Benoit P. Delhaye, Ewa Jarocka, Allan Barrea, Jean-Louis Thonnard, Benoni B. Edin and Philippe Lefèvre collected the recordings. This analysis extracts earlier plate forces and nerve impulses and fits new pooled prediction models. The observed task was passive loading of a supported fingertip. Predictions refer to the recorded sensory unit. The source does not measure voluntary motor commands or force produced by the participant’s muscles. [Study](https://doi.org/10.7554/eLife.64679) · [Deposited data](https://zenodo.org/records/4818439) · [CC BY 4.0 data licence](https://creativecommons.org/licenses/by/4.0/)
