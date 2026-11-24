# Forecasting the next 100 milliseconds of walking

This NeuroTranslate model uses the recent positions of both heels and the force under each foot. For each side it estimates the chance of a new load on the floor, the total effect of vertical force over the next tenth of a second, and how far the heel will move in each direction.

For shorter walking clips and a mode that uses camera positions without force readings, see the [overground preview](OVERGROUND.md).

To try four small walking models on invented readings in a browser, see the [compact NeuroTranslate 0.0 walking download](../../neurotranslate-0.0/compact-walking/README.md).

## Open the example

Download and extract the paired-plates preview. In a terminal, open the extracted folder and run the command for your computer. You need Python 3.9 or later. The folder contains the saved weights and an invented example. It runs offline.

| Computer | Command |
| --- | --- |
| Linux | `./launch-walk-linux.sh` |
| macOS | `./launch-walk-macos.command` |
| Windows | `.\launch-walk-windows.cmd` |

On Linux and macOS you can also run `python3 aligned_walk.py`. On Windows, use `py -3 aligned_walk.py` or `python aligned_walk.py`. The output gives two predictions in left, right order. The chance of a new load runs from 0 to 1. Signed force impulse adds up the vertical force across the next 100 milliseconds, weighting each reading by how long it lasted. Its unit is the newton-second. Heel displacement gives the change along the lab's three axes, in millimetres, with the third axis pointing up.

## What the recordings showed

The [Kuopio recordings](https://doi.org/10.5281/zenodo.24194741) put the cameras, floor force sensors and muscle electrodes on a common recording clock. Six people supplied fitting data and five different people had enough complete recordings to score. One assigned fitting file lacked the expected channel layout, and one assigned scoring file had no common input windows. All the comparisons below use the same 5,700 scored foot forecasts, including 531 measured starts of a new load. Each person counts equally.

| Recent measurements | Load probability error | Force impulse error (N·s) | Heel displacement error (mm) |
| --- | ---: | ---: | ---: |
| Force plates only | 0.0170 | 4.64 | 46.1 |
| Heel positions only | 0.0120 | 8.54 | 37.7 |
| Force plates and heels, starting with earlier force weights | 0.0118 | **3.93** | 30.6 |
| Force plates and heels, starting with new weights | **0.0097** | 4.60 | **27.8** |
| Force plates, heels and recent muscle readings | 0.0147 | 4.36 | 35.2 |
| Force plates, heels and muscle readings from one second earlier | 0.0142 | 4.44 | 34.6 |
| Continue the last measured heel velocity | — | — | 63.3 |

Lower values mean smaller forecast errors. The first column averages the squared difference between a predicted chance and the measured outcome of 0 or 1. The force column averages the absolute error. The heel column averages the straight-line distance between the predicted and measured heel displacement.

Adding heels to the force model reduced all three errors for each of the five people. Using heels alone gave about the same mean load probability error as using both, while its force impulse error was more than twice as large. The model started with new weights scored better on average for load probability and heel motion, and the model started with earlier force weights had the lowest mean impulse error. The launcher defaults to that second model. Recent muscle readings increased the mean error on all three measures compared with force and heels alone. The recording and muscle comparisons are available for further testing.

This first test covers walking-labelled captures from one lab. The trigger interval establishes the time covered by usable readings. The exact treadmill speed and the start and end of steady walking within those recordings are unknown. The forecast horizon follows the recording clock. This experiment uses prepared sensor readings and has no live camera benchmark. [How the recordings were made](https://doi.org/10.1038/s41597-026-08550-z)

## How the same weights fared in a second lab

We applied the saved model to a second lab's treadmill recordings without changing its weights. These recordings come from the comfortable-speed condition in the Fukuchi walking dataset. Earlier experiments had used their force readings. This test also uses the left and right heel markers. It compares 14,585 foot forecasts and 983 measured load starts across 39 people. [Fukuchi study and recording methods](https://doi.org/10.7717/peerj.4640)

| Recent measurements | Load probability error | Force impulse error (N·s) | Heel displacement error (mm) |
| --- | ---: | ---: | ---: |
| Force plates only | 0.0174 | 5.39 | 46.1 |
| Heel positions only | 0.0402 | 7.67 | **31.4** |
| Force plates and heels, starting with earlier force weights | 0.0139 | 4.88 | 38.0 |
| Force plates and heels, starting with new weights | **0.0130** | **4.85** | 31.5 |
| Continue the last measured heel velocity | — | — | 65.2 |

The default model was fitted using the earlier force weights as its starting point. It had lower average error on all three forecasts than the model fitted on force alone. Heel positions alone had the lowest average heel error by a small margin. Their force impulse error was more than 50% higher than that of the combined fits.

The `force_motion_cold` option uses both readings and was fitted from new starting weights. It had a lower average heel error than the default at both labs. In the second lab its average heel error was 31.5 mm, compared with 38.0 mm for the default. The difference in force impulse error was small compared with the variation across people. In the first lab the default gave the lower impulse error. The second test covers the lab's comfortable-speed setting on its recording clock. [Source recordings](https://doi.org/10.6084/m9.figshare.5722711.v2)

## Use your own prepared readings

Copy `example-walking.json`. Give every field in the order left foot, right foot. The two sides share one list of `bin_end_ms` times, spaced exactly 20 milliseconds apart, with the last time at the forecast moment. For each time, supply the mean vertical force in `vertical_force_n`, in newtons with upward force positive. Also supply the most recent recorded heel position as `[x, y, z]` in `heel_xyz_mm`. The force bin uses only samples already available by its end. The heel positions must share the same lab frame and use millimetres.

In `plate_state_by_bin`, use 0 for unknown, 1 for unloaded, 2 for a load that is awaiting confirmation, and 3 for loaded. In this study, a plate became unloaded after 20 milliseconds within ten newtons of zero. A new load then began at the first sample at or above 20 newtons if the force stayed at least that high for 20 milliseconds. Use only readings available by each bin end to set its input state. Later readings confirm a new load for scoring. The event comparison covers predictions issued when the plate was unloaded or loaded. Treat a new-load estimate from an unknown or unconfirmed state as untested.

Use 35 or more complete bins for the default and the other options without the one-second delay. The default uses ten consecutive bins for a foot and five matching windows of the other foot. The windows end at the forecast moment or 100, 200, 300 or 500 milliseconds earlier.

Run `python3 aligned_walk.py --input your-walking.json`. Use `py -3` on Windows. Add `--arm` and one of these names to try a different set of saved weights.

- `force_motion_cold` takes force and heels and uses the weights fitted from a new start.
- `force` needs only the force and state fields. `motion` needs only the heel positions.
- `force_motion_muscle` and `force_motion_earlier_muscle` also need `relative_muscle_activity`. Use the outer thigh muscle (vastus lateralis) first and the inner hamstring (semitendinosus) second on each side. In the original processing, each activity value was the natural logarithm of one plus the ratio of voltage variation in the current bin to variation over the five preceding bins. Subtract the mean from the voltages separately within each bin. For the numerator, take the square root of the mean of the squared remaining voltages in the current bin. For the denominator, take the square root of the mean of the squared remaining voltages pooled across the preceding bins. Supply at least 85 complete bins for the one-second comparison.

`walking-heads.json` contains the six sets of weights. `walking-results.json` contains the scores and matched comparisons. The authors' recordings are shared separately under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). This preview ships the model, an invented example, and aggregate results.
