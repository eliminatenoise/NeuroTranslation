# Can a model tell when the floor will take your weight?

NeuroTranslate 0.0 reads the last 200 milliseconds of muscle voltages and vertical force on a plate built into a walkway. It estimates the chance that the plate **starts** to carry load in the next 100 milliseconds. It also estimates the signed force impulse. That target is the sum of the vertical force readings multiplied by the time between readings. Upward force is positive, and the result is in newton-seconds.

These three checkpoints are **fit only**. They learned from five walks by two of twelve assigned people. Thirty-one walks lacked the required names on their muscle recordings. The comparison uses 1,525 overlapping windows from plates 1 and 2. Forty-four positive windows cover nine loading events. Accuracy on new walks or people has yet to be measured. The loading probability applies to the named plate. The plates cover part of the walkway.

## Try the invented walk

Extract the ZIP and open `recorded-force/`. Use Python 3.10 or later with NumPy installed in the same environment. If you need NumPy, run `python -m pip install numpy` using the Python you will open the demo with. The demo runs offline after setup.

Open **Run on Windows.cmd**, **Run on macOS.command**, or **Run on Linux.sh**. You can also run `python forecast.py` in the extracted folder. Use `py -3` or `python3` if that is how you start Python. Each model reads the same invented measurements in `example.json`.

```text
python forecast.py --model released-core example.json
python forecast.py --model random-core example.json
python forecast.py --model scratch-attention example.json
```

| Checkpoint | How it learned |
| --- | --- |
| [Released core](checkpoints/released-core.npz) | The shared attention weights from NeuroTranslate 0.0 stayed fixed. The new input and output layers learned from the walks. |
| [Random core](checkpoints/random-core.npz) | The same attention block stayed fixed at its random starting values. The new input and output layers learned from the same walks. |
| [Scratch attention](checkpoints/scratch-attention.npz) | The whole model learned from the same walks, including the attention block. It started from the same random weights as the random-core check. |

The checkpoints include the learned weights and the means and scales used to put the readings on a common numerical scale. Those few summary numbers come from the fit set. The package contains no original recordings or individual predictions. The [seven-task joint demo](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/) is the default at the top level of the ZIP.

## Use the same input format

Keep the task and domain names from `example.json`. Supply ten consecutive 20 ms bins on the original 1,000 samples-per-second clock. The last bin ends at the issue tick. Each row of `X` has fourteen muscle voltages in the order shown in `CHECKPOINTS.json`, followed by the mean signed upward force of the named plate in newtons. The muscle values are root-mean-square volts, a measure of the size of the voltage in that bin. Use `null` for an unavailable reading. The forecast is withheld when any required reading is missing.

The training label dates each new load at the first rise to at least +20 N after the plate has unloaded. The reading must stay at or above +20 N for 20 consecutive samples, including the first one. A plate already carrying weight can therefore have a negative label for a *new* load. The force-impulse target starts one sample after issue and ends 100 samples after issue. [Recording study](https://pubmed.ncbi.nlm.nih.gov/38040770/) · [Credits and licence](NOTICE.md)
