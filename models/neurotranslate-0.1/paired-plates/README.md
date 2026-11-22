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

## Use your own recorded readings

Copy `example.json` and keep the fields in the same format. Use the same ten bin end times for both plates, with 20 milliseconds between bins. Each force value is the mean vertical force for that bin, in newtons, with upward force positive. The final bin ends at forecast time. Use readings available by each bin's end to calculate its mean. Use `null` for a missing value.

Give each plate a state based on readings already available at that time. Use `0` for unknown, `1` for unloaded, `2` for a load that has started and is awaiting confirmation, or `3` for loaded. Use `0` if you lack a reliable state.

In the source tests, a plate became unloaded after 20 milliseconds between −10 and +10 newtons. Once the plate was unloaded, a new load counted from the first sample at or above 20 newtons if the force stayed at least that high for 20 milliseconds. Use readings available at forecast time to decide the input state. Later samples confirm what happened for scoring.

The scored recordings included unloaded and loaded plates. The output field `plate_state_in_scored_recordings` flags the other states as outside those tests. Treat their estimates as untested.

Run `python3 paired_plates.py --input your-recording.json`. On Windows use `py -3` in place of `python3` if needed.

The default uses force readings. For the muscle experiment, add `--arm paired_relative_muscle`. The six muscle channels are left and right biceps femoris, rectus femoris and tibialis anterior, in the order given in the example. Each value compares the voltage variation in one bin with variation in at least three earlier bins from that same channel. Use the natural logarithm of one plus the ratio. Take the variation as the root mean square after removing each bin’s mean voltage, and pool the squared variation across the earlier bins before taking their square root. Leave the first three bins empty.

If you already have signed force impulse estimates from the full model, put them in an optional `signed_impulse_ns` list. This is the vertical force added up over the forecast window, measured in newton-seconds. The command copies the two estimates to its output in the same order.

## What the tests covered

The two-plate force model lowered average probability error versus the one-plate model on the original Belgian fitting archive and on three other people from that archive. Error rose for one of those three additional people. Only three of the six assigned validation participants could be scored under the original rules. The two previously inspected development walks from Pisa had four measured load starts. On those two walks, the version with muscle readings had the lowest average probability error of the models compared here.

This is a recorded-data experiment. Performance with new equipment, in live use, and across a wider population is still open. The ZIP contains the checkpoint, code and one invented input. See the source studies for the recordings. [Belgian recording methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC10692332/) · [Pisa recording methods](https://www.nature.com/articles/s41597-025-06209-9)

The code and checkpoint are released under CC0 1.0. The Belgian source recordings use CC0 1.0 and the Pisa recordings use CC BY 4.0. [Belgian data record](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Pisa data record](https://doi.org/10.6084/m9.figshare.29371769.v1)
