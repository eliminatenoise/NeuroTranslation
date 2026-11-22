# Forecast the next step during overground walking

The NeuroTranslate overground model uses 200 milliseconds of recent readings to forecast the next 100 milliseconds. For each foot, it estimates where the heel will move, whether its assigned floor plate will start carrying a new load, and how much vertical force will add up on that plate.

## Run the invented example

Extract the paired-plates preview ZIP and open a terminal in the extracted folder. Run the command for your computer. You need Python 3.9 or later. The model and the invented example are in the download.

| Computer | Command |
| --- | --- |
| Linux | `./launch-overground-linux.sh` |
| macOS | `./launch-overground-macos.command` |
| Windows | `.\launch-overground-windows.cmd` |

The default, `body-force`, uses the heel positions, the midpoint between two front pelvis markers, and the force readings. Add `--mode body-motion` for the camera-position-only fit. Add `--mode room-force` to use heel positions in room coordinates with force. The room mode can leave out the pelvis positions. Each option loads weights already fitted to treadmill recordings.

The result shows which earlier windows the model could use. A load probability runs from 0 to 1. Force impulse is vertical force added up over 100 milliseconds, using the time between readings. Its unit is the newton-second. Heel displacement gives the predicted travel in three directions in millimetres.

## What a shorter history changes

We fitted all three models on the same six treadmill walkers. We then applied the saved weights to 266 overground clips of 12 other people at six step widths. The entire test had 4,820 scores each for heel movement and force impulse, and 3,246 scores for the chance of a new load. Each person counts equally within each measure.

There were 265 confirmed starts of new loads, all on the right plate. The clips began around the left-foot contact, leaving too little earlier force to confirm a new left-foot load. The shorter histories covered all the confirmed right-foot starts. The earlier model’s full 700 milliseconds of history would have missed all of them in these clips. [Overground recordings and methods](https://doi.org/10.1038/s41597-025-05113-6)

| Forecast method | Load probability error | Force impulse error (N·s) | Heel displacement error (mm) |
| --- | ---: | ---: | ---: |
| Original treadmill weights with the same shortened windows | 0.1872 | 13.96 | 113.1 |
| `room-force` | **0.0543** | 9.22 | 74.0 |
| `body-force` | 0.0566 | **7.86** | 36.7 |
| `body-motion` | 0.1074 | 9.83 | **29.6** |
| Simple reference for each measurement | 0.0826 | 10.11 | 60.6 |

Smaller errors mean closer forecasts. The load probability score averages squared differences from the observed outcomes of 0 and 1. Force impulse error is the average absolute difference. Heel error is the average straight-line distance between the predicted and recorded movement. In the first row, the original weights use only the windows available to the newer models at that moment. The simple references predict no new load, hold the last measured force, or keep the last measured heel speed and direction.

`body-force` had lower heel and impulse errors than `room-force` for all twelve people. It is the default because it improved both physical measurements and beat all three simple references on average. The camera-position-only fit had the lowest heel error. Supplying force readings reduced force impulse error and load probability error for every person compared with that fit.

The tests use recordings with two plates in the floor. Each plate measures force within its own area. A heel elsewhere in the room can carry force outside the plates. The study used the authors’ saved marker positions, including gaps they had filled before release. These tests cover the recording clock and one sample of young men. [Source recordings and CC BY 4.0 terms](https://doi.org/10.17608/k6.auckland.27015301.v2)

## Give the model your own prepared history

Copy `example-overground.json`. Keep left, right order wherever there are two sets of readings. Use shared `bin_end_ms` times exactly 20 milliseconds apart. The final time is when the forecast is made. Supply at least ten bins. Use `[x, y, z]` positions in millimetres, with X to the left, Y backward, and Z up.

- `heel_xyz_mm` has one position per foot per bin. Use the last recorded position available by each bin end.
- `pelvis_xyz_mm` has one position per bin. Average the positions of the front left and front right pelvis markers. Both body modes need this field. The model takes out horizontal pelvis motion and then adds its estimated travel back to the forecast.
- `vertical_force_n` gives the mean vertical force per plate in each bin. Upward force is positive. Use samples available by the end of the bin. The camera-position-only option can run without this field.
- `plate_state_by_bin` gives the known state at each bin end. The codes are 0 for unknown, 1 for unloaded, 2 for a new load awaiting confirmation, and 3 for loaded. The event test covers 1 and 3. Use the [walking guide](WALKING.md#use-your-own-prepared-readings) for the exact force thresholds. The camera-position-only option can run without this field.

Use `null` for a missing position or force sample. The most recent ten bins must have complete readings for the chosen inputs. An older window is skipped when a needed reading is missing. The saved model can use older windows that ended 100, 200, 300, or 500 milliseconds before the forecast time.

Run `python3 adaptive_walk.py --input your-walk.json` on Linux or macOS. On Windows, use `py -3 adaptive_walk.py --input your-walk.json`. Add `--mode body-motion` to use only the positions. Prepare positions from your camera recording before running the program. The sample is invented, and the download includes the fitted weights and aggregate results.
