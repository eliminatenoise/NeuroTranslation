# Outdoor insole pressure · Simple edition

An insole sits inside a shoe. In this study, each insole had eight pads that measured pressure beneath different parts of the foot. The model reads the previous fifth of a second and forecasts what each pad will read a tenth of a second later. This is a forecast of the pressure under each pad, measured in millibar, written mbar. The unit describes pressure at the pad. An estimate of the total force through the foot would require separate measurements or calibration. [Original recordings](https://doi.org/10.6084/m9.figshare.19834324.v1)

## Try the browser example

Open the interactive example. Choose a foot, a sensor and a model, then move the pressure level control. The green line shows the earlier readings. The brown dot repeats the last reading a tenth of a second later. The blue dot shows the model's forecast at that same time. The numbers just below the chart give the most recent reading and the forecast. All readings you can change here are generated. The final test table lower down reports the separate study on recorded walks.

The offline download works without an internet connection once extracted. Open `Open insole pressure.html` in your browser, or use the included launcher for Windows, macOS or Linux. [Interactive example](https://eliminatenoise.github.io/NeuroTranslation/outdoor-insole-pressure/) · [Offline ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/outdoor-insole-pressure/outdoor-insole-pressure.zip) · [Technical edition](TECHNICAL.md)

## How the recordings were used

Twenty adults each walked three outdoor courses. After the walks, the researchers lined up the different devices' recordings and placed the pressure values on an even time grid with 60 readings per second. Where that grid landed between two readings, they filled in a value along the straight line between those readings. A filled-in pressure can use the next original reading. The models and tests here use the prepared files. Live insole timing needs its own test.

We used one person's file to check the format. Eight other people provided the examples the models learned from, and three different people let us compare early versions. After we fixed the models and the test procedure, we tested them on eight more people. All the recordings from a person stayed together. That matters because seeing one of a person's walks during fitting could make another of their walks easier to predict. There were 66,909 fitting examples, 26,138 development examples and 67,355 final forecasts across 24 recordings. Those forecasts come from eight people, so each person counted equally when we summarized the results. [How the data were collected](https://doi.org/10.1038/s41597-022-01580-3)

## How the forecasts work

The simplest forecast carries the latest pressure forward. The trend forecast measures how quickly the pressure changed over the last two intervals and continues that change. The two linear models learn a fixed way to add up the earlier readings, with a small penalty that discourages relying too heavily on any one input. One reads only the foot it is forecasting. The other reads both feet.

The two recurrent models also read the samples in time order. Each keeps a short internal record made of 20 numbers and updates it as the next reading arrives. It uses that record to calculate how much pressure to add to or subtract from the latest reading. Both versions learned 2,616 adjustable values. They went through the fitting examples ten times in groups of 512, beginning from the same starting settings generated with seed 2731. Calculations used 64-bit floating-point numbers. One version reads both feet in a single pass. The other makes a separate pass for each foot, with the other foot's inputs set to zero after centering and scaling. Both versions learned their scaling from the fitting group. Each person's three courses carried equal weight in fitting. The linear models used a penalty of 0.01 on their weights. [Technical edition](TECHNICAL.md)

## What the final test found

For each reading, we measured how far the forecast was from the later recorded value. We averaged the errors for a course, then the three courses for each person, then the eight people. Lower is better.

| Forecast | Average error (mbar) |
|---|---:|
| Latest reading carried forward | 60.37 |
| Recent trend extended | 63.01 |
| Same-foot linear | 60.62 |
| Both-feet linear | 62.63 |
| Both-feet recurrent | 50.27 |
| Same-foot recurrent | **49.58** |

The same-foot recurrent model missed by 11.04 mbar less than the same-foot linear model and 10.80 mbar less than carrying the last reading forward. It beat both methods for each of the eight people. To see how much this depended on who happened to take part, we made 10,000 new groups by drawing eight people from the same eight, allowing the same person to be drawn again. The middle 95% of those groups gave an advantage from 9.85 to 12.29 mbar against the linear model and from 7.95 to 14.00 mbar against carrying the last reading forward.

Reading both feet gave 0.69 mbar more error than reading the foot being predicted. That difference was small. The middle range went from the model with both feet doing 0.43 mbar better to 1.72 mbar worse. We tested prepared recordings from one study. Timing with a live insole, estimation of the force through a foot, and performance on another dataset still need their own tests. [Full results](results.json)

## Use your own numbers

With Node.js installed, open a terminal in the extracted folder. Run `node run.mjs example.json` to check the included example. You can copy that JSON file and replace its numbers. Give 13 rows at 60 readings per second, from oldest to newest. For each foot the readings go in this order. Big toe, other toes, the pads beneath the first, third and fifth long bones of the forefoot, arch, left heel pad, right heel pad. Use `"left"` or `"right"` for an eight-value row. Use `"both"` for 16 readings with the left foot first. The output lists the estimated pressures in that same order.

We checked the standalone code against the original PyTorch forecasts on 72 real test windows covering all 24 test recordings. On those windows, the largest difference was below one trillionth of a millibar. The download supplies generated examples, the tested weights and source code. The researchers released the original data under CC0. The released code and models also use CC0. [Source and license](https://doi.org/10.6084/m9.figshare.19834324.v1) · [License included with the model](LICENSE)
