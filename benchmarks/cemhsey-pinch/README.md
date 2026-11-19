# What did forearm EMG add to the pinch-force forecast?

**Force history and task phase carried most of the predictive gain.** Adding four amplitude features from the same trial's forearm surface EMG reduced mean absolute error from 0.004634370 to 0.004631948, about 0.052% relative to force history and phase alone. The same-trial features also beat the matched other-trial comparison by 0.000007766. Both margins were small, and both participant-resampling ranges crossed zero. The incremental benefit remains unresolved on this panel. [Aggregate results](RESULTS.json)

A dynamometer already tells us how hard someone is pinching. We asked whether surface EMG helps forecast its later reading once the model knows the current force, its recent history and where the person is in the prescribed task. CEMHSEY GRASP recorded a right-hand thumb–index pad-to-pad pinch with a P200 dynamometer at a prescribed 30% of maximum voluntary contraction (MVC). The measured target is the released scalar force normalized to the participant's MVC for that recording session and grasp. Its units are dimensionless. The displayed cue supplies context. The dynamometer supplies the outcome. [Study methods](https://doi.org/10.1038/s41597-025-05733-y) · [Prespecified protocol](PROTOCOL.md)

## Four new people, two new recording-day indices

The fit used three people on recording-day indices 1 and 2, with two repeats per person per day and 12 trials. Evaluation used four people unseen during fitting on the separate recording-day indices 3 and 4. Both repeats gave 16 trials, with 592 issue times per trial and 9,472 forecasts per method. People, days, repeats and issue times contribute equal weight on this balanced panel. The 9,472 windows share trial histories. The four participants are the resampling units. Person and day changed together in this comparison. [Prespecified protocol](PROTOCOL.md)

## What the models could see

At each issue the models forecast the dynamometer reading 24 stored force intervals later, a nominal 120 ms on the 200 Hz force grid. Persistence returns the current reading. The force models use the current reading and four differences from recent force. The phase model sees the current phase of the fixed schedule and how much of that phase has elapsed. The EMG arms add the median and 90th percentile of per-channel RMS amplitudes from each of two earlier 100 ms windows, after the prespecified log transformation. The nominal EMG windows end 100 ms before the issue index. The other-repeat control transfers those four EMG features from the same person, day, grasp and load at the same issue index. We fitted that control separately, then also tested what happened when the same-trial fit received other-trial EMG during scoring. [Prespecified protocol](PROTOCOL.md) · [Source compatibility](SOURCE-COMPATIBILITY.md)

## Errors on the fixed evaluation panel

Lower is better. Mean absolute error (MAE) was the primary metric and root mean squared error (RMSE) was secondary. All values use the release's normalized-force scale.

| Model | MAE | RMSE |
| --- | ---: | ---: |
| Persistence | 0.005464 | 0.007365 |
| Task phase only | 0.015789 | 0.023175 |
| Force history only | 0.005287 | 0.007220 |
| Force history + phase | 0.004634 | 0.006290 |
| Force history + phase + same-trial EMG | 0.004632 | 0.006281 |
| Force history + phase + other-trial EMG | 0.004640 | 0.006294 |
| Same-trial fit, other-trial EMG at scoring | 0.004641 | 0.006299 |

Adding force history and task phase lowered MAE by 15.18% relative to persistence. The incremental same-trial EMG improvement was much smaller. The same-trial fit also had the lowest overall RMSE of the seven comparisons on this panel.

### Did same-trial EMG help more than the alternatives?

Signed MAE differences below are baseline minus same-trial EMG. A positive value favors the same-trial fit. The ranges are the 2.5th and 97.5th percentiles of all 256 draws that resample the four participants with replacement. They describe sensitivity to the people sampled, conditional on the two evaluated day indices. Four people give limited evidence about the effect in a new cohort.

| Comparison | Overall MAE difference | Person-resampling range | People favoring paired EMG | Day 3 | Day 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Force history + phase minus same-trial EMG | +0.000002 | -0.000005 to +0.000007 | 3/4 | +0.000002 | +0.000003 |
| Other-trial EMG minus same-trial EMG | +0.000008 | -0.000004 to +0.000020 | 3/4 | +0.000012 | +0.000004 |

Both indexed days had a positive average difference for each comparison. Three of the four people favored the same-trial fit in each comparison, with small pooled differences.

### The resting phases told a different story

Phase refers to the issue time. The paired model had the lowest MAE during ramp-up, hold and release. The force-history-and-phase model had the lowest MAE in both rest phases. The largest paired gain over force history and phase was during release, 0.000009103. The largest loss was during initial rest, 0.000007060. The full phase table for all seven models, including their RMSE, is in the aggregate file.

| Issue phase | Issues per trial | Persistence MAE | Force history + phase MAE | Same-trial EMG MAE | Other-trial EMG MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial rest | 94 | 0.003171 | 0.002637 | 0.002644 | 0.002647 |
| Ramp up | 100 | 0.007774 | 0.005953 | 0.005948 | 0.005955 |
| Hold | 200 | 0.005315 | 0.005136 | 0.005130 | 0.005146 |
| Release | 100 | 0.007835 | 0.006056 | 0.006047 | 0.006052 |
| Final rest | 98 | 0.003189 | 0.002728 | 0.002735 | 0.002735 |

## What this forecast measures

The measured output is one normalized pinch force in one condition. These results describe an offline comparison over native sample indices. The public data establish nominal rates and within-trial pairing. The common physical sample origin, drift and delivery latency remain unmeasured, so the EMG guard is a release-index convention. The dynamometer measures the force between opposing digits as one reading. Separate digit forces, an effect in other tasks, online timing and clinical performance require their own evidence. This separately acquired dataset tests a complementary task to Hyser's five-sensor Random experiment. [Study methods](https://doi.org/10.1038/s41597-025-05733-y) · [Source compatibility](SOURCE-COMPATIBILITY.md) · [Hyser record](https://physionet.org/content/hd-semg/2.0.0/)

## Try the reader

The public example uses invented readings and invented weights. Load your own local fit and a trial converted from its original MATLAB file to explore that trial. The converter and owner-training commands run locally. Reveal the later reading at one cutoff, or score all 592 cutoffs to see aggregate trial errors. [Offline reader](../../docs/cemhsey-pinch/README.md) · [Local commands](LOCAL-CONVERTER.md) · [Invented fit](BUNDLED-FIT.json)

## Data credit

The CEMHSEY deposits are by Shutian Yang, Dongxuan Li, Chen Chen and Xiangyang Zhu. This analysis uses the v2 GRASP recordings, selects one pinch condition, derives four surface EMG amplitude summaries per issue, fits the prespecified comparisons and reports aggregate errors. The datasets are licensed CC BY 4.0. [CEMHSEY Part I v2](https://doi.org/10.5281/zenodo.15077957) · [CEMHSEY Part II v2](https://doi.org/10.5281/zenodo.15070187) · [Data license](https://creativecommons.org/licenses/by/4.0/)

The acquisition is described by Shutian Yang, Chen Chen, Dongxuan Li and Xiangyang Zhu in Scientific Data 12, article 1420 (2025). [Acquisition paper](https://doi.org/10.1038/s41597-025-05733-y)

[Try the pinch reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) · [Download the offline reader and Python converter](downloads/CEMHSEY-Pinch-Reader.zip) · [Model code](pinch.py) · [Public demonstration weights](BUNDLED-FIT.json) · [Fit on local recordings](fit_local.py) · [Source compatibility](SOURCE-COMPATIBILITY.md)
