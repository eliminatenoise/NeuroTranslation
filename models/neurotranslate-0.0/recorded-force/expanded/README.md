# NeuroTranslate 0.0 force-plate preview

Run two versions of NeuroTranslate on the same invented sensor readings. Each estimates whether a force plate will start carrying load and how much vertical force will accumulate over the next 100 milliseconds. A force plate is a platform in the floor that measures the push on it.

## Set up and run the example

Extract the entire ZIP. Install [Python 3](https://www.python.org/downloads/) if needed, then open a terminal in the extracted folder. The setup below creates a Python environment in the folder and installs NumPy, the library the models use for calculations. Keep the same terminal open until the example runs.

### Linux and macOS

In Bash or Zsh, run each line in order.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install numpy
python predict.py --check-example
```

### Windows

In Command Prompt, run each line in order. If Windows does not recognize `py`, use `python -m venv .venv` for the first line.

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install numpy
python predict.py --check-example
```

When setup succeeds, the program prints **Example matches the reference for both checkpoints** and shows the forecasts. A small tolerance allows for numerical differences between computers. Setup may require internet access. After NumPy is installed, the forecasts run offline.

If creating the environment fails with a message about `venv` or `ensurepip`, install a Python distribution with support for virtual environments and pip. On Debian or Ubuntu, install the `python3-venv` package for the Python version you use. Then run the creation command again. If the environment was created and activated but `python -m pip` is missing, run `python -m ensurepip --upgrade` in the activated environment and repeat the NumPy installation.

## Run it again

After setup, the launcher for your system uses the Python environment beside it. Run one of these commands from the extracted folder.

| System | Command |
| --- | --- |
| Linux | `sh "Run forecasts on Linux.sh"` |
| macOS | `sh "Run forecasts on macOS.command"` |
| Windows | `"Run forecasts on Windows.cmd"` in Command Prompt |

You can also run `python predict.py` after activating the environment. The result lists two numbers for each of the two invented histories and each model. **New-load probability** is a number from 0 to 1. **Signed force impulse** adds up the estimated force over the next tenth of a second and is given in newton-seconds. The invented readings help you check that the program works.

## Use the same input format

Copy `example.json` and replace the invented values. Each item in `histories` describes one plate and contains ten rows of synchronized measurements, oldest first. Each row spans 20 milliseconds.

- **`emg_rms_v`** contains six numbers per row, in the order `LBF`, `LERS`, `LGAS`, `LRF`, `LST`, `RERS`. These source labels refer to muscle recordings on the left and right sides. Each value is a root-mean-square magnitude in volts, calculated by squaring the 20 signed samples in that bin, averaging them, and taking the square root.
- **`force_mean_n`** contains one number per row. Use the average signed upward force in newtons from the same plate you want to forecast.

Use `null` where a measurement is missing. A history with no measurements is rejected. The original replay scored complete histories, so results for incomplete input should be treated as untested. In the activated environment, run `python predict.py --input my-history.json`.

## What this release tells us

On a replay of people and walks used in training, both expanded models beat the earlier six-update model on both measurements. For the amount of vertical force, simply extending the most recent force reading was more accurate than either expanded model. Performance on new people or equipment remains untested in this release.

See the [model card](MODEL-CARD.md) for the exact comparison, measurement rules, and sources. This standalone preview covers the force-plate task. Other NeuroTranslate 0.0 tasks have their own entry points.
