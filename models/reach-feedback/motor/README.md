# Where does the hand go in the next tenth of a second?

Open the last 200 milliseconds of one recorded reach. The cameras have tracked the hand and elbow, the handle encoder has tracked the hand-held device, and electrodes in somatosensory cortex have counted spikes. A controller has also recorded the times of the go cues. How much of the next movement can these observations predict?

Run the example with Python and NumPy from this directory.

```sh
python forecast.py
```

The ten output rows are displacements 10, 20, …, 100 ms after the last known position. The first three columns give hand XYZ in metres, the next three elbow-marker XYZ in metres, and the last two handle XY in centimetres. Add each row to the last observed position to recover the corresponding forecast position on the recording grid. The example comes from the training set and lets you check the software. Its recorded history, sorted channel identities and reference outputs are in `recorded-example.json`.

The default forecast uses the full Transformer with seed 17. Each of the five input combinations has three trained Transformers and one ridge regression. Supply a different coefficient file to replay another fit.

```sh
python forecast.py recorded-example.json --weights weights/pose_cue-41.npz
python forecast.py recorded-example.json --weights weights/full-ridge.npz
```

| Filename stem | Measurements available to the fit |
|---|---|
| full | Past marker and handle positions, cortical counts, elapsed go cues |
| pose_cue | Past marker and handle positions, elapsed go cues |
| spike_cue | Past cortical counts, elapsed go cues |
| spikes_only | Past cortical counts |
| cue_only | Elapsed go cues |

A replacement JSON record needs the same field layout and sorted channel identities as the example. Supply 20 oldest-to-newest rows of 8 positions, 23 counts and 3 cue fields. The cue fields are the number of go events strictly before the bin, seconds since the latest such go (zero before the first), and an indicator that a go has occurred. Each ablation removes its excluded inputs internally. A stimulus location or target direction is absent from this recording.

The model learned from workspace 1 of a single macaque session. Its weights cover all 198 retained training sequences. Each sequence has equal total training weight, even when it contains several eligible go cues. The elbow marker describes a point on the forearm near the elbow. The released marker positions are shoulder-relative and underwent offline processing. The handle encoder reports in its own planar coordinate system. Agreement here measures prediction on that processed recording grid. Live latency, a different subject and other tasks each require their own measurements.

`model.py` contains the PyTorch Transformer and weighted linear fit. `train.py` reproduces the frozen training recipe from the exact source shard. Install PyTorch as well as NumPy to refit, use a new empty output directory, and keep native math pools at one thread for the reference route.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python train.py TRAIN.npz fit --fold 5 --threads 1 --device cpu
```

Folds 1 through 4 fit earlier pieces of the training session and predict the next distinct piece. Fold 5 refits all five input combinations on the complete training set. The evaluation compares each seed separately before averaging errors. A single rounded example cannot stand in for that comparison.

Chowdhury, Glaser and Miller recorded these data and released the source under CC0. The member used here is `C_20170907_TRT_TD.mat`, SHA-256 `6062b7e8dacdf46f7eee465bd844ffe1fb3b7ce0793c34d3e4d106be357f4746`. [Primary study](https://doi.org/10.7554/eLife.48198) · [Dryad data](https://doi.org/10.5061/dryad.nk98sf7q7)
