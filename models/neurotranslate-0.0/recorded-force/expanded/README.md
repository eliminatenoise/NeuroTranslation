# NeuroTranslate 0.0 walking force preview

A force plate in the floor measures the push of a foot during a walk. Give NeuroTranslate the last 200 milliseconds of muscle voltage and vertical force measured during the walk. It predicts whether the plate will start carrying load and estimates how much force will accumulate over the next 100 milliseconds. This second output is called **impulse**. It adds up force over time and is measured in newton-seconds.

To try both new checkpoints with invented readings, extract the ZIP and run `python predict.py --model past-load-gate --check-example` after the setup below.

## Set up Python and run the example

Install [Python 3](https://www.python.org/downloads/) if needed. Open a terminal in the extracted folder. These steps create a Python environment in the folder and install NumPy, the software that runs the calculations. Use the same terminal for all four lines.

### Linux and macOS

Enter these four commands in Bash or Zsh.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install numpy
python predict.py --model past-load-gate --check-example
```

### Windows

In Command Prompt, run the following. If `py` is unavailable, replace the first line with `python -m venv .venv`.

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install numpy
python predict.py --model past-load-gate --check-example
```

The check prints **Example matches the reference for both checkpoints** when the outputs agree with the saved numbers. The small tolerance accounts for numerical differences across computers. The model runs offline after NumPy is installed.

If the first command reports that `venv` or `ensurepip` is missing, install a version of Python that includes both. On Debian or Ubuntu, install the matching `python3-venv` package and repeat the first command. If the environment is active and `python -m pip` is unavailable, run `python -m ensurepip --upgrade` there before installing NumPy.

## What the example shows

Each checkpoint returns a probability from 0 to 1 and a signed impulse. The example includes three histories. One has little force, one has a higher force reading, and one has muscle readings with force missing. For that last history, the gated model reports a probability and leaves impulse as `null`.

The `past-load-gate` option runs the two new checkpoints. One keeps its starting attention weights fixed during fitting. The other learns changes to them. To check the two earlier expanded checkpoints against their original example, run `python predict.py --check-example` or add `--model expanded` to that command.

You can also run the new example through the launcher for your system. The launcher uses the Python environment in the extracted folder.

| System | Example command |
| --- | --- |
| Linux | `sh "Run forecasts on Linux.sh" --model past-load-gate --check-example` |
| macOS | `sh "Run forecasts on macOS.command" --model past-load-gate --check-example` |
| Windows | `"Run forecasts on Windows.cmd" --model past-load-gate --check-example` in Command Prompt |

## Enter your own readings

Copy [the example file](past-load-gate-example.json). Each item in `histories` holds ten 20-millisecond rows from the same plate, oldest first. The last row ends at the last sample available when the forecast is requested.

- **`emg_rms_v`** gives six muscle voltage magnitudes per row, in order `LBF`, `LERS`, `LGAS`, `LRF`, `LST`, `RERS`. For each channel, square the 20 voltages, average the squares, then take the square root. Enter the result in volts.
- **`force_mean_n`** gives the mean vertical force on the plate for each row. Enter newtons, with upward force positive.

Write `null` for a missing measurement. Provide at least one observed value in each history. Run `python predict.py --model past-load-gate --input my-history.json` in the Python environment you set up.

## How the model did on the fitting walks

The trainable-core gate had a mean impulse error of **3.042 N·s**. Extending the last force reading gave **3.422 N·s**. The largest improvement came when the plate already carried load. Error rose when the plate started unloaded and no new load was recorded.

Both scores come from the same 12 people and 36 walks used to fit the models. Neighboring forecast windows overlap. The example with missing force is invented, and performance on new people remains unmeasured. [Full comparison and sources](MODEL-CARD.md)
