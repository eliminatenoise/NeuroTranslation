# Where will the wrist be in a quarter of a second?

A person steers a cursor by bending the right wrist. Stop the recording halfway through the reach. How far back will the wrist bend, and how far will it tilt towards the thumb, a quarter of a second later? This wrist specialist gives both angles in degrees. First it reads the recent wrist movement. If you supply four measurements of electrical activity from the forearm, it also estimates how much to add to or subtract from each angle.

## Run one forecast

Use Python 3 with NumPy installed. From this directory, run the following command or open the launcher for your operating system. The tested Linux environment used Python 3.13.15 and NumPy 2.4.6.

```sh
python specialist.py invented-window.json
```

The example uses invented inputs and the actual fitted weights. The motion forecast puts the wrist at 13.77° of extension and 1.02° of radial deviation. The correction subtracts 2.49° from extension and adds 0.62° towards the thumb. The final forecast is **11.28° and 1.65°**. An encoder on a real wrist would supply the future measurement needed to judge its accuracy. [Example input](invented-window.json) · [Expected output](invented-forecast.json)

## Read your own window

Choose `"domain": "wrist_angle_specialist"` to use this dedicated convolutional network. Each JSON record carries a batch of one or more windows. Keep the same row order in every field. A Python caller can pass the same dictionary to `specialist.predict_record(record)`.

| Field | Meaning |
| --- | --- |
| `mode` | `emg` for motion plus four forearm channels, or `motion` for the bare motion forecast. |
| `bins` | For each window, sixteen consecutive bins, earliest first. The first two columns are mean wrist angles in degrees, each minus its angle at the cutoff. In EMG mode append four forearm amplitudes in microvolts, ordered M1 through M4. |
| `anchor_deg` | For each window, the two measured angles at its final input row. Positive extension bends the hand back. Positive radial deviation tilts it towards the thumb. |
| `slot` | One integer per window, from 0 through 5. The six forecast targets lie 384, 512, 640, 768, 896 and 1,024 stored ticks after the cue, respectively. |

For a target at row *T*, the input contains precisely rows *T*−383 through *T*−128 inclusive. The source stores 512 rows per second. Split these 256 rows into sixteen equal groups of sixteen. Average each angle within each group and subtract its value at the shared cutoff, *T*−128. For each forearm electrode pair M1L/M1R through M4L/M4R, subtract right from left at each sample, then take the root mean square of those sixteen differences. Use the two angle bins alone in motion mode. The nominal encoder refresh is about 100 Hz. Repeated values on the stored grid stay in place. Device delays were unmeasured. [Source and units](https://doi.org/10.1038/s41597-026-07287-z)

The three output arrays use that same axis order and unit. `motion_angle_deg` is the bare motion forecast. `correction_deg` is the signed correction learned from motion, cue timing and forearm activity together. `angle_deg` is their sum. Motion mode always returns a zero correction. The EMG correction includes contributions from motion and cue phase even for a window with zero muscle amplitudes.

## What the six people showed

The earlier experiment left one person out, fitted a model using the other five and repeated this for each of six people. It compared predicted angles with 11,274 measured angle pairs from 1,879 trials in 47 runs. These people had already contributed to wrist-model development. The error below is the square root of mean squared error, with equal weight for each person and each axis. [Historical experiment and controls](https://github.com/eliminatenoise/NeuroTranslation/tree/784101090dc3bb2da6f4dc1e168cc1037643756a/benchmarks/wrist-forearm-correction)

| Earlier held-person forecast | Error |
| --- | ---: |
| Motion CNN, zero correction | 3.618° |
| Motion CNN plus a separately fitted motion-only correction | 3.665° |
| Motion CNN plus motion and aligned forearm activity | 3.549° |
| Same correction, with another person's trial supplying the forearm activity | 3.828° |
| Same correction, with the forearm bins played backwards | 3.720° |

The aligned forearm correction improved on the separately fitted motion-only correction for all six people. It improved on the bare motion forecast for three. The biggest gain came at the earliest target time. The forearm electrodes measured surface voltage. Whether movement artifacts or changes in electrode contact contributed to the gain remains open.

**The distributed model uses all six people. Its error on a new person is unknown.** The 3.549° result belongs to the six earlier held-person fits. The distributed motion network has the original seed-17 weights. Its new correction learned from the discrepancy between each measured angle and the forecast made when that person was held out. The earlier motion-only correction appears above as a historical comparison. Running with `mode="motion"` gives the uncorrected CNN. [Fit method and source identities](provenance.json) · [Source credits and terms](NOTICE.md)
