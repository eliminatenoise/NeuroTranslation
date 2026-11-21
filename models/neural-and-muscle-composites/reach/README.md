# Forecast the next tenth of a second

A macaque slides a handle towards a target. Stop the recording. From the previous fifth of a second of handle motion and cortical spikes, where will the handle be 50 and 100 milliseconds later? Turn the question around. How many spikes will each recording contact pick up in those next two 50-millisecond intervals?

Three small Transformers learned from one recording day. A week later the same animal returned. Diffusion gave the closest handle forecasts of the three when each received both streams. A linear forecast was closer still. For cortical activity, simply carrying forward each contact’s last spike count beat every fitted model. [Area 2 study](https://doi.org/10.7554/eLife.48198) · [Chowdhury, Glaser and Miller’s recorded data, CC0](https://doi.org/10.5061/dryad.nk98sf7q7)

## What changed when the animal came back?

There were 519 training windows from 198 original trials on September 7, 2017. September 14 supplied 493 windows from 274 original trials in two recording blocks and two workspaces. Each original trial counts equally in the averages below. The movement score measures the distance between the predicted and observed endpoints, averaged over the two horizons. Neural error is the root mean squared difference between predicted and observed counts, per contact per 50 ms. Smaller is better in each column.

| Method | Handle, cm | Counts with handle history, spikes | Optical hand marker, cm | Counts with hand history, spikes |
| --- | ---: | ---: | ---: | ---: |
| Autoregressive Transformer | 0.716 | 1.666 | 0.611 | 1.650 |
| Diffusion Transformer | 0.677 | 1.666 | 0.597 | 1.660 |
| Autoregressive–diffusion hybrid | 0.732 | 1.698 | 0.619 | 1.652 |
| Linear ridge regression | **0.633** | 1.493 | 0.741 | 1.486 |
| Repeat last position or count | 0.939 | **1.255** | 0.604 | **1.255** |
| Continue last velocity | 0.687 | — | **0.570** | — |

The handle is an object whose position the apparatus measured in two dimensions. The optical marker tracked the hand itself in three dimensions relative to the shoulder. We added the marker comparison after the handle analysis and fixed its settings before running it. It uses the same trials. The primary handle test and this exploratory optical test each found that no architecture met the bidirectional winning criterion.

Among both-stream models, joint diffusion reduced handle error by 0.040 cm relative to autoregression (paired 95% interval 0.023–0.056 cm). Ridge beat diffusion by 0.044 cm (0.005–0.082 cm). For the reverse forecast, the mean squared errors were 2.7761 for autoregression and 2.7767 for diffusion. The interval for their difference covered zero (−0.0121 to +0.0114 spikes squared). Carrying the last count forward scored 1.5750. These intervals resample original trials within each block and workspace. They describe uncertainty on this one previously studied date. [Primary protocol](protocol.json) · [Results by block, workspace, seed and horizon](results.json) · [Optical protocol](optical-protocol.json) · [Optical results](optical-results.json)

### Did the second recording stream help?

Watch what happens when diffusion loses its cortical input. Its handle error falls from 0.677 to 0.625 cm. Give it the spikes from an earlier, different trial at the same go-cue ordinal and its error rises to 0.760 cm on the 485 windows with a matching earlier trial. On those same windows, properly timed spikes beat wrong-trial spikes by 0.088 cm (0.069–0.106 cm). All three model families suffered when the correct cortical trace was replaced. Yet all three did better at predicting the handle when the cortical input was omitted altogether.

The optical hand marker told much the same story. With optical history alone, diffusion reached 0.536 cm. Adding cortical history raised the error to 0.597 cm. In the other direction, replacing the real handle history with a different trial’s handle history produced no clear change in neural error for any family. A model’s sensitivity to timing and the value of adding a channel answer different experimental questions.

### How much spread did the models predict?

For the handle, the intended central 80% intervals covered just 53.2% of measured coordinates under autoregression, 54.4% under diffusion and 46.9% under the hybrid. The neural count intervals covered 85.1%, 84.2% and 83.3%. These are marginal intervals calculated from 16 trajectories. Counts are discrete, endpoints are included and ties are common. An average across channels cannot establish calibration at each contact or on another date. The result files include interval widths and the finite-ensemble corrected continuous ranked probability score.

## How the three forecasts work

The source clock advances in 10-ms rows. Each of four history tokens summarizes 50 ms of simultaneous movement and cortical activity. Its movement values give the final position and displacement between the first and last samples of that token. Its 37 neural values give the number of spikes at each matched recording contact. Every available sort column at a contact contributes once. The matching tracks electrode labels across the two days. Individual neurons can change. All predictors stop at the final history row. Offline signal processing, including marker interpolation and handle filtering, limits what these processed timestamps can tell us about live acquisition.

The autoregressive model learns the next vector with the true preceding vector available during fitting. During a forecast it uses its own first draw to produce the second. It adds diagonal Gaussian innovations estimated from training residuals. Diffusion learns to remove noise from both future vectors together. It starts with fresh Gaussian noise and takes eight deterministic denoising steps. The hybrid first denoises the early vector and then runs a second eight-step denoising trajectory conditioned on the first. Its two intervals come from a single sequential model.

Every comparison uses a 32-wide, four-head history encoder and cross-attending decoder, three seeds and 180 optimizer updates per seed. The history can contain both streams or either stream alone. There is one set of weights per direction, sensor, architecture and seed. No pretrained weights entered the comparison. The two pure approaches supervise both target vectors per update. The hybrid trains one randomly selected horizon per example, and diffusion fits a noise-dependent velocity. Equal update counts give different supervision and computational costs. Each model draws 16 trajectories. We average their physical values within each fitted model and average scores over seeds. For neural counts, continuous latent draws are rounded and clamped to zero before scoring.

On the two-thread CPU run, 16-draw handle forecasts took 0.081 ms per window for autoregression, 0.266 ms for diffusion and 0.550 ms for the hybrid, averaged in batches of up to 32 windows. These figures cover model computation. Sensor acquisition and live single-case latency need separate measurements. [Runtime and parameter counts](runtime.json)

The recording captures a specific relationship between one animal’s cortex and its reach during rewarded trials. Spinal signals, peripheral nerve activity and muscle activity were unobserved here. The bidirectional forecasts apply to this task. Establishing causal circuitry, invertibility or transfer to a person would require different measurements.

## Use the fitted models

The package contains the train-only normalization and all 36 fitted checkpoints as NumPy arrays. Install NumPy and PyTorch in a Python environment. Start with `python predict.py --help`. From the directory containing this guide, pass your observations in the same coordinate frame and contact order as the source.

```sh
python predict.py observations.json --task movement --architecture diffusion --seed 17
python predict.py observations.json --task neural --architecture ar --seed 41
```

The JSON object supplies `sensor` (either `handle` or `hand`), plus `pose`, `counts` or both. Each has four consecutive rows in chronological order. For a handle row, supply ending X and Y followed by within-token change in X and Y, all in cm. For hand rows, use the corresponding XYZ triples in shoulder-relative cm. Each count row contains the integer spikes at each of the 37 contacts. When supplying counts, include the `contacts` list in the exact order recorded in the protocol. Use JSON null or omit a stream to mark it missing. Output gives the two forecast means and marginal deciles. The models support the study’s frames and channels.

## Reproduce the comparison

The reconstruction script checks the two original MATLAB files against their published study-specific SHA-256 digests. The accompanying fetch script optionally retrieves just those members from the research archive. With the files already on disk, begin at reconstruction. Source reconstruction used NumPy 2.5.5 and SciPy 1.18.1. Training and scoring used NumPy 2.5.3 with PyTorch 2.14.0 on Linux CPU. Different builds may produce small floating-point differences. [Source archive](https://zenodo.org/records/5010943/files/s1-kinematics.zip) · [Pinned upstream reconstruction](https://github.com/eliminatenoise/NeuroTranslation/tree/4da36703e5d85ff2f7be9952af337562a04b228e/models/reach-feedback-week/source)

```sh
python reconstruct/fetch.py train raw
python reconstruct/fetch.py held raw
python reconstruct/reconstruct.py train --mat raw/C_20170907_TRT_TD.mat --output data
python reconstruct/reconstruct.py held --mat raw/C_20170914_TRT_TD.mat --output data
python experiment.py score --sensor handle --data data --weights weights/handle --out replay-handle --threads 2
python report.py --scores replay-handle --out reproduced-handle.json
python check_model.py --sensor handle --data data --weights weights/handle
python experiment.py score --sensor hand --data data --weights weights/hand --out replay-hand --threads 2
python report.py --scores replay-hand --out reproduced-hand.json
python check_model.py --sensor hand --data data --weights weights/hand
```

To train from scratch, use `python experiment.py fit --sensor handle --data data --out refit-handle --threads 2` or replace `handle` with `hand` in the sensor and output directory. Score the resulting checkpoint directory with the corresponding command above. [CC0 terms](CC0-1.0.txt)
