# Five grids and one pinch

The earlier pinch study reduced 320 channels of forearm muscle activity to four amplitude features. This experiment keeps the five grid identities and asks whether their relative activity improves a forecast of the same later dynamometer reading. The comparison uses new evaluation participants and new recording-day indices. [Prespecified protocol](PROTOCOL.md) · [Channel numbering and grid coordinates](channel-map.json) · [Acquisition study](https://doi.org/10.1038/s41597-025-05733-y) · [Earlier whole-forearm study](../cemhsey-pinch/README.md)

Choose an electrode to compare its earlier and later activity, then reveal the force reading for that cutoff. The example uses invented signals and weights. To inspect your own recording, open the reader and select the original Session 5, Task 2 MATLAB file or a converted array packet. [Open the array reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) · [Download the offline reader and local fitting tools](downloads/CEMHSEY-Array-Reader.zip)

## What did the five grids add?

Keeping the recorded grid boundaries lowered the mean absolute error against all four prespecified controls. The small comparison is the one that matters for adding this feature to the earlier model. After overall muscle activity was already available, five grid profiles reduced error by 0.00000042 of maximum voluntary contraction (MVC). Two of four people favored the grids. The sign reversed between the two recording days, and root mean squared error increased from 0.006936 to 0.006941 MVC fraction.

| Comparator | Comparator MAE | Grid reduction in MAE | People favoring native grids | Participant-resampling range for reduction |
| --- | ---: | ---: | ---: | ---: |
| Same-trial overall amplitude | 0.00516633 | +0.00000042 | 2 of 4 | -0.00001017 to +0.00001101 |
| Five interleaved groups | 0.00518823 | +0.00002232 | 4 of 4 | +0.00001172 to +0.00003292 |
| Five grids from the other repeat | 0.00517369 | +0.00000778 | 3 of 4 | -0.00000431 to +0.00001729 |
| Amplitude and grids from the other repeat | 0.00518120 | +0.00001529 | 4 of 4 | +0.00001368 to +0.00001705 |

The native-grid model averaged 0.00516591 MVC fraction in absolute error. Interleaving the channels into five equally sized groups increased that error for all four people. That comparison trained a separate model for each grouping. A second test held the native-grid coefficients fixed and changed only the inputs at evaluation. Substituting the interleaved groups reduced mean absolute error by 0.00000823 MVC fraction. The fitted model’s sensitivity to the input groups therefore gave a different result from fitting the two groupings separately. Adding channel-rank persistence made the native-grid mean error slightly worse (0.00516644), and the rank from the other repeat also beat the matched rank. The prespecified rank test failed.

Each trial contributed 592 forecasts at a nominal horizon of 24 force samples (120 ms). The held panel covers 16 trials from four people on two indexed days, for 9,472 forecasts per method. A person contributes repeated observations. The ranges come from resampling the four people while keeping both days together. Changing both people and days at evaluation leaves their separate effects unresolved. The released array map locates each electrode on its own sheet. A physiological timing claim would require an independent measurement of the offset between devices.

[Full aggregate, including phase scores and fixed-fit controls](RESULTS.json) · [Prespecified comparison](PROTOCOL.md) · [Original acquisition study](https://doi.org/10.1038/s41597-025-05733-y)

## Work with the original recordings

Open the original Session 5, Task 2 MATLAB trial in the browser to inspect the two guarded measurement windows. The earlier Python converter and compatible array packets remain supported. To train the four reader forecasts on your own study set, open the local fitting panel. It accepts days 1 and 2 and both repeats for three people. Use different recordings to assess a fit. [Open the array reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) · [Fit from original recordings](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/#fit-local) · [Original acquisition and task conventions](https://pmc.ncbi.nlm.nih.gov/articles/PMC12354741/)

[Browser fitting method and numerical agreement](BROWSER-FITTING.md)
