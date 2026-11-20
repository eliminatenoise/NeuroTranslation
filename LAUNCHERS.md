# Launchers and offline copies

Almost everything here runs in a browser. A launcher is a shortcut that opens the right page. An offline copy is a ZIP that holds the page itself, so it works with no network. The general model’s five-sensor walking page and the study 28 wrist command need Python. The two newer stride and rat viewers open without it.

## A shortcut to the app

The shortcut opens the app in your browser, at the part that replays a recorded palm movement. It needs a network connection.

| Your computer | What to do |
| --- | --- |
| Windows | Download [`NeuroTranslation-Windows.url`](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-Windows.url) and open it. |
| macOS | Download [`NeuroTranslation-macOS.webloc`](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-macOS.webloc) and open it. |
| Linux | Download [`NeuroTranslation-Linux.desktop`](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-Linux.desktop) and open it the way your desktop opens launchers. For an entry in the applications menu, extract [the launchers ZIP](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-Launchers.zip) and run `sh Install-NeuroTranslation-Linux.sh` in that folder. |

Keep the file extensions, and follow your system's usual prompts about a downloaded file. If a shortcut opens as text, take it from the ZIP instead. The Linux installer writes one menu entry for your user, leaves existing entries alone and opens no browser.

Checked: the format of the Windows and macOS shortcuts, and the Linux installer in an isolated folder. Not checked: opening the shortcuts on a real Windows or macOS machine. [Checksums](docs/launchers/SHA256SUMS)

## Compare the rhythm in two walking recordings

Extract the ZIP and open the launcher for your operating system, or open `docs/gait-rhythm/index.html` directly. Select any of 11 walks to compare its published muscle and knee rhythms offline. The reader can also recalculate each spectrum from the two original PhysioNet files you choose on your computer. [Open the rhythm reader](https://eliminatenoise.github.io/NeuroTranslation/gait-rhythm/) · [Download the reader and study](models/gait-rhythm.zip)

## See both knees 15 stored frames ahead

Extract the download and open the launcher for your operating system. You can also open `docs/knee-motion/index.html` directly. The invented example works offline. To reveal a recorded endpoint, open a supported angle file from the study in the viewer. Five snapshots of both hips, knees and ankles predict the two knee angles 15 frames later in a stored 60 Hz treadmill recording. On 40,201 forecasts from 12 held-out walkers, replaying a stride from four seconds of knee history gave 3.54° mean absolute error. The transformer, with 0.4 seconds of joint history, gave 4.46° on the same windows. Six of the 51 recordings used whole-file Xsens HD processing, including test recording S48. The other 45 carry the Live label. Physical prediction latency was never measured. Only reconstructed joint angles entered the forecast.

[Open the knee viewer](https://eliminatenoise.github.io/NeuroTranslation/knee-motion/) · [Download the viewer, model and source](models/knee-motion.zip)

## Continue a measured stride or follow a rat’s trip

Choose a download, extract it, and open the launcher for Windows, macOS or Linux at the top of the extracted folder. You can also open the indicated HTML file directly. Both viewers carry the recordings they show and work offline in a browser.

| Download | Open this file | What you can see |
| --- | --- | --- |
| [Human stride forecast](models/stride-continuation.zip) | `docs/stride/index.html` | Give the model eleven measured poses and compare its next twelve with the recording. |
| [Rat movement forecast](models/population-motion.zip) | `docs/population-motion/index.html` | Explore a rat’s filmed path, firing recorded in two brain regions, and competing distance forecasts. |

The folder under `models/` in each ZIP has fitted weights, Python code and an example input. Python inference requires NumPy. Each model’s README gives the command, units and original study.

## Walk or run, online or offline

Type **walk** or **run** to see a short model-generated stride. For the offline version, unpack the ZIP and open `docs/word-motion/index.html`, or use the Windows, macOS or Linux launcher beside it. The fitted weights and Python and JavaScript inference code are in `models/word-motion/`. [Open the viewer](https://eliminatenoise.github.io/NeuroTranslation/word-motion/) · [Download the viewer and model](models/word-motion.zip)

## Offline copies of the study readers

Each ZIP holds one reader and its own launchers for Windows, macOS and Linux. Unpack the whole folder, then open the launcher for your system, or open `index.html`. A recording you open is read on your computer and goes nowhere. Each reader is named after its study, with the study's number on [the studies page](benchmarks/README.md).

| The reader for | Online | Offline ZIP | The recording it reads |
| --- | --- | --- | --- |
| 1 · Wrist pointing: brain signal on a learned forecast | [open](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) | [WristMotion-Recorded-Replay.zip](benchmarks/wrist-pointing-temporal/WristMotion-Recorded-Replay.zip) | One trial of the wrist-pointing dataset, prepared with the [study's converter](benchmarks/wrist-pointing-temporal/#replay-a-recorded-trial) |
| 2 · Wrist pointing: muscle signal on a straight-line fit | [open](https://eliminatenoise.github.io/NeuroTranslation/wrist-pointing/) | [wrist-pointing-muscle-r1-preview.zip](benchmarks/wrist-pointing-muscle/wrist-pointing-muscle-r1-preview.zip) | Invented inputs that you can change |
| 3 · Wrist pointing: muscle signal on the learned forecast | [open](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) | [WristMotion-Forearm-Browser.zip](benchmarks/wrist-forearm-transfer/WristMotion-Forearm-Browser.zip) | One of the dataset's own ZIP files, opened as it comes |
| 4 · Everyday tasks: wrist angle from the muscle signal | [open](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) | [UJI-Daily-Wrist-Browser.zip](benchmarks/uji-wrist-emg/UJI-Daily-Wrist-Browser.zip) | Half a second of seven forearm channels, as JSON |
| 9 · Pinch and lift: grip force | [open](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) | [WAY-EEG-GAL-grip-force-browser.zip](benchmarks/way-grip-force/WAY-EEG-GAL-grip-force-browser.zip) | One lift, saved as JSON with the converter on the page |
| 10 · Pinch and lift: grip force, timed from the squeeze | [open](https://eliminatenoise.github.io/NeuroTranslation/contact-force/) | [NeuroTranslation-Grip-After-Contact-Comparison.zip](benchmarks/way-contact-force/NeuroTranslation-Grip-After-Contact-Comparison.zip) | A prepared JSON capture of one lift |
| 11 to 13 · Paced grip | [open](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | [HYGRIP-trial-replay.zip](benchmarks/hygrip-force/trial-replay/HYGRIP-trial-replay.zip) | One right-hand trial, converted from the dataset's `hygrip.h5` |
| 14 to 17 · One finger | [open](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | [Hyser-Index-Voltage-Reader.zip](benchmarks/hyser-index/downloads/Hyser-Index-Voltage-Reader.zip) | The dataset's own `.hea` and `.dat` files |
| 18 · Pinch: muscle signal | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) | [CEMHSEY-Pinch-Reader.zip](benchmarks/cemhsey-pinch/downloads/CEMHSEY-Pinch-Reader.zip) | One trial, converted with the Python tool in the ZIP |
| 19 · Pinch: five electrode grids | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) | [CEMHSEY-Array-Reader.zip](benchmarks/cemhsey-arrays/downloads/CEMHSEY-Array-Reader.zip) | The dataset's own MATLAB file for one trial |
| 21 · Pinch at new targets: a practice pinch, then a second one | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/) | [CEMHSEY-Pinch-Transfer.zip](docs/cemhsey-transfer/CEMHSEY-Pinch-Transfer.zip) | Two recordings of one person at the same target |
| 23 · Pinch: a correction learned from other people | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/reader/) | [CEMHSEY-Population-Forecasts.zip](docs/cemhsey-phase/reader/CEMHSEY-Population-Forecasts.zip) | Two recordings from each of three people to fit, one from someone else to test |

Most readers open with an invented example, so you can try one before you have a file. The pinch readers also ship with invented weights, and say so on the page: the weights fitted in the pinch studies are not published.

Several studies have a Python runner as well, for scoring many recordings at once. Each study's own page says how: [the studies](benchmarks/README.md).

## A page that runs from your own computer

The general model's five-sensor walking fit has a page of its own that is not on the site: a small Python program on your computer serves it to your browser. Install Python 3.13 and the two libraries in the folder's [`requirements.txt`](benchmarks/daily-sports-limbs/requirements.txt), then open the launcher for your system, or run `python serve.py` in [the folder](benchmarks/daily-sports-limbs/README.md). Pick a sensor on the torso, an arm or a leg to see its last 16 readings, the model's forecast and what the sensor recorded 120 ms after the last of them. The walk it shows is one the model was fitted on, so it shows the model running, not how well it would forecast someone new.

| Your computer | Launcher |
| --- | --- |
| Windows | [Open on Windows.cmd](<benchmarks/daily-sports-limbs/Open on Windows.cmd>) |
| macOS | [Open on macOS.command](<benchmarks/daily-sports-limbs/Open on macOS.command>) |
| Linux | [Open on Linux.sh](<benchmarks/daily-sports-limbs/Open on Linux.sh>) |

## Two results pages, and the wrist models on an invented example

Two folders under `benchmarks/` hold a page of their results and a launcher for each system that opens it in your browser. The page computes nothing and needs no network.

| Folder | What the page shows | Windows | macOS | Linux |
| --- | --- | --- | --- | --- |
| [Study 28](benchmarks/paired-wrist-forecast/README.md) | The general model's three wrist fits, with and without forearm EMG and scalp EEG, against the earlier forecasts | [Open on Windows.cmd](<benchmarks/paired-wrist-forecast/Open on Windows.cmd>) | [Open on macOS.command](<benchmarks/paired-wrist-forecast/Open on macOS.command>) | [Open on Linux.sh](<benchmarks/paired-wrist-forecast/Open on Linux.sh>) |
| [Row 29](benchmarks/wrist-forearm-correction/README.md) | A correction from forearm EMG, scored on the people the wrist models were fitted on (not a test) | [Open on Windows.cmd](<benchmarks/wrist-forearm-correction/Open on Windows.cmd>) | [Open on macOS.command](<benchmarks/wrist-forearm-correction/Open on macOS.command>) | [Open on Linux.sh](<benchmarks/wrist-forearm-correction/Open on Linux.sh>) |

In study 28's folder, one command also runs its three fitted models. With Python, NumPy and PyTorch installed, run `python -B predict.py --input example.json --mode all` in [the folder](benchmarks/paired-wrist-forecast/README.md): it prints each model's forecast of the two wrist angles, in degrees, and the variance the model expects around each, in degrees squared. The input, `example.json`, is a made-up history of the wrist, the forearm and the scalp, so the output says nothing about accuracy; `example-predictions.json` holds what the command should print.

## Four seconds of walking

[Download the offline knee reader](models/knee-stride.zip), unpack all of it, and open the launcher for your system. On an invented walk it compares the forecasts trained for the knees and the general model's with copying the previous stride. To run the fitted transformer and straight-line corrections yourself, with Python and NumPy, use the launcher for your system in [the model download](models/knee-stride-model.zip); it runs them on an invented example. [The reader's source and how to build it (ZIP)](models/knee-stride-source.zip)

## Five finger forecasts

Open [the reader](https://eliminatenoise.github.io/NeuroTranslation/finger-signals/), or [download it](models/finger-signals.zip), unpack all of it and open the launcher for your system: it runs offline, on invented inputs. To run the fitted models on an invented input with Python and NumPy (and PyTorch for the transformer), follow [the study's example](models/cortical-glove/README.md#run-an-invented-example).

## How much each finger will move

Open [the reader](https://eliminatenoise.github.io/NeuroTranslation/finger-motion/), or [download it](models/finger-motion.zip), unpack all of it and open the launcher at the top of the folder for your system (or open `docs/finger-motion/index.html` directly). The download also holds the study, the six models for the browser, seven for Python, invented examples and both licences.

## Calibrated finger movement

[Download the finger-transfer reader and model](models/finger-transfer.zip), extract the folder and open the launcher for your system. You can also open `docs/finger-transfer/index.html` in a browser. [Model and reproduction instructions](models/finger-transfer/)

## Knee turning moments

[Download the knee-moment reader and materials](models/knee-moment.zip), extract the folder and open the launcher. The reader predicts signed moments from an invented gait. [Run the shared checkpoint with Python](models/neurotranslate-0.0/load/)

## Forecast the force underfoot during a walk

[Open the two-plate viewer](https://eliminatenoise.github.io/NeuroTranslation/walking-force/) or [download its ZIP](models/walking-force.zip) and extract it. Open **index.html** or the launcher labelled for Windows, macOS or Linux. All six fitted models run in the browser without a connection. Try the same marker history twice and change one muscle signal. The recorded error comparison sits below the invented walk.

[Download the Python study](models/overground-force-forecast.zip) for the fitted weights, NumPy command and source-to-score instructions. [Download the source reader](models/overground-source-reader.zip) to reconstruct the trial selection locally from the original deposit. For the separate estimate on the plate under the right foot, [open the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#right-plate).

## Where a walking marker moves next

[Open the six-point walking model](https://eliminatenoise.github.io/NeuroTranslation/walking-landmarks/) or [download the offline viewer](models/walking-landmarks.zip). Extract the ZIP, then open **index.html** or the launcher marked for Windows, macOS or Linux. Rotate the invented walker and compare each forecast with where its marker actually goes in the example. To make a forecast from nine positions of a single marker, [open the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#point-motion) or [download its offline viewer](models/movement-browser.zip) and select **One tracked body point (mm)**. [See measured marker travel on a stride](https://eliminatenoise.github.io/Interoceptomics/stride-signals/).

To run the six-marker forecast with Python and NumPy, [download the study and fitted models](models/walking-landmark-forecast.zip), extract the ZIP and use its launcher. Its README gives the input format and the steps to repeat the study from the original deposit.

## Forecast the response to an arm cue

[Give the model a right-arm instruction](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#cued-arm). To run it offline, [download the shared browser model](models/movement-browser.zip), extract it and open **index.html**. Press **F** to focus the instruction field. A browser with local speech recognition can also insert a dictated phrase for you to review and submit. Choose a phrase for one of the seven pictured tasks and compare the changes predicted at the elbow, forearm and index finger. [Python model](models/neurotranslate-0.0.zip) · [Inputs and outputs](models/neurotranslate-0.0/cued-arm/)

For the separate elbow experiment, [open the viewer](https://eliminatenoise.github.io/NeuroTranslation/elbow-cue/) or [download it for offline use](docs/elbow-cue-offline.zip). Extract the whole ZIP, then open **index.html** or the launcher marked for your operating system. [The Python download](models/cue-elbow-forecast.zip) includes the fitted coefficients, an invented input, a reference forecast and its own Windows, macOS and Linux launchers. [Read both experiments](https://eliminatenoise.github.io/NeuroTranslation/papers/cued-arm/) · [See the recording setup](https://eliminatenoise.github.io/Interoceptomics/scalp-and-arm/)

## Compare a cued arm forecast across people

[Open the arm Transformer](https://eliminatenoise.github.io/NeuroTranslation/arm-transfer/) or [download the offline reader](docs/arm-transfer-offline.zip). Extract the ZIP. Open **index.html** or the launcher marked for Windows, macOS or Linux. Change the cue or an invented sensor reading to compare forecasts. The experiment’s recorded errors appear below the controls.

[Download the fitted arm model](models/arm-transfer-model.zip) to make the same nine predictions from a local input. Its launcher runs an invented example with Node.js or Python and NumPy. [Open the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#arm-transfer) to try its earlier-run correction, or [download the shared browser](models/movement-browser.zip). [Study and instructions](https://eliminatenoise.github.io/NeuroTranslation/papers/arm-transfer/)

## Try an arm forecast with scalp or eye readings

[Open the reader](https://eliminatenoise.github.io/NeuroTranslation/scalp-forecast/) or [download its offline version](docs/scalp-forecast-offline.zip). Extract the ZIP and open the launcher for Windows, macOS or Linux, or open **index.html**. Change the movement cue, then switch the recordings the model can use. The recorded test results appear beneath the invented example.

[Download the fitted Transformer](models/scalp-forecast-model.zip) to run a forecast with Node.js or Python and NumPy. [Open the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#early-signals) to try an adjustment for activity shared with the eye electrodes. Its [offline browser](models/movement-browser.zip) also includes the earlier movement experiments. [Read the illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/scalp-forecast/)
