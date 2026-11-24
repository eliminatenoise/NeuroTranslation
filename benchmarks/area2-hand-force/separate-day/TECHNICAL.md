# Trade-off between pooled Area 2 activity and handle-force forecasts across days

Two FP64 regularized linear models predicted planar displacement 100 ms after issue. One used recent position and force. The other added pooled Area 2 spike counts. We fit both on 218 trials from Han on December 7, 2017 and used 72 other trials from the same recording to select model settings and fit blending rules. The earlier 74-trial DANDI test contributed no training or evaluation rows. The independent test used `H_20171204_COactpas_TD.mat` from the same animal and lab on December 4. [Earlier benchmark](../TECHNICAL.md) · [Development data, CC BY 4.0](https://dandiarchive.org/dandiset/000127/0.220113.0359) · [Test data, CC0](https://datadryad.org/dataset/doi:10.5061/dryad.nk98sf7q7) · [Original experiment](https://doi.org/10.7554/eLife.48198)

## Sampling and model

Inputs cover ten 20 ms bins ending at issue. At each bin start, x and y position in millimetres is relative to the measured issue position. The force inputs are calibrated x, y and z in newtons. The three moment columns were excluded. Spikes were counted in half-open 20 ms windows on December 7. On December 4 each bin combines two adjacent stored 10 ms counts. We used the 65 eligible sorted units on December 7 and the 83 positive-sort units on December 4. The neural features for each bin are the mean and population standard deviation of `log1p(count)` and the fraction of units with nonzero counts. Pooling removes dependence on unit order. [Author conversion](https://github.com/raeedcho/preprocess-from-limblab/blob/d7b78757bdfdd82cbc99aeeec549c763cc76ad17/convertCOactpasfiles.m)

Each linear head selected a ridge penalty of 0.0001 from six settings between 0.0001 and 10. Normalization was fitted on the 218 trials. The fixed blend was a weighted average with 0.35738 assigned to the forecast using Area 2. The adaptive blend assigns that weight using a sigmoid of four covariates. These are the length of the latest 20 ms displacement, magnitude of force change between the oldest and newest bin, length of the motion-and-force forecast, and vector distance between the forecasts. We applied `log1p`, normalized on the 72 configuration trials and clipped standardized values at ±5. The blend fitting used Euclidean error smoothed with a 0.01 mm floor and a 0.05 mm penalty on the squared adaptive slopes. The adaptive weight's 5th, 50th and 95th percentiles on December 4 were 0.344, 0.368 and 0.437.

Of 805 archived trials, 786 supported at least one issue time. The first issue was 200 ms from the original trial start. Later issues were 320 ms apart within the same trial, with each target strictly before the original trial end. The target-position indices were disjoint from the position inputs. We froze all six methods' predictions and compared the same 5,921 valid endpoints. Endpoint error is the norm of the vector residual. Displacement length error is the absolute difference between forecast and observed vector lengths. Each original trial counted equally. We calculated paired 95% intervals from 4,000 whole-trial bootstrap resamples.

## Test results

| Forecast | Endpoint error, mm | Displacement length error, mm |
| --- | ---: | ---: |
| Stay put | 7.391 | 7.391 |
| Constant velocity from the preceding 20 ms | 3.788 | 2.758 |
| Motion and force | 2.126 | 1.528 |
| Motion, force and pooled Area 2 | 2.141 | 1.538 |
| Fixed blend | 2.126 | 1.528 |
| Adaptive blend | 2.126 | 1.528 |

The paired reduction in endpoint error from motion and force to the adaptive blend was 0.000011 mm (95% interval −0.002629 to 0.002773). Against the fixed blend it was −0.000074 mm (−0.000384 to 0.000232). Replacing motion and force with the model that always adds Area 2 increased error by 0.015068 mm (0.008084 to 0.021698). The motion-and-force model remains the reference.

| Measured displacement | Forecast times | Trials | Adaptive endpoint gain in mm |
| --- | ---: | ---: | ---: |
| Under 2 mm | 2,373 | 677 | −0.0023 |
| 2 mm to under 10 mm | 2,149 | 735 | −0.0015 |
| 10 mm to under 20 mm | 803 | 517 | 0.0016 |
| At least 20 mm | 596 | 472 | 0.0062 |

The strata are descriptive and use the later measured displacement. All four intervals include zero. For at least 20 mm the interval was −0.0030 to 0.0153 mm. The archived push label applies to whole trials. The earlier within-day study used individual unit readings and found a larger difference for large movements. This comparison changes both timing of the recording and the export, along with the neural features. The study concerns one animal and nominal archival timing. The source performs offline filtering and resampling, and physical inter-device delay was unverified. [All scores and paired intervals](results.json)

## Run inference

Place the supplied files together with Python and NumPy available. Run `python infer.py example-input.npz forecasts.npz` with a new output path. The example is synthetic. Use `motion` shaped `(rows, 10, 2)` in millimetres relative to issue, `force` shaped `(rows, 10, 3)` in newtons, and `counts` shaped `(rows, sorted_units, 10)`. The number of sorted units can vary. Arrange bins oldest first and match archive axes and timing. The six output arrays give x and y displacement in millimetres. `dynamic_weight` gives the Area 2 blend weight per row. [Inference](infer.py) · [Coefficients](blend-weights.npz) · [Synthetic input](example-input.npz) · [Simple edition](README.md)

Recording credit goes to Raeed Chowdhury, Joshua Glaser and Lee E. Miller for the Dryad data, and Felix Pei, Raeed Chowdhury, Lee E. Miller and the source contributors for the DANDI recording.
