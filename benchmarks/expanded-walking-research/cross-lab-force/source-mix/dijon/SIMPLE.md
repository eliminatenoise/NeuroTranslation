# Force forecasts on walking recordings from Dijon

A small model trained on walking had lower average error than a simple trend forecast for each of the 29 people when a plate was already carrying load. On those loaded windows, its average error was **10.13 newton-seconds**, compared with **14.03** for the trend. Training on recordings from a second lab lowered the model’s average error a little further, to **10.04**, with uncertainty that includes no gain. [Technical edition](TECHNICAL.md) · [Exact scores](results.json)

## What the test measured

The Dijon researchers embedded two force plates in a walkway. A plate recorded the upward push it exerted on the walker. Each forecast uses 200 milliseconds of earlier readings from one plate. It estimates the push accumulated over the next 100 milliseconds. That quantity is called impulse. A constant 500-newton force for a tenth of a second gives 50 newton-seconds. [Original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11139954/)

For each forecast, we split the earlier readings into ten slices of 20 milliseconds and averaged each slice. We placed forecasts 400 milliseconds apart so the readings used to make all the forecasts stayed separate from the later readings used to score them. We saved all forecasts before reading those later values. For each person we averaged how far the forecasts were from the measured outcomes. Each person’s average then counted equally in the table.

We compared seven ways to make this forecast. One holds the latest force average steady. Another continues the recent rise or fall. Three methods use small networks that read the sequence of earlier force values. For each of those methods, we average the forecasts of three independently trained networks. Two methods learn to correct the hold-steady rule, one trained on walking and one trained on that same walking data plus mixed activities from another lab. The third predicts impulse directly from the mixed training data. The two remaining methods learn simpler corrections that give each earlier reading a fixed weight. [Training comparison and runnable models](../SIMPLE.md)

## How the starting load changes the result

The table gives average errors in newton-seconds. Lower is better. The threshold uses the last force average the model received. It indicates how much the instrumented plate was carrying at that moment.

| Method | At least 20 N on the plate | Below 20 N | All forecast windows |
| --- | ---: | ---: | ---: |
| Hold the latest force steady | 15.31 | **0.17** | 0.87 |
| Continue the recent trend | 14.03 | 0.21 | 0.85 |
| Weighted correction, walking only | 11.70 | 1.34 | 1.82 |
| Weighted correction, both archives | 12.37 | 1.43 | 1.93 |
| Recurrent correction, walking only | 10.13 | 0.35 | 0.80 |
| Recurrent correction, both archives | **10.04** | 0.36 | 0.81 |
| Direct recurrent forecast, both archives | 10.85 | 0.28 | **0.76** |

All 29 people contributed to both groups. The loaded group had 855 forecasts, and the lower-load group had 18,991. In the loaded group, the walking-only correction lowered the error against trend by **3.90** on average. We repeatedly drew groups of 29 people from the same 29, allowing repeats. The middle 95% of those group averages ran from **3.17 to 4.70**. The correction trained on both archives beat trend for 28 of 29 people, with a gain of **3.99** and a range of **3.19 to 4.86**. The estimated gain from adding a training archive ranged from **0.26 worse to 0.49 better**. In the lower-load group, holding the latest force steady gave the lowest average error.

These recordings came from a lab absent from both training sets. We used one separate recording to check how the instruments stored their readings. We ran the published models without fitting them again. The result concerns force on the two floor plates. A plate can have very little load while the walker is supported elsewhere on the floor. [Source archive](https://doi.org/10.6084/m9.figshare.25592865.v1)
