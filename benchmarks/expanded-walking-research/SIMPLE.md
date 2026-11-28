# Forecasting force underfoot

A separate CPU timing trial measured how long an invented two-plate forecast took to return. All 176 measured requests took longer than the 100 ms forecast window. [Forecast return times](forecast-timing/SIMPLE.md)

The treadmill test compares all five pass counts on new people using force readings alone. [Treadmill test](cross-lab-force/SIMPLE.md)

The [five-pass-count comparison](pass-count/SIMPLE.md) adds tests at one, seven and nine passes on the same recordings.

Three passes through the Research Edition’s middle layers gave the lowest impulse error among the tested settings. Average error fell from **3.24 to 2.89 newton-seconds** compared with extending the last measured force. Five passes raised that error to **3.12 newton-seconds** and took **52% longer** to calculate. This comparison used nine walks from three people already used for validation. [Technical report](TECHNICAL.md) · [Download the checkpoint](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)

## What the model reads

A force plate is a section of the floor that measures how hard someone pushes on it. We used two plates and six channels of muscle activity measured at the skin. The instruments sampled these readings 1,000 times per second. Every forecast started with 200 milliseconds of earlier readings. It got ten summaries, one from each 20 milliseconds. Each summary gives the size of those electrical readings and the average vertical force. [Walking data and recording methods](https://doi.org/10.1038/s41597-023-02767-y)

The first forecast gives the chance that a plate starts to carry a new load within the next 100 milliseconds. We treat the plate as unloaded after 20 milliseconds between −10 and +10 newtons. A load starts when the force rises to at least 20 newtons and stays there or higher for 20 milliseconds. Its start has to fall within the 100 milliseconds. A late start can take until 119 milliseconds to confirm.

The second forecast adds up the push over exactly the first 100 milliseconds. This is called impulse. For example, a steady upward push of 50 newtons for a tenth of a second gives 5 newton-seconds (N·s). We keep the direction of the force when calculating the total.

The simple rule keeps the most recent average force going for the next tenth of a second. It gives each plate a fixed chance of a new load based on the training walks. The Research Edition learns adjustments to those two guesses. Its middle 12 layers can repeat their calculations before it produces a result. During this fit they repeated the calculation three times. The fit let 28.67 million values change during 547 updates. It went through 9,586 plate examples from 36 walks and 12 people. Some of those updates changed the original parts that pass information between repeats. [Original model](https://huggingface.co/thinkingmachines/TML-d24-varloop-research)

## What changed after fitting

Reopening the saved checkpoint reproduced the first forecast exactly. The replay covered 864 recorded times with two plates at each time. On 1,647 plate forecasts where we could score both results, the average impulse error fell from **3.44 to 2.84 N·s** and probability error fell from **0.03352 to 0.03264**. These walks were used to fit the weights. The comparison shows what the new fit learned on those recordings.

We also fitted a blend that could keep any share of the Research Edition’s adjustment. It gave the best fit when it kept the whole adjustment for both outputs. We fixed that choice using the fitting walks. We then ran three and five passes on the same recorded inputs from the validation subset, with the saved weights fixed for both runs.

## What happened on the validation walks

We compared both settings at the same 216 recorded times, with one forecast for each plate. Each person counted equally. We first averaged the applicable errors across plates for one time, then across times in a walk and across a person's walks. The probability score squares the difference between the forecast and what happened. For example, a 20% forecast when no new load occurs has a squared error of 0.04. There were 427 usable probability outcomes. Eighteen forecast rows saw a new load, referring to eight separate onsets. The impulse test used all 432 outcomes and averaged how far each forecast missed the measured total.

| Forecast | Probability error | Impulse error |
| --- | ---: | ---: |
| Recent force and the training chance of a new load | 0.039950 | 3.237 N·s |
| NeuroTranslate 0.0 with its learned attention layers | 0.038311 | 10.867 N·s |
| Earlier six-update Research Edition | 0.462322 | 11.472 N·s |
| Expanded fit, three passes | 0.038625 | **2.895 N·s** |
| Expanded fit, five passes | 0.038593 | 3.118 N·s |

Three passes lowered impulse error against the simple rule for two of the three people. Five passes lowered probability error by about 0.000032 compared with three and raised impulse error for all three people. The 0.0 model had the smallest probability error in the table and an impulse error of 10.867 N·s. With four CPU threads, the median time after loading was **0.687 seconds** for three passes and **1.046 seconds** for five.

The three people contributed nine of 18 assigned validation walks. The other nine lacked verified names for at least one of the six muscle channels. These results use the same three people as an earlier validation study. The separate test group stayed sealed. The experiment measures forecasts from stored force and muscle readings, and live accuracy and performance on a new population remain open. [Scores and timings](RESULTS.json) · [Healthy cohort data](https://doi.org/10.6084/m9.figshare.24192480.v1)

## Run the local example

Extract the download and start with `python -B launch.py --self-test`. This checks the files and the invented example before you fetch the large base model. The archive contains about 86 MB of fitted weights. It uses the separate 19.53 GB base. For the full forecast use Linux on an Intel or AMD computer, Python 3.13 and at least 64 GiB of available memory. Follow the setup in the extracted guide, then run the two invented plate histories with three passes. [Checkpoint and release instructions](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)
