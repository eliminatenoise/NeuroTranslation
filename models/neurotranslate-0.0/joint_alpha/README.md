# NeuroTranslate 0.0 · joint temporal model

A macaque moves a handle. The camera sees its arm and the recording electrodes count spikes. Give the model the last 200 milliseconds from both instruments and it can forecast either the arm displacement or how many spikes each of 37 cortical contacts will record in the next tenth of a second. A second experiment asks a different pair of questions about people standing or walking. The earlier scalp, muscle and sacrum readings go in. Future leg-muscle voltage or pelvis motion comes out.

All seven forecasts use one trained attention network and one checkpoint. Each instrument has an input conversion and a readout in its own units. Training on a rat spike sequence changes parameters that the human movement forecast also uses. Pairing happens within a recording. No worm, fish or rodent observation stands in for an unmeasured signal from a human.

## Run a forecast

Install NumPy in a Python environment. These commands load the packaged checkpoint. The examples contain fictional readings in the units required by each input.

```sh
python inference.py --list
python inference.py --example
python check_model.py
```

Your own JSON object needs a task name and an array called `X`. For a movement, voltage, count or fluorescence forecast, the axes are case, time, channel. For next-unit prediction, insert an axis for every locally sorted candidate between case and time. One object may contain multiple cases for the same task. `--list` provides the channel order, units, issue clock, target and limits. Run an object with `python inference.py --input case.json`.

To use two tasks from the same loaded weights, call the Python interface. Each row of `example.json` is ready to pass to it.

```python
import json
from inference import JointModel

model = JointModel.load()
examples = json.load(open("example.json"))["examples"]
movement = model.predict(**examples["macaque_cortex_to_motion"])
counts = model.predict(**examples["macaque_motion_to_cortex"])
```

A missing measurement may be supplied as JSON `null`. A recorded zero carries information and stays zero. A dense case with no observations raises an error. On the rat task, give every eligible unit, including the ones that have stayed silent. The result gives one probability per supplied candidate, conditional on the next occupied millisecond bin containing exactly one spike. A wholly unobserved eligible candidate makes the forecast unavailable. An explicit boolean `valid` mask can mark padded slots in a batch with different roster sizes. It cannot make competing recorded units disappear from the scientific task.

## What the shared weights do

An input adapter maps calibrated readings and their presence flags into a 32-number vector at each supplied time. Four attention heads let the latest observation weight earlier observations at different relative times. A learned empty memory position lets a head reduce its reliance on earlier input. A feed-forward layer combines the four attention outputs. A linear readout turns the resulting shared state into the appropriate forecast. Counts use an exponential link. On the rat task the same scalar scorer visits each candidate, then a softmax across the local roster converts scores to probabilities. One rat input contains a single time point with causal traces measured over several decay scales.

On every optimizer update, each task supplies 32 cases sampled by first drawing a recording group with equal probability, then drawing a case within it. The seven losses contribute equally. Continuous values use a smooth absolute-error loss in training units, counts use a Poisson loss, and unit identity uses cross-entropy. Training produces one set of shared weights and seven input/output adapters. The mean and scale of each channel come from its development observations. The healthy human cohort supplies pooled parameters. No participant ID is a model input. [Architecture and source code](network.py) · [Fitting protocol](protocol.json) · [Shared gradient evidence](training-summary.json)

## How much model did these data support?

We fitted widths from 32 to 512 and depths from one to six on the same seven development tasks. The largest candidate had 12.82 million parameters. Each fixed-budget candidate took 480 mixed updates. The larger candidates also ran at a second learning rate. The final comparison trained a 32-wide model and a 256-wide model for 1,920 updates with a warmup and cosine decay. Two seeds were used for each finalist, including the original 480-update incumbent.

The score gives the macaque, human, rat, fluorescence and tracked-landmark tasks equal weight. Within each domain, lower means less error relative to a simple prediction learned from the development data. The longer 32-wide fit scored 0.6837. Its shorter fit scored 0.6883, and the longer 256-wide fit scored 0.7163. These results select 21,445 parameters, including 8,576 in the shared attention network. The recordings offer limited evidence about how the ranking would change with more animals, more people, different tasks, different optimizers or more training. [All candidate and seed results](capacity-results.json) · [Development comparison](capacity-plan.json) · [Longer training comparison](refinement-plan.json) · [Sizes, memory and latency](specifications.json)

## What held recordings showed

The validation score chose a model size. The following forecasts then used the full-development fit on recordings reserved from that fit. These assessment recordings had appeared in earlier studies. Each row gives the same held groups and target to the joint and independently trained networks. Lower is better. The two networks saw the same training examples for each task, from the same initialization, with the same number of updates. A separate trained model provides a comparison, while the released predictor uses a single checkpoint.

| Held recording and primary error | Joint | Single task | Source comparison |
|---|---:|---:|---:|
| Six adults, leg muscle voltage MAE (µV) | 10.116 | 9.878 | 9.853 earlier early-fusion model |
| Same adults, mean four-knot sacrum distance (mm) | 2.645 | 2.500 | 2.533 earlier paired model |
| Macaque movement, later date block 1 (mm MAE) | 4.404 | 4.379 | 3.273 earlier cue-aware model |
| Same date block 2 (mm MAE) | 4.412 | 4.522 | 3.024 earlier cue-aware model |
| Macaque contact counts, block 1 (Poisson loss, nats) | 2.367 | 2.704 | 1.978 smoothed recent rate |
| Same count task, block 2 (nats) | 2.471 | 2.748 | 2.009 smoothed recent rate |
| Sorted rat units, later JS14 trips (log loss, nats) | 2.786 | 2.779 | 2.884 earlier unit scorer |
| Sorted units, different rat ER1 (nats) | 3.288 | 3.287 | 3.380 earlier unit scorer |
| Seven fish, optical fluorescence MAE (assay training SD) | 0.0707 | 0.0807 | 0.0501 last observed value |
| Landmark motion, 13 recordings at 120 ms (body-radius MAE) | 0.0922 | 0.0914 | 0.1722 constant velocity |
| Locust motion, one recording at 200 ms (body-radius MAE) | 0.1381 | 0.1507 | 0.1066 constant velocity |

Joint training reduced error on five of the eleven rows and increased it on six. The human muscle and path forecasts both lost accuracy compared with their single-task controls. The macaque count forecasts gained accuracy over those controls in both blocks, while a simple estimate combining recent counts with the training mean did better still. The earlier macaque movement specialist also had cue history. Changing one input modality at a time on the same held rows sometimes helped and sometimes hurt. An ablation measures how this particular predictor responds to missing input.

The uncertainty follows the recording. Both macaque blocks came from one animal, and the fourteen landmark recordings span several kinds of tracking. Tens of thousands of sorted spike events in ER1 still represent one rat. Muscle electrical activity measures voltage; mechanical contraction, force, peripheral nerve signalling, subjective sensation and live control remain unmeasured here. [Held results, group intervals and modality changes](results.json)

## Reproduce the fit

The input kit rebuilds measured cases from the separately credited recordings. Keep these arrays in private storage. Use a PyTorch environment for training and NumPy for the portable predictor. On the measured CPU route, two PyTorch threads and one BLAS thread ran the selected small network. Larger candidates also ran on Radeon hardware. Kernels, thread groups and synchronization are managed by PyTorch and its backend. [Recording sources and preparation](inputs/README.md) · [Credits and changes](NOTICE.md)

```sh
python inputs/rebuild.py train --cache recording-cache --out packed
python refit.py capacity-results.json packed/manifest.json --out rebuilt.npz --evidence private/controls
python inputs/rebuild.py held --cache recording-cache --out packed --frozen-model rebuilt.npz
python evaluate.py packed/manifest.json rebuilt.npz private/controls reproduction-results.json
```

The input kit gives the two additional commands for aligning earlier trained specialists to the held human and macaque rows. Run those before `evaluate.py` to reproduce those particular comparator scores. To repeat the model-size search from scratch, first create the inner development folds. Use the identical `--large-device` option for both selection stages. The original larger fits used `cuda` through PyTorch on ROCm.

```sh
python capacity.py build packed/manifest.json private/folds
python select_capacity.py one private/folds/manifest.json private/search --large-device cuda
python select_capacity.py two private/folds/manifest.json private/search --large-device cuda
```

