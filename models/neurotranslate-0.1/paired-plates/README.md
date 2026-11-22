# Predicting a new load on two force plates

This NeuroTranslate experiment estimates the chance that each plate will start carrying weight in the next 100 milliseconds. A force plate is a floor panel that measures how hard someone presses on it.

## Run the included example

Extract the ZIP. Open a terminal in the extracted folder and run the command for your computer. You need Python 3. No extra packages or model downloads are needed.

| Computer | Command |
| --- | --- |
| Linux | `./launch-linux.sh` |
| macOS | `./launch-macos.command` |
| Windows | `.\launch-windows.cmd` |

You can also run `python3 paired_plates.py --example` on Linux or macOS, or `py -3 paired_plates.py --example` on Windows. The result lists a chance for each plate in the order shown in the input. The included example uses invented readings.

## Try the longer force history

Add `--arm timing_attention` or `--arm timing_linear` to your launcher command. For example, run `./launch-linux.sh --arm timing_attention` on Linux. Both options use the second invented example, `example-timing.json`, when you run them without an input file.

These options use 700 milliseconds of recent force. For your own input, copy `example-timing.json`. In `bin_end_ms`, give one row of 35 integer times per plate, with the same times in each row. Supply 35 force values per plate and the plate state at each bin end in `plate_state_by_bin`. Each bin covers 20 milliseconds. The final bin ends at forecast time. All force bins must have values. The attention option weighs five windows of the other plate's force. They end at forecast time or 100, 200, 300 or 500 milliseconds earlier. The linear option uses the same windows with fixed learned coefficients.

Run `python3 paired_plates.py --arm timing_attention --input your-timing.json`. Use `--arm timing_linear` to try the linear option. On Windows use `py -3` in place of `python3` if needed.

## Use your own recorded readings

Copy `example.json` and keep the fields in the same format. Use the same ten bin end times for both plates, with 20 milliseconds between bins. Each force value is the mean vertical force for that bin, in newtons, with upward force positive. The final bin ends at forecast time. Use readings available by each bin's end to calculate its mean. Use `null` for a missing value.

Give each plate a state based on readings already available at that time. Use `0` for unknown, `1` for unloaded, `2` for a load that has started and is awaiting confirmation, or `3` for loaded. Use `0` if you lack a reliable state.

In the source tests, a plate became unloaded after 20 milliseconds between −10 and +10 newtons. Once the plate was unloaded, a new load counted from the first sample at or above 20 newtons if the force stayed at least that high for 20 milliseconds. Use readings available at forecast time to decide the input state. Later samples confirm what happened for scoring.

The scored recordings included unloaded and loaded plates. The output field `plate_state_in_scored_recordings` flags the other states as outside those tests. Treat their estimates as untested.

Run `python3 paired_plates.py --input your-recording.json`. On Windows use `py -3` in place of `python3` if needed.

The default uses force readings. For the muscle experiment, add `--arm paired_relative_muscle` and use the short history in `example.json`. The six muscle channels are left and right biceps femoris, rectus femoris and tibialis anterior, in the order given in the example. Each value compares the voltage variation in one bin with variation in at least three earlier bins from that same channel. Use the natural logarithm of one plus the ratio. Take the variation as the root mean square after removing each bin’s mean voltage, and pool the squared variation across the earlier bins before taking their square root. Leave the first three bins empty.

If you already have signed force impulse estimates from the full model, put them in an optional `signed_impulse_ns` list. This is the vertical force added up over the forecast window, measured in newton-seconds. The command copies the two estimates to its output in the same order.

## What the tests covered

The short two-plate force model lowered average probability error versus the one-plate model on the original Belgian fitting archive and on three other people from that archive. Error rose for one of those three additional people. Only three of the six assigned validation participants could be scored under the original rules. On the two previously inspected development walks from Pisa, the short model with muscle readings gave lower probability error than the short force-only model. Those walks had four measured load starts.

We trained both longer-history options on the Belgian fitting archive and scored their saved weights on a separate set of comfortable-speed treadmill walks. Thirty-nine of the 41 assigned people provided scoreable windows, with 983 measured load starts. For two people the force readings never met the unloaded-state rule. The attention option had an average squared probability error of 0.03575, compared with 0.04121 for the short two-plate model. It improved this score for 31 of the 39 people. The longer linear option gave 0.03700 and had the lowest log loss, a score that penalizes confident wrong forecasts. These results cover one treadmill speed at each person's comfortable pace. [Treadmill study](https://peerj.com/articles/4640/) · [Dataset](https://doi.org/10.6084/m9.figshare.5722711.v2)

## What changed with walking speed

We tested the saved models on two further sets of treadmill walks from the same study. The percentages below refer to each person’s comfortable speed. Lower squared probability error means forecasts were closer to what was measured. [Walking protocol](https://pmc.ncbi.nlm.nih.gov/articles/PMC5922232/)

| Speed | People with scores | Measured load starts | Short history | Longer attention | Longer linear |
| --- | --- | --- | --- | --- | --- |
| 40% | 34 of 41 | 511 | 0.02741 | 0.03089 | 0.03379 |
| 130% | 33 of 39 | 857 | 0.03928 | 0.04451 | 0.03679 |

Among the 29 people with scores at all three speeds, attention had lower error than the short-history model at comfortable speed and higher error at both other speeds. The short-history model had the lowest log loss at both additional speeds. At 130%, the linear model’s squared error was lower on average than the short-history model’s. The uncertainty across people still includes a possible increase in error.

This is a recorded-data experiment. Performance with new equipment, in live use, and across a wider population is still open. The ZIP contains the checkpoint files, code and two invented input files. See the source studies for the recordings. [Belgian recording methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC10692332/) · [Pisa recording methods](https://www.nature.com/articles/s41597-025-06209-9)

The code and checkpoints are released under CC0 1.0. The Belgian source recordings use CC0 1.0. The Pisa and treadmill recordings use CC BY 4.0. [Belgian data record](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Pisa data record](https://doi.org/10.6084/m9.figshare.29371769.v1)
