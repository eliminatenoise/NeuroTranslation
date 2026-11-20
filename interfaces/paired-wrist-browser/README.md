# Predict a wrist movement in a browser

Given the previous half-second of a person’s wrist angles, this model predicts how far the wrist will bend and tilt a quarter of a second later. You can compare three versions. One reads wrist angles alone. The other two also use electrical recordings from the forearm or from both the forearm and scalp. Each returns a predicted angle in degrees and its estimated variance in square degrees.

To see an actual recording next to the model predictions, open the game preview and press **M**. Choose the forecast below the traces. [Game preview for review](https://github.com/eliminatenoise/NeuroSurge/pull/2) · [What the models learned](../../benchmarks/paired-wrist-forecast/)

The folder `public/` contains the complete browser module, fitted weights, scales, attribution and exporter. A caller imports `public/predictor.mjs` and awaits `loadPairedPredictor(mode)`. Its `predict(payload)` accepts the published predictor's schema and computes both angles and variances synchronously. Use a loopback or HTTPS origin for the browser's SHA-256 verification. [Usage, inputs and licences](public/NOTICE.md)

## Replay the synthetic qualification

The oracle comes from calling the published `predict.py` on 36 invented windows with all three original fits. Six offsets are crossed with zero, flat and varying histories and single-feature pulses. The pulse checks demand a change when that channel is in the selected fit and the same output when it is absent. No participant file is needed.

Use a Python environment containing the benchmark's pinned NumPy and CPU PyTorch, Node.js, Chromium and ChromeDriver. Run from this folder. The final command starts and closes a loopback test server and a temporary headless browser.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B reference_fixtures.py ../../benchmarks/paired-wrist-forecast fixtures.json
node check_node.mjs
python -B check_browser.py
```

Angle agreement is checked against an absolute tolerance of 0.00005° regardless of anchor size. Variance agreement is checked against 0.00005 deg² plus eight parts per million of the PyTorch value. Float32 reductions in attention, normalization and the output head can accumulate round-off differently across engines. Converting log variance back to deg² makes the absolute difference grow with the variance, which is why the test includes a relative term. These are numerical port tolerances, separate from the model's error on measured movement.

The browser references only local model assets, verifies the selected binary, and caches the fit across concurrent callers. The check confirms no weights load at import and exactly one body per selected mode. `node-check.json` and `browser-check.json` contain the measured maxima and load, first-prediction and steady timings. These timings describe singleton computation on the test host. The game, camera, acquisition latency and other devices are outside the measurement.
