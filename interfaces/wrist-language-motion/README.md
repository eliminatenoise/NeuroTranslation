# From a pointing cue to a wrist measurement

A participant sees a target and bends the right wrist. Which parts of that sentence did the equipment record? One scalp electrode records voltage. Two forearm electrodes give a voltage difference. Two encoders record the angles of the wrist. The computer logs when it shows the target. The sentence describing the movement comes from us. This example gives a movement model those distinctions as well as the numbers. [Wrist pointing study](https://pubmed.ncbi.nlm.nih.gov/42020458/)

## Open one trial

The [three-second recording](wrist-pointing.json) ships with this example. NeuroSurge plays the same bytes. From the NeuroTranslation repository root, enter the example directory and run:

```sh
cd interfaces/wrist-language-motion
python -B wrist_bridge.py wrist-pointing.json
```

The saved [example window](example-window.json) opens directly. The command needs only Python 3.10 or later. It prints a JSON sample and checks the replay's SHA-256 before it reads the channels. The clip comes from participant 41, run 03, block 1, trial 1, already exposed for development. No other participant or recording is needed. Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz published the EEG-EMG-WristMotion Dataset, version 3, under CC BY 4.0. The NeuroSurge extractor selected this interval, subtracted the two forearm channels and retained the source row numbers. This bridge selects a shorter history and converts its row numbers to seconds. The original bridge code is available under the project's CC0 dedication. The data and derived numerical examples retain their attribution. [Dataset and licence](https://figshare.com/articles/dataset/EEG-EMG-WristMotion_Dataset/29666735/3) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Code dedication](https://creativecommons.org/publicdomain/zero/1.0/)

## Follow the clock

The visual cue occurs at stored row 2587. The default sample uses rows 2812 through 2843 inclusive as history. Its question is what the two encoders read at row 2971, a quarter of a second beyond the cutoff. At that row the stored readings are −1.0382° on the extension-positive axis and −2.1748° on the radial-positive axis. The program checks both against a separate export of the same encoder readings. That agreement tests extraction and alignment. Both exports trace back to one instrument.

| Channel | Meaning in this trial |
| --- | --- |
| C3, µV | Scalp electrical potential at one electrode. Localization of the generating brain tissue remains unknown. |
| M3L minus M3R, µV | Difference of two surface electrode readings over the right forearm. Muscle force and motor nerve activity would each need their own measurement. |
| Extension and radial deviation, degrees | Wrist encoder positions. A more negative extension angle means more flexion. The instrument updates at 100 Hz. The 512 Hz file rows can repeat an encoder state. |
| Visual cue | Source marker `TrialInitMovStam` with target code 1. The subject saw a target. The indicator changes only when the cutoff reaches its marker. |
| Protocol words | “Right wrist visual pointing” comes from the task description. A fixed dictionary exposes those words as trial context. Their availability at the start is an offline protocol assumption. |
| Outcome caption | “The right wrist bends toward the palm” describes the interval after inspection. The wrist moved from about +2.63° at the cue to −49.30° at the end. The human trial contains no timed words. |

Set `--cutoff-offset -1` to stop one source row before the cue. The protocol stays the same, and the cue flag becomes zero. A different query can use one of six source-verified target offsets, 384, 512, 640, 768, 896 or 1024 rows after the cue. The extractor requires a complete 32-row history and a strictly later target.

Time in the learner is stored row divided by 512, in seconds from the run origin. This clock describes offline availability. Hardware latencies, sensor offsets and filter delays limit interpretation of the physical ordering. A repeated encoder reading is a valid stored state and supplies no evidence of a fresh measurement. Keep feature masks, subject/run and trial identities with the sample. The shared clock does not establish that its scalp signal caused the wrist movement.

## Pass the data to the Transformer

The general learner takes the arrays under `observations` and a separate `query`. The bridge converts them to its native `ObservationBatch` and `AlignedQuery`, with a distinct `AlignedTarget` for the two encoder readings. A measured zero has an observed flag of true. A missing channel has no observed value. Missing spinal, afferent, motor nerve, force, torque, video and speech observations have zero training weight. The measured target has zero training weight here too, because this participant's replay is public development material. Its encoder target, future rows and outcome caption stay outside the forecast inputs.

The six conditioning features are ordered protocol-word indicators for `right`, `wrist`, `visual`, `pointing` and `release`, then the observed cue-start indicator. This is a small, inspectable vocabulary. The broader learner can accept that context alongside electrical signals and angle histories. The adapter supplies a read-only real tensor example. A general-purpose text encoder, a model trained on synchronized language and physiology, and a validated real prediction from these features remain open work.

The second example asks a different question. Release a virtual rotational spring from rest and it swings back. For an invented inertia of 0.02 kg·m² and stiffness of 0.50 N·m/rad the equation is `J q″ = −k q`. Its closed-form solution supplies angle, angular velocity and restoring torque to the learner’s physics input. The demo starts at 0.2 rad. A separate invented trajectory starting at 0.4 rad supplies the normalization statistics. A fresh, small Transformer makes a forward pass, then repeats it with the protocol words removed. The change in output checks the conditioning wire. The weights are random and receive no updates. Each trajectory comes from the equation alone. The spring has no muscles or evidence about the participant's stiffness.

The [daily-sports-limbs directory](../../benchmarks/daily-sports-limbs/) supplies the two general learner source modules. The wrist example uses the code only. Its command never loads the walking checkpoint. With CPU PyTorch installed, stay in `interfaces/wrist-language-motion` and run in a POSIX shell:

```sh
export PYTHONPATH="../../benchmarks/daily-sports-limbs"
export WRIST_REPLAY="wrist-pointing.json"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python -B model_bridge.py real "$WRIST_REPLAY"
python -B model_bridge.py synthetic
python -B test_bridge.py -v
```

In Windows PowerShell, set the paths and thread counts in the same directory, then run the examples.

```powershell
$env:PYTHONPATH = "../../benchmarks/daily-sports-limbs"
$env:WRIST_REPLAY = "wrist-pointing.json"
$env:OMP_NUM_THREADS = $env:MKL_NUM_THREADS = $env:OPENBLAS_NUM_THREADS = "1"
python -B model_bridge.py real $env:WRIST_REPLAY
python -B model_bridge.py synthetic
python -B test_bridge.py -v
```

In Python, `replay_tensors(path)` returns the observations, query and separate targets. `replay_contracts()` supplies the task and source specifications, units and frames. Both work with the included edition of `broader_learner.py` and `aligned_forecast.py`. The replay has no trained model or fitted normalizers attached. Inspecting the example supplies no estimate of performance on a new participant.

## What another source can add

| Question | Source and conditions |
| --- | --- |
| Can words describe a movement someone else actually performed? | The KIT Motion-Language release of 22 June 2017 pairs 3,911 motion clips with 6,353 annotations. Match annotations and motion by file ID. Keep the captions clip-level unless independent word timing exists. The download combines KIT and CMU motion sources. The project page lists their origins but gives no blanket redistribution licence. Carry the relevant original terms before using individual assets. [KIT download and data layout](https://motion-annotation.humanoids.kit.edu/dataset/) |
| How closely does motion estimated from footage match optical markers? | The Capital University of Physical Education and Sports v3 deposit describes 120 Hz marker capture and 30 Hz smartphone footage from 21 male university students. Its CC BY 4.0 data record offers a source for a separate camera-versus-marker comparison. Keep camera calibration, person, activity and capture rate with each example. The full files and subject permissions for redisplaying identifiable footage need inspection for a chosen use. The deposit supplies no recorded connection to the wrist participant. [Version 3 record](https://zenodo.org/records/19720803) · [Licence metadata](https://zenodo.org/api/records/19720803) |
| Can a controller imitate reference motion in a simulation? | An adversarial differential discriminator (ADD) learns a training signal from the difference between motion and its reference. The physics engine advances state under the specified forces and constraints. Improving an imitation score supplies evidence about the simulated task. Measured muscle force or a nerve recording would answer different questions. MimicKit's code carries Apache 2.0. Its motion assets need their own terms. [ADD paper and authors’ project](https://xbpeng.github.io/projects/ADD/index.html) · [MimicKit licence](https://github.com/xbpeng/MimicKit/blob/main/LICENSE) · [MuJoCo dynamics](https://mujoco.readthedocs.io/en/stable/overview.html) |

Separate corpora can teach useful representations. To fuse their streams as one measured event, a new trial needs the same person, task, source clock and independently established alignment. A motion caption from KIT cannot supply the missing speech or afferent activity in participant 41.
