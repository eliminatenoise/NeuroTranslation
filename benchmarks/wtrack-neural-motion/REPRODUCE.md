# Run a prediction or repeat the experiment

Open `results.html` in any modern desktop browser for the recorded comparisons. The Windows, macOS and Linux launchers all open this local file. In the downloadable study, the `recording` directory contains the original timestamps, positions and spike trains for the selected 34 trips. The five reserved trips have no array files in the package.

## Predict from the saved example

The example is from training trip 55. It contains the original unit IDs, four earlier count vectors, four movement tokens, five actual camera times and the two elapsed-time inputs. There is no target in the example. Install NumPy to run the ridge predictor. The frozen reference environment used Python 3.13, NumPy 2.5.3 and CPU PyTorch 2.14.1.

```sh
python -m pip install numpy==2.5.3
python predict.py
```

The combined ridge returns X = 70.7605113 cm and Y = 101.5796011 cm for the nominal time 5972.2933333 seconds on this recording’s clock. For a different model or an earlier-history input with exactly the same recording, units and feature layout, use `--model` and `--example`. The attention models also require PyTorch. For the same example, the combined attention forecast is X = 69.0394039 cm, Y = 99.9182560 cm.

## Fit and evaluate

Install the numerical libraries in an isolated Python environment. CPU builds are sufficient. For machine comparison set `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and `OMP_NUM_THREADS` to `1` in the environment before launching Python.

```sh
python -m pip install -r requirements.txt
python test_study.py
python study.py fit --pairs recording/pairs --output repeat --threads 1
python study.py score --pairs recording/pairs --output repeat --threads 1
```

The fit checks each training file against the source manifest. It chooses the ridge penalty only on three earlier-to-later splits within training and records all candidates. The attention models use fixed settings, including 48 passes over training. A seal binds all five fitted weights and the fit, score and prediction code before test arrays are opened. The scoring step verifies the seal and places an intent file before opening test arrays. Each fresh fit directory supports one evaluation. The reference results live in `fitted`; leave that directory in place for comparison. The portable fit record shortens two machine-local library paths to basenames. The comparison record identifies both the original pre-score digest and the portable copy. The five weights and the scientific settings match the sealed fit. See [fit record hashes](fitted/portable-seal.json) and the [independent numerical reconstruction](fitted/independent-check.json). The original source rebuild has its own dependency list and network requirements. [Recording rebuild](recording/README.md)

The scorer uses Euclidean distance in centimetres for each future position, averages those distances within a trip, and then takes the mean of the nine trip averages. It also reports the window-weighted mean, trial-level errors, exact capture delays, all registered row exclusions, paired block intervals and the five simultaneous decision bounds. The earlier-trip control borrows an intact one-second population history from a completed test trip, choosing its time by proximity to elapsed trip time. The within-unit control rotates the four available count bins by a unit-specific number of steps. Both use the original fitted weights. Archive code, dates, support limits and uncertainty are in the [study design](protocol.json), [training seal](fitted/fit-seal.json) and [scoring record](fitted/scores.json).
