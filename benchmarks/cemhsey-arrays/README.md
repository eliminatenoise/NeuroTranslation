[The studies](../README.md) › Study 19 · Pinch: five electrode grids

# Keeping the five electrode grids apart made no measurable difference

[Study 18](../cemhsey-pinch/README.md) boiled 320 channels of forearm muscle activity down to four amplitude numbers. This study keeps the five electrode grids apart and asks whether their activity relative to one another improves the same forecast of the pinch gauge 120 ms ahead. Once the model already had the overall muscle amplitude, for four new people, the five grids moved the average miss from **0.51663%** to **0.51659%**: 0.00004% lower, better for two of the four, with a range from 0.00110% lower to 0.00102% higher. The sign flipped between the two recording days, and the measure that punishes large misses got slightly worse, 0.69358% to 0.69408%.

Every error here is in % of the person's hardest squeeze that day (their maximum voluntary contraction, MVC). The main measure is the plain average miss (mean absolute error); the measure that punishes large misses is root mean squared error. The forearm signal is surface EMG, electrical activity of muscle picked up on the skin.

The grids did beat every one of the four controls fixed in the plan on average, and the real grid boundaries beat channels dealt into five mixed groups for all four people. But the comparison that matters for adding the grids to study 18's model is the first row below, and it is the small one. So the grids passed the weaker half of the rule set before scoring, a lower average against all four controls, and failed the stronger half, which also asked both days and every range to favour them.

| Compared with | Its average miss | Gain from the five grids | People favouring the grids | Range of the gain when people are resampled |
| --- | ---: | ---: | ---: | ---: |
| Overall amplitude from the same trial | 0.51663% | +0.00004% | 2 of 4 | −0.00102% to +0.00110% |
| Channels dealt into five mixed groups | 0.51882% | +0.00223% | 4 of 4 | +0.00117% to +0.00329% |
| The five grids from the other repeat | 0.51737% | +0.00078% | 3 of 4 | −0.00043% to +0.00173% |
| Amplitude and grids from the other repeat | 0.51812% | +0.00153% | 4 of 4 | +0.00137% to +0.00170% |

The five-grid model's average miss was 0.51659%. The mixed groups were worse for all four people when each grouping got a model of its own. A second test kept the five-grid model's weights fixed and changed only the inputs at scoring: fed the mixed groups instead, the same fixed model missed by 0.00082% less. So how the fitted model responds to the input groups gave a different answer from fitting the two groupings separately. Adding a feature for each channel's rank made the five-grid model slightly worse (0.51664%), and the rank taken from the other repeat beat the real one. The rank test fixed in the plan failed.

Each trial gave 592 forecasts at a nominal 24 force samples (120 ms) ahead. The test group was 16 trials from four people on two recording days, 9,472 forecasts per method. The ranges come from resampling the four people, keeping their two days together. [Results file, with scores by stage of the cue and the fixed-weight controls, in fractions of MVC (multiply by 100 for %)](RESULTS.json) · [The plan, fixed before scoring](PROTOCOL.md) · [Channel numbering and the grid each electrode sits on](channel-map.json) · [Acquisition study](https://doi.org/10.1038/s41597-025-05733-y)

## What it does not show

Four people, each contributing repeated looks. People and days both changed between fitting and test, so their separate effects stay unknown. Nobody measured the offset between the two devices' clocks, so the 120 ms is a count of stored samples.

## Look at the grids yourself

Choose an electrode to compare its earlier and later activity, then reveal the force reading at that cutoff. The example uses invented signals and weights. To look at your own recording, open an original Session 5, Task 2 MATLAB file, or an array file from the earlier Python converter, and inspect the two measurement windows before the forecast moment. The fitting panel fits the reader's four forecasts on days 1 and 2 and both repeats of three people; judge such a fit on other recordings. [Open the array reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) · [Download the offline reader and the tools to fit on your own computer](downloads/CEMHSEY-Array-Reader.zip) · [Fit from original recordings](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/#fit-local) · [Original recording and task conventions](https://pmc.ncbi.nlm.nih.gov/articles/PMC12354741/)

[How the browser fits, and how closely it matches the Python code](BROWSER-FITTING.md)

The recordings are CEMHSEY GRASP, by Shutian Yang, Dongxuan Li, Chen Chen and Xiangyang Zhu, under CC BY 4.0. Full credit: [docs/RIGHTS.md](../../docs/RIGHTS.md).

The same model then faced three prescribed pinch targets, with one practice repeat at each to adjust it to the person: [Study 21 · Pinch at new targets](../cemhsey-transfer/) · [Compare the three targets](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/results/) · [Try two recordings on your computer](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/)
