# How far will a sensor on the back turn?

Stand still or walk with a sensor on your back. Its orientation tells us how far it just turned. Can voltages from two patches of skin help forecast how far it will turn in the next tenth of a second? Each patch carries 32 electrodes. One sits over the upper back, near C4, and the other over the lower back, near L2. Their signals can include muscle, heart activity and movement of the electrodes. The angle belongs to the sensor. A turn of one degree to the left or the right has the same size. [Recording study](https://doi.org/10.1038/s41597-026-07592-7) · [Sensor locations](https://eliminatenoise.github.io/Interoceptomics/back-rotation/)

Four volunteers supplied two trials each for training. Four others supplied two trials each for the planned tests. One person's files label the four orientation rows as quaternion components 2, 3, 4 and a buffer. The first component could not be verified, so the size of that person's turn is unknown. Both original four-person tests therefore remain incomplete. The table describes the other three people and gives the average error in degrees, with equal weight for standing and walking and for each person. Smaller is better.

| Three people with verified orientation labels | Motion alone | Both voltage grids | Unrelated voltage |
|---|---:|---:|---:|
| Task-trained Transformer | 0.361° | 0.382° | 0.381° |
| Shared movement encoder | 0.376° | 0.385° | 0.385° |

For these three people, adding the two voltage grids increased the average error in both models. The specialist pairs the unrelated voltages within the same trial and task. The shared model takes them from the person's other trial of the same task. [Test rules and results](ASSESSMENT.md) · [Illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/back-rotation/)

## Make a forecast

[Open the browser model](https://eliminatenoise.github.io/NeuroTranslation/back-rotation/) or [download the offline reader](https://eliminatenoise.github.io/NeuroTranslation/back-rotation-offline.zip). To run the Python model here, install Python 3 and NumPy, extract the entire model ZIP, and open the launcher for Windows, macOS or Linux. It evaluates an invented walking example and prints the predictions in degrees. A custom input has the same shape as `example.json`. In a terminal, run the following command from the extracted directory.

```sh
python forecast.py example.json
```

Ten rows describe ten successive 10 ms bins. The columns give the turn within each bin, the turn since the history began, the walking indicator, and three voltage features for each patch. Use degrees for angles and follow the raw microvolt transformations in the [feature definitions and architecture](METHOD.md). The eight outputs include the four specialist fits and four simpler forecasts. Comparing real voltage timing also needs a separate donor window from the recording. [Try the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-back-rotation/)

## Reproduce the study

The acquisition program requires Python 3.11 or later. Source verification uses the original Zenodo archive catalogue and published ZIP member information. Use the commands below from this directory to save recordings in separate folders beside the package. They reproduce eight fitting trials and eight assessment trials. The download here contains the fitted parameters, analysis code and group results. [Acquisition and quality checks](source/SOURCE.md) · [Assessment source checks](source/ASSESSMENT-SOURCE.md) · [Dataset and attribution](NOTICE.md)

```sh
python source/acquire.py ../back-development
python source/acquire.py ../back-assessment --metadata source/assessment-source.json
```

Extract the [NeuroTranslate 0.0 model ZIP](https://github.com/eliminatenoise/NeuroTranslation/raw/refs/heads/main/models/neurotranslate-0.0.zip) beside this package. Install NumPy and SciPy to reproduce the orientation check and the descriptive scores for the three eligible people. Fitting and the synthetic test suite also use CPU PyTorch. The specialist used Python 3.13.15, NumPy 2.5.3, SciPy 1.18.1 and PyTorch 2.14.1+cpu, with one numerical thread. Use fresh output paths. The original specialist scorer, `assess.py`, stops at the unverified channel labels. The eligibility check and the subsequent descriptive calculation are provided separately.

```sh
python -B evaluate.py ../back-assessment --shared ../neurotranslate-0.0 --out ../eligible-results
python -B test_back_rotation.py
python -B fit.py ../back-development --out ../back-rotation-refit --threads 1
```

The [shared model package](https://github.com/eliminatenoise/NeuroTranslation/raw/refs/heads/main/models/neurotranslate-0.0.zip) contains its original movement encoder, fitted readouts, scored controls and Python implementation. Extract it and run the command below from the directory containing `predict.py`, substituting the locations of the same data folders. Its last argument names a new output folder.

```sh
python -B back_rotation/study.py fit ../back-development ../shared-refit
```

The shared package checks orientation labels before scoring. To reproduce both descriptive summaries, run `evaluate.py` here with that shared package as shown above. The two studies have distinct averaging and control rules. [Specialist design](protocol.json) · [Shared encoder design](SHARED-DESIGN.md) · [Files fixed before assessment](PRETEST-SHA256.json) · [Source attribution and terms](NOTICE.md)
