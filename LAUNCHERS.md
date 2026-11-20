# Launchers and offline copies

Everything here runs in a browser. A launcher is a shortcut that opens the right page. An offline copy is a ZIP that holds the page itself, so it works with no network.

## A shortcut to the app

The shortcut opens the app at its palm replay. It needs a network connection.

| Your computer | What to do |
| --- | --- |
| Windows | Download [`NeuroTranslation-Windows.url`](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-Windows.url) and open it. |
| macOS | Download [`NeuroTranslation-macOS.webloc`](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-macOS.webloc) and open it. |
| Linux | Download [`NeuroTranslation-Linux.desktop`](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-Linux.desktop) and open it the way your desktop opens launchers. For an entry in the applications menu, extract [the launchers ZIP](https://eliminatenoise.github.io/NeuroTranslation/launchers/NeuroTranslation-Launchers.zip) and run `sh Install-NeuroTranslation-Linux.sh` in that folder. |

Keep the file extensions, and follow your system's usual prompts about a downloaded file. If a shortcut opens as text, take it from the ZIP instead. The Linux installer writes one menu entry for your user, leaves existing entries alone and opens no browser.

Checked: the format of the Windows and macOS shortcuts, and the Linux installer in an isolated folder. Not checked: opening the shortcuts on a real Windows or macOS machine. [Checksums](docs/launchers/SHA256SUMS)

## Offline copies of the study readers

Each ZIP holds one reader and its own launchers for Windows, macOS and Linux. Unpack the whole folder, then open the launcher for your system, or open `index.html`. A recording you open is read on your computer and goes nowhere.

| Reader | Online | Offline ZIP | The recording it reads |
| --- | --- | --- | --- |
| Wrist pointing, recorded trials | [open](https://eliminatenoise.github.io/NeuroTranslation/wrist-replay/) | [WristMotion-Recorded-Replay.zip](benchmarks/wrist-pointing-temporal/WristMotion-Recorded-Replay.zip) | One trial of the wrist-pointing dataset, prepared with the [study's converter](benchmarks/wrist-pointing-temporal/#replay-a-recorded-trial) |
| Wrist pointing, with and without the muscle signal | [open](https://eliminatenoise.github.io/NeuroTranslation/wrist-pointing/) | [wrist-pointing-muscle-r1-preview.zip](benchmarks/wrist-pointing-muscle/wrist-pointing-muscle-r1-preview.zip) | Invented inputs that you can change |
| Wrist pointing, forearm correction | [open](https://eliminatenoise.github.io/NeuroTranslation/wrist-forearm/) | [WristMotion-Forearm-Browser.zip](benchmarks/wrist-forearm-transfer/WristMotion-Forearm-Browser.zip) | One of the dataset's own ZIP files, opened as it comes |
| Wrist angles in everyday tasks | [open](https://eliminatenoise.github.io/NeuroTranslation/daily-wrist/) | [UJI-Daily-Wrist-Browser.zip](benchmarks/uji-wrist-emg/UJI-Daily-Wrist-Browser.zip) | Half a second of seven forearm channels, as JSON |
| Grip force during a lift | [open](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) | [WAY-EEG-GAL-grip-force-browser.zip](benchmarks/way-grip-force/WAY-EEG-GAL-grip-force-browser.zip) | One lift, saved as JSON with the converter on the page |
| Grip force after the squeeze registers | [open](https://eliminatenoise.github.io/NeuroTranslation/contact-force/) | [NeuroTranslation-Grip-After-Contact-Comparison.zip](benchmarks/way-contact-force/NeuroTranslation-Grip-After-Contact-Comparison.zip) | A prepared JSON capture of one lift |
| Paced grip, sensor voltage | [open](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/) | [HYGRIP-trial-replay.zip](benchmarks/hygrip-force/trial-replay/HYGRIP-trial-replay.zip) | One right-hand trial, converted from the dataset's `hygrip.h5` |
| One finger, sensor voltage | [open](https://eliminatenoise.github.io/NeuroTranslation/hyser-index/) | [Hyser-Index-Voltage-Reader.zip](benchmarks/hyser-index/downloads/Hyser-Index-Voltage-Reader.zip) | The dataset's own `.hea` and `.dat` files |
| Pinch, overall muscle amplitude | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-pinch/) | [CEMHSEY-Pinch-Reader.zip](benchmarks/cemhsey-pinch/downloads/CEMHSEY-Pinch-Reader.zip) | One trial, converted with the Python tool in the ZIP |
| Pinch, five electrode grids | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/) | [CEMHSEY-Array-Reader.zip](benchmarks/cemhsey-arrays/downloads/CEMHSEY-Array-Reader.zip) | The dataset's own MATLAB file for one trial |
| Pinch, a practice attempt and a second one | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/) | [CEMHSEY-Pinch-Transfer.zip](docs/cemhsey-transfer/CEMHSEY-Pinch-Transfer.zip) | Two recordings of one person at the same target |
| Pinch, a correction learned across people | [open](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/reader/) | [CEMHSEY-Population-Forecasts.zip](docs/cemhsey-phase/reader/CEMHSEY-Population-Forecasts.zip) | Two recordings from each of three people to fit, one from someone else to test |

Most readers open with an invented example, so you can try one before you have a file. The pinch readers also ship with invented weights, and say so on the page: the weights fitted in the pinch studies are not published.

Several studies have a Python runner as well, for scoring many recordings at once. Each study's own page says how: [the studies](benchmarks/README.md).
