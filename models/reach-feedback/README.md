# Can a forecast of the arm predict what sensory cortex will do next?

Stop a macaque reach five samples after its second, third or fourth go cue. You have 200 milliseconds of hand, elbow and handle positions, counts from 23 sorted cortical units, and the go signals the controller has already sent. Predict the next ten positions. Now give that prediction to a second model and ask how many spikes each unit will produce in the following 100 milliseconds. Does the second model gain anything over reading the same history directly?

**On the held-out reaches, the movement forecast did not establish an advantage.** In the second workspace it raised the mean error in spike-count predictions. The earlier cortical spikes helped forecast where the hand would end up there, while the error at the elbow increased. These are predictions of recorded motion and activity in one rhesus macaque, C, on 7 September 2017. A second workspace tests another region of the same apparatus on the same day. [Original experiment](https://doi.org/10.7554/eLife.48198) · [CC0 measurements](https://doi.org/10.5061/dryad.nk98sf7q7)

## Try one reach

Open `reader/index.html` in a browser, or use the launcher for Windows, macOS or Linux after extracting the whole package. To calculate a fresh prediction with the supplied weights, use Python 3.11 or later and NumPy. Run these commands from the directory containing this README.

```sh
python -m pip install numpy
python predict_reach.py
python predict_reach.py examples/transfer.json --seed 41 --output reach.json
python predict_reach.py examples/transfer.json --family regression
python check_examples.py
```

The default example is the second go of original trial 520, a held-out reach in workspace 1. The program prints the hand and elbow endpoint displacements in millimetres, the handle endpoint in centimetres, and expected spike totals for each electrode channel and sort code. The optional JSON output preserves all ten movement samples in their source units and both ten-bin count forecasts. Each count is the expected number of spikes in a 10 ms bin. Divide by 0.010 to express it in spikes per second.

The same `pose`, `spikes` and `cue` histories enter both stages. The code forms the first model’s displacement forecast and passes it straight to the second model. Each Transformer count head receives the path from its matching motor seed. The count regression receives a ridge regression path. The comparison head gets only the history. The command rejects a different electrode/sort order. Its numerical inputs are fully specified in the [source guide](source/RECONSTRUCT.md).

For one record, supply the three history arrays in oldest-to-newest order and the 23 channel/sort pairs in `unit_guide`. Each of the 20 position rows contains shoulder-relative hand XYZ and proximal-ulna XYZ in metres, followed by robot handle XY in centimetres in its own frame. Spike inputs are nonnegative integer counts. Each cue row gives the number of go events strictly before that bin, seconds since the latest such event (zero before the first), and an indicator of any previous go. The four examples also contain later measurements for scoring. The forecast command reads only the histories and unit identities. Files in `examples/` were selected by timing and trial identity before numerical evaluation.

## Where the forecast helped

| Change in mean error | Later reaches in workspace 1 | Reaches in workspace 2 |
|---|---:|---:|
| Count deviance per unit, predicted movement plus history minus history alone | +0.00347 [−0.02320, +0.02774] | +0.01002 [+0.00113, +0.01846] |
| Count deviance per unit, correct predicted path minus an earlier reach’s predicted path | −0.01940 [−0.03747, −0.00476] | −0.00329 [−0.00802, +0.00241] |
| Hand endpoint error, adding past spikes to pose and cues (mm) | +0.346 [+0.211, +0.581] | −0.964 [−1.102, −0.861] |
| Elbow-marker endpoint error, adding past spikes to pose and cues (mm) | +0.341 [+0.264, +0.467] | +0.305 [+0.247, +0.359] |

Negative differences favour the added input. Brackets give paired 95% intervals from 5,000 resamples of consecutive blocks of eight original trials. Each original has equal weight and the three seeds have equal weight in the mean loss. The two count comparisons use the same 113 reaches from 42 trials in workspace 1 and 822 reaches from 315 trials in workspace 2. The motor comparisons use all 116 and 825 eligible reaches respectively. The spike-count criterion required a reduction against both comparisons in each workspace, and the transfer motor criterion required a reduction for both hand and elbow. Neither criterion passed. On matched transfer reaches even the training mean count gave lower deviance (1.1595) than direct history (1.1834) or history with a predicted path (1.1934).

A separate model can feed its last predicted position back into its next calculation. Against the model that predicts every horizon in parallel, this lowered transfer hand endpoint error by 0.566 mm and count deviance by 0.0201 per unit, and raised elbow endpoint error by 0.385 mm. It missed its three-outcome criterion too. The model feeds its own numbers back into a calculation. A biological feedback experiment would need an independently measured or manipulated signal.

## Follow the experiment

- [Motor fits](motor/README.md) include all five input combinations, three Transformer seeds per combination and five ridge regressions. The training and scaling details are in [Motor methods](motor/METHOD.md).
- [Count fits](cortex/README.md) include seven input combinations, each with three Transformer seeds and a log-link regression, plus persistence, training-mean and go-ordinal rate controls. The retrospective `privileged` comparison alone receives measured future displacement. [Count methods](cortex/METHOD.md)
- [Joint model](joint/PROTOCOL.md) includes parallel estimates, a recurrent state, a recurrent state with predicted movement feedback, and two single-objective comparisons. For example, run `python joint/portable.py joint/weights/rollout-17.json examples/within.json`.
- [Results](results/) contain the training, validation and both held assessments. Each split includes errors in the endpoint and trajectory, signed components, count errors by time and sorted unit, controls, per-seed losses, paired uncertainty and the original pass/fail decisions. The separate joint files carry that experiment’s comparisons. [How errors are scored](scores/METHOD.md)

The source lacks the exact target coordinates. Eventual reward, later cues and sufficient recording time determine eligibility. The first-target rule left zero validation reaches. Hand tracking used offline reconstruction, the handle had bidirectional filtering, and spike sorting was offline. The task supplies no direct measurement of a peripheral nerve or spinal pathway. The forecast describes this recording grid. A causal interpretation, a real-time instrument and transfer to another animal each need further evidence.

## Rebuild everything from the recording

With Python 3.11 or newer, NumPy, SciPy and PyTorch installed, download the one checksum-verified MATLAB member or reuse your copy. The downloader also accepts the official ZIP via `--archive`. With the MATLAB member and dependencies available locally, the entire reconstruction runs offline. Start from the directory containing `reproduce.py`.

```sh
python -m pip install numpy scipy torch
python source/fetch.py input
python reproduce.py --mat input/C_20170907_TRT_TD.mat --out reproduction
```

Supply a new or empty output directory. The driver extracts training data, fits the four chronological motor folds and the all-training refit, trains the count and joint models, then freezes the fits. Each count-training forecast comes from a motor model fit on earlier original trials. The first 40 trials supply the initial fit and have no out-of-fold forecast. This leaves 408 reaches from 158 trials for count training. The driver scores training first, releases validation next, then reconstructs and scores both held workspaces under their shared release. It rebuilds the matched earlier-donor control as well as the three simple rate controls. The complete scores are compared against the published values, including case counts, interval endpoints and decisions.

The reference used Python 3.13.15, NumPy 2.5.5 and SciPy 1.18.1 for extraction, regression and scoring. The neural fits used Python 3.14.8, NumPy 2.5.3 and PyTorch 2.14.0 with CPU tensors. To use separate environments, add `--torch-python /path/to/second/python` to the reproduction command. All training runs on the CPU. The final comparison uses absolute and relative tolerances of 0.00002 for floating-point summaries. Different math libraries may produce different fitted weights. A mismatch is reported with its result field. The supplied fitted weights support replay without retraining. In the reference rebuild, every fitted weight and every source and prediction archive matched byte for byte. The independent reader and model checks report their own numerical differences. [Numerical verification](results/verification.json)

The MATLAB file occupies 211,140,370 bytes. The reproduction directory holds fitted weights, out-of-fold forecasts, the four reconstructed arrays, prediction arrays and detailed scores. Allow at least 1 GB of disk and 2 GB of memory for the run.

Raeed Chowdhury, Joshua Glaser and Lee Miller deposited the measurements under CC0. The project repository dedicates its original software and explanatory material to the public domain under CC0. The paper and linked upstream software retain their own terms. [Source and attribution](source/RECONSTRUCT.md) · [CC0 dedication](CC0-1.0.txt)
