# Treadmill transfer of NeuroTranslate 0.1 force forecasts

[Compare in your browser](https://eliminatenoise.github.io/NeuroTranslation/treadmill-muscle-gaps/technical.html) · [Simple edition](README.md) · [Download the tested models](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/803c645d63055245b084efb10f34b13d83a10d29/benchmarks/walking-neural-scaling/held-walks/Held-Walking-Forecasts.zip)

The frozen three-pass NeuroTranslate 0.1 model trained with simulated input disruptions reduced mean absolute 100 ms vertical force impulse error from **16.176 to 12.029 N·s** when the final 60 ms of muscle input was hidden. It improved on the same model trained with complete input for all nine people. The earlier linear fit scored **12.810 N·s** on the same inputs. [Georgia Tech recordings](https://doi.org/10.35090/gatech/70296)

## Comparison and uncertainty

Use the [browser comparison](https://eliminatenoise.github.io/NeuroTranslation/treadmill-muscle-gaps/technical.html) to switch between full recordings and the nominal 1.2 m/s bout and between complete, 20 ms delayed and 60 ms missing muscle input. All conditions retain measured past force. Lower mean absolute signed impulse error is better. A newton-second measures the integral of force.

### Whole recording, 7,268 forecast times

| Forecast method | Complete readings | 20 ms delay | Latest 60 ms hidden |
| --- | ---: | ---: | ---: |
| Three-pass model trained in Belgium | 12.844 | 12.978 | 14.535 |
| Three-pass model trained with complete readings | 12.045 | 12.601 | 16.176 |
| Three-pass model trained with simulated interruptions | 11.964 | 11.984 | 12.029 |
| Carry the latest force forward | 17.551 | 17.551 | 17.551 |
| Continue the recent force trend with damping | 17.478 | 17.478 | 17.478 |
| Ridge linear fit | 12.213 | 12.410 | 12.810 |
| Boosted decision trees | 13.592 | 13.829 | 14.405 |

### Marked 1.2 m/s walk, 440 forecast times

| Forecast method | Complete readings | 20 ms delay | Latest 60 ms hidden |
| --- | ---: | ---: | ---: |
| Three-pass model trained in Belgium | 6.737 | 6.874 | 9.125 |
| Three-pass model trained with complete readings | 5.156 | 5.893 | 11.771 |
| Three-pass model trained with simulated interruptions | 5.210 | 5.219 | 5.394 |
| Carry the latest force forward | 11.633 | 11.633 | 11.633 |
| Continue the recent force trend with damping | 11.428 | 11.428 | 11.428 |
| Ridge linear fit | 7.923 | 7.801 | 8.896 |
| Boosted decision trees | 7.328 | 7.743 | 8.439 |

The full-recording missing-input difference, defined as interruption-trained minus complete-trained error, is **−4.147 N·s** with a paired 95 percent interval of **[−4.695, −3.521]**. The corresponding marked-bout result is **11.771 to 5.394 N·s**, a difference of **−6.377 [−7.490, −5.380]**. Complete-input differences were **−0.081 [−0.179, 0.054]** and **+0.054 [−0.115, 0.242]**. Under the 20 ms delay, interruption-trained forecasts also had lower error relative to complete-input training. Take the mean absolute window error for each person and average people equally. Use 20,000 paired person-level draws with replacement, seed 20261126, and the central 95 percent interval. [All scores and comparisons](../../../docs/treadmill-muscle-gaps/results.json)

## Recording and measurement

The verified belt provides positive-up force through its recorded Type 2 plate geometry. Six left-side muscle-voltage signals represent tibialis anterior, medial gastrocnemius, vastus lateralis, rectus femoris, biceps femoris and gluteus medius. Match the six channels and timestamps to the named voltage export at stored ticks `[2000, 4000)`. At the stored 2 kHz clock, issue at tick 4,800 and every 600 ticks after it. For time `t`, use ticks `[t−400, t)` as input and `[t, t+200)` as outcome. Sum the measured signed vertical force values and divide by 2,000 to obtain N·s. Freeze all forecasts before scoring. Independent replay reproduced all values and intervals to numerical precision.

One engineering recording fixed the plate identity. One of ten nominated evaluation recordings lacked the surveyed belt. The other nine supplied **7,268** common issues. The **440** marked-bout issues use the same nine people, full input and outcome windows, and a two-second margin inside the authors’ force-derived bounds. The full recording contains multiple treadmill movements and pauses. [Original methods](https://pubmed.ncbi.nlm.nih.gov/38129422/)

## Encoding and checks

Use ten bins of 40 samples. Each supplies force divided by 800 N, two muscle summaries and force and muscle availability indicators. Summaries are the median and 80th percentile of `log(1 + current RMS / earlier RMS)` over channels with at least three earlier available bins. RMS is the square root of mean squared voltage. The fixed width-24 recurrent forecast repeats its learned calculation three times and adds a signed correction to the latest-bin force mean times 0.1 seconds.

Include the Belgian-only starting model, trained on 12 people. The two matched arms start from weights fitted with those 12 and eight İzmir participants and reuse the same 900 updates and history draws. The augmented arm applies a 0.15 chance of a 20 ms shift and a separate 0.20 chance of a 60 ms gap to the muscle features and availability indicators. The two test conditions are applied separately. Force persistence carries forward the latest mean. The damped trend fits the last five bin means and decays extrapolation with a 50 ms time constant. Ridge and boosted trees fit the same earlier people and receive the same features. [Earlier training and comparison](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/walking-neural-scaling/held-walks)

## Run the saved models

Extract the [tested checkpoint ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/803c645d63055245b084efb10f34b13d83a10d29/benchmarks/walking-neural-scaling/held-walks/Held-Walking-Forecasts.zip). Install its pinned packages in a Python 3.13 environment. Create it with `python3.13 -m venv .venv` or, on Windows, `py -3.13 -m venv .venv`. Install with `.venv/bin/python -m pip install -r requirements.txt` or `.venv\Scripts\python.exe -m pip install -r requirements.txt`.

Use `sh "Open on Linux.sh"`, `sh "Open on macOS.command"` or `"Open on Windows.cmd"` in Command Prompt. Linux was tested after extraction. The other launchers were checked from source. Run with `--model clean_08` or `--model augmented_08`, plus `--condition delay-muscle` or `--condition hide-muscle` for the input tests. With `--input history.json`, supply ten oldest-first force means in N under `measured_plate_force_n` and four or six RMS voltages per bin under `emg_rms_volts`. Use `null` for missing voltages. The default example is synthetic. The archive contains recurrent checkpoints and force persistence. The Georgia score file includes all seven comparisons.

These are archived-clock results with simulated disruptions. The Georgia people supplied no fitting data for these checkpoints and appear in other programme tasks. The 2 kHz stored rate differs from acquisition rates reported by the authors. Physical delay and resampling remain unmeasured here. Scherpereel, Molinaro, Inan, Shepherd and Young released the original measurements under CC BY 4.0. This report supplies aggregates. [Dataset and terms](https://doi.org/10.35090/gatech/70296)
