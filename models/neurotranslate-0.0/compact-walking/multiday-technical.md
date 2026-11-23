# Multi-day heel forecast evaluation

[Simple edition](multiday-simple.md) · [Download the offline example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/neurotranslate-0.0/compact-walking/overground-preview.zip)

The frozen Compact model with a past pelvis velocity correction averaged **27.11 mm** error over seven participants. The recent heel velocity rule averaged **72.09 mm** and pelvis velocity alone averaged **165.76 mm**. The adjusted model beat both rules for every participant and in the mean of every recorded day.

## Signals and timing

Horst et al. recorded repeated barefoot overground walking at 250 Hz. Use native `LH` and `RH` for heel coordinates and `LASIS` and `RASIS` for the anterior pelvis midpoint. In two excluded trials the interpreted heel markers lay below and behind their matching ankles and behind the forefoot. Map lab Y, negative lab X and lab Z to left, backward and up in millimetres. Use exact native rows with finite coordinates and positive reconstruction residuals, reading the scaled low byte of the fourth stored word. Camera identity masks were unavailable for the engineering examples and the scored heel targets. [Dataset](https://doi.org/10.17632/8kyv4jm759.1) · [C3D floating-point format](https://www.c3d.org/HTML/Documents/3ddatafloatingpointformat.htm)

Schedule starts 80 frames apart, with initial phase equal to the first two bytes of SHA-256 of the member name, modulo 80. Require full 200 ms capture support. Read ten points at 20 ms intervals. Forecast the heel 25 native frames after the last reading, or 100 ms after that reading and 90 ms after nominal issue. Freeze forecasts before reading target rows. All past and target index sets were disjoint within trials.

## Forecast comparators and scores

Subtract each heel's first history position from its ten readings. Continue recent heel motion by multiplying the difference between the last two readings by five. For the pelvis-only forecast, fit a straight line to each horizontal component of the ten pelvis midpoints and multiply the resulting velocity by 0.1 seconds. Compact was trained on treadmill recordings. The corrected forecast removes the corresponding pelvis travel from each heel history and adds the pelvis-only displacement to the model's prediction. Average the predictions from frozen seeds `2731` and `4119` in each direction, with force inputs absent, for both Compact variants. [Pinned model code and weights](https://github.com/eliminatenoise/NeuroTranslation/tree/2e6e3e4ac3caf3bcc5adde13ca5a5f48a3a63f46/models/neurotranslate-0.0/compact-walking)

All trials from one participant were excluded from scoring. Of 829 reserved walks, 15 lacked unique heel labels. Of 2,266 scheduled starts, 31 lacked complete history and three lacked a valid earlier heel point. The remaining 2,232 forecasts had 4,464 valid heel targets. The common comparison includes 4,402 points with complete past pelvis support. Calculate Euclidean position error in millimetres and weight each participant equally.

| Method on common support | Mean error |
| --- | ---: |
| Last position | 173.97 mm |
| Recent heel velocity | 72.09 mm |
| Frozen Compact | 95.50 mm |
| Pelvis velocity alone | 165.76 mm |
| Compact with pelvis travel removed and restored | **27.11 mm** |

Adjusted Compact minus recent heel velocity was **−44.98 mm** with a paired 95% bootstrap interval of −47.14 to −43.00 mm. Against pelvis alone the difference was **−138.65 mm**, interval −142.41 to −134.63 mm. The intervals use 10,000 resamples of participants, with each participant's repeated records kept together. Adjusted daily mean errors span 26.19 to 27.85 mm. Day 1 has five participants with eligible targets. Days 2–8 have seven each. Day means are descriptive repeated measures. The archive is a separate release from the same research site as the earlier evaluation. Recruitment overlap remains unverified. This evaluation covers recorded optical displacement. Force prediction and live tracking latency were outside the study. [Daily and overall scores](multiday-results.json) · [Earlier evaluation](overground-technical.md)

## Reproduce the forecast

Use Node.js 18 or later and run a launcher from the extracted ZIP. The included `overground-example.json` uses invented positions. Its `time_ms`, `heel_mm` and `pelvis_mm` fields encode ten frames at 20 ms intervals and the two three-axis readings per frame, left first. [Offline download](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/neurotranslate-0.0/compact-walking/overground-preview.zip) · [Source and input details](overground-technical.md#run-the-frozen-transform)

Data released under CC BY 4.0 by Fabian Horst, Franziska Kramer, Bastian Schäfer, Alexander Eekhoff, Patrick Hegen, Benno M. Nigg and Wolfgang I. Schöllhorn. [Dataset and licence](https://doi.org/10.17632/8kyv4jm759.1) · [Original paper](https://doi.org/10.1016/j.gaitpost.2016.07.073)
