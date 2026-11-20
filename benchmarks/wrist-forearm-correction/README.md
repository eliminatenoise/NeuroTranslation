# Forearm signals helped predict the early turn of a wrist

A target appears. A person turns a supported right wrist to move a cursor towards it. Two sensors measure how far the wrist bends and how far it tilts sideways. From half a second of earlier movement, a forecast estimates where both angles will be a quarter-second later. Can the muscles tell us something the moving wrist hasn't already told us?

Four pairs of electrodes on the forearm recorded small voltages during the turn. Adding that electrical activity, called surface electromyography (EMG), to a correction based on movement lowered the forecast error from **3.665° to 3.549°**. All six people showed an improvement in that comparison. The original motion forecast, before either correction, already scored **3.618°**. Only three of six improved on that original forecast when EMG was added.

[Open the results](results.html) · [All aggregate scores](results.json) · [Reproduce the study](REPRODUCE.md)

## When did the extra signal help?

The largest gain came 0.75 seconds after the cue. The movement-based correction missed by 7.441°. Adding the forearm signal brought that down to 6.949°. The signal also helped at 1.00 seconds. At all four later times, from 1.25 through 2.00 seconds, adding it made the forecast worse. Averaged over the whole trial, most of the gain came from predicting wrist extension.

| What the forecast used | Two-axis error |
| --- | ---: |
| Last measured angle, repeated | 7.216° |
| Last measured velocity, extrapolated | 7.166° |
| Motion alone, using a network that recognizes short movement patterns | 3.618° |
| Same motion forecast plus a correction learned from motion alone | 3.665° |
| Same motion forecast plus a correction learned from motion and paired EMG | 3.549° |
| Motion and EMG learned together in one network | 3.575° |

A correction learned from another person's mistakes has a fairer test than one that has already seen yours. We took turns holding out each of six people. To teach the correction, we first had the motion network predict each of the other five in turn, with only four people available to fit it. Those mistakes supplied the learning examples. The final forecast for the held person used the motion network fitted to the five other people.

To see whether the source of the signal mattered, we kept the wrist's path and prediction time fixed and substituted a forearm recording from another person's trial. The EMG correction then missed by 3.828°. Keeping the original recording and reversing the order of its sixteen short time bins raised the error to 3.720°. Movement and electrode contact can both influence surface EMG. Neither control separates those contributions.

Each person counted equally in the error across 1,879 eligible trials and 11,274 forecast times. These six belonged to the study's existing training group. The three previously evaluated people and the six people reserved for confirmation stayed outside this analysis. The lead of 250 milliseconds refers to the stored recording clock. The physical delays between instruments and the accuracy of a live forecast remain unknown.

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz published the EEG-EMG-WristMotion Dataset, version 3. NeuroTranslation derived the movement and muscle features and trained these experimental forecasting models. [Dataset](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Data descriptor](https://doi.org/10.1038/s41597-026-07287-z) · [Sources and rights](NOTICE.md)
