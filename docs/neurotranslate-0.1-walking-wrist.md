# NeuroTranslate 0.1 forecasts from walking and wrist recordings

For wrist pointing, recent wrist angles and forearm signals gave the lowest average error. Adding scalp signals increased that error for all six people. For walking, the largest fit that used leg muscle signals gave the lowest error on force impulse. Hiding those signals from the same fit gave the lowest error on marker movement.

These scores come from a miniature NeuroTranslate 0.1 research model tested offline on archived recordings. The public adapter for the full-size Inkling base model is a separate package.

## Wrist angles a quarter of a second ahead

The model used recent wrist angles and forearm muscle activity recorded at the skin (EMG). The added input was electrical activity picked up by electrodes on the scalp (EEG). The device worn on the wrist recorded how far the wrist bent and tilted at the target time, **250 ms** after the forecast on the stored clock. The forecast was an estimate of those two measured angles.

Lower scores are better. For each person, square the errors on both axes and average them within each recording run. Average those run scores equally, then take the square root to get that person's root mean squared error in degrees. The table averages the six scores, one per person. Three training splits used four people to fit the model and scale its inputs and the other two to check it. The check used one forecast per selected trial, **1,691 trials** in total.

| Forecast | Error (degrees) |
| --- | ---: |
| Wrist angles and forearm EMG | **5.464** |
| Add scalp EEG from the same trial | 5.786 |
| Replace that EEG with an earlier matched trial | 5.789 |
| Hide EEG from the same scalp-trained model | 6.027 |
| Continue at the last angular speed | 6.980 |
| Repeat the latest angle | 7.246 |

Adding scalp EEG raised the error by **0.323°** on average compared with the separate fit that used angles and forearm signals. The replacement scalp readings matched the person, recording run, cue and time after the cue. The other inputs stayed fixed. The same-trial EEG score was just **0.003°** lower on average, with lower error for three people and higher error for three. Both differences use unrounded scores. The six people had already been used in development. Signals picked up on the scalp can include muscle activity, and a repeated cue can produce similar recordings in both trials. [Wrist dataset, version 3](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Recording methods](https://doi.org/10.1038/s41597-026-07287-z).

## Marker movement and floor force over 100 ms

For walking, the model read earlier camera positions and force-plate readings, with leg EMG as an optional input. Marker error is the three-dimensional distance between predicted and recorded displacement, in millimetres. To measure force impulse, multiply each signed vertical force sample by the time it represents, then add the contributions over the next **100 ms**. Impulse error is the absolute difference between prediction and measurement, in newton-seconds (N·s).

For each forecast, average marker errors over six tracked markers and impulse errors over two force plates. Average those errors within each walk, then average the walk scores for each person. Each person counts equally in the final score. The simple reference continued the last marker velocity and held the recent plate force constant. It scored **15.087 mm and 3.665 N·s**.

Each cell lists marker error in mm followed by impulse error in N·s. Camera and plates used a separate fit. The EMG-hidden forecast used the same weights as the all-input fit and hid muscle readings only when making the forecast.

| Training examples | All inputs | Camera and plates | EMG hidden |
| ---: | ---: | ---: | ---: |
| 415 | 15.160 / 4.108 | 15.044 / 3.965 | 15.123 / 4.047 |
| 828 | 14.860 / 3.609 | 14.953 / 3.478 | 14.800 / 3.545 |
| 1,652 | 14.158 / **2.254** | 14.174 / 2.512 | **14.039** / 2.536 |

Across all three sizes, the fit used windows from the same **20 people**, and the check reused **77 forecast points from 10 walks by five other people**. Some training windows overlapped. The number of training updates and the scaling of inputs changed with the number of examples. Any one of those changes could have contributed to the difference between sizes. [Walking dataset, version 8](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Recording methods](https://doi.org/10.1038/s41597-019-0124-4).

## Walking after wrist training

Each wrist fit started from the 828-example walking model with all inputs. The updates used wrist examples and continued to include examples from the walking fit. Both updated versions had lower average walking errors on the same archive check.

| What the training added | Marker error (mm) | Impulse error (N·s) |
| --- | ---: | ---: |
| Starting walking model | 14.860 | 3.609 |
| Wrist angles and forearm EMG | 14.763 | 3.287 |
| Wrist angles, forearm EMG and scalp EEG | 14.744 | 3.481 |

The walking scores give equal weight to each of the three wrist splits. Each split used the same five walking participants and the same 77 measured outcomes, so it was a repeated check. The clock in the archive gives a forecast horizon. It leaves real sensor delays unmeasured, and the walking data use filtering that can draw on later samples. Separate evaluation and reserve recordings stayed unopened.
