# Forecast the next sensory spikes

A muscle spindle is a receptor inside muscle. In this experiment a machine stretched a rat muscle while a separate recording detected spikes in one sensory nerve fiber. These models take the previous 100 milliseconds of measured force, position and earlier spike counts, then estimate how many spikes will arrive in the next 20 milliseconds. A second, separate pair of models forecasts changes in force and position. Both directions can be checked against later measurements from the same trial.

Extract the entire model ZIP and open the launcher for your operating system, or open **reader/index.html**. The reader runs entirely on your device. Use the slider to follow one recorded stretch or choose **Invent a history** to change the inputs. [Online reader](https://eliminatenoise.github.io/NeuroTranslation/muscle-spindle/) · [Scientific paper](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-spindle/) · [Rotatable anatomical schematic](https://eliminatenoise.github.io/Interoceptomics/muscle-spindle/)

## Use a trained model

Five rows give five consecutive 20 ms intervals, oldest first. Each row holds mean tendon force, mean apparatus position, force change per second, position change per second, and the number of detected spikes. The force and position channels use their original archived units. The following two commands produce the same forecast from one fitted set of weights.

```sh
node launch.mjs fit/strict-afferent/checkpoints/aff015-seed1641-all.json fit/strict-afferent/history-example.json
python fit/predict.py fit/strict-afferent/checkpoints/aff015-seed1641-all.json fit/strict-afferent/history-example.json
```

The example checkpoint was trained on the other two eligible sensory fibers. All 45 checkpoints are included. Their names identify the held-out fiber, starting seed and available inputs. The five-input Transformer, the regularized count regressions and the simple baselines use the same native outcome. The reverse forecasts in **mechanics/** use each bin’s last observed force and position in place of its average; each model’s input is documented. [Count model](fit/MODEL.md) · [Score tables](score/strict-afferent/READOUT.md) · [Reverse forecast results](mechanics/strict-afferent/results.json)

## Rebuild the results

Use the [source instructions](source/README.md) to retrieve the nine eligible development filenames from the original public archive and reconstruct the window tables. The two reserve files stay outside the source reader. Install the listed numerical dependencies for source extraction, plus PyTorch for neural training. The standalone Python event predictor uses only the standard library.

Run the [held-fiber training and verification](fit/MODEL.md), followed by the [count-model scoring commands](score/README.md). Rebuild the reverse forecast separately from the package root:

```sh
OPENBLAS_NUM_THREADS=1 python mechanics/mechanics.py source/private/windows.npz regenerated-mechanics --validation strict-afferent
```

Three fibers, 94 trials and 16,262 usable windows survived the strict checks. The original three-group test could not be run. On this smaller comparison, the spike-history Transformer gave lower count deviance than the model that also read the mechanics. Repeating the last count gave lower mean absolute error than either network. A mismatched earlier mechanical history still hurt the combined network. Distinct questions can have distinct answers even on the same recording. [Source eligibility](source/QC-SUMMARY.json) · [Original comparison status](score/strict/status.json) · [Clock sensitivity](score/mixed-clock/status.json) · [Licence and credits](NOTICE.md)
