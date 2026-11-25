# Forecasting what ultrasound will show during a reach

This study tested how much recent ultrasound helps predict a later image. The forecasts looked three tenths of a second ahead. With recent images available, a simple calculation was more accurate than the trained NeuroTranslate 0.1 models in this test. When all ultrasound history was withheld, errors were much larger.

## What the study measured

The recordings follow people reaching with one arm. Motion capture measures where markers on the arm are. Electrical muscle recordings, called EMG, measure voltages at the skin. Ultrasound shows moving tissue beneath the skin. The researchers tracked points on two muscles, the triceps and the brachialis. For each muscle, we measured how far four points spread around their centre in the image.

The model learned from recordings of 24 people. The comparison used 6,275 forecasts across five other people from the same recording site. Each person's average counted equally. One more recording had labels that did not let us assign the points to the two muscles reliably. Six final test recordings stayed reserved.

## What changed when ultrasound was removed

Every forecast could use up to a fifth of a second of past readings. The gap condition removed the last tenth of a second of ultrasound and left the earlier tenth available. The final condition removed all ultrasound from the forecast. The table averages the errors for both muscles in millimetres. Lower numbers mean the forecast was closer to the points measured in the later image.

| Ultrasound available to the forecast | Forecast | Average error |
| --- | --- | ---: |
| Complete history | Continue the ultrasound trend and apply a linear correction | 0.121 mm |
| Latest 100 ms hidden | Linear forecast using older ultrasound, motion and EMG | 0.177 mm |
| All ultrasound hidden | Shared model with one extra calculation after reading the history | 1.847 mm |
| All ultrasound hidden | Linear forecast using motion | 1.863 mm |

Continuing the older ultrasound trend after a gap also gave about 0.18 mm of error. The trained model that received all three signals scored 0.149 mm with complete ultrasound and three extra calculations. The shared model doing three extra calculations scored 0.192 mm with the gap and 2.159 mm with all ultrasound hidden. The small difference between the best two methods with all ultrasound hidden came from the same five validation recordings.

To test the contribution of EMG without ultrasound, we trained matching models on motion alone and on motion plus EMG. At three extra calculations, the motion and EMG model gave a lower average triceps error and a higher average brachialis error. For both muscles, the estimated range of the difference included zero.

## What one earlier measurement changed

For the one-pass model with ultrasound hidden, most of the variation in how far it overestimated or underestimated the measurements showed up between recordings. The person, the placement of the ultrasound probe and other parts of the recording setup could all contribute.

After the main comparison, we tested one early ultrasound measurement per muscle. We used the same five people again and left out the first four forecasts from each person. For all 6,255 later forecasts per muscle, that early measurement was already in the past. Repeating it gave average errors of 0.582 mm for triceps and 0.417 mm for brachialis. Using it to adjust the linear motion and EMG forecast lowered triceps error to 0.475 mm and raised brachialis error to 0.778 mm.

The comparison covers the spread of points on two-dimensional images from the stored recordings. It gives a starting point for testing how to adapt forecasts to a new recording, with a separate check still needed on the six reserved people. The study used the reaching dataset published by Pallarès-López and colleagues. Its recordings are available under CC BY 4.0. [Original research](https://doi.org/10.1038/s41597-026-07019-3) · [Recordings](https://doi.org/10.6084/m9.figshare.31030252.v1)
