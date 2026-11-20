# Can leg muscle signals improve a force-plate forecast?

In these slow overground walks, six optical markers gave a better average forecast of what two force plates would record 100 ms later than a separately fitted Transformer given the same markers and eight right-leg muscle signals. The marker-only model missed by **65.19 N** on average. With muscle signals, its error rose to **70.20 N**. Across eight previously unseen walkers, the paired change was +5.01 N, with a 95% participant-bootstrap interval from −0.04 to +10.23 N. Adding EMG did not meet the prespecified improvement criterion.

## What the plates measured

The volunteers walked barefoot along a level walkway at 0.4–0.8 m/s. Each step could land on a plate or on ordinary floor. The target is the sum of vertical load on the two instrumented surfaces. A foot on ordinary floor can support the walker while both plates record zero. The source also coded missing instrument samples as zero and suppressed loads below 50 N. Its paper and code comment describe a 5 N cutoff, while the published reaction-processing code executes 50 N. [Dataset and experimental setup](https://doi.org/10.1038/s41597-019-0124-4) · [Author processing code](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/tree/e35dc90c1acd24da134897fd1b4241152cff6005)

The model received 240 ms of history. Three-dimensional coordinates placed each heel, second metatarsal head and anterior pelvic marker relative to the midpoint between the plates. On the right leg, eight pairs of surface electrodes recorded muscle electrical activity. The input reduced each 30 ms of electrical samples to a root-mean-square amplitude. The target occupied the 10-ms analog block ten stored optical frames later. Input and target block centres were 100 ms apart. The last input sample and first target sample were roughly 91 ms apart on the stored clock.

The authors filled gaps in marker trajectories, centred the EMG traces over the whole trial and filtered markers, force and EMG in both time directions. Events also determined the beginning and end of each released trial. Our analysis reads only earlier stored bins to make a prediction. Those upstream operations prevent the stored-bin result from establishing a prospective live forecast or a physiological delay. [Data and processing details](https://doi.org/10.1038/s41597-019-0124-4)

## Which walks counted

The split followed the original participant ID order. Of the 50 walkers, 30 were assigned to training, ten to assessment and ten to an unopened reserve. For each walker the design specified the three lowest-numbered recorded C2 repeats. We kept trials only when the source table documented reliable contacts by the two feet on two distinct plates. The model still predicts their sum. All eligible windows within an accepted recording counted, including source-coded zeros. Neither future force nor gait phase decided which windows entered the comparison.

This gave **25 training walkers, 62 trials and 4,846 windows**. In the assessment group **eight walkers contributed 17 trials and 1,297 windows**. Of the 28 training trials excluded, 25 had incomplete or unreliable contact assignments and three belonged to a participant ID with no exact table match. All 13 assessment exclusions had incomplete assignments. All selected marker and muscle channels were finite in all retained stored tokens. The raw marker gaps filled by the original processing remain unknown. Selection for clean contacts limits the result to that subset of this single-site dataset. [Dataset, version 8](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Supplementary tables](https://static-content.springer-cdn.net/esm/art%3A10.1038%2Fs41597-019-0124-4/MediaObjects/41597_2019_124_MOESM2_ESM.docx)

## Held-person results

Each trial contributes equally within a walker. Each walker contributes equally to the overall error. A positive bias means that the forecast tends to overshoot. The persistence comparison has access to an extra measurement, the current plate load.

| Predictor | Mean absolute error (N) | Root mean squared error (N) | Bias (N) |
|---|---:|---:|---:|
| Earlier measured plate load, carried forward | 63.43 | 112.77 | +23.15 |
| Marker Transformer | 65.19 | 95.03 | −9.68 |
| Marker and EMG Transformer | 70.20 | 107.03 | −12.37 |
| Nonlinear marker ridge | 91.25 | 123.14 | −13.58 |
| Marker and EMG linear ridge | 274.89 | 312.73 | −7.11 |
| Marker linear ridge | 279.75 | 314.21 | −20.60 |
| EMG Transformer | 286.35 | 333.01 | +0.52 |
| EMG linear ridge | 289.90 | 331.45 | +1.83 |
| Training mean | 292.22 | 329.58 | −4.68 |
| Zero | 481.19 | 583.22 | −481.19 |

At 354 source-coded-zero windows, the combined Transformer averaged 21.13 N of absolute error. At 943 nonzero windows, it averaged 88.18 N. These conditional errors use the same equal-trial, equal-walker averaging inside each stratum.

For the wrong-repeat comparison, we replaced the aligned muscle history with an earlier or equally far advanced history from another qualifying repeat by the same person. We matched ending marker positions without consulting force. Six people had a suitable second repeat. Across their 15 trials and 1,143 windows, aligned EMG gave **72.20 N** and wrong-repeat EMG **73.28 N**. The paired difference was −1.08 N (95% interval −7.31 to +4.67 N). This control preserves the walker and roughly matches the pose. Contact phase may still differ.

The combined Transformer did improve on nonlinear marker ridge by 21.06 N (95% interval −34.75 to −7.24 N). The frozen gate required at least 5% lower error and an interval strictly below zero against each of nonlinear marker ridge, marker Transformer and wrong-repeat EMG, with at least eight contributing walkers. Only the nonlinear ridge comparison passed. Whole-person uncertainty is substantial in this cohort. These results concern the stored instrument load at one speed range. Surface EMG measures electrical activity at the muscle. The study did not observe neural commands, muscle force or the force from every foot contact.

## Try the fitted model

The NumPy predictor runs on the included invented history. The distribution also contains the frozen protocol, complete aggregate results, six fitted models and source-to-score instructions. The nonlinear ridge baseline is reproducible from source. Its 256 training-window landmarks stay out of the download. [Reproduction instructions](REPRODUCE.md) · [All numerical results](results.json) · [Source attribution](RIGHTS.md)
