# Predict a quarter-second of movement

Given one second of past movement, how far will the tracked point move in the next quarter-second? This offline predictor returns the straight-line distance in centimetres from the last observed position. It was fitted to the three-dimensional right wrist in HoloAssist device tasks and the two-dimensional tracked position of rat JS14 on a W-shaped track. Its output gives distance only. The original study compares predictions with measurements taken 0.20–0.30 s after the last observed point.

The model uses four consecutive motion intervals. Both domains pass through the same Transformer. Each domain selects its own learned correction to an estimate based on the last speed. The comparison against models trained on each domain alone did not establish a transfer benefit. The rat measurements come from a single animal and session.

## Use it from a local file

Load the classic script before the code that calls it. The script carries all 5,234 parameter values. Initialization checks their SHA-256 and keeps them in memory. The runtime uses no network request, package installation or GPU.

```html
<script src="shared-motion.js"></script>
<script>
async function predictWrist(intervals) {
  const model = await SharedMotion.loadSharedMotion();
  return model.forecast("wrist", intervals);
}
</script>
```

A module-based app on localhost or HTTPS can import the same functions. Place the two JavaScript files next to each other. The example below uses the invented wrist history in `examples.json`.

```js
import {loadSharedMotion, recentDistance} from "./predictor.mjs";
const example = await (await fetch("./examples.json")).json();
const model = await loadSharedMotion();
const cm = model.forecast("wrist", example.x[0]);  // 0.5241024170144033
const lastSpeedEstimateCm = recentDistance(example.x[0]);
```

## Supply prepared intervals

Pass the domain string `"wrist"` or `"rat"` and a four-row array. The rows run from oldest to newest. Each row has five finite numbers in this order.

| Column | Quantity |
| --- | --- |
| 1 | Straight-line distance from the previous observation, in centimetres |
| 2 | Elapsed source time between those observations, in seconds (0.20–0.30) |
| 3 | Age of the final observation at its scheduled tap, in seconds (0–0.05) |
| 4 | Straight-line distance from two observations back, in centimetres |
| 5 | Cosine of the turn between successive displacements (−1 to 1) |

The first row has zero in columns 4 and 5. A zero-length step gives a turn cosine of zero. Supply all four intervals from the same tracking frame. The prepared-input API checks the same ranges as the NumPy predictor. Frame identity, visibility and the gaps between taps must be verified when preparing the observations. Invalid input raises an exception. The model abstains when history is incomplete.

## Supply observed geometry

```js
const intervals = SharedMotion.historyFromGeometry({domain, cutoffS, samples});
const cm = (await SharedMotion.loadSharedMotion()).forecast(domain, intervals);
```

Pass a dense chronological array from one recording, ending at or before `cutoffS`. Each rat sample has `timeS` and `positionCm: [x, y]`. Each wrist sample has `timeS`, `gridTimeS`, `positionCm: [x, y, z]` and boolean `active`, `valid` and `tracked` flags for the right wrist. A null position marks a missing observation. Supply positions in a fixed frame and source-relative times in seconds. Use positive originating hand ticks when preparing HoloAssist data, subtract the first tick before converting to seconds and convert metres to centimetres. For JS14 use times relative to the trip start and keep each window inside a single camera segment. The rat camera supplies a single clock. An optional rat `gridTimeS` must equal `timeS`.

The five taps end 1.00, 0.75, 0.50, 0.25 and 0 seconds before the cutoff. For each tap the adapter selects the latest eligible observation at or before it. It checks distinct readings, a maximum tap age of 50 ms and a maximum intervening gap of 100 ms. On the wrist, only the first appearance of each native reading can qualify. Elapsed native and frame-grid time across selected taps must agree within 50 ms. Five isolated coordinates alone cannot establish continuous tracking. The study sampled eligible cutoffs every two seconds. Other user-supplied cutoffs can be computed locally, with performance outside the qualified study material unmeasured.

The bundled histories are invented and have no measured outcomes. Their five selected positions document the derivation of each example's prepared intervals. The package contains no recorded human window. Source attribution and reuse terms accompany the files. [Credit and reuse](NOTICE.md)
