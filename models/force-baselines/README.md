# Forecast the next tenth of a second on a force plate

A force plate is a patch of floor that measures how hard a foot pushes on it. Take the latest 200 milliseconds of upward force on one plate and of the tiny voltages picked up by electrodes over named muscles. Can those measurements tell us whether the plate will start to carry weight in the next 100 milliseconds, and how much force will build up over that interval?

These NeuroTranslate baseline candidates give two numbers for that experiment. One is the estimated probability of a new load. The other is the signed vertical force added up through the next 100 milliseconds, called **impulse** and measured in newton-seconds (N·s). A plate that already carries weight can have a substantial impulse without a new loading event.

## Run the example

With Python 3 and NumPy installed, keep the files together and open **Run on Windows.cmd**, **Run on macOS.command** or **Run on Linux.sh**. Each opens the six-channel example. To try either example from a terminal, run one of the commands below. The program uses invented histories and prints the predictions for all four penalty settings in the combined force-and-muscle comparison.

```sh
python -B predict.py common-six
python -B predict.py strict-fourteen
```

Both archives contain 40 fitted candidates. Each includes two outputs, five sensor comparisons and four penalty values. The fitted scales and coefficients come from the fitting walks. Choosing a penalty and judging how well a probability matches observed frequency both require separate validation. The example shows how to run the candidates. Its numbers describe the invented inputs.

| Archive | Fit recordings | EMG channels |
| --- | --- | --- |
| `common-six.npz` | 36 walks from 12 people | LBF, LERS, LGAS, LRF, LST, RERS |
| `strict-fourteen.npz` | 5 walks from 2 people. The other 31 assigned walks lacked at least one required name. | LBF, LERS, LGAS, LRF, LST, LTA, LVL, RBF, RERS, RGAS, RRF, RST, RTA, RVL |

EMG is the voltage recorded by electrodes placed on the skin over a muscle. In the archive names, L and R mean left and right. BF is biceps femoris, ERS is erector spinae, GAS is gastrocnemius, RF is rectus femoris, ST is semitendinosus, TA is tibialis anterior and VL is vastus lateralis.

## Supply a history

Use ten 20 ms bins, oldest first. End the last bin at the current recorded sample. At the source rate of 1,000 samples per second, each bin contains 20 samples. For each muscle, square its voltage samples, average the squares, then take the square root. That gives root-mean-square (RMS) voltage in volts. For the same ten bins, take the mean signed, calibrated vertical force in newtons on the plate you want to forecast. Supply the original physical units. The loader applies the saved fitting scales.

```python
import numpy as np
from predict import load

grid = load("common-six")
emg = np.full((10, len(grid.channels)), 0.00003)
force = np.linspace(-0.5, 1.0, 10)
probability = grid.predict(
    endpoint="event", group="main", arm="force_emg", penalty=0.01,
    emg_rms_v=emg, past_force_n=force,
)
print(probability)
```

The `main` group compares muscle alone (`emg`), force alone (`force`), and both histories (`force_emg`). The `early` group compares `force_emg` against `force_earlier_emg`. For the latter, pass `earlier_emg_rms_v` from the same 200 ms window moved 500 ms earlier, and keep `past_force_n` current. For an impulse estimate, use `endpoint="impulse"`. The penalty choices in every comparison are `0.001`, `0.01`, `0.1` and `1.0`.

## What the plate measured

The fitting walks came from adults walking barefoot at their preferred speed on a laboratory walkway. Each prediction concerns plate 1 or 2. A new load was dated at the first crossing of +20 N after at least 20 milliseconds between −10 and +10 N, provided the load stayed at or above +20 N for 20 milliseconds. Predict from complete earlier bins. For a comparison with later measurements, keep pending or unknown load states and missing samples out of the event comparison.

The experiment uses one clock stored in the recording to align both signals. It leaves physical sensor delays unmeasured. The two plates cover part of the walkway, so the event count covers those surfaces. The model output describes loading at that patch of floor. An independent recording is needed to test accuracy, probability calibration and transfer to another setup or to new people.

The archives contain coefficients and fitting scales. Check them against [SHA256SUMS](SHA256SUMS). The bundled code, documentation and fitted candidates carry the project's [CC0 dedication](LICENSE). Tamaya Van Criekinge and colleagues published the underlying healthy walking recordings under CC0 1.0. [Versioned source archive](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Study and methods](https://www.nature.com/articles/s41597-023-02767-y)
