# Where will the knees be 15 frames from now?

Give the model five snapshots of someone walking at 0.5 m/s on a treadmill. Each snapshot records how far the hips, knees and ankles have bent. From those five snapshots, a small Transformer estimates the angle of each knee 15 frames later, about a quarter of a second at 60 frames per second.

**A previous stride gave the closest estimate.** When four seconds of knee history were available, finding a repeated movement and copying its next position gave **3.54°** mean absolute error. The Transformer gave **4.46°** on the same 40,201 forecasts. The stride rule won for 10 of the 12 test participants. Its advantage averaged 0.93°, with a participant-bootstrap 95% interval of 0.36° to 1.57°. It saw a longer stretch of walking and needed no training. These numbers describe one treadmill speed in this dataset.

## What the shorter history tells us

The Transformer sees angles 24, 18, 12, 6 and 0 frames before each cutoff, spanning 0.4 seconds. With precisely that history, a straight-line model fitted to the same six joints came closest to the Transformer. The Transformer reduced its mean error by 1.13° and improved the prediction for each of the 12 walkers. The paired participant-bootstrap 95% interval for that reduction was 0.86° to 1.46°.

| Method | Inputs available at the cutoff | Mean absolute error |
| --- | --- | ---: |
| Transformer | Both hips, knees and ankles over 0.4 s | 4.47° |
| Six-joint ridge regression | Same five snapshots | 5.60° |
| Knee-only ridge regression | Both knees at the same five times | 6.34° |
| Hold the last angle | Most recent knee angles | 15.82° |
| Continue the latest slope | Knee change in the last six frames | 22.75° |

The table uses all 42,781 eligible test cutoffs. The stride comparison above requires 240 consecutive earlier samples, which removes the early cutoffs from each trial. The split was chosen before scoring. The model trained on 39 walkers and saw each of the 12 test walkers for the first time at evaluation. Each walker contributes equally to the averages. Overlapping windows from one person share much of the same movement.

The Transformer averaged 4.45° on the right knee and 4.48° on the left. Individual participants' bilateral errors ranged from 2.72° to 6.02°. Shift the hip and ankle histories halfway around each test trial while keeping its knees in place and the error rises to 16.30°. The model uses the timing between those joints. The perturbation disrupts that coordination artificially and cannot identify which joint drives another.

## What was measured

Xsens body-worn inertial sensors supplied the recorded movement. The knee target is the angle reconstructed between the upper and lower leg in the source's ZXY coordinate convention. Both predictors and targets come from the same stored reconstruction. Its error against an independent measurement of the physical knee was not tested here. All 51 recording headers report 60 Hz. Six identify HD processing, which uses the complete recording to refine earlier estimates. The other 45 say Live. The processing label gives neither an end-to-end delay measurement nor an online performance test. Restricting a model to earlier stored frames establishes the order of its inputs. Establishing a real-time forecast from the sensors would also require a streaming reconstruction with known delay and an independent movement measurement. [Dataset and acquisition protocol](https://physionet.org/content/multimodal-gait-dataset/1.0.0/) · [Xsens manual, §9.1](https://www.xsens.com/hubfs/User_Manual_Xsens%202025.pdf)

The study also recorded scalp electrical activity and lower-limb muscle signals. It describes a hardware trigger at acquisition. The inspected exports did not establish the common sample origin or the time coverage of each muscle-amplitude measurement. This experiment uses the inertial joint estimates alone.

## Run a forecast

Install NumPy, open a terminal in this folder and run the example. It contains invented angles and has no measured future endpoint.

```sh
python predict.py example.json
python predict.py example.json --model all_ridge
```

The first command returns the right and left knee estimates in degrees. For your own example, supply five chronological rows in the order used in `example.json`. Each row gives right hip, left hip, right knee, left knee, right ankle and left ankle. Hip and knee values are flexion/extension. Ankle values are dorsiflexion/plantarflexion.

The participant-weighted errors, uncertainty and source hashes accompany the weights. [Reproduce the study](REPRODUCE.md) · [Model results](results.json) · [Prior-stride comparison](phase-results.json) · [Sources and reuse](RIGHTS.md)
