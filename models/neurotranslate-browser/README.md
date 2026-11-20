# Forecast movement from one recording

How far will a tracked point move? Where will a wrist point? Give the model one movement history and it returns the quantity that instrument measured.

| `domain` | Recording and task | Forecast |
| --- | --- | --- |
| `wrist` | HoloAssist right-wrist positions during device tasks | Straight-line displacement in 3D, one distance in centimetres |
| `rat` | JS14 camera positions while one rat ran a W-track | Straight-line displacement in 2D, one distance in centimetres |
| `wrist_angle` | WristMotion v3, a person pointing with a supported right wrist | Absolute wrist extension and radial deviation in degrees, 128 stored ticks after the last observed angle |
| `knee_angle` | Reconstructed right and left knee angles during treadmill walking at 0.5 m/s | Both flexion/extension angles in degrees, 15 stored frames later |
| `rat_population` | Five W-track camera positions, optionally with spikes from dorsal CA1 and prefrontal cortex | Straight-line displacement in 2D, one distance in centimetres |

The trained shared model uses the same four-token temporal encoder across five domains. Each recording has its own input and output. Each call uses the clock of its own recording. The rat population study paired camera and firing histories from that one clock. Supply one history per call. [Spatial recording and clock rules](SPATIAL-API.md) · [Source credits](NOTICE.md)

## Forecast two knee angles

Open **index.html** in the extracted download and choose **Right and left knee angles (°)**. To try the same invented pair of waves from the command line, run `node predict.mjs knee-example.json`. To make a forecast from a recording, supply a single JSON object with exactly four fields.

| Input | What to supply |
| --- | --- |
| `domain` | `"knee_angle"` |
| `mode` | `"stride"` repeats the closest past stride. `"raw"` fits a correction from the earlier angles. `"shared"` also uses the model trained on wrist and rat movement. `"scrambled"` fits the same kind of correction after shuffling the shared weights. |
| `frames` | Exactly 240 consecutive nonnegative integer frame numbers, below 2⁵³, from one 60 Hz walk. The first and last samples are 239/60 seconds apart. |
| `kneeDeg` | One pair of finite numbers per frame, in order from oldest to newest. The first angle is right knee flexion/extension and the second is left, both in degrees. |

The JavaScript API and CLI return `angleDeg` in right/left order, `unit`, `axes`, `mode`, `cutoffFrame`, the estimated stride length `periodFrames`, `storedHz: 60` and `horizonStoredFrames: 15`. The target is a quarter second after the last frame. The caller must establish the recording rate, units, joint convention and common recording. Use `knee_deg` in place of `kneeDeg` to run the same JSON in both JavaScript and Python. Supply just one spelling. The Python reader returns a batch. [Complete invented input](knee-example.json)

Across 40,201 forecasts for 12 previously studied people, the shared correction had a mean absolute error of 3.465°, compared with 3.460° from the earlier angles alone, 3.422° using shuffled weights and 3.535° repeating the previous stride. Each person and knee counts equally. The results show no advantage of the trained representation over the two fitted controls. How well these methods predict a new cohort or live movement remains unknown. [Source credits](NOTICE.md)

## Try an invented wrist movement

Put this example in an HTML file beside `shared-motion.js`, then open it in a browser with local-file WebCrypto support. It prints the forecast for a wrist held at 5° extension and −2° radial deviation throughout the invented half-second of history. Positive radial deviation points toward the thumb.

```html
<!doctype html>
<meta charset="utf-8">
<pre id="result"></pre>
<script src="shared-motion.js"></script>
<script>
  const cueTick = 1000, slot = 1;
  const cutoffTick = cueTick + 256 + 128 * slot;
  const record = {
    domain: "wrist_angle", mode: "motion", slot, cueTick, cutoffTick,
    binEndTicks: Array.from({length: 16}, (_, i) => cutoffTick - 240 + i * 16),
    bins: Array.from({length: 16}, () => [0, 0]),
    anchorDeg: [5, -2]
  };
  SharedMotion.forecastMovement(record).then(
    forecast => document.querySelector("#result").textContent = JSON.stringify(forecast),
    error => document.querySelector("#result").textContent = error.message
  );
</script>
```

`forecastMovement(record)` returns a promise. For angles, read `angleDeg` in the order given by `axes` (`extension`, `radial_deviation`). The result also gives `domain`, `unit: "deg"`, `storedHz: 512`, `horizonStoredTicks: 128` and `targetTick`. For a HoloAssist or JS14 record, pass `{domain, intervals}` for prepared measurements or `{domain, cutoffS, samples}` for dense source observations. Read one number from `distanceCm` with `unit: "cm"`. The spatial study measured distances over 0.20–0.30 s around a nominal 0.25 s lead. [Spatial examples](examples.json)

The classic script carries all parameter bytes and requires no network connection. Each input route verifies and decodes its weights on first use. Modules can import the same functions from `predictor.mjs`. The older `historyFromGeometry`, `recentDistance` and synchronous `model.forecast(domain, intervals)` still work through their existing entry points. Obtain `model` with `await SharedMotion.loadSharedMotion()`. Both the module and the loaded model also expose `forecastWristAngles(record)`, which returns the angular fields directly. [Tensor inventory and checkpoint identities](model.json)

## Compare movement with correctly timed firing

Run the JS21 record from the W-track replay with Node.js 22 or newer.

```sh
node predict.mjs population-example.json
```

The camera measured **1.831 cm** between the last input frame and the scoring frame. The shared model predicts **6.424 cm** from movement alone. Add firing from the matching second and it predicts **6.998 cm**. Substitute the earlier trip’s firing and it predicts **7.148 cm**. The same test can favour a different forecast on another trip. [Measured input and aligned firing](population-example.json)

Call `forecastMovement(record)` with `domain: "rat_population"` and one measured history. The result holds `distanceCm` and `unit: "cm"`. Choose `mode: "motion"` for the camera alone or `mode: "combined"` to add grouped firing.

| Input | Units and order |
| --- | --- |
| `cutoffS` | Cutoff on the recording clock, in seconds |
| `priorTimeS` | Five distinct native camera times increasing from oldest to newest |
| `priorXyCm` | Five corresponding [X, Y] positions in centimetres |
| `regionalCounts` | Combined mode needs four [CA1, PFC] spike-count pairs, oldest bin first |
| `unitCounts` | Combined mode needs the two positive counts of recorded units, [CA1, PFC], from this recording |

Use the latest available camera frame at or before each tick, from cutoff −1 s through cutoff in 0.25 s steps. A frame may precede its tick by at most 75 ms. Count spikes in four quarter-second bins on that clock, each open on the left and closed on the right. Supply whole counts in the browser’s safe-integer range. The caller checks the recording identities, native time alignment, region order and source units. The browser checks the shapes, counts, time order and ages. The Python field spellings `cutoff_s`, `prior_time_s`, `prior_xy_cm`, `regional_counts` and `unit_counts` also work. Give each field once.

The frozen movement encoder reads four camera intervals. The motion-only readout uses four speed extrapolations and the encoder’s last state. In combined mode, each region’s firing count first becomes log(1 + spikes per second per recorded unit). The readout then pairs both rates in each time bin with the rat movement correction from that bin’s encoded camera state. Firing enters after attention. To run the earlier-trip control, replace only the four firing pairs with the matched earlier trip from the same recording.

Across 549 windows in three rats held out of these readout fits, the mean absolute errors were 2.805 cm for shared motion, 2.778 cm with aligned firing, 2.804 cm with earlier firing, and 2.870 cm for direct ridge with aligned firing. Each trip counts equally within a rat, then each rat equally. Only KL8 improved on both timing and motion comparisons. A single scrambled encoder with a newly fitted readout scored **2.763 cm**, slightly better than the trained encoder. The direct ridge results on these same test rats were known when we designed the comparison. [W-track recordings](https://doi.org/10.48324/dandi.000978/0.240511.0307)

## What goes into an angular forecast?

Take sixteen consecutive bins from the same trial. Each bin contains sixteen stored samples. Together they cover half a second at 512 Hz, ending at the cutoff sample. The six cue slots 0 through 5 set the target ticks at cue +384, +512, +640, +768, +896 and +1024. Count back 128 ticks from the target to the cutoff. The sixteen `binEndTicks` must run from cutoff −240 to cutoff in steps of 16. The first bin starts at cutoff −255. The wrist encoder refreshes at about 100 Hz on this stored grid. Hardware latency remains unknown.

The caller supplies calibrated bins. Each fitted mode has its own input projection and angular readout.

| Mode | Values in each bin, in order |
| --- | --- |
| `motion` | Mean extension minus anchor extension, mean radial deviation minus anchor radial deviation. Both in degrees. |
| `emg` | The two motion values, then four surface EMG amplitudes in µV. For each forearm pair M1 to M4, subtract R from L on each sample and take the root mean square over the bin. |
| `full` | The six preceding values, then eight signed scalp EEG means in µV, ordered C3, C1, Cz, C2, C4, CP3, CPz, CP4. |

Use the two measured angles at the cutoff for `anchorDeg`. WristMotion source encoder words use `(25 × word / 65535 − 12.5) × 180 / π` degrees, with the second axis reversed. A zero word or an absolute decoded angle above 180° fails the source validity check. The source EDF stores one µV per count, with signed values −32,768 through 32,767. That sets a maximum bipolar difference of 65,535 µV. The API checks source-compatible ranges and the supplied bin ends. Provenance, electrode order, raw timestamps and the derivation of each mean or RMS remain the caller’s responsibility. [WristMotion source study](https://doi.org/10.1038/s41597-026-07287-z)

Select a mode explicitly. Every required value must be finite and every bin must have exactly the selected width. Missing, extra, negative-RMS or out-of-range measurements reject the input. If physiology is unavailable, choose the fitted motion route and supply two columns. For the six-column route, select `emg` and supply the two encoder columns and all four forearm columns. The model standardizes the observed columns with the fitted six-person scales and holds the unused columns at zero **after** standardization.

For a reproducible three-mode check, take `input` from the invented example. Set `mode` and keep the first 2, 6 or 14 entries of each bin as appropriate. The file gives the expected pair of future angles under each fitted mode. [Invented example and reference predictions](angular-example.json)

## Adjust the forecast with the forearm history

First estimate where the wrist will point from its angles alone. Then ask how far to adjust that estimate. Choose `mode: "motion", forearmResidual: "motion"` to base the adjustment on the sixteen angle bins, the two current angles, the two predicted changes and the cue slot. Choose `mode: "emg", forearmResidual: "emg"` to give the correction the four measured forearm amplitudes in each bin as well. Both choices start from the same motion-only estimate. `full` has no fitted correction.

The input clock, channel order and outputs are the same as above. Omit the optional field or set it to `null` for the original direct forecast. The Python field name `forearm_residual` also works here. Supply only one spelling. The browser takes one window with explicit cue and bin-end ticks. The Python reader takes batched arrays and relies on the caller to check their timing.

From this directory, run the included example with Node.js. The calculation stays on this computer.

```sh
node predict.mjs forearm-example.json
```

The invented half-second ends at tick 1512, with the wrist at 10° extension and −2° radial deviation. The program estimates **18.970° extension and −2.058° radial deviation** at tick 1640. Tick 1640 is 250 ms after the cutoff on the stored grid. The delay from physical movement to its recording remains unknown. These numbers are a software check. [Input](forearm-example.json) · [Weights](model.json)

## What the recordings support

In exploratory whole-person cross-validation among six previously used training participants, two-axis angular RMSE was 4.503° for motion, 4.291° with forearm EMG and 4.491° with EMG and scalp EEG. The EEG addition increased error relative to EMG alone. An earlier EMG-corrected model reached 3.549°. Matched frozen-random encoders also gave lower error than the shared pretrained encoder in all three modes. The deployed weights use the registered all-six refit. The training comparison used complete trials selected retrospectively, including future target availability. Generalization to new participants and performance in live use remain open.

In a separate comparison, six development participants each took a turn as the test person. Each correction learned from the other five people's errors on forecasts made without them. Across 1,879 trials and 11,274 overlapping windows, the motion correction reached 4.175° and the correction with forearm signals reached 4.054° (root mean squared error over both axes, each person weighted equally). Four of six people improved with the forearm input. The wrist-specific convolutional model with its own forearm correction still did better at 3.549°. The packaged corrections use all six people. Their accuracy on new people remains unmeasured.

The scalp electrodes measure scalp voltage. The forearm electrodes measure muscle electrical activity. The encoders measure angles. Spinal signalling, peripheral nerve traffic, muscle force and the timing of a causal brain-to-muscle pathway remain unmeasured. The separate spatial study did not establish positive transfer between the human wrist and animal tracking tasks. [WristMotion dataset](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Original spatial study](https://github.com/eliminatenoise/NeuroTranslation/tree/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/models/shared-motion)

The model places no anatomical limit on a forecast. In a deliberately extreme invented example, the forearm correction returned an extension angle of about −1,692°. A human wrist cannot reach that position. The number shows how the calculation can fail far from ordinary movements. Its frequency in real recordings is unknown. [Study, comparison rules and measured errors](https://github.com/eliminatenoise/NeuroTranslation/tree/c8dfb5e641a4832a965f83469b3c38a601bfdb99/models/neurotranslate-0.0/forearm)
