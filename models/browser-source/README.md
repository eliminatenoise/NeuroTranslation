# Rebuild the offline movement predictor

Open **index.html** in the extracted ZIP to forecast movement from one recording. The included runtime also works from Node.js 22 or newer. For example, run `node predict.mjs knee-moment-example.json` in the top-level folder. The example contains invented waves. The packaged source can rebuild the predictor, the standalone page and the ZIP offline with Python 3.10+ and NumPy 2.x.

From this generator’s directory (`source/models/browser-source` in the ZIP), run

```sh
python -B build.py --model ../neurotranslate-0.0 --out build
```

In a complete NeuroTranslation checkout, add `--direct ../population-motion` to also generate the separate rat-trip viewer at `build/viewer/index.html`. The offline package contains the model and the sources needed for its own products. The separate rat replay reads the published camera, firing and study files from the checkout.

The generator checks scientific input files against `src/inputs.json`. All 65 numerical arrays from the preceding movement checkpoint keep their original stored values. This version adds 35 arrays for the knee moment models. The generator verifies both knee exports and keeps the two studies’ different encoder permutations separate. The checkpoint hash and tensor identities appear in `runtime/model.json`. Archive members come from an explicit list, in a fixed order with fixed timestamps.

| Output | Use |
| --- | --- |
| `build/index.html` | Open directly in a browser with local-file Web Crypto support. |
| `build/runtime/` | Use the classic JavaScript, the ES module or the Node CLI. The directory includes input examples, credits and file checksums. |
| `build/movement-browser.zip` | Extract the viewer, launchers, runtime and rebuild sources. |
