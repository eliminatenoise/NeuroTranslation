# Compare walking-force forecasts

Before giving a larger model the job, see what a simpler calculation can do. These fitted calculations use earlier muscle or force readings, or both, to estimate what happens on one plate in the floor. They predict whether the plate will start carrying load and the signed vertical force accumulated in the next 100 milliseconds.

## Try the invented example

1. [Download the baseline ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/force-baselines.zip) and open the extracted `force-baselines/` folder.
2. Install Python 3 and install NumPy in the same environment with `python -m pip install numpy`.
3. Open **Run on Windows.cmd**, **Run on macOS.command**, or **Run on Linux.sh** to try the six-channel example. Or run either command from this folder.

   ```sh
   python -B predict.py common-six
   python -B predict.py strict-fourteen
   ```

The program prints two values for each of four settings. The first estimates the chance of a new load. The second is *impulse*, the sum of the vertical force readings multiplied by the time between readings, in newton-seconds. A plate that is already carrying weight can have substantial impulse without a new load.

| Saved file | Walks used for fitting | Muscle channels in order |
| --- | --- | --- |
| [`common-six.npz`](common-six.npz) | 36 walks from 12 people | LBF, LERS, LGAS, LRF, LST, RERS |
| [`strict-fourteen.npz`](strict-fourteen.npz) | 5 walks from 2 people. The other 31 walks lacked one or more required channel names. | LBF, LERS, LGAS, LRF, LST, LTA, LVL, RBF, RERS, RGAS, RRF, RST, RTA, RVL |

## Choose a calculation

Each file holds 40 candidates. There are two forecasts, five ways to combine the inputs and four values for the *penalty*, which controls how much the fitted weights can vary. The example uses the calculation that reads both current muscle activity and force. Select a penalty on separate validation recordings before comparing accuracy on new people. The output's chance estimate also needs checking against the rate of observed events.

| Set | Options |
| --- | --- |
| `main` | Current muscle (`emg`), current force (`force`), or both (`force_emg`). |
| `early` | Compare `force_emg` with `force_earlier_emg`. The latter uses muscle readings from the same 200 ms window moved 500 ms earlier while keeping current force fixed. |

The available penalties are `0.001`, `0.01`, `0.1` and `1.0`. This example calls the six-channel file directly from Python with invented data.

```python
import numpy as np
from predict import load

grid = load("common-six")
emg = np.full((10, len(grid.channels)), 0.00003)
force = np.linspace(-0.5, 1.0, 10)
print(grid.predict(
    endpoint="event", group="main", arm="force_emg", penalty=0.01,
    emg_rms_v=emg, past_force_n=force,
))
```

Use `endpoint="impulse"` for the second forecast. Supply `earlier_emg_rms_v` when using `force_earlier_emg`.

## Use your recordings

Take 200 samples ending at the issue tick, when you ask for the forecast. Group them into ten consecutive 20 ms bins, oldest first, on the shared 1,000 Hz clock. For each muscle, square its samples, average them and take the square root. This gives root-mean-square voltage in volts. For the plate, average the signed vertical force in each bin and supply newtons, with upward positive. The loader applies the saved fitting scales.

The channel names refer to voltages recorded by electrodes placed on the skin over a muscle. L and R mean left and right. BF is biceps femoris, ERS is erector spinae, GAS is gastrocnemius, RF is rectus femoris, ST is semitendinosus, TA is tibialis anterior and VL is vastus lateralis.

## What the walking experiment measured

Adults walked barefoot at their preferred speed. Forecasts cover plate 1 or 2, which measure force on part of the walkway. The study dates a new load at the first crossing of +20 N after at least 20 milliseconds between −10 and +10 N, if force then stays at or above +20 N for at least 20 milliseconds. Keep missing samples and unresolved load states out of an event comparison. The stored clock aligns the signals, while the physical sensor delays remain unmeasured.

The two files contain fitted weights and their scaling values. Check them with [`SHA256SUMS`](SHA256SUMS). The bundle uses [CC0](LICENSE). Van Criekinge and colleagues also published the walking recordings under CC0 1.0. [Versioned data](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Study methods](https://www.nature.com/articles/s41597-023-02767-y)
