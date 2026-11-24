# Forecast force on a plate with NeuroTranslate 0.0

A plate set into a walkway measures how hard a foot pushes against it. Give the model the last 200 milliseconds of muscle and force readings. It estimates whether that plate will start to carry load in the next 100 milliseconds. It also estimates the force accumulated over that interval.

## Try the example

1. Extract the NeuroTranslate 0.0 ZIP and open `recorded-force/`. The seven-task demo is in the top-level folder.
2. Install Python 3.10 or later. In the Python environment you will use for the demo, run `python -m pip install -r requirements.txt`.
3. Open **Run on Windows.cmd**, **Run on macOS.command**, or **Run on Linux.sh**. If the launcher opens as text, open a terminal in `recorded-force/` and run `python forecast.py`. Use `py -3` or `python3` in place of `python` if that is how you start Python.

The example uses invented readings from [`example.json`](example.json). It runs offline once NumPy is installed. To try one set of saved weights at a time, use these commands.

```sh
python forecast.py --model released-core example.json
python forecast.py --model random-core example.json
python forecast.py --model scratch-attention example.json
```

| Saved weights | What was fitted |
| --- | --- |
| [Released core](checkpoints/released-core.npz) | The original NeuroTranslate 0.0 attention weights stayed fixed. The new input and output layers learned from the walks. |
| [Random core](checkpoints/random-core.npz) | The attention block stayed at its random starting values. The same new layers learned from the same walks. |
| [Scratch attention](checkpoints/scratch-attention.npz) | The whole model learned from the walks. Its attention block started at the same random values as the random-core example. |

## Read the forecast

- **Chance of a new load** describes the named plate. A plate can carry weight throughout the forecast window without a new loading event. The test checks whether force reaches +20 N after the plate has unloaded and stays at or above +20 N for 20 consecutive samples.
- **Signed vertical impulse** adds the next 100 vertical force readings and multiplies the sum by the time between readings, one millisecond. The unit is the newton-second. Upward force is positive.

The example shows how to run the models. It does not establish their accuracy on a real walk. All three fitted the same five walks from two of twelve assigned people. The other 31 walks lacked at least one required muscle name. The eligible walks yielded 1,525 overlapping windows from plates 1 and 2. Forty-four positive windows represent nine loading events. Accuracy on other people or walks is still unmeasured. The plates cover part of the walkway.

## Use your recordings

Start from [`example.json`](example.json) and keep its task and domain names. Supply ten consecutive groups of 20 samples on a common 1,000 Hz clock. End the last group at the issue tick, which is the last sample available when you ask for the forecast.

In each row of `X`, put the 14 muscle readings in the order listed in [`CHECKPOINTS.json`](CHECKPOINTS.json). For each muscle, square the 20 voltages, average those squares, then take the square root. This gives the root-mean-square voltage in volts. Put the average signed vertical force of plate 1 or 2 in newtons in the last column. Use `null` for a missing value. The program withholds a forecast when a required reading is missing. Both outputs cover the samples one through 100 ticks after the issue tick.

The files hold learned weights and the scaling values computed from the fitting walks. They carry the license and attribution given in the notice. [Recording study](https://pubmed.ncbi.nlm.nih.gov/38040770/) · [Credits and license](NOTICE.md)
