# Blend an electrode forecast with no movement

[Package overview](README.md) · [Simple guide](SIMPLE.md) · [Measurements](results.json)

## Inputs and fitted rule

Use 200 ms of complete primary motor cortex recording from the 96 archive electrodes numbered 96–191. Each channel provides ten 20 ms bins of voltage threshold crossings. Preserve the source order and an exact native start 200 samples before issue. Count events in half-open windows, including the start and excluding the end. The same three FP32 models fitted on September 23 estimate planar Hand displacement and straight-line distance 100 ms after issue. The blend multiplies each output by a shared weight from zero to one. The three base models keep their original weight sets. [Data deposited in DANDI](https://dandiarchive.org/dandiset/000070/0.261122.2046) · [Original models](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/cortical-electrode-identity)

The six blend features are the logarithm of one plus the mean vector length, the same transformation of mean predicted distance, length of the mean vector divided by mean vector length plus 0.000001 mm, logarithm of one plus the mean recent 60 ms count, its difference from the first 60 ms log count, and logarithm of one plus the across-electrode standard deviation of average recent counts. Features are standardized using the calibration mean and scale, then clipped between −5 and 5. `BLEND.json` contains the means, scales, slope and intercept. The sigmoid of the linear combination gives the shared weight.

Fit only this weight on 52,468 windows from the final quarter of September 22 and the admitted September 20 trials. The FP64 fit minimized smoothed Euclidean error, using the square root of squared vector error plus (0.01 mm)². It adds a penalty of 0.05 mm times the sum of squared slopes. It retained the lowest objective from three L-BFGS starts. Allocate equal weight to each calibration date, equal trials within date, then equal rows per trial. The inference path uses past inputs and the frozen forecasts. Movement markers and actual Hand positions are reference data for training or scoring.

## Measured comparisons

Forecasts were saved before opening each held recording's exact issue and +100 ms positions. Both evaluation dates precede the calibration dates. The same animal contributed all recordings. Each mean weights trials equally and averages the errors from the three base seeds. Ending-position error measures the distance between predicted and measured endpoints. Distance error compares the separate straight-line distance prediction with the measured distance. Values are mean errors in millimetres.

| Held recording | Trials | Windows | Endpoint, original | Endpoint, blend | Endpoint, stay put | Distance, original | Distance, blend | Distance, stay put |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 19 August 2010 | 3,126 | 39,297 | 14.61 | 8.19 | 7.89 | 13.24 | 6.20 | 7.89 |
| 12 August 2010 | 3,038 | 46,102 | 8.47 | 5.00 | 6.65 | 7.72 | 3.60 | 6.65 |

For actual displacements at least 20 mm, endpoint error was 24.01 mm for original and 25.51 mm for blend on August 19. It was 21.38 mm and 23.42 mm on August 12. For measured movement under 2 mm, no movement averaged 0.40 and 0.32 mm on the two days, compared with 4.36 and 1.21 mm for the blend. The measured bands describe the results after scoring. They are unavailable as inputs. On August 19 the blend's overall endpoint error exceeded no movement by 0.29 mm, with a paired 95% interval of 0.19–0.40 mm from 4,000 whole-trial draws. The interval describes the sampled day. These tests do not establish transfer to a new person, animal, or recording system.

## Run a forecast

1. Extract the ZIP and open its folder in a terminal. Install with `python3.12 -m pip install -r requirements.txt` on Linux or macOS, or `py -3.12 -m pip install -r requirements.txt` on Windows.
2. Open the launcher for your system. It runs a generated example. To run directly, use `python3.12 predict.py` on Linux or macOS, or `py -3.12 predict.py` on Windows. The Linux example and full saved predictions were replayed. The Windows and macOS launchers are included.
3. Append `--input window.json` to the direct Python command for prepared counts. Each ID in `electrode_ids` from 96 to 191 appears once. The corresponding row of `counts` must give ten nonnegative whole numbers, oldest bin first, from a complete observed window on the matching electrode array.

The result gives `blend_weight` and an original and blended triplet for each fitted seed. Output fields give X and Y changes and the separate distance, all in millimetres. The ZIP includes the three runnable ONNX graphs, full SafeTensors weights and the fitted blend coefficients. The recordings are distributed by DANDI. This package's code and weights use [CC0](LICENSE).
