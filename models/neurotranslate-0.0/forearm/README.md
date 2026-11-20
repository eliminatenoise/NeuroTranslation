# How much does the forearm add to the wrist forecast?

A person turns their wrist to steer a cursor. Two encoders measure the bend of the wrist and its tilt towards or away from the thumb. The shared movement model sees the previous half-second of angles and estimates both angles a quarter-second ahead. We gave a second model that first forecast and asked it how far to adjust the answer. How much could it learn from the wrist history alone? What did four forearm electrode pairs add? [Original study and electrode positions](../wrist-source/README.md)

| Forecast on the same held-person rows | Error |
| --- | ---: |
| Shared movement model, wrist history and cue | 4.503° |
| Same forecast with a motion-only correction | 4.175° |
| Same forecast with a motion and forearm correction | **4.054°** |
| Earlier shared movement model fitted directly to wrist motion and forearm | 4.291° |
| Earlier wrist-specific convolutional network, motion only | 3.618° |
| Earlier wrist-specific network with forearm correction | **3.549°** |

The first correction already recovered 0.328°. Comparing the two correction models isolates the contribution of the forearm inputs under this fitting procedure. They reduced error by a further **0.121°**. Four of six people improved. Leaving out each person in turn moved that reduction between 0.067° and 0.165°. Error here is a root mean square over both angles, giving each person equal weight. [Scores, axis breakdown and all contrasts](results.json)

Keep the observed wrist motion and the forecast fixed. Substitute forearm voltages from a different trial at the same time after the cue, and error rises to 4.419°. Reverse the sixteen forearm bins and it rises to 4.305°. Give every bin its own window’s average amplitude and it rises to 4.170°. The time course of the recorded signals carried information in this task. Muscle activity, movement and electrode contact can all affect those signals. The other-trial swap uses an offline recording. [Fixed comparison plan](PROTOCOL.md) · [Decision rules](PROTOCOL-ADDENDUM.md)

The earlier wrist-specific convolutional network with its own forearm correction still had the smallest error. It beat the corrected shared forecast for five of the six people. Its advantage averaged 0.505° and ranged from 0.380° to 0.595° when we removed one person at a time from the summary. The shared correction offers an extra input choice for this model. This study used six previously examined people, 1,879 cued trials and 11,274 overlapping windows. All six took a turn as the test person. These results describe those recordings. [Measured inputs and eligibility](../wrist-source/README.md) · [Earlier wrist-specific study](https://github.com/eliminatenoise/NeuroTranslation/tree/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/benchmarks/wrist-forearm-correction)

## Predict two angles

From the model’s top directory, run the invented wrist example with Python and NumPy.

```sh
python predict.py forearm/example.json
```

It forecasts 18.970° of extension and −2.058° of radial deviation (tilt away from the thumb). Use `mode` and `forearm_residual` both set to `emg` for two encoder channels followed by four bipolar forearm RMS channels. Use `motion` for both fields with two encoder channels. Both corrections receive the same motion-only shared forecast. Omitting `forearm_residual` runs the original angular mode. Distance forecasts keep their original inputs and centimetre outputs. Bare arrays require the caller to verify source clocks and row alignment. [Invented input](example.json) · [Invented input generator](make_example.py) · [Measurement conventions](../REPRODUCE.md)

## Reproduce the comparison

Follow the original six-person extraction and base-fitting instructions. The original base fit produces the six held-person adapters and an uncorrected all-six checkpoint in a fresh `fits` directory. Obtain the earlier CNN held-person forecasts by following its published benchmark recipe. Its `predictions` subdirectory belongs under `cnn-output` in the example below. Both paths must come from the named source recordings in the published row order. The numerical hashes of scales, trained base arrays and earlier CNN estimates are checked. The reference used Python 3.13.15, NumPy 2.5.3, PyTorch 2.14.1+cpu and the deterministic CPU route. Numeric-library changes may fail those exact identity checks. [Base fit](../REPRODUCE.md) · [CNN reproduction](https://github.com/eliminatenoise/NeuroTranslation/blob/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/benchmarks/wrist-forearm-correction/REPRODUCE.md)

With BLAS, OpenMP and MKL each limited to one thread, run these commands from the model’s top directory. The fit uses two PyTorch intra-op threads, one inter-op thread and the original batch order. Choose fresh output directories. Store the resulting fit files and scored rows privately.

```sh
python -B forearm/test_synthetic.py
python -B forearm/study.py fit --data train.npz --manifest wrist-source/array-hashes.json --spatial spatial-seed.npz --bases fits --out residual-fits
python -B forearm/study.py score --data train.npz --manifest wrist-source/array-hashes.json --spatial spatial-seed.npz --bases fits --fitted residual-fits --comparators cnn-output --out residual-scores
```

For each test person, five others supplied the correction. To estimate the base error for each of those five, a separate base fit saw only the remaining four people. Fifteen unique four-person fits cover all pairs of exclusions. The correction sees the two forecasted changes, wrist history, current angles and cue time. Its second version also sees the four forearm channels over sixteen bins. Each correction learns an additive adjustment with a fixed ridge penalty. Swaps run through the same fitted coefficients. The packaged final coefficients use all six people, with each person’s training forecast supplied by the other five. That final model awaits a fresh assessment. [Nested fits and scoring](study.py) · [Correction equation](residual.py) · [Sources, changes and reuse](../NOTICE.md)
