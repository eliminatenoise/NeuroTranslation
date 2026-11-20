# Rebuild the offline movement predictor and rat replay

The build reads the released NeuroTranslate movement checkpoint and the original rat transfer study. It exports the stored numbers and assembles a single saved HTML file. It requires Python 3.10 or newer and NumPy. Running the finished viewer only requires a browser that supports WebCrypto on local files or HTTPS.

Run these commands from this directory inside a complete NeuroTranslation checkout. Paths can be made absolute when building elsewhere. Use the release edition containing the rat population adapter in `models/neurotranslate-0.0/population/` and the W-track replay inputs in `models/population-motion/`. From the generator directory, run:

```sh
python -B build.py --model ../neurotranslate-0.0 --direct ../population-motion --out build
```

The build checks each scientific input against its SHA-256 entry in `src/inputs.json`. It checks the old tensor groups against their original manifest, copies all 51 numerical arrays from the checkpoint in their stored precision and verifies their shapes and lengths. The ZIP uses a fixed timestamp and file order. The only dependencies that it reads outside this generator are the public files named in the input manifest.

| Output | Use |
| --- | --- |
| `build/viewer/index.html` | Open or copy this one file. It contains the trip, both forecast calculations and licence texts. |
| `build/runtime/` | Use the classic script or import the ES module. The directory includes source credits and the table of SHA-256 checksums. |
| `build/movement-browser.zip` | Extract the runtime into an empty folder. Run `node predict.mjs population-example.json` there with Node.js 22 or newer. The first JS21 record returns 6.998122304990752 cm to floating-point precision. |

In the replay, both models receive the same five camera frames. Compare the two trip timings, reveal the measured endpoint and move to another cutoff. The page includes all 12 eligible cutoffs from the displayed trip. The results tables cover 549 forecasts across three test rats.
