# Forecast movement from one recording

How far will a tracked point move? Where will a wrist point? Give the model one movement history and it returns the quantity that instrument measured.

| `domain` | Recording and task | Forecast |
| --- | --- | --- |
| `wrist` | HoloAssist right-wrist positions during device tasks | Straight-line displacement in 3D, one distance in centimetres |
| `rat` | JS14 camera positions while one rat ran a W-track | Straight-line displacement in 2D, one distance in centimetres |
| `wrist_angle` | WristMotion v3, a person pointing with a supported right wrist | Absolute wrist extension and radial deviation in degrees, 128 stored ticks after the last observed angle |

All three use the same four-token temporal encoder. Each recording has its own input and output. A camera track and a wrist-electrode trial have separate clocks and subjects. Supply one history per call. [Spatial recording and clock rules](SPATIAL-API.md) · [Source credits](NOTICE.md)

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

## What the recordings support

In exploratory whole-person cross-validation among six previously used training participants, two-axis angular RMSE was 4.503° for motion, 4.291° with forearm EMG and 4.491° with EMG and scalp EEG. The EEG addition increased error relative to EMG alone. An earlier EMG-corrected model reached 3.549°. Matched frozen-random encoders also gave lower error than the shared pretrained encoder in all three modes. The deployed weights use the registered all-six refit. The training comparison used complete trials selected retrospectively, including future target availability. Generalization to new participants and performance in live use remain open.

The scalp electrodes measure scalp voltage. The forearm electrodes measure muscle electrical activity. The encoders measure angles. Spinal signalling, peripheral nerve traffic, muscle force and the timing of a causal brain-to-muscle pathway remain unmeasured. The separate spatial study did not establish positive transfer between the human wrist and animal tracking tasks. [WristMotion dataset](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Original spatial study](https://github.com/eliminatenoise/NeuroTranslation/tree/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/models/shared-motion)
