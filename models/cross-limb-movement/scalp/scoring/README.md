# Reproduce the scalp forecast comparison

The scorer compares predicted muscle activity and marker paths with recorded measurements for people left out of each fit. The primary table in `results.json` contains four differences in error, two per study. Negative values favor adding the past scalp measurements. Read `RESULTS.md` for the findings and `PROTOCOL.md` for the selection rule fixed before fitting.

Use Python and NumPy in the training environment. Rebuild the development windows, scalp histories, archived movement/muscle forecasts and scalp-augmented forecasts using their respective source and fit instructions. Keep the raw caches and individual predictions locally. Pass the accepted input and scoring source files explicitly. Keep `PROTOCOL.md` beside `score_fusion.py`.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python score_fusion.py \
  --data private/muscle-motion/development.npz \
  --scalp private/scalp/development.npz \
  --input-source path/to/scalp_inputs.py \
  --metrics-source path/to/path-maps/scoring/score_decoder.py \
  --fit private/scalp-fits --original-fit private/movement-fits \
  --out reproduced-scores.json
```

The input code provides exact source masks and the previously fixed earlier-trial assignment. The scorer checks those masks against original channel names, checks donor membership and nonoverlap on the native clocks, verifies the checksums for both development inputs and checks every forecast's receipt, row order, fold and support. It compares the archived movement/muscle forecasts directly with the three reused prediction arrays.

Inside each study, `central_minus` gives the two models' scores on the same events, their paired differences, and the numbers of people and events included and excluded. `primary_subgroups` describes the central and reference errors by task and observed sites. A two-person group can contribute means. A one-person group contributes counts only. `availability` gives counts per site or muscle by condition. Axis indices 0, 1 and 2 follow the study's `axes` list. Positive axis bias means the predicted coordinate exceeded the observed coordinate on average. `seed_means` follows the listed seed order. Bootstrap intervals resample whole people after seed averaging.

The balance measurements are from Steven M. Peterson and Daniel P. Ferris. The grasp-and-lift measurements are from Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin. [Balance recordings](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [WAY grasp-and-lift recordings](https://doi.org/10.6084/m9.figshare.c.988376.v2)
