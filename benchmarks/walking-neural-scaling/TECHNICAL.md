# Walking and cortical forecasts

[Simple edition](SIMPLE.md) · [Results data](results.json) · [Download both walking checkpoints](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/walking-neural-scaling/Walking-Forecasts.zip)

## Run a walking checkpoint

Extract the ZIP and open a terminal in its folder. The reference runs used Python 3.13 with PyTorch for the three-pass model and Python 3.12 with ONNX Runtime for the trees.

| Checkpoint | Install | Run the generated example |
| --- | --- | --- |
| Three-pass model | `python -m pip install -r requirements-recurrent.txt` | `python predict.py --model three-pass` |
| Boosted trees | `python -m pip install -r requirements.txt` | `python predict.py --model trees` |

`Open on Linux.sh`, `Open on macOS.command` and `Open on Windows.cmd` run the three-pass example by default. Pass `--model trees` to a launcher from the terminal to run the tree example after installing its packages. The supplied example uses generated values. To use a recorded window, append `--input window.json`. The JSON field `emg_rms_volts` contains ten rows of root-mean-square muscle voltage ordered oldest to newest. Use `null` for an unavailable muscle entry. `measured_plate_force_n` contains ten finite mean vertical force values in newtons from the forecast plate. For trees, supply ten corresponding finite values in `other_plate_force_n` and order the six muscle columns LBF, LERS, LGAS, LRF, LST and RERS as in the Belgian source. The three-pass model takes four or six voltage streams and a single plate without assigning muscle names.

Both checkpoints forecast vertical force impulse in newton-seconds and the probability that a plate begins carrying load in the next 100 ms. A new load starts when the force reaches at least 20 N and stays at or above 20 N for 20 ms. The unloaded state requires 20 ms within −10 to +10 N. For the three-pass model the probability head was fitted on Belgian recordings. The two packaged weight sets are research checkpoints.

## Belgian walking comparison

Both new methods fitted 9,586 plate rows from 36 walks by 12 people. The development comparison reused nine walks from three of the six assigned development people. These three had the common sensor channels needed for the comparison. The tree and convolution-LSTM forecasts each use their target plate and the simultaneous past of the other plate. The comparison therefore includes sensor access as well as model design. Errors aggregate by person after trials, issue times and plates. Impulse scores use 432 rows. Load probability scores use 427 supported cases, including 18 positive rows representing eight distinct onsets.

| Forecast | Impulse mean absolute error (N·s) | Mean squared probability error |
| --- | ---: | ---: |
| Fit load prior and force persistence | 3.237 | 0.03995 |
| Research Edition, three passes | 2.895 | 0.03863 |
| Causal convolution and LSTM | 1.933 | 0.03512 |
| Histogram gradient-boosted trees | 1.609 | 0.02941 |

Force persistence extends the latest 20 ms mean force for 100 ms. The published ONNX tree graphs reproduce the scikit-learn forecasts on all 432 cases to within 0.000017 N·s and 0.00000026 probability. The single-core median for one complete 432-row forecast was 1.53 ms with ONNX and 3.15 ms with scikit-learn. ONNX session creation took 18.66 ms on the benchmark machine.

## Cross-laboratory walking and simulated sensor disruptions

The compact model used ten past force means from one plate and the median and 80th percentile of within-channel relative EMG change. New fitting sets added 0, 4, 8 or 16 people from the İzmir archive to the same 12 Belgian people. The archive supplied 48 additional fitting walks from 16 people and one measured plate at 2,000 Hz. The first 200 ms of each usable window formed the history. Two C3D readers agreed on the analogue values, and independent calibration and rotation reproduced the vertical force. The İzmir fitting windows contain zero supported new-load events. This release scores the load output on Belgium and force on both labs.

Development used the same nine Belgian walks and 18 İzmir walks from six different people. The three-pass force error, averaging the two labs equally and three training seeds, was **3.196, 2.442, 2.306 and 2.464 N·s** across the four fitting sizes. The physical reference scored 5.000 N·s. Six reserved İzmir participants and the separate Belgian final-test group remain unopened.

The next paired comparison continued all weights for 900 FP32 updates per seed on the eight-person and sixteen-person fitting sets. Within each pair, both variants started from the same weights and sampled the same examples. The augmentation independently delayed muscle input by 20 ms with probability 0.15 and removed its latest 60 ms with probability 0.20. The same earlier development measures were used for all comparisons. Complete-input results on the eight-person fitting set improved for seven of nine development people and two of three fitting seeds relative to clean-only continuation.

| Eight added fitting people | Complete (N·s) | 20 ms delay (N·s) | 60 ms missing (N·s) |
| --- | ---: | ---: | ---: |
| Before continuation | 2.306 | 2.886 | 8.192 |
| Clean-only continuation | 1.924 | 2.800 | 7.790 |
| Continuation with generated disruptions | 1.816 | 1.840 | 1.808 |

The two disruption conditions are generated changes applied to recorded inputs. The comparison uses the original force measurements in both conditions. Both disruptions improved relative to clean-only continuation in all nine development people and all three seeds. The included SafeTensors checkpoint is the first prespecified training seed of the eight-person augmented fit. The table reports the mean across three seeds. The PyTorch runtime reproduces the frozen forecasts for the two labs.

## Recorded cortical spikes and later hand position

This separate benchmark uses the MC Maze Small public NWB file. It counts spikes for 142 recorded units in ten half-open 20 ms bins from the primary and premotor cortex of one macaque. Predictions use these counts and their availability flags. The target is two-dimensional hand position 100 ms later in millimetres. Position uses exact timestamps on the archive's 1 ms grid and the stored unit conversion. The input gives the model cortical history alone.

The fit used nested sets of 25, 50 and 75 trials from the archive's fitting role. The score averages Euclidean error over 991 forecasts within 15 other trials, then weights trials equally. Ten separate confirmation trials and the official NLB test file remain closed. This custom task uses all recorded units available in the public file, including channels designated held-out for the official benchmark.

| Fit trials | Eight-pass hand error (mm) |
| --- | ---: |
| 25 | 28.922 |
| 50 | 23.105 |
| 75 | 21.121 |

At 75 trials the fixed training mean scored 51.575 mm and the regularized linear model with penalty 100 scored 42.707 mm. Moving existing spike history back by a generated 40 ms raised the eight-pass error to 25.047 mm. The eight-pass fit used the lowest development error at 75 trials. The scope is transfer across trials from one session and animal. Another animal or session is needed to measure transfer at that level.

## Sources and software

The Belgian raw data are from Van Criekinge and colleagues, CC0. The İzmir data are from Mihcin and colleagues, CC BY 4.0. The cortical archive is from the Neural Latents Benchmark, CC BY 4.0. The package contains trained weights, export settings, code and aggregate scores. Obtain recordings from their original repositories. [Belgian gait data](https://doi.org/10.6084/m9.figshare.24192480.v1) · [İzmir gait data](https://doi.org/10.48623/aperta.286865) · [MC Maze Small](https://doi.org/10.48324/dandi.000140/0.220113.0408)

Open tools used here include scikit-learn, PyTorch, SafeTensors, c3d, EZC3D, PyNWB and ONNX Runtime. Both packaged checkpoints are walking models. The cortical study is available in this report and the aggregate results file. Training size, approach and recording conditions all affected the scores. A lasting performance plateau remains unestablished. [EZC3D](https://github.com/pyomeca/ezc3d) · [PyNWB](https://github.com/NeurodataWithoutBorders/pynwb) · [ONNX Runtime](https://github.com/microsoft/onnxruntime)
