# Forecast pelvis movement in a browser

[Open the forecast](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/missing-pelvis-markers/run/). Change which markers are visible and see how a fitted model changes its estimate of how far the pelvis will rise or fall in the next 100 milliseconds. The default numbers are invented. You can also paste prepared readings into the page. The page performs the calculation in your browser.

## Prepare readings

Supply an object with `heights_mm` and, if available, `force_log_change`. The example below includes five sets of heights measured 50 milliseconds apart. `null` means a missing reading. Keep at least two positions at 0 milliseconds.

```json
{
  "heights_mm": [
    [698, 694, 673, 668],
    [null, 702, 680, 674],
    [null, 710, 687, 680],
    [722, 718, 694, 686],
    [730, 726, 701, 692]
  ],
  "force_log_change": [0, 0.09, 0.14, 0.11]
}
```

- Arrange the rows from −200 to 0 milliseconds. The four columns are left front, right front, left back and right back. Heights are in millimetres along the calibrated vertical axis. These markers are placed over four bony landmarks on the pelvis. The front pair are the anterior superior iliac spines and the back pair are the posterior superior iliac spines.
- Use four force values only if you have synchronised force plates with readings from both feet. Add the vertical force under both feet, then average that total over the 40 milliseconds ending at each of −150, −100, −50 and 0 milliseconds. Raise any mean below 1 newton to 1, take the natural logarithm of each mean, then subtract the first logarithm from all four values. The first value is always 0. Omit the field or leave the checkbox off when no plate data is available.
- The two outputs give a change in height in millimetres from 0 to +100 milliseconds. A positive value means up. The four-marker centre averages all four marker heights. The back-marker centre averages the two back heights. These are different targets, so the two values can differ even when the same markers are visible.

A regular webcam returns positions in an image. To use webcam measurements here, first recover the four named marker heights in millimetres at the required times. The study measured performance on optical-marker recordings with markers deliberately hidden. It did not test a live webcam or accuracy during real camera dropouts. See the [pelvis marker study](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/missing-pelvis-markers/) for how the models were tested and where simpler forecasts performed better.

## Use the predictor from code

Serve this directory over HTTPS or a localhost web server. The browser verifies the SHA-256 of the bundled weights before it runs them. `engine.mjs` can also load the same files in Node.js with `decodeModel(manifest, arrayBuffer)`.

```js
import {loadPelvisModel} from "./engine.mjs";

const model = await loadPelvisModel();
const forecast = model.predict({heights_mm: [
  [698, 694, 673, 668],
  [null, 702, 680, 674],
  [null, 710, 687, 680],
  [722, 718, 694, 686],
  [730, 726, 701, 692],
]}, "mixed");

console.log(forecast.estimates.four_marker_centre, forecast.estimates.back_pair_centre);
```

`"mixed"` selects models trained with both complete readings and deliberately hidden markers. `"complete"` selects models trained with all four markers available. Both ensembles give the same two outputs. The [offline package with launchers](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/missing-pelvis-markers/NeuroTranslate-marker-availability.zip) includes the original fitted weights and Python forecast. `model.json` records the original revision and the hashes of the browser weights and the original bundle inputs. The code and model are available under [CC0](LICENSE.txt). The original study links source datasets and their own licences.
