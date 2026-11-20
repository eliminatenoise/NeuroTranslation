[The studies](../README.md) › Study 18 · Pinch: muscle signal

# Forearm EMG made no measurable difference to the pinch-force forecast

A gauge between thumb and forefinger already says how hard someone is pinching. For four test people holding a pinch at 30% of their hardest squeeze, a straight-line fit on the recent force and the stage of the on-screen cue forecast the gauge 120 ms ahead with an average miss of **0.4634%**. With four amplitude features from the same trial's forearm EMG added, it missed by **0.4632%**: a fall of 0.00024%, about 0.052% of the error itself, better for three of the four people, with a range that crosses zero. Force history and the cue did the work: repeating the current reading missed by 0.5464%.

Every error here is in % of the person's hardest squeeze that day (their maximum voluntary contraction, MVC). The main measure is the plain average miss (mean absolute error); the measure that punishes large misses (root mean squared error) comes second. EMG is electrical activity of muscle, picked up on the skin: a recording of muscle, not of nerve. A *straight-line fit* is a weighted sum of its inputs, here a ridge regression.

Against EMG taken from the person's other repeat, the same-trial EMG's average miss was 0.0007766% lower, and that range crosses zero too. The rule set before scoring counted a lower average in both comparisons as an observed advantage on this group, to be reported with its size and uncertainty. Both averages were lower, by margins too small to tell from zero. [Results file](RESULTS.json)

CEMHSEY GRASP recorded a right-hand pinch, thumb pad to index pad, on a P200 dynamometer at a prescribed 30% of the hardest squeeze. The target is the released force reading, divided by the person's hardest squeeze for that session and grasp. The cue on the screen supplies context; the dynamometer supplies the outcome. [Study methods](https://doi.org/10.1038/s41597-025-05733-y) · [The plan, fixed before scoring](PROTOCOL.md)

## Four new people on two new recording days

The fit used three people on recording-day indices 1 and 2, with two repeats per person per day: 12 trials. The test used four people the fit had never seen, on the separate day indices 3 and 4. Both repeats gave 16 trials, with 592 forecast moments per trial and 9,472 forecasts per method. People, days, repeats and moments count equally in this balanced group. The 9,472 forecasts share trial histories, so the four people are the units that are resampled. Person and day changed together, so the two effects cannot be told apart. The plan says there is no further group set aside.

## What the models could see

At each moment the models forecast the dynamometer reading 24 stored force samples later, a nominal 120 ms on the 200 Hz force grid. "Repeat the current reading" returns the current reading. The force models use the current reading and four differences of recent force. The cue model sees the current stage of the fixed schedule and how much of that stage has passed. The EMG versions add the median and the 90th percentile of each channel's amplitude (root mean square) in each of two earlier 100 ms windows, after the log transform fixed in the plan. The EMG windows end, nominally, 100 ms before the moment of the forecast. The other-repeat control takes those four EMG features from the same person, day, grasp and load at the same moment of the other repeat. That control was fitted separately; the same-trial fit was also scored with the other repeat's EMG swapped in. [The plan](PROTOCOL.md) · [A longer force record in one file, and why it changed nothing](SOURCE-COMPATIBILITY.md)

| Model, on the four test people | Average miss | Large misses |
| --- | ---: | ---: |
| Repeat the current reading | 0.5464% | 0.7365% |
| Cue stage only | 1.5789% | 2.3175% |
| Force history only | 0.5287% | 0.7220% |
| Force history and cue stage | 0.4634% | 0.6290% |
| Force history, cue stage and same-trial EMG | 0.4632% | 0.6281% |
| Force history, cue stage and other-repeat EMG | 0.4640% | 0.6294% |
| The same-trial fit, given the other repeat's EMG at scoring | 0.4641% | 0.6299% |

Adding force history and the cue stage cut the average miss by 15.18% of what repeating the current reading missed. The same-trial EMG's step beyond that was far smaller. The same-trial fit also had the fewest large misses of the seven.

### Same-trial EMG against the alternatives

Each difference below is the comparison's average miss minus that of the same-trial EMG fit, so a positive value favours same-trial EMG. The ranges are the 2.5th and 97.5th percentiles of all 256 ways of resampling the four people with replacement. They describe how much the result depends on which people were sampled, for these two day indices; four people say little about a new group.

| Comparison | Difference | Range when people are resampled | People favouring same-trial EMG | Day 3 | Day 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Force history and cue stage, minus same-trial EMG | +0.0002% | −0.0005% to +0.0007% | 3/4 | +0.0002% | +0.0003% |
| Other-repeat EMG, minus same-trial EMG | +0.0008% | −0.0004% to +0.0020% | 3/4 | +0.0012% | +0.0004% |

Both day indices favoured same-trial EMG on average in each comparison, and three of the four people favoured it each time, by small pooled differences.

### The resting stages told a different story

The stage is the stage of the cue at the moment of the forecast. The same-trial EMG fit had the smallest average miss during the rise, the hold and the release; the fit on force history and cue stage had the smallest in both resting stages. The largest gain from EMG over force history and cue stage was during the release, 0.0009103%; the largest loss was during the first rest, 0.0007060%. The results file has the full table by stage for all seven models, with their large misses.

| Stage of the cue | Forecasts per trial | Repeat the current reading | Force history and cue stage | Same-trial EMG | Other-repeat EMG |
| --- | ---: | ---: | ---: | ---: | ---: |
| First rest | 94 | 0.3171% | 0.2637% | 0.2644% | 0.2647% |
| Rise | 100 | 0.7774% | 0.5953% | 0.5948% | 0.5955% |
| Hold | 200 | 0.5315% | 0.5136% | 0.5130% | 0.5146% |
| Release | 100 | 0.7835% | 0.6056% | 0.6047% | 0.6052% |
| Final rest | 98 | 0.3189% | 0.2728% | 0.2735% | 0.2735% |

## What it does not show

The output is one normalised pinch force, in one condition, compared after the fact on the stored sample counts. The public data give the nominal sampling rates and the pairing within a trial; the common physical starting point of the two devices, their drift and their delivery delay were never measured, so the gap before the EMG window is a convention on the release's sample counts. The dynamometer reads the force between the two fingers as one number. Separate finger forces, other tasks, live timing and clinical use each need evidence of their own. This dataset was recorded separately from Hyser and tests a different task from [the finger studies](../hyser-index/README.md). [Study methods](https://doi.org/10.1038/s41597-025-05733-y) · [Hyser record](https://physionet.org/content/hd-semg/2.0.0/)

## Try the reader

The public example uses invented readings and invented weights. Load your own fit and a trial converted from its original MATLAB file to explore that trial; the converter and the commands that fit on your own recordings run on your computer. Reveal the later reading at one cutoff, or score all 592 cutoffs for the trial's errors. [Offline reader](../../docs/cemhsey-pinch/README.md) · [Commands to run on your computer](LOCAL-CONVERTER.md) · [Invented fit](BUNDLED-FIT.json)

[Try the pinch reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) · [Download the offline reader and Python converter](downloads/CEMHSEY-Pinch-Reader.zip) · [Model code](pinch.py) · [Invented demonstration weights](BUNDLED-FIT.json) · [Fit on your own recordings](fit_local.py)

## Whose recordings

The CEMHSEY deposits are by Shutian Yang, Dongxuan Li, Chen Chen and Xiangyang Zhu. This study uses the version 2 GRASP recordings, takes one pinch condition, works out four EMG amplitude summaries for each forecast moment, fits the comparisons fixed in the plan and reports summary errors. The datasets are licensed CC BY 4.0. [CEMHSEY Part I v2](https://doi.org/10.5281/zenodo.15077957) · [CEMHSEY Part II v2](https://doi.org/10.5281/zenodo.15070187) · [Data licence](https://creativecommons.org/licenses/by/4.0/)

The recording is described by Shutian Yang, Chen Chen, Dongxuan Li and Xiangyang Zhu in Scientific Data 12, article 1420 (2025). [Acquisition paper](https://doi.org/10.1038/s41597-025-05733-y)
