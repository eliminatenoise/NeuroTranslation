# Where will the ankle be in 200 milliseconds?

Eight skin markers trace a barefoot walker across a laboratory. Give the model forty camera frames and it predicts how far each ankle, knee and wrist marker will move over the next twenty. Add electrical recordings from the right leg, and we can ask a second question. What do the electrodes tell us that the cameras missed?

On ten walkers assessed with the fitted models held fixed, a Transformer using both signals missed the recorded point by **18.02 mm** on average. A linear forecast using just the markers missed by **17.78 mm**. Neither the added value of muscle signals nor an advantage for the Transformer cleared the two prespecified tests.

## Try it

With Python 3 and NumPy installed, open the launcher for your system or run `python predict.py`. The program returns six XYZ displacements in millimetres from an invented walking sequence. Add each vector to the corresponding marker's last position to get a forecast position in the laboratory. Run `python check_example.py` to compare all six software paths with their saved outputs. The [reproduction guide](REPRODUCE.md) covers your own inputs, the original recordings and the full analysis.

## What the cameras saw

The injury-free adult participants walked barefoot on a ten-metre level walkway. The authors set a metronome cadence for the 0.4–0.8 m/s condition and checked the speed of the first trial. The thirty fitting walkers supplied ninety walks. The ten assessment walkers supplied thirty more. Their recordings had previously been used to study other outcomes. Ten additional walkers remained in reserve. [Original recordings](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Schreiber and Moissenet, 2019](https://doi.org/10.1038/s41597-019-0124-4)

For both sides of the body, the target points sit at the outer ankle, the outer knee and the thumb side of the wrist. Two markers at the front of the pelvis help place them. We included each eligible cutoff regardless of whether a foot reached a force plate. The cameras supplied 1,220 cutoffs, each with six complete target points. Across those 7,320 displacements the median distance moved was 109.09 mm. The middle 80% ranged from 7.58 to 282.02 mm.

| Forecast using the forty-frame history | Mean error, mm | 95% walker interval, mm |
| --- | ---: | ---: |
| Markers, linear ridge regression | 17.78 | 15.61–20.50 |
| Markers and muscle, linear ridge regression | 17.90 | 15.77–20.64 |
| Markers, residual Transformer | 18.22 | 16.31–20.76 |
| Markers and muscle, residual Transformer | 18.02 | 15.95–20.72 |
| Keep the marker moving at its recent velocity | 53.00 | 47.44–59.62 |
| Keep the marker where it is | 129.30 | 119.39–139.62 |
| Training mean for the last annotated gait event and elapsed time | 126.22 | 117.07–135.44 |

The statistic averages the distance between forecast and recorded XYZ over cutoffs for each landmark and walker, then gives each landmark and each walker equal weight. Each walker contributed 113–127 cutoffs. The combined Transformer's mean error across individual walkers ranged from 14.06 to 27.94 mm. Left and right ankle errors were 22.10 and 22.44 mm. Knees averaged 14.00 and 13.80 mm, wrists 18.48 and 17.29 mm. The intervals resample whole walkers 10,000 times. [Aggregate scores and intervals](results.json)

On all thirty walks, adding the right-leg recordings to the Transformer changed mean error by −0.21 mm, with a paired 95% walker interval from −0.78 to +0.50 mm. Six of ten walkers improved. On the twenty later walks, substituting the previous recording's muscle signal increased the error. The correct signal gave 18.05 mm against 18.97 mm for the substituted signal across the same 815 cutoffs. The paired difference was −0.92 mm (−1.46 to −0.41). The prespecified muscle test required both comparisons to pass. The combined Transformer also failed to improve on either linear forecast. [Frozen tests and controls](protocol.json) · [Pre-fit source correction](source-clarification.json)

## Turn the walker around

How much can we learn from one previous walk? Both recordings come from the same session. On each later walk we matched the marker history to the most similar moments in that person's preceding recording. In fixed laboratory axes the template missed by 133.61 mm. Ten of the twenty later walks travelled the other way down the walkway from the preceding one.

After scoring the frozen models, we repeated the comparison with forward travel aligned. The recent motion of the two pelvic markers identifies the walking direction at the cutoff. Turning a return traverse through 180 degrees aligns the horizontal coordinates while preserving anatomical left and right. The same-person template then missed by **18.94 mm**, compared with **18.05 mm** for the combined Transformer on the same cutoffs. Their paired difference, −0.89 mm, had an interval from −4.25 to +1.98 mm. The event-and-time template also improved, from 126.22 to 31.85 mm. This follow-up uses a design chosen after seeing the primary results. [Direction check](direction-results.json) · [Method](direction-protocol.json)

## What the clock measures

The cameras sampled at 100 Hz. The authors filled marker gaps and filtered the signals forward and backward before export. The eight surface electrodes sampled the right leg at 1,500 Hz. The authors removed each channel's trial mean and filtered voltage forward and backward between 30 and 300 Hz. We calculate a trailing root-mean-square voltage for each model token. The stored marker and muscle values can therefore reflect samples recorded after the nominal cutoff. The twenty-frame forecast is an offline test on processed recordings. Real-time lead, neural activity, joint-centre positions and transfer to other tasks remain unmeasured. [Article and processing methods](https://doi.org/10.1038/s41597-019-0124-4) · [Source attribution and licence](NOTICE.md)
