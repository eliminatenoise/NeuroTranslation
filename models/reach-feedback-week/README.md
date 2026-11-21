# One week later

A macaque reaches for a target. The handle moves, two markers trace its arm, and an electrode array counts spikes in its brain. A week later the same animal returns. Can a model fitted on the first day still use the spikes to predict where the hand will go? Can seeing where the hand actually went improve a forecast of the next spikes?

**Open the reader** by double-clicking the launcher for your operating system, or open [reader/index.html](reader/index.html) in your browser. The eight example reaches work offline. The muscle view follows changes in 39 muscle–tendon paths calculated by the source OpenSim arm model. The camera measured marker motion. OpenSim calculated the length references.

## Run a recorded reach

Python 3.11 or newer and NumPy are sufficient for a case. Extract the package, open a terminal in this folder, and run:

```sh
python -m pip install numpy
python reach_week.py list
python reach_week.py case 1
python reach_week.py case 2 --json case-2.json
```

Case 1 is the first eligible reach from workspace 1 in block 1. An earlier reach at the same go cue is unavailable there. Case 2 has one, so its results include the control that borrows an earlier reach's movement or cortical counts. The JSON includes each contact, all ten movement samples and all 39 paths. Python callers can use `from cases_api import case_list, forecast_case`. Call `forecast_case(2)` to get the same result as the command.

## What changed in the second recording?

September 7 supplied 519 windows from 198 rewarded reaches in workspace 1. September 14 supplied 493 candidate windows in two recording blocks and two workspaces. On this date 197 windows from 109 reaches in workspace 1 and 288 from 161 in workspace 2 had an earlier comparison reach. Repeated windows from one reach share its weight. Both days came from one animal. [Data and CC0 dedication](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original experiment](https://doi.org/10.7554/eLife.48198)

| Question | Held-day result |
|---|---|
| Can a movement update improve a forecast of the total spikes on 37 contacts? | Against the earlier estimate, mean deviance changed by −0.201 in workspace 1 and +0.103 in workspace 2. Lower is better. The sign switched. Separate fits test unsorted spikes alone on 37 contacts and positively sorted spikes on 17. [Count results](counts/RESULTS.md) |
| Does seeing the movement still help when a model already has the intervening spikes? | An independent fit used positive sorts on 17 shared contacts. Its change from the stale-position model was +0.004 and +0.096 deviance in the two workspaces. [Late counts](late_counts/README.md) |
| Do cortical counts sharpen the arm forecast made at the original cutoff? | Adding counts to a three-Transformer movement model raised average hand trajectory error by 0.47 and 0.88 mm. The elbow result changed direction between workspaces. [Movement and controls](motor/RESULTS.md) |
| Do the resulting paths predict changes in OpenSim muscle–tendon lengths? | Using the count-informed movement forecast gave 1.047 and 1.539 mm mean endpoint error across 39 paths. Predicting zero change gave 0.689 and 0.540 mm. [Path-length results](muscles/README.md) |

All four comparisons missed their prespecified requirement for consistent improvement. Each table of scores retains the simpler forecasts, the uncertainty intervals and the denominators. The electrodes recorded cortex. These observations alone cannot establish a causal feedback pathway, identify the same neurons across days or establish timing in a live device.

## Rebuild the entire comparison

Install NumPy, SciPy and PyTorch in a Python environment of your choice. Run **one command** from this folder:

```sh
python -m pip install numpy scipy torch
python reach_week.py reproduce rebuilt
```

The command requests only two original MATLAB members from the public source ZIP, verifies their digests, and saves them under `rebuilt/raw`. Allow at least 650 MB of free space beyond the Python environment. The full source ZIP is about 4 GB. A server that does not support HTTP range reads requires the full ZIP as a local input. If you already have the source, use either form below with an empty output directory:

```sh
python reach_week.py reproduce rebuilt --archive /path/to/s1-kinematics.zip
python reach_week.py reproduce rebuilt --train-mat /path/to/C_20170907_TRT_TD.mat --held-mat /path/to/C_20170914_TRT_TD.mat
```

The first recording supplies the training trials, five chronological folds, fitted scales and all model weights. The command reconstructs the original positive-sort archive, trains the three pose-and-cue Transformers from their seeds, and fits the contact, movement-correction and length models before processing numerical data from September 14. A comparison against an earlier reach always respects its physical recording block, workspace and cue ordinal. Blocks restart both the sample clock and the trial numbers. [Recording fields and units](source/RECONSTRUCT.md)

Look in `rebuilt/scores` for the full count tables, movement errors and modelled length errors. The NPZ files contain per-window values and donor identities for the analyses that emit them. `rebuilt/verification.json` compares the rebuilt array fields and complete result files with the original run. Exact fingerprints are a stringent test. Different numerical libraries, CPU backends or compressor versions can change fitted values or serialized bytes. The reference used NumPy 2.5.5 and SciPy 1.18.1 for the scientific pipeline and NumPy 2.5.3 with PyTorch 2.14.0 for the CPU Transformer and movement stages. To reproduce those separate environments, use `--torch-python PATH_TO_PYTHON`. The underlying build of PyTorch recorded `2.14.0+rocm10.1.0`; the reproduction here runs its tensor operations on CPU.

## Read the clock

The bin width is 10 ms. Row *k* occurs five bins after a following go cue. The twenty rows ending at *k*−1 supply the movement forecast. The next ten rows hold observed movement at *k* through *k*+9. The last of these positions is 100 ms after the last known position. An update issued at *k*+10 can use that observed path. The target of both count studies is the total number of spikes in rows *k*+10 through *k*+19.

The first six movement coordinates give hand and near-elbow marker XYZ displacement in shoulder-relative metres. Handle X and Y use centimetres in the handle's own plane. In the case JSON, `muscle_path_change_m` uses metres relative to the OpenSim value at *k*−1. The scientific length tables report errors in millimetres. Mean Poisson deviance measures count forecast error. A smaller value indicates a closer count forecast.

The original recordings are by Raeed H. Chowdhury, Joshua I. Glaser and Lee E. Miller. Their source-derived excerpts retain the CC0 dedication; the project supplies the fitted models and code. [Source and reuse](NOTICE.md)
