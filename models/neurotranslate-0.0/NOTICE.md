# Source credits

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz published the **EEG-EMG-WristMotion Dataset**, version 3. Their encoders and electrical recordings come from cued, constrained right-wrist pointing. We used the six named participants, formed sixteen bins of earlier wrist angles and voltages, calculated four bipolar forearm amplitudes, and fitted and compared angular forecasts. The source, derived training scales, fitted weights and numerical results carry the original attribution and CC BY 4.0 terms wherever applicable. The publisher hosts the original recordings. [Version 3 deposit](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Study descriptor](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

Xin Wang, Taein Kwon, Mahdi Rad, Bowen Pan, Ishani Chakraborty, Sean Andrist, Dan Bohus, Ashley Feniello, Bugra Tekin, Felipe Vieira Frujeri, Neel Joshi and Marc Pollefeys published *HoloAssist*, ICCV 2023. The original spatial study converted wrist tracking to centimetres and used successive positions to calculate distances, elapsed times and changes in direction. HoloAssist's data carry the Community Data License Agreement – Permissive 2.0. [Dataset](https://holoassist.github.io/) · [Included agreement](CDLA-Permissive-2.0.txt)

Justin Shin and Shantanu Jadhav published *Single Day W-Track Learning*, DANDI version 0.240511.0307 (2024), under CC BY 4.0. The spatial study used tracked positions from JS14, session 01, running epoch 5, to derive movement histories and future distances. [Versioned dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The spatial weights are redistributed under CC BY 4.0. Their numerical values are preserved in the new checkpoint. NeuroTranslation contributes the three angular input projections and outputs, scales, aggregate comparisons and packaging. Retain the above credits and indicate any further changes when reusing those weights or results. The project's original code, documentation and invented inputs are dedicated to the public domain under CC0. NumPy and PyTorch retain their own terms. [Code dedication](LICENSE) · [Original spatial study](https://github.com/eliminatenoise/NeuroTranslation/tree/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/models/shared-motion)

The forearm correction adds fifteen four-person base fits for the development comparison and two final linear corrections to the shared wrist-motion forecast. The downloadable checkpoint contains the final pooled coefficients and scales. Its forearm data and derived weights/results retain the wrist source attribution and CC BY 4.0 terms above. The forearm example is generated from analytic curves and uses invented angles and amplitudes. [Changes and method](forearm/README.md) · [Example generator](forearm/make_example.py)

The population adapter groups sorted dorsal CA1 and prefrontal units and pairs four quarter-second firing bins with five camera measurements in six additional recordings from Shin and Jadhav’s *Single Day W-Track Learning* (2024), DANDI version 0.240511.0307. ER1, JS15 and JS17 supplied training. JS21, JS34 and KL8 supplied testing. This reanalysis fits two output heads, checks firing substitutions and redistributes derived coefficients, example measurements and evaluation tables with attribution under CC BY 4.0. Credit the original authors, identify any further changes and preserve the licence when reusing these materials. The authors do not endorse this analysis. The project’s new source code and documentation carry the same CC0 dedication as its earlier code. [Versioned dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Reanalysis method](population/README.md)

## Treadmill knee angles

The four-second knee corrections and aggregate results derive from the PhysioNet version 1.0.0 recordings of Katmah and colleagues, under CC BY 4.0. We selected one speed and trained new readouts to estimate reconstructed angles. The previous movement weights retain the terms described above. [Authors, processing and licence](knee/README.md) · [Original dataset](https://doi.org/10.13026/r0ea-7161)

## Knee turning moments during walking

Emma Reznick, Kyle R. Embry, Ross Neuman, Edgar Bolívar, Nicholas P. Fey and Robert D. Gregg released the optical walking recordings and inverse-dynamics estimates under CC0. The new knee-moment readouts use these recordings. The original shared checkpoint retains its earlier source conditions. [Original dataset](https://doi.org/10.6084/m9.figshare.14558181.v1) · [Methods and credit](load/SOURCE.md)

## Right foot on a force plate

Céline Schreiber and Florent Moissenet released the motion, muscle and platform recordings from the Rehazenter study under CC BY 4.0. This edition selects barefoot walking trials, fits new model readouts and reports errors on other walkers. The right-platform readouts and results use those data. Keep the authors’ credit and licence with the derived material and identify further changes. [Original data release](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Authors’ licence and citation](right-plate/DATA-LICENCE.txt) · [Processing and results](right-plate/README.md)

The single-marker readouts and error summaries use optical positions from the same Schreiber and Moissenet version 8 walking dataset. These new weights and aggregate results retain the source attribution and CC BY 4.0 terms. [What was fitted](point-motion/README.md) · [Original licence and citation](point-motion/DATA-LICENCE.txt)

## Instructed right-arm movement

Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz (2017) released *Upper limb movements can be decoded from the time-domain of low-frequency EEG*, Zenodo record 834976, under CC BY 4.0. This study uses the visual task classes and mechanical instrument readings from the first participant’s first three execution runs to derive time bins, fit readouts and compare errors. Retain the data attribution and identify further changes. [Original data](https://doi.org/10.5281/zenodo.834976) · [Acquisition study](https://doi.org/10.1371/journal.pone.0182578) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Across-person right-arm forecasts

The group-arm readouts, cue medians and scores derive from Ofner, Schwarz, Pereira and Müller-Putz’s 2017 recordings (Zenodo 834976, CC BY 4.0). We fitted on execution runs 1–3 from S1–S7 and tested on the same numbered runs from S8–S12. The last three people remained reserved. This edition adds a pooled fit, a test of sensor starting levels, and a method for personal corrections made with earlier recordings. [Original data](https://doi.org/10.5281/zenodo.834976) · [Methods and reuse](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/neurotranslate-0.0/arm-transfer)

## Early electrical recordings and arm readings

Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz (2017) released *Upper limb movements can be decoded from the time-domain of low-frequency EEG* under CC BY 4.0. This analysis uses task categories, four bins of scalp and eye readings, and mechanical arm and hand readings. We fitted robust corrections in seven people and assessed them on five previously unopened fourth execution runs. Their fitted coefficients and numerical summaries retain the source attribution requirement. [Original data](https://doi.org/10.5281/zenodo.834976) · [Acquisition paper](https://doi.org/10.1371/journal.pone.0182578) · [Methods and licence](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/neurotranslate-0.0/scalp-residual)

The cervical voltage preview uses the CC0 dataset published by Nierula and colleagues, [OpenNeuro ds004388 v1.0.0](https://doi.org/10.18112/openneuro.ds004388.v1.0.0). The coefficients and reader use the project CC0 dedication. [Primary article](https://doi.org/10.1371/journal.pbio.3002828).
