# Can a model trained on one day forecast next week's reach?

A macaque reaches for a target. A camera track tells you where its arm has been, but where will it be a tenth of a second from now? Here the history comes from optical markers on the hand and elbow, an encoder on the handle, and the timing of the go cue. The network learned those movements on September 7. A second, smaller network learns how much to correct its forecast when it also receives recent spike counts from electrodes in the animal's somatosensory cortex. The forecast ends 100 milliseconds after the last observation. [Recording](https://doi.org/10.5061/dryad.nk98sf7q7) · [Chowdhury, Glaser and Miller](https://doi.org/10.7554/eLife.48198)

## See one reach

From this folder run the following command with Python and NumPy installed. It uses one real September 7 training example and prints the predicted and measured hand displacement at ten times. Use the September 14 scores to judge transfer to a different day.

```sh
python example.py
```

The model starts 5 sample intervals after the second, third or fourth go cue. It sees only the 20 earlier samples, 10 milliseconds apart. The cameras record the hand and elbow in shoulder-relative coordinates. Each of the first six output columns gives displacement in metres. The last two columns give the native planar handle displacement in centimetres. Add the last known position to a displacement to recover the predicted position in that instrument's frame.

## Run it on recorded histories

Call `replay.pooled_history(all_history, all_guide)` with a batch of 20-bin local spike histories and the recording's own two-column electrode/sort guide. It returns four 50-ms counts on each of the 37 shared acquisition contacts. Every exported column for a contact contributes once, including counts outside the individually sorted groups. This design needs no claim that a particular neuron was recorded again seven days later.

```python
from replay import pooled_history, predict

counts = pooled_history(all_history, all_guide)
movement = predict(pose, cue, counts)
pose_only = predict(pose, cue, None, arm="pose")
```

Each array passed to `predict` begins with the number of examples. Position histories have shape (examples, 20, 8). Cue histories have shape (examples, 20, 3) and use the recording reconstruction's prior-go count, elapsed time in seconds and indicator that a prior go cue exists as defined in its source. The contact array has shape (examples, 4, 37), in ascending channel order. Full and pose models each average three independently trained networks. The linear control uses `family="ridge"`.

## Refit and test

Rebuild the three arrays in the accompanying recording reconstruction. Install PyTorch for refitting. Python with NumPy is sufficient to score the supplied weights. Run from this folder, using fresh output directories.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python reproduce.py refit ../arrays/train.npz my-weights
OPENBLAS_NUM_THREADS=1 python reproduce.py score ../arrays/block1.npz ../arrays/block2.npz my-scores
```

The first command reuses the three frozen September 7 body-and-cue Transformers and fits the small corrections on all 519 September 7 windows, with each of the 198 trials carrying equal weight. The second command uses the supplied fitted weights by default. Add `--weights my-weights` to use your refit. It returns forecasts for every window, errors for hand, elbow and handle, and paired intervals on complete trial sequences. Missing histories and missing earlier donor trials remain visible. Each recording block keeps its own clock and trial numbers.

The body-only correction has the same 24-neuron hidden layer, input width, 80 outputs and training schedule as the correction that also received cortical counts. To check whether the timing of those counts matters, a third calculation keeps the true arm movement history and substitutes counts from the last earlier eligible trial with the same go-cue ordinal in the same block and workspace. Two simpler forecasts keep the last position fixed or carry the last five samples' velocity forward.

The first day supplied every fitted weight and scale. The second day supplied two workspaces from one returning animal. Contacts can retain their acquisition labels while recorded neurons, thresholds and response gains change. The optical tracking, spike sorting and clocks come from a processed recording. These results describe offline movement prediction.
