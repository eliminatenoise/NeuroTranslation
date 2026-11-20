# Walking, 200 ms ahead

Open `index.html` in a browser, or use the Windows, macOS or Linux launcher beside it. Extract the whole archive first. The page includes its weights, geometry, evaluation and browser inference code in one file and also opens on its own. A current browser with JavaScript is sufficient. The links to the study and original data require internet access.

## Read the walk

A pale dot marks the last known position of each landmark in an invented walk. The green trail behind it covers 40 frames. A dashed line reaches a yellow diamond at the model's forecast. A coral square marks where the synthetic marker ends up 200 ms later. Use **Follow a landmark** to label a point. The table below the scene gives each predicted change along X, Y and Z, plus the three-dimensional miss. Drag the scene, use the arrow keys while it has focus, or choose an orthographic view. **Play stride** advances the example in slow motion.

Speed changes how fast the whole body moves forward. Cadence changes the step rate. The muscle slider scales the eight invented right-leg voltage envelopes independently of the body. The marker-only and constant-velocity predictors ignore that slider. All six choices recompute from the displayed walk. The invented example is a way to inspect the model, and its errors have no clinical or population meaning.

## Read the recordings

The fitting data come from 30 adults in the Rehazenter Adult Walking Dataset. An assessment group of ten other adults supplied three barefoot overground walks each at condition C2. A camera recorded positions every 10 ms. Three left–right marker pairs sit at the lateral ankle, lateral knee and radial wrist. The input also includes two anterior pelvic markers. Eight right-leg surface muscle signals, when used, contribute eight short windows of root-mean-square amplitude.

The model receives 40 consecutive camera frames, spanning 390 ms between the first and last. The target is the later marker position minus its position in the last input frame, 20 frames later. The camera coordinate system is in millimetres with Z up. The original recordings underwent gap filling and two-way filtering. The reported horizon applies to these processed recordings. Prospective or causal operation remains untested.

The results section reports errors on the ten assessment walkers. Its tables compare the Transformer, linear, persistence, constant-velocity and walking-phase forecasts. The control table adds a previous-repeat personal template and the wrong-repeat muscle comparison. Differences within walkers and their bootstrap intervals are shown on matching targets. A separate, exploratory check aligned walking direction before comparing templates. On 815 later-repeat cutoffs the aligned personal template came within 0.9 mm of the combined Transformer. The 95% paired interval included zero. The walker-level table reports the quartiles of the ten mean errors. Source participants 31–40 were previously studied for other outcomes. This release contains aggregate errors and invented examples. Individual participant trajectories remain in the original study.

## Rebuild or rerun

- Run `python3 build.py` to rebuild the same offline page using only the Python standard library (Python 3.9 or newer). Run `python3 build.py --zip ../walking-landmarks.zip` to repack the verified inventory with fixed paths, permissions and timestamps.
- With Node.js, run `node verify.cjs` to execute every browser predictor on the included synthetic fixture and check it against the saved Python outputs.
- With Python and NumPy, run `python3 check_reference.py` to calculate those reference outputs again from the same JSON weights.
- In JavaScript, call `LandmarkPredictor.predict(markers, muscle, model, weights)` from `src/predict.js`. In Node.js, use `require('./src/predict.js').predict`.
- `data/protocol.json` records the target, split, input normalization, controls, metrics and comparison rules. Its source correction in `data/source-clarification.json` takes precedence on muscle-channel availability and clarifies marker names. `data/results.json` holds aggregate scores, coverage and intervals. `data/weights.json` holds the trained parameters. `data/example.json` and `data/example-results.json` are a separate invented parity test.

Pass laboratory XYZ in millimetres as 40 × 8 × 3 numbers. The marker order is left/right ankle, left/right knee, left/right radial wrist, left/right anterior superior iliac spine. A missing point may contain a null coordinate. Muscle input has shape 8 × 8, in microvolts RMS, or may be null. Tokens are 50 ms apart. Each trailing 40 ms window ends at the stored centre of the last camera frame in its token. Muscle channel order is tibialis anterior, soleus, medial gastrocnemius, vastus medialis, rectus femoris, semitendinosus, gluteus maximus and gluteus medius, all right-sided. Missing channels may be null. A finite zero indicates a measured zero. The JS and Python return six XYZ displacements in millimetres. Add them to the last observed marker positions to draw the endpoints.

Model names are `transformer_combined`, `transformer_markers`, `ridge_combined`, `ridge_markers`, `velocity` and `persistence`. The method uses only available frames in the model history, though the source filtering uses both time directions. The illustrated body and its invented future are generated from the same equation. Neither the geometry of the displayed body nor the invented future is a model input.

Read [the author’s licence](DATA-LICENCE.txt) and [credits](NOTICE.md) when reusing the work.
