# A cylinder in motion

Extract the whole folder. Double-click **index.html**, or use **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh**. A modern browser executes the models locally. If an operating system asks how to open an unpacked launcher, open **index.html** in the browser. Only the atlas, paper and source links need an internet connection.

## Run a forecast

Choose a held-out recording, a cutoff, a method and, for temporal fits, a seed. Switch between the sensor’s angular velocity and acceleration. X, Y and Z are device-fixed components. The left side of the graph shows twenty earlier samples at 100 Hz. The two horizontal marks on the right give the forecast and recorded means of the next ten samples. A mark represents a single mean across that whole interval. The earlier table gives the individual input rows.

Open **Edit an earlier reading** and move the slider. This changes one selected acceleration component by up to 10 m/s² on a fresh copy of the chosen history. The software recomputes the models after each edit. Unused channels can change without affecting a model that excludes them. The recorded future is available for the original sensor history. A borrowed accelerometer history or manual edit has no observed physical outcome of its own. **Restore original** returns to the recorded values. Examples and results remain on the computer.

## What the model reads

Each 20-row history makes five ordered blocks of four samples. Each block contains the last and mean three-axis gyroscope reading, the last and mean three-axis accelerometer reading, its ending time in seconds, the hand, and the hand-specific assigned target. The program scales inputs with training statistics and clips standardized values to ±10. Missing inputs in a model’s designated condition are set to standardized zero. Each temporal fit uses one 16-wide block with two attention heads and a 32-wide feed-forward layer. The final block position supplies the forecast. Linear fits use the same feature blocks flattened in temporal order. The five input sets have both sensor histories and target, gyro and target, acceleration and target, both sensors without a target, or task cues alone. Hand and time remain available throughout.

The single-task temporal fit takes all inputs and was trained only on angular velocity. Its unused acceleration coordinates have no interpretation and are omitted. Every other fit predicts both angular velocity and acceleration. Both outputs remain in the cylinder sensor’s native axes. Gyroscope units are rad/s. Acceleration includes gravity and is measured in m/s². The instrument processes these signals onboard. Separate optical measurements, joint angles, commands and person identifiers are absent from the input. Identifiers select and group recordings for the comparison.

A wrong-acceleration forecast sends the full fit twenty accelerometer rows from the closest eligible earlier original in the same split, hand, participant, target and cutoff. It preserves the recipient’s task and gyroscope. A missing donor yields no such forecast. The recent mean uses the last ten samples. The trend adds the difference between the two preceding ten-sample means to the more recent mean. The hand/target/cutoff mean uses training repetitions only.

## Read the evidence

The source study enrolled 31 people. The model experiment uses later repetitions of the same 24 development participants. Both original optical and inertial quality flags had to pass. The nine targets are assigned task labels. The exact time a participant received the cue, per-packet delay and processing latency do not follow from the exported sample clock. This forecast evaluates new repetitions by known people. The earlier optical alignment needs later measurements and plays no part in this forecast.

The deterministic excerpt selection uses the first eligible original and the first original with at least one earlier match for each hand. Ordering is ascending source participant, then native recording number. We keep every usable cutoff in those originals. Screen numbering counts recordings and repetitions from one. The portable example data stores their zero-based source indices. Example choice is independent of forecast error.

The group table uses all eligible windows or the donor-matched subset. Error is the Euclidean distance between the predicted and measured three-component ten-sample means. Compute errors separately for each trained seed, average windows within each original, give originals equal weight inside each participant, then give participants equal weight. A paired 95% interval resamples whole participants (10,000 draws, seed 20261124). The predeclared primary endpoint requires both upper limits below zero for full temporal minus gyroscope plus task and full temporal minus an earlier matched recording’s acceleration. Aggregate intervals describe comparisons across participants. They cannot supply an uncertainty band for an individual forecast.

## Run the portable model from JavaScript

In the browser console of the open page, evaluate the following. The output has three angular velocity coordinates followed by three acceleration coordinates. For a gyro-only loss fit the output has only three angular velocity coordinates.

```js
const r = CYLINDER_DATA.records[0];
const window0 = r.windows[0];
const history = {gyro: window0.gyro, accel: window0.accel, time: window0.time,
                 hand: r.hand, target: r.target};
CylinderForecast.predict(CYLINDER_WEIGHTS["full-17"], history);
```

The 23 frozen fits come with this package in **weights.js**. The 28 example windows, native recorded means, eligible donor accelerations and matching training means are in **examples.js**. **inference.js** also supports Node.js via CommonJS. **results.json** contains the participant-balanced scores, comparison intervals, counts and source/model identities. **SHA256SUMS** covers the distributed files except itself. [Data, paper and reuse terms](NOTICE.md)
