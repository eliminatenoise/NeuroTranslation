# Open NeuroTranslation

[Open Palm replay](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay) or [download a launcher for Windows, macOS or Linux](https://eliminatenoise.github.io/NeuroTranslation/START.html). These shortcuts lead to the same current replay as the browser link.

Import a prepared IACKD right-hand trial and choose **Compare estimates**. For an R1 trial, compare the fixed hand and EEG models. For R2, compare the original estimates with the estimates calibrated on the person's first recording. Files stay in your browser. [Prepare R1](benchmarks/scalp-eeg-palm-history/#replay-a-recorded-trial) · [Prepare R2](benchmarks/scalp-eeg-personal-calibration/#replay-a-second-recording) · [Import and alignment](demo/README.md)

- **Windows** — Download and open `NeuroTranslation-Windows.url`.
- **macOS** — Download and open `NeuroTranslation-macOS.webloc`.
- **Linux** — Open `NeuroTranslation-Linux.desktop` using your desktop’s usual launcher handling. For an application-menu entry, extract the ZIP and run `sh Install-NeuroTranslation-Linux.sh` in that folder.

The installer writes one per-user menu entry. It prefers the installed Omarchy opener and otherwise uses `xdg-open`. Installation opens no browser. An earlier entry from this installer still opens the preview. Choose **Palm replay** in its navigation. The installer preserves existing entries, including customized files and symlinks.

Keep the filename extensions and follow your operating system’s normal trust prompts. Opening the preview requires a network connection and browser. The shortcuts carry the URL only. The study parameters are served to the browser, and you provide the trial file. A general NeuroTranslate model and live decoding remain outside the preview.

Windows and macOS shortcut formats were checked. Isolated installation was tested on Linux. Native shortcut opening on Windows and macOS remains unchecked.

## Open the wrist models

The wrist studies have their own downloads and launchers. Open a study, download its ZIP and extract the folder before running the launcher for your system. The temporal model includes a three-seed convolutional ensemble. The muscle study compares fitted linear models using wrist history, surface EMG and scalp EEG. [Temporal forecast](benchmarks/wrist-pointing-temporal/) · [Surface EMG forecast](benchmarks/wrist-pointing-muscle/)

The [recorded-trial replay](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) runs the six fitted temporal models on a trial file in your browser. For offline replay, [download the standalone browser and desktop launchers](benchmarks/wrist-pointing-temporal/WristMotion-Recorded-Replay.zip), extract the folder and open the launcher for your system. Use the [trial converter](benchmarks/wrist-pointing-temporal/#replay-a-recorded-trial) to prepare a file from the original study.

To compare an original wrist movement with the learned forearm correction, [download the recorded-trial runner](benchmarks/wrist-forearm-transfer/WristMotion-Forearm-Recorded-Trial.zip), extract it and use the launcher for your system. The [study](./benchmarks/wrist-forearm-transfer/README.md) also includes a Python-only synthetic model demonstration.

The [forearm browser ZIP](benchmarks/wrist-forearm-transfer/WristMotion-Forearm-Browser.zip) runs all three trained models on an original wrist development recording without Python. Extract the entire folder, then open `index.html` or the included launcher for your system. The [hosted version](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) uses the same local recording reader.

The [UJI forearm estimator](benchmarks/uji-wrist-emg/UJI-Wrist-Supported-Forearm-Model.zip) has its own desktop launchers. Extract the full ZIP, open the launcher for your operating system, and follow its README to run the two trained models on a compatible input. The [study and replication code](benchmarks/uji-wrist-emg/) describe the required seven channels and the offline time convention.

The daily-activity wrist browser runs the UJI models on a compatible seven-channel window. For offline use, extract the whole archive, then open the launcher for your desktop or open `index.html`. [Open the browser preview](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) · [Download the browser and launchers](benchmarks/uji-wrist-emg/UJI-Daily-Wrist-Browser.zip)

## Open the grip-force forecast

The grip-force browser shows the past sensor window alongside four fitted forecasts. Open it online, or extract the browser ZIP and open its Windows, macOS or Linux launcher. You can also open `index.html` directly. [Open the browser forecast](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) · [Download the offline browser](benchmarks/way-grip-force/WAY-EEG-GAL-grip-force-browser.zip)

The separate Python runner can forecast batches of compatible windows. Extract its ZIP and open the launcher for your system to try an invented window with Python and NumPy. This launcher ran on Linux. Native Windows and macOS launches remain unchecked. [Download the Python runner](benchmarks/way-grip-force/WAY-EEG-GAL-grip-force-experimental-preview.zip) · [Study and input instructions](benchmarks/way-grip-force/)

The contact-triggered study has two offline Python runners. The ridge runner takes a compatible capture. The temporal CNN runner takes a window prepared through the forecast time. Both ZIPs include Windows, macOS and Linux launchers and start with invented readings. The European Commission supported the original recordings through WAY (FP7-ICT-288551). [Download both contact-triggered forecasts](benchmarks/way-contact-force/#run-the-forecasts) · [Original study acknowledgments](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/#ack1)
