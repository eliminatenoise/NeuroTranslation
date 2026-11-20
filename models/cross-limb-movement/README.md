# Can a model that follows a wrist also follow the base of the spine?

An object is ready to lift. A light comes on. Four hundred milliseconds later, the model gets its last look at the wrist and the muscles of the right arm. Where will the wrist go in the next eighth of a second? How much electrical activity will its electrodes record? In a second experiment a visual scene turns around someone standing or walking on a beam. The same model gets 625 milliseconds of leg-muscle and sacrum measurements to answer the same two questions in that study's units.

The shared model predicted both tasks. The advantage over the specialist depended on which task and how long the specialist could train. With 192 updates per study, the shared fit tracked the wrist 0.230 mm more closely than the wrist specialist and the sacrum 0.207 mm less closely than the balance specialist. Give the wrist specialist all 384 updates and its path error falls to 4.394 mm, below the shared model's 4.870 mm. [Results and uncertainty](RESULTS.md)

## Run one forecast

Open the launcher for Windows, macOS or Linux in this folder to inspect a synthetic example in your browser. You can also open **forecast.html** directly. The two examples are generated mathematically. The forecast occupies the source coordinate frame and describes the next 125 milliseconds of movement under the recorded task conditions.

To get machine-readable output, run the JavaScript command with Node.js 20 or later. It accepts an event JSON file and an optional weights file. The alternative Python CLI uses NumPy and PyTorch.

```sh
node launch.mjs synthetic-upper-amplitude.json model-joint.json
python predict.py model-joint.json synthetic-lower.json
```

The returned `path_mm` contains 32 ordered XYZ displacements. `rms` has thirteen named slots. Unavailable muscles return JSON null. The model recognizes the thirteen anatomical names in `interface.py`. The examples use all eight balance channels or four available arm channels. The original `synthetic-upper.json` is an out-of-range numerical stress test. Choose `synthetic-upper-amplitude.json` for an illustrative amplitude near the recorded scale.

For an application, import `predict(weights, event)` from `inference.mjs`. `encodeHistory` accepts signed native muscle samples and source-frame marker knots in millimetres on their own clocks. Pass their times in seconds relative to cutoff. Historical muscle input is in µV for balance and original exported amplitude units for WAY. The caller supplies channel-quality decisions. The source reader includes the offline future-quality gates used to define this experiment. Keeping the anatomy names with their columns permits reordering; a different muscle or segment requires a new measurement and validation study.

## Repeat the comparison

Use Python with the versions in `requirements.txt` for training and the native CLI. The benchmark ran on Linux with Python 3.14, NumPy 2.5.3 and PyTorch 2.14.0. The PyTorch build there also supported ROCm. Installation packages differ by operating system and accelerator. Run the source-preparation commands in `source/README.md` first, with participant recordings and outputs kept in local private storage. The commands below assume those two prepared NPZs reside in `private/windows/` relative to this folder.

```sh
python -m pip install -r requirements.txt
python training.py --data private/windows/development.npz --out replay --private private/replay --device cpu --threads 3
python evaluation.py --data private/windows/assessment.npz --models replay --out private/scores-full.json --private private/assessment-predictions.npz
python public_scores.py private/scores-full.json replay/scores.json
```

The 192-update lower and upper specialists are `model-lower.json` and `model-upper.json`. The 384-update versions add `-total` to those names. Each `model-adapt-` name ends with its target study. Corresponding `model-shuffled-` and `model-paired-source-` files give the source-label permutation control and its matched intact fit. Every checkpoint contains its own scales, named muscle vocabulary and native parameter arrays. Exact grouped development and assessment metrics are in `development.json` and `scores.json`. `fixture-oracle.json` supplies independent entry points with the native outputs to expect from the small synthetic examples. `fit-log.json` records the batch-order fingerprints and the measured time of each training phase. [Experiment and controls](EXPERIMENT.md) · [Recordings and permissions](NOTICE.md)
