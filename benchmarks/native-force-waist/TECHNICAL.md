# Native-clock force and waist rotation forecasts

Persistence had the lowest overall force-impulse error at **2.979701 N·s**. Ridge had the lowest error when the latest force mean reached 20 N. For waist rotation, ridge and attention lowered error from **0.516938** to **0.306853** and **0.307716 rad/s**, respectively. Both improved on persistence in all three held participants. Ridge had lower waist error than attention in two of the three. [Aggregate results](results.json) · [Simple edition](SIMPLE.md)

## Inputs and targets

The authors recorded force plates and watches in five activities: walking, jogging, running, heel drops and step drops. We use the engineering participant for source checks, six other people for fitting and three held people for scoring. Force and waist use their own native clocks. The authors started the devices separately and used complete recordings to align their signals afterward. This test concerns each device’s own later values. [Author methods](https://doi.org/10.1038/s41597-026-07183-6) · [Source archive](https://doi.org/10.5281/zenodo.17376717)

Every input contains ten completed 20 ms means. Force uses the signed vertical reading in newtons, with the positive loading direction corroborated in the engineering recordings. Forecasts are spaced 400 ms apart. The 1 kHz clock provides 200 earlier samples through the issue and 100 later samples. The target sums the later samples and divides by 1,000, producing newton-seconds.

Waist inputs use three acceleration axes in units of gravity and three rotation-rate axes in rad/s. Each nominal 400 ms forecast time is moved to the next recorded sample if it arrives within 25 ms. The forecast uses values strictly before that sample. Its target begins with the withheld sample and averages its three rotation-rate axes over the next 100 ms. Time-weighted means hold each sample forward until the next. Required spans with a gap or endpoint sample age over 25 ms are ineligible. The wrist archive contains long gaps in 154 of 460 recordings, compared with 13 of 451 at the waist. Wrist forecasts are outside this comparison.

## Model and matched results

The 9,220-parameter model uses separate input and output layers and one shared temporal attention block. Training used 5,763 force and 5,058 waist windows for 240 updates. Scaling, ridge coefficients and attention weights were fitted only on the six fitting people. Persistence extends the latest mean. The trend rule extrapolates the last two means. Ridge is a linear fit with a penalty on the size of its coefficients. All four forecasts were sealed before later signal values were decoded.

Force error is the absolute impulse miss. Waist error is the root mean square across the three rotation-rate components for each window. Each person contributes equally after averaging windows within trials and trials within that person. Force scored 2,537 windows in 128 recordings. Waist scored 1,561 of 1,573 forecasts from 102 recordings. Twelve lacked a valid target, and one other recording failed the clock check before any forecast was issued.

| Method | All force (N·s) | Latest mean ≥20 N (N·s) | Latest mean <20 N (N·s) | Waist (rad/s) |
| --- | ---: | ---: | ---: | ---: |
| Persistence | **2.979701** | 20.106671 | **0.635377** | 0.516938 |
| Linear trend | 4.081067 | 25.460167 | 0.744325 | 1.309280 |
| Ridge | 4.239630 | **18.202190** | 1.783313 | **0.306853** |
| Shared attention | 3.900747 | 19.607338 | 1.431896 | 0.307716 |

The 372 higher-recent-force windows and 2,165 lower-recent-force windows are defined by the observed last input bin. The ranking applies to three held people on these archived tasks. The output on the waist task is device rotation rate. [Exact aggregate scores](results.json)

## Run the checkpoint

In the browser, select **Force plate** or **Waist watch**. Open **Edit earlier readings** or click the graph to focus an input. The page updates all four forecasts from the edited means. **Input channel** selects which waist measurements to plot and edit. The waist output table shows all three rotation axes. **Restore example** resets the selected history. Under **Results on recorded data**, filter force by its last observed mean. The table uses the original held results. [Browser preview](https://eliminatenoise.github.io/NeuroTranslation/walking-force/force-and-waist/)

The browser package opens without a server. Extract it and open `index.html`, or use **Open on Linux.sh**, **Open on macOS.command** or **Open on Windows.cmd**. The page contains the same model weights as the Python checkpoint.

For the command-line program, extract `Native-Force-and-Waist.zip`. It requires Python 3.10 or later and NumPy. Use `python3 -m pip install numpy` on Linux and macOS, or `py -3 -m pip install numpy` on Windows. Run `Run-Forecasts.sh` on Linux, `Run-Forecasts.command` on macOS or `Run-Forecasts.cmd` on Windows. From a terminal in the extracted folder, use `python3 run_forecast.py` on Linux and macOS or `py -3 run_forecast.py` on Windows. Use `python` in place of `py -3` if Windows has only the `python` command.

The program prints all four methods on two generated inputs. To use your own averaged readings, add `--input history.json` to the terminal command. Provide a JSON object with `task` and `history` fields. Use `force` with ten rows of one force value, or `waist` with ten rows of six ordered values. Put the oldest row first. Each waist row uses acceleration X, Y, Z in g, then rotation X, Y, Z in rad/s.
