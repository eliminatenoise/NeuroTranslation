# HYGRIP’s first development result

The hand has already started squeezing. Recent transducer readings and the cue schedule forecast its signed voltage with **0.360083 mV RMSE** on the first HYGRIP development check. Adding aligned scalp EEG raised that to **0.461331 mV**. All three development participants had higher error after EEG was added. The experiment compares forecasts of one measured signal in one paced right-hand grip task.

[Open the voltage forecast](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) · [Download the offline browser and launchers](HYGRIP-voltage-forecast-20261119-r2.zip) · [Read the protocol before DEV](https://github.com/eliminatenoise/NeuroTranslation/blob/dd3526d4e5d67986febe01983dbdf875504d6643/benchmarks/hygrip-force/DESIGN.json) · [Unrounded aggregate results](AGGREGATES.json)

## The check

Seven of eight assigned TRAIN volunteers passed the clock screen. One entire run remained assigned to TRAIN and was withheld because its adjacent force-versus-EEG Go intervals differed by 249.5 ms, above the prespecified 40 ms limit. The seven eligible volunteers supplied **79 right-hand trials and 16,195 scored issues**. Their scores come from held-person folds that also chose the penalties. The models were fitted on all seven eligible TRAIN people and frozen before DEV scoring.

All three original DEV volunteers passed the same eligibility screen. All **39 right-hand trials and 7,995 scheduled issues** were scored, with the same rows used by every branch. Scoring used their fixed coefficients and settings. The three people assigned to FINAL remain reserved. The protocol was posted before any DEV observations. The split and original design had been fixed locally before waveform access, followed by a TRAIN-only screen and its pre-fit amendment. [Original prospective record](../README.md) · [GitHub publication run](https://github.com/eliminatenoise/NeuroTranslation/actions/runs/44432686103)

| Forecast | TRAIN RMSE (mV) | DEV RMSE (mV) | DEV RMSE (V) |
| --- | ---: | ---: | ---: |
| Scheduled cue timing | 0.854152 | 0.889869 | 0.000889869 |
| Keep the current voltage | 0.531851 | 0.516850 | 0.000516850 |
| Extend the backward 80 ms slope | 0.558423 | 0.496622 | 0.000496622 |
| Force history and timing | 0.393763 | 0.360083 | 0.000360083 |
| Force history, timing and aligned scalp EEG | 0.417955 | 0.461331 | 0.000461331 |
| Force history, timing and rotated EEG | 0.402970 | 0.422755 | 0.000422755 |
| Force history, timing and earlier EEG | 0.415367 | 0.384986 | 0.000384986 |

Every person counts equally in the group estimate. Within a person, trials count equally, and each issue counts equally within its trial. For each person we take the square root of the weighted mean squared error, then average those roots. Millivolts are volts multiplied by 1,000. The measured target and the fitted models use volts.

## The EEG controls

The rotated control takes EEG from the next right-hand trial in the same person and protocol at the same time relative to Go. The earlier control uses the same trial's EEG ending 400 ms sooner, so its history does not overlap the aligned window. Both keep the force features and predicted target from the original trial. The planned test required aligned EEG to reduce mean error against force history and both controls.

| DEV comparison, aligned minus comparator | Mean RMSE change (mV) | Descriptive paired 95% t interval (mV) | Lower / higher / ties | Exact two-sided sign p |
| --- | ---: | ---: | ---: | ---: |
| Force history | +0.101248 | [−0.276644, +0.479140] | 0 / 3 / 0 | 0.25 |
| Rotated EEG | +0.038576 | [−0.039377, +0.116528] | 0 / 3 / 0 | 0.25 |
| Earlier EEG | +0.076345 | [−0.295544, +0.448234] | 2 / 1 / 0 | 1.00 |

The directional test failed in TRAIN and DEV. Aligned EEG raised mean error against all three comparisons in each. For the earlier control on DEV, two people had lower error with aligned EEG and one had higher error. The mean still favored the earlier control. All three DEV intervals span zero. Three people leave the size and direction of effects in other populations uncertain. The result does not identify the origin of the scalp signal or establish what EEG would add in a different task.

## What the forecast uses

HYGRIP measured a transducer during visually paced power grip. The nominal cue schedule follows Go and supplies a timing input. The physical reference shown on the screen and its delivery time were unmeasured. The target is the released signed transducer voltage exactly six samples ahead on the 50 Hz force grid. EEG was released at 1 kHz. Its window ends at least 20 ms before the mapped issue time on the released clocks. That designed margin leaves physical synchronization, filter phase and live acquisition-to-output latency unmeasured. The release has no usable calibration for a result in newtons. [HYGRIP descriptor](https://doi.org/10.3389/fnins.2020.00919) · [Figshare v1 data and license](https://doi.org/10.6084/m9.figshare.12383639.v1)

The browser starts with an invented example and runs three fixed TRAIN models for timing, force history and aligned EEG. Its synthetic numbers are forecasts of invented inputs. The tables above come from the measured HYGRIP study. The offline ZIP contains Windows, macOS and Linux launchers, input instructions and the same readable HTML and JavaScript used by the hosted page. Open a compatible JSON window locally or open the example. [SHA-256 checksums](SHA256SUMS)
