# Find a recorded hand movement from your own words

A person was setting up a printer. A HoloLens headset estimated the positions of 26 joints in their right hand. An observer later described five parts of the recording. Type “press the button” and compare which part each model selects. Click a time range to see what the headset tracked, rotate the view or scrub through individual samples. **Try a training example** reveals where the original observer’s sentence belongs. [Open the hand search](https://eliminatenoise.github.io/NeuroTranslation/hand-search/)

The word-count and attention models both put the button press first for that example. The headset interval starts at 42.65 seconds and ends at 47.65 seconds. This recording was in training. An arbitrary new description may fit more than one movement, or none. If every word is unfamiliar, the viewer lets you browse the five moments manually.

## Which information did the work?

The two movement models used the wrist and five fingertips. Fifteen distances describe the shape of the hand, and one measures how far the wrist has moved from its first usable position in the interval. The timing comparison uses the words too. It ranks the intervals by their duration, their position within the recording and how often tracking was available.

On **60 descriptions from ten assessment recordings**, each from a recording group excluded from fitting, the simpler movement model ranked the paired interval first 23.89% of the time. The attention model reached 23.59%. The timing comparison reached **35.56%** without hand coordinates. Random ordering reached 20.66%. Scores first average descriptions within each interval, intervals within a recording and recordings within each of six acquisition-code groups. Each group contributes equally. People and annotators may recur under different codes. Ten recording sessions remained in reserve. [Study, fitted weights and reproduction instructions](../../benchmarks/hand-language-retrieval/)

## What the viewer shows

The viewer preserves 3,419 original rows across five intervals. Hand tracking was missing throughout 1,039 of those rows. A missing joint leaves a gap. The sample slider follows the recording clock. The headset’s sensor timestamps can repeat on adjacent camera-aligned rows. Positions use the archive's spatial anchor and metres. The physical room origin, per-joint position error and camera-to-hand delay are unknown. The model searches recordings of past movement. It scores no brain or muscle signals here.

The browser computes a new text score for every candidate each time you search. It uses movement representations calculated from the training recording in advance. All searches and replays run locally. To use the viewer offline, save **[index.html](index.html)** and open it in a browser. The operating-system launchers in this folder open the same file. Linux Chromium was tested with the network disabled at desktop and phone-sized widths. Native Windows and macOS execution remains unverified.

The game uses the same files. Press **F**, type a description and choose **Find hand recording**, or open **M → Hand search**. [NeuroSurge game preview](https://github.com/eliminatenoise/NeuroSurge/pull/2)

## Source and rebuilding

The files in `app/` contain the text scorer, the 3D hand viewer and the search interface. `assets/` contains the model coefficients, saved candidate vectors, source sentences, tracking rows and their checksums. Run `npm ci` followed by `npm run build` from this folder to rebuild the single offline page. The public study includes the smaller 206-interval training and assessment feature edition. Its normal CPU entry points reproduce fitted weights, the gallery and the aggregate results.

Xin Wang, Taein Kwon and colleagues released the HoloAssist dataset with CDLA-Permissive-2.0. This edition selects five intervals from R031-12July-SmallPrinter, retains original observer descriptions and estimates of the right hand, and arranges the measurements for browser replay. The data agreement accompanies the derived recordings and is also embedded in the offline page. Project-authored software and fitted parameters carry the CC0 dedication. [Publisher](https://holoassist.github.io/) · [HoloAssist paper](https://doi.org/10.1109/ICCV51070.2023.01854) · [Data agreement](CDLA-Permissive-2.0.txt) · [CC0](LICENSE)
