# Outdoor insole pressure · Technical edition

The model forecasts each insole sensor's pressure 100 milliseconds after the latest reading. It takes 13 consecutive readings at 60 Hz, spanning 200 milliseconds. The eight sensors per foot are in the order big toe, other toes, first, third and fifth metatarsal, arch, left heel pad, right heel pad. Each input and output value is in millibar (mbar). [Source data](https://doi.org/10.6084/m9.figshare.19834324.v1)

## Data and fitting

The NEWBEE study recorded three outdoor courses with 20 adults. The authors aligned sensor streams after recording and linearly interpolated insole readings to 60 Hz. We used one person to check the files, eight to fit models, three to compare development versions, and eight for the frozen test. Every course from a person stayed in the same group. The training and development groups contributed 66,909 and 26,138 forecast windows respectively. The final group contributed 67,355 across 24 recordings. We issued forecasts every 12 rows and checked timestamp spacing. Each scored endpoint was 100 milliseconds after the issue time on the interpolated clock. Interpolating an input can use the next original sample, so the test measures the prepared export and leaves live input availability unverified. [Recording methods](https://doi.org/10.1038/s41597-022-01580-3)

The two recurrent models use the same 20-unit gated recurrent layer and linear output, with 2,616 adjustable values each. The layer updates an internal state as it reads each sample. It predicts the change from the latest reading. The same-foot model makes a separate pass for each foot, replacing the other foot with zeros after standardization. Each pass supplies only the forecast for its own foot. The both-feet model forecasts all 16 readings in one pass. Fit-only standardization, training order, seed 2731, ten epochs, 512-example batches, and double precision were shared. The linear models used a fixed penalty of 0.01 on standardized input weights and each person's courses had equal training weight. The trend baseline extended the change between the latest reading and the reading two ticks earlier.

## Final test

The error is the absolute difference between forecast and recorded pressure. We averaged channels and windows within each course, then courses within each person, then people equally.

| Forecast | Mean absolute error (mbar) |
|---|---:|
| Latest reading carried forward | 60.37 |
| Recent trend extended | 63.01 |
| Same-foot linear | 60.62 |
| Both-feet linear | 62.63 |
| Both-feet recurrent | 50.27 |
| Same-foot recurrent | **49.58** |

Drawing eight people with replacement in 10,000 paired draws gave the following central 95% intervals. The same-foot recurrent model lowered error by 11.04 mbar versus the same-foot linear fit (9.85 to 12.29 lower) and 10.80 mbar versus carrying pressure forward (7.95 to 14.00 lower). It beat both baselines for all eight people. The both-feet recurrent model had 0.69 mbar higher average error, with an interval from 0.43 lower to 1.72 higher. The observed benefit of the recurrent models applies to this offline collection. Live sensor timing, force estimates, and transfer to another collection remain untested. [Full results](results.json)

## Run the model

Open the browser example or extract the offline ZIP and open `Open insole pressure.html`. The example uses generated pressures. To run your own history with Node.js, use `node run.mjs input.json`. The JSON file uses `{"side":"left","history":[...]}` with 13 rows of eight values, oldest first. Use `"right"` for the other foot. The included `example.json` is a valid input. For both feet, use `"both"` with 16 values per row, placing left before right. [Interactive example](https://eliminatenoise.github.io/NeuroTranslation/outdoor-insole-pressure/) · [Offline ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/outdoor-insole-pressure/outdoor-insole-pressure.zip) · [Simple edition](SIMPLE.md)

The standalone implementation reproduced archived PyTorch forecasts on 72 windows from all 24 final recordings to within 0.000000000001 mbar. The public inputs are generated. Archive data are CC0 through Figshare and the released code and weights are CC0. See [the license](LICENSE) and [the source record](https://doi.org/10.6084/m9.figshare.19834324.v1).
