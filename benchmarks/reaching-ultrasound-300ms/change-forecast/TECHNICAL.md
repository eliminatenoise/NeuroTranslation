# Participant-disjoint prediction of 300 ms point-spread changes

[Simple report](README.md) · [Aggregate scores](RESULTS.json)

The earlier browser preview estimates absolute spread. Here the target is the signed change from the newest measured ultrasound frame in the last pre-issue 20 ms slot to the observed spread at the nominal 300 ms forecast time. Each spread is the root mean square distance of four tracked points from their centre in the image plane. The motion and EMG predictors receive ten strictly past slots and use ultrasound to define the outcome. The separate assisted trend also uses previous ultrasound as an input. For the relative representation, subtract the first available position of each marker inside the history. Preserve availability flags.

Six complementary splits of the original 24 training participants hold out four people per fold. Normalization uses the 20 fitting participants. Frozen forecasts cover 29,664 issues, with 28,334 triceps and 28,461 brachialis observations. Two participants each lack measurements for one tissue. The scorer records those two errors as missing and averages 23 person errors per tissue. All methods use the same measured rows. The original scorer stopped at the complete-tissue assertion. The repaired scorer used the original prediction bundle.

| Selected method | Triceps error | Brachialis error | Mean |
| --- | ---: | ---: | ---: |
| Motion-only ridge | 0.1479 mm | 0.1274 mm | 0.1377 mm |
| Zero change | 0.1489 mm | 0.1290 mm | 0.1389 mm |
| Relative motion, 800 updates, one refinement | 0.1518 mm | 0.1319 mm | 0.1418 mm |

The ridge fit uses a squared-weight penalty of 0.01. The learned comparison uses 48 fits across four input conditions, six folds and two seeds. The checkpoint settings are 800, 1,600 and 3,200 updates, each tested with one, three, five and eight refinement passes. For the nominated motion-only branch, one-pass errors are 0.1418, 0.1457 and 0.1495 mm. The paired participant intervals for motion-only ridge versus zero change include zero for both tissues. The assisted trend scored 0.1436 mm on the same eligible rows.

At 1,600 updates and three passes with motion and EMG, relative coordinates reduce mean error from 0.1602 to 0.1464 mm. The mean relative-minus-original errors are −0.0165 mm for triceps and −0.0111 mm for brachialis. The corresponding EMG-versus-motion comparisons within relative coordinates have intervals spanning zero.

The nominations use the same internal folds being reported. The methods were locked before the six reserved recordings were retrieved. The [reserved comparison](reserved/) reports that test. Dataset by Pallarès-López et al., licensed CC BY 4.0. [Data descriptor](https://doi.org/10.1038/s41597-026-07019-3) · [Recordings](https://doi.org/10.6084/m9.figshare.31030252.v1)
