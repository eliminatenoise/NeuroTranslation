# A 300 ms forecast of projected muscle point spread

For each tissue, the target is the root mean square distance of four tracked ultrasound points from their centre, in millimetres. The model receives ten half-open 20 ms history bins. Forecast times follow the recorded motion clock at 100 ms intervals. The nearest ultrasound target falls 291.7–308.3 ms after issue.

The fit used 29,664 windows from 24 people. The existing validation split yielded 6,275 windows from five usable people. One recording had ambiguous tissue labels. The six final test recordings stayed reserved. Forecasts were saved before scoring the outcome file. Independent replay recovered the clocks, all 94 prediction streams and the planned paired comparisons.

Each compact network has 32,114 FP32 parameters. It updates an internal state across the history and refines that state by repeating the same calculation. Specialist networks see fixed inputs. Shared training switches among full ultrasound, a 100 ms gap and complete ultrasound removal. Within each seed, the fits share initial weights and row draws. The reported network scores average predictions across both seeds before scoring. The linear controls use a fixed squared-weight penalty of 0.01.

| Inputs and method | Mean absolute error across tissues |
| --- | ---: |
| Complete, ultrasound linear correction | 0.1210 mm |
| Complete, five-bin ultrasound trend | 0.1289 mm |
| Complete, learned model with all signals, three passes | 0.1489 mm |
| Gap, linear correction with all available signals | 0.1771 mm |
| Gap, older ultrasound trend | 0.1775 mm |
| Gap, shared model, three passes | 0.1919 mm |
| Ultrasound withheld, shared model, one pass | 1.8468 mm |
| Ultrasound withheld, linear motion | 1.8632 mm |
| Ultrasound withheld, shared model, three passes | 2.1586 mm |

The mean absolute error gives each participant equal weight. At three passes with ultrasound withheld, adding EMG changed triceps error by −0.307 mm and brachialis error by +0.458 mm. Both paired participant intervals span zero.

An exploratory check defined after the main comparison used the same five people. The first eligible measurement supplied a fixed offset, measured spread minus the frozen forecast at that measurement. Each tissue had 6,255 scored issues after excluding four per person. The measurement preceded every retained issue. Adjusted forecasts were bounded below at zero. Holding that measurement gave triceps and brachialis errors of 0.582 and 0.417 mm. Adjusting the motion-and-EMG linear forecast gave 0.475 and 0.778 mm. Between-recording differences accounted for 84% and 90% of the signed error variance of the uncalibrated one-pass model without ultrasound input.

This is validation on archived measurements from one site. The studied target is projected image-plane spread. Physical timing and performance on the reserved cohort remain unverified. Dataset by Pallarès-López et al., CC BY 4.0. [Original research](https://doi.org/10.1038/s41597-026-07019-3) · [Recordings](https://doi.org/10.6084/m9.figshare.31030252.v1)
