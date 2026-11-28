# Inference depth with frozen Research Edition weights

A follow-up tests two and four inference passes alongside a repeated three-pass control on the same forecasts. [Results and methods](near-three/TECHNICAL.md)

We varied the number of passes through the middle 12 of 24 decoder layers while holding the 547-update native-recurrence checkpoint fixed. Fitting used three passes and 9,586 rows from 12 people. The comparison uses the same three qualifying people from the six-person validation assignment. There are nine walks and 216 same-tick force-plate pairs. The reserved final test was unopened. [Original recordings](https://doi.org/10.6084/m9.figshare.24192480.v1)

Each forecast uses ten 20 ms history bins of six named muscle voltages and signed vertical plate force. It estimates signed force impulse and the probability of new loading over 100 ms. The reference extends the latest force and uses the fitted event prior. There are 432 impulse rows and 427 rows with a usable event target. The 18 positive rows represent eight distinct confirmed onsets. We averaged errors within each person before weighting people equally. Brier error is squared probability error. The impulse measure is mean absolute error.

| Method | Impulse MAE, N·s | New-load Brier error |
| --- | ---: | ---: |
| Fitting prior and force persistence | 3.23650 | 0.03994999 |
| 1 pass | 3.55654 | 0.03918078 |
| 3 passes | **2.89490** | 0.03862550 |
| 5 passes | 3.11755 | **0.03859348** |
| 7 passes | 3.09739 | 0.03876195 |
| 9 passes | 3.09861 | 0.03890711 |

Three passes retain the lowest impulse error. Five reduced Brier error by 0.00003202 relative to three. The validation set was used previously and only three people qualified. Three passes remains the preview example. The results describe this validation subset. [Endpoint-specific and joint support](results.json)

The shared traversal captured hidden state and block history at each depth, then ran the ordinary final layers and output heads at each capture. It preserved the original precision, measurement clocks and masks. Both outputs were bitwise equal to five separate runs at the first, middle and last pair. Prior three- and five-pass probabilities and impulse predictions matched exactly across all rows. Median elapsed time for the five settings at the three checked pairs was 2.103 seconds with shared computation and 5.215 seconds with separate calls. Across the 215 pairs after the first, the median shared forward time was 2.140 seconds with four CPU threads. Loading was measured separately. [Current preview and setup](../TECHNICAL.md) · [Simple edition](SIMPLE.md)
