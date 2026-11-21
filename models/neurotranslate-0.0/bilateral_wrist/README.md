# Where will each wrist land?

Take the last half-second before a movement. A camera gives the image positions of both wrists, elbows and shoulders. Eight electrodes give the voltage at the surface of the brain. The model reads that history and predicts two points for each wrist, eight and fifteen camera frames beyond its last observed position.

From the extracted NeuroTranslate 0.0 folder, with Python 3 and NumPy installed, run:

```sh
python predict.py bilateral_wrist/example.json
python predict.py bilateral_wrist/example.json --wrist-case 2 --wrist-modality pose --wrist-treatment direct
```

The first invented movement puts the predicted right wrist at (52.10, 35.34) and the left at (−49.90, 21.37) pixels after eight frames. After fifteen frames the predictions are (51.79, 36.85) and (−49.49, 23.87). Coordinates use the original camera origin. In the output, `absolute_endpoint_px` and `displacement_px` each have three axes in order: horizon (+8, +15), wrist (right, left), coordinate (x, y). Add each displacement to that wrist's `last_wrist_px` to recover the absolute forecast. [Full-precision example forecast](expected.json)

## Make a prediction from your own recording

A `wrist-forecast-v1` file holds the earlier history and the fitted parameters for that task. To export one complete bilateral example from locally prepared study archives:

```sh
python bilateral_wrist/export_case.py weights.npz inputs.npz private-case.json --row 0
python predict.py private-case.json
```

Both commands run locally. Keep fitted participant parameters and individual histories private. Use the study's versioned AJILE12 preparation and fitting instructions for real recordings. For another compatible fit, match the contact order, camera convention, units, sampling, window alignment and numeric schema. A valid JSON shape alone says nothing about performance on another recording. [Study source and reproduction](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/human-wrist) · [AJILE12 recording source](https://doi.org/10.48324/dandi.000055/0.220127.0436)

- `ecog_uv` has 250 earlier samples at 500 Hz × 8 recorded cortical contacts in microvolts. For AJILE12 these are GRID ranks 0, 9, 18, 27, 36, 45, 54 and 63 in recording-column order.
- `pose_px` has 15 earlier frames at 30 Hz × 2 sides (right, left) × 3 joints (wrist, elbow, shoulder) × 2 image coordinates (x, y). Camera and electrode windows both end before the annotated movement. Keep the original camera coordinates, including their signs.
- Each example needs finite measurements for both arms, a varying voltage window and no all-zero voltage row, including for the pose-only comparison. The study scores eligible arms individually. An optional numeric `future_px` reference from the browser exporter is discarded before either model runs.
- `weights` carries the numeric scaling constants and the seed-17 models for each side, treatment and input condition. `cases` accepts one to eight paired histories. Select one with `--wrist-case` (counting from zero). The browser accepts files up to 2 MiB. The Python API accepts the same record via `predict_record(record, wrist_case=0, wrist_treatment="anchored", wrist_modality="full")`.

## What does the model learn?

Each wrist has its own fitted Transformer. It divides the history into five consecutive groups. Each group supplies ten measurements of arm geometry and motion, eight mean voltages and eight voltage amplitudes. A single causal attention layer combines those groups before predicting both horizons. The two wrists share the same computation and input recording. Their fitted weights are separate, as are those of the full and pose-only models. This task runs alongside the other NeuroTranslate 0.0 tasks using its own parameters. The older movement checkpoint has no role in its predictions.

`--wrist-treatment anchored` extends the wrist's observed movement with a fitted damping factor and learns a bounded correction. `direct` learns the entire displacement. `bounded_zero` learns a bounded correction from a stationary starting forecast. `--wrist-modality full` reads pose and earlier voltage. `pose` selects the separately fitted pose-only branch. Neither branch produces a brain recording from camera movement.

The AJILE12 study trained on 60 selected right-wrist movement events from one recording day and assessed 58 events on a later day in the same person. Both wrists were tracked during those right-wrist events. Adding earlier voltage gave the anchored seed-17 fit a smaller mean right-wrist error at eight frames (29.68 versus 30.03 pixels). Replacing the matching voltage with voltage from a different event could do as well or better. Neither wrist showed a consistent advantage from the matching voltage. Detector pixels allow comparison in this camera view. They do not establish physical distance, decoded intent or transfer to another person. [Study and comparisons](https://eliminatenoise.github.io/NeuroTranslation/human-wrist/)

## Rebuild the invented example

The example's parameters come from 64 generated two-arm movements (motion seed 19037). Three oscillators drive invented joint positions and invented voltage channels. Each of twelve branches starts with seed 17 and receives 48 full-batch AdamW updates. Four new movements (motion seed 33117) supply the earlier histories in the download. Their future coordinates are omitted. With NumPy and PyTorch installed, regenerate the JSON at a new path:

```sh
python bilateral_wrist/simulate.py rebuilt.json --threads 1
python predict.py rebuilt.json
```

The Python reader compares the fitted parameters and the selected earlier history separately with the bundled simulation's fingerprints. “Local, unverified origin” means the numbers differ from that known example. The label makes no inference about who supplied them or how they were measured. [Generator](simulate.py) · [Fitting equations](demo_math.py) · [Example fingerprints](provenance.json)
