# Why try two output maps?

Moving a wrist to lift an object and balancing on a beam leave two different traces. The model reads movement and muscle recordings from each task. Its final calculation turns what it has learned into a position along three axes. We compared two ways to do that calculation. One assigns a map to the wrist and a map to the pelvis. The other uses the same pair of maps in both studies and gradually shifts the weight from the first to the second as the forecast runs forward. Both store 3,975 fitted numbers. The time-blended version draws on both maps during each trajectory. Both can recognize which study supplied the input.

The body-part maps reduced the average pelvis-path error from 2.645 to 2.582 mm. Extending the last 31.25 milliseconds of marker velocity in a straight line gave 2.583 mm. The two learned approaches produced almost the same average wrist error, 3.878 mm. A model trained on the wrist data alone for the full update budget achieved 3.686 mm. These comparisons used three training seeds on the same 18 balance participants and six wrist participants. Each person’s forecasts came from a model trained on other people. Each seed changes how training starts and which events it samples. [Full results and uncertainty](https://eliminatenoise.github.io/NeuroTranslation/papers/cross-limb-movement/decoder-study/) · [Numerical results](path-maps/scoring/results.json)

## Run the study

Build the development file using the [two original source readers](source/README.md). Each event supplies 625 milliseconds of measured history, the next 125 milliseconds of measured muscle activity and a sequence of 32 marker positions. The same data preparation supports the original and two-map models. The full training and scoring commands below ran on Linux. The included fitted examples also run in a browser through **forecast.html** on the ordinary desktop launchers.

From this package directory, replace the two paths with the location of your prepared development file and a new directory for training outputs.

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
DATA=/path/to/development.npz
OUT=/path/to/replay-output
python -B fit.py prepare --data "$DATA" --output "$OUT"
python -B fit.py fit --data "$DATA" --output "$OUT"
python -B fit.py predict --data "$DATA" --output "$OUT"
python -B path-maps/scoring/score_decoder.py --data "$DATA" --fit "$OUT" --output "$OUT/scores.json"
```

For a single forecast use any of the six supplied JSON checkpoints in **path-maps/**. Their filenames identify seed 1641, the held participant group (f0, f1 or f2), and the output map. The reader uses f0 for its editable invented examples. The measured atlas selects the fold that held out the participant in each recording. The split map is named `separate` and the equal-size early/late map is named `matched`. Both keep the original per-study muscle scales and marker coordinates. [Source and fit design](path-maps/DESIGN.md) · [Scoring protocol](path-maps/scoring/PROTOCOL.md) · [Measured movement atlas](https://eliminatenoise.github.io/Interoceptomics/cross-limb-movement/)
