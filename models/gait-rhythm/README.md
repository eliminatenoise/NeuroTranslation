# Do muscle and knee recordings pick out the same walking rhythm?

An electrode on the skin of a leg records muscle electrical activity. In the same treadmill trial, inertial sensors estimate how the knees bend. These instruments can record a repeating rhythm even when we cannot put a particular muscle event at a particular point in a step. We compared the strongest repeating frequency in the two recordings at one walking speed, 0.5 metres per second. [Try the recordings and rhythm estimates](https://eliminatenoise.github.io/NeuroTranslation/gait-rhythm/)

For 9 of the 11 test participants, the two instruments picked the same frequency on the analysis grid. For the other two, the peaks were one grid interval apart. Their average absolute difference was **0.027 cycles per minute**. Using the training group’s median knee rhythm for everyone gave **2.550 cycles per minute** of error. Substituting another test participant’s muscle rhythm gave **3.055**. The matched estimate beat the training median for ten people with one tie, and beat the substituted estimate for all eleven. [Per-person estimates and errors](results.json)

| Estimate of the knee rhythm | Mean absolute difference (cycles/minute) |
| --- | ---: |
| Muscle rhythm from the same trial | 0.027 |
| Training group’s median knee rhythm | 2.550 |
| Linear adjustment to the same person’s muscle rhythm, fitted on training participants | 0.042 |
| Muscle rhythm from another test participant | 3.055 |

## What counts as a cycle?

One knee bends and straightens repeatedly during walking. We looked for the strongest periodicity in the left and right knee angles and compared it with periodicity in twelve surface muscle channels. A cycle in one leg is different from a count of individual alternating footfalls. Here the knee angles are stored estimates from Xsens and the electrical readings are exported muscle-signal amplitudes in volts. Neither is a force measurement.

Each instrument contributes its own 40-second interval starting five seconds after its first available row. The analysis uses the actual muscle timestamps in seconds and the 60 Hz frame counter for joint angles. It searches **0.45–1.50 Hz**, using a Hann taper, and averages power across channels after normalizing each channel's in-band power. The search grid is spaced by 0.0025 Hz, or 0.15 cycles per minute. For a 40-second observation, ordinary Fourier spacing is about **1.5 cycles per minute**. Searching a finer grid does not make a physiological step counter accurate to 0.027 cycles per minute. The reported difference describes agreement between estimates made with the same algorithm.

Thirty-eight people provided training recordings to set the median and fit the linear adjustment. Eleven others provided a muscle recording and knee-angle file at the chosen speed for testing. Three IDs across the selected ranges lacked a file for the pair. Each person counted once. Giving each test recording the next participant’s muscle rate in ascending ID order, wrapping at the end, provided the wrong-person comparison. Leaving each person out of the test summary in turn gave a matched-minus-median mean error difference between −2.775 and −2.190 cycles/minute, and a matched-minus-wrong-person difference between −3.315 and −2.685. These are sensitivity ranges within this group.

The comparison measures agreement in dominant rhythm over two long windows. It cannot establish the time from a particular electrical event to movement, muscle force, felt movement, or a causal neural pathway. The clocks and processing histories of the exported files would need further evidence for an event-timing claim. All trial-level rhythm estimators and controls were fixed before we examined these rhythm outcomes. Some of the same people’s *angle forecasts* had been studied separately. [Analysis specification](protocol.json) · [Timestamp units](source-clarification.json) · [Separate angle forecast](../knee-motion/)

## Reproduce the comparison

Use Python 3.11+ and NumPy. Keep the original files in a local directory. The setup verifies publisher and member checksums and extracts only the selected angle and technical files. The technical reader uses the frame-rate field. The original IMU archive is several gigabytes. Pass its local path if you already have it, or replace `--imu-archive PATH_TO_IMU.tar.gz` with `--fetch-imu` to permit the download.

```sh
python prepare.py --cache gait-input --imu-archive PATH_TO_IMU.tar.gz
python study.py fit --cache gait-input --index gait-input/SHA256SUMS.txt --output rebuilt
python study.py score --cache gait-input --index gait-input/SHA256SUMS.txt --output rebuilt
```

The [source manifest](sources.json) identifies the files, and [fit.json](fit.json) contains the training-group rate estimates and the fixed line. The public study ships derived rates and code. The original voltage and angle time series remain with PhysioNet.

## Sources and reuse

Rateb Katmah, Aamna AlShehhi, Doua Kosaji, Nour Al-Rahmani, Muhammad Abdullah, Abdul Aziz Vaqar Hulleck and Kinda Khalaf (2026), *A multimodal gait dataset of brain activity, muscle activity, kinematics and ground forces in young adults*, version 1.0.0, PhysioNet. The database and these derived frequency estimates and fitted coefficients retain CC BY 4.0 attribution. This study selected one speed, estimated spectral peaks from the exported muscle and joint-angle signals and compared them across recorded participants. The original code and text are dedicated to the public domain under CC0. [Original data and requested citations](https://doi.org/10.13026/r0ea-7161) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Code dedication](LICENSE)
