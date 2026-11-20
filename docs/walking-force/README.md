# Walking force

Estimate the combined vertical load on two force plates in a walkway. For each prediction, a model sees six moving markers, eight muscle electrical signals from the right leg, or both. Its target is a plate reading 100 ms later on the stored recording clock. The interactive walk is invented. The accuracy panel uses real plate readings from people held out of training.

Extract the entire package and open **index.html**, or use **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh**. The HTML contains all six fitted models and works by itself offline. The launchers open it in the system browser.

## Try the same movement twice

1. Leave **Movement and muscle** selected. Change **Signal strength** or **Signal timing** for all eight muscles or for a single muscle. Both curves share the same foot and pelvis paths. The dashed curve keeps the original muscle signals.
2. Choose **Movement only**. The curves now coincide for every muscle setting. Under **Change both marker paths**, move the walker along the walkway. Both predictions can change together.
3. Drag the time slider, use its arrow keys, or tap a point on the graph. Open **See the current eight inputs** to inspect the numbers behind that forecast. The current time marks the target. Each input history ends 100 ms earlier on the example clock.

**Save this input and prediction** writes the two complete input histories, their exact fitted-file hash, settings and predicted loads to JSON. **Save curve data** writes all 49 forecasts to CSV. The two **Save … plot** buttons produce standalone SVG figures. The initial [invented force plot](invented-load.svg) and [recorded assessment plot](held-walkers.svg) are included. Every force curve from the editor is a fitted model’s response to invented data.

## What the recordings showed

Of 30 people designated for fitting, 25 supplied 62 eligible walks. Of the next 10 designated for assessment, eight supplied 17 eligible walks and 1,297 overlapping predictions. The remaining 10 people stayed unopened. All retained trials had independently documented contacts on both instruments. Source processing smoothed the recordings in both time directions and could turn missing or small forces into zero. Force exerted elsewhere on the floor remains unknown.

On the eight held-out walkers, the movement-only Transformer averaged **65.19 N** absolute error. The movement-plus-muscle Transformer averaged **70.20 N** and the nonlinear movement-only ridge **91.25 N**. Carrying forward an earlier plate reading averaged **63.43 N**. That last comparison has access to force, which the six interactive models never receive.

A wrong-repeat control kept each marker history and used right-leg signals from a similar pose in a different walk by the same person. Six walkers contributed paired data. Correctly paired signals averaged **72.20 N** error against **73.28 N** when swapped. The paired 95% interval for the difference ran from −7.31 to +4.67 N. Only the comparison with nonlinear marker ridge met the prespecified improvement rule. These walks do not establish an added benefit from muscle signals. The source and model limits apply to both plots. [Source credits and licences](NOTICE.md)

## Reproduce a saved prediction

Node needs no extra packages. From the extracted directory run the demo or replay a saved JSON file.

```sh
node predict.cjs
node predict.cjs walking-force-input.json
```

A single history is also accepted as an object with `rows`, `method` and `modality`. Use `ridge` or `transformer` with `markers`, `emg` or `combined`. Each history contains eight 30 ms bins, oldest first. Every row has 40 entries.

| Columns, starting at zero | Input |
| --- | --- |
| 0–17 | Six XYZ marker positions (metres from the midpoint of the plates), in the order L_FCC, L_FM2, R_FCC, R_FM2, L_IAS, R_IAS |
| 18–23 | One availability flag, 0 or 1, for each marker |
| 24–31 | Right-leg root mean square surface voltage (µV), in the order tibialis anterior, soleus, medial gastrocnemius, vastus medialis, rectus femoris, semitendinosus, gluteus maximus, gluteus medius |
| 32–39 | One availability flag per electrical channel |

Use zero with the matching flag cleared for an unavailable input. Training-set mean imputation makes the missing numerical value zero after standardization. Observed numerical features are scaled with training statistics and clipped to ±8 standardized units. The six flags for movement and eight flags for muscle travel with their respective inputs. Output is newtons, clipped at zero. The nonlinear marker control needs sample windows from the source data, so its result is reported and its examples stay outside this distribution.

## Rebuild

The following commands work from this directory in the full NeuroTranslation repository. The standalone HTML build uses the Python standard library. Re-exporting the fitted arrays and checking parity also require NumPy, Node, and the published model source under `models/walking-force/`.

```sh
python export.py ../../models/walking-force ../../models/walking-force/results.json
python build.py
python -B verify.py ../../models/walking-force
```

The exporter checks the six source weight hashes and the assessment hash. Verification compares JavaScript with the model’s NumPy implementation on 85 invented histories covering normal, missing and clipped inputs. The threshold is 0.002 N. On a clean page, **Save force plot** and **Save error plot** recreate the two default figures. The collected screen values are rounded for display. The CSV, JSON and Node exports preserve the underlying numeric predictions.
