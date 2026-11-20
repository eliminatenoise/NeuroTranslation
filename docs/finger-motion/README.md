# Which fingers follow the cue?

A participant saw the name of a finger and moved at their own pace. Can an electrical recording from the brain’s surface add anything to the instruction on the screen? This offline companion compares six fitted models. Each estimates the size of the next changes in five glove sensors.

## Try it

Open `index.html` in a current browser, or use the launcher for Windows, macOS or Linux. On the hosted page, **Save offline** makes a single HTML file with its code, six fitted models, recorded results and rights notices. It opens directly from disk. The page makes its calculations locally.

Choose the **finger named by the cue**. Keep the 90 Hz rhythm fixed and change the finger. The cortex-only estimates stay fixed. Now keep the cue fixed and change the rhythm. The cue-only estimates stay fixed. **Ridge** and **Transformer** each show the estimates for cue alone, cortex alone and both together. Arrow keys operate the selectors, slider and model control.

The example uses two invented waves at 24 and 90 Hz across 46 ordered contacts. Contact number sets each wave’s phase and amplitude by a fixed formula. The 90 Hz amplitude also grows over the 280 ms example. The slider scales just that component from zero to twice its original amplitude. These arbitrary contact patterns carry no anatomical assignment. The source feature extractor computes four overlapping 160 ms summaries from each waveform. The page uses those summaries for the nine slider positions and evaluates the fitted weights on each change. No glove reading enters these six models. No participant contributed an example waveform or a measured outcome for the controls.

## What was measured

Starting just after the cutoff, the study takes glove counts at +40, +80, +120 and +160 ms. For each finger it takes the size of three successive changes and averages them. The unit is stored glove counts per nominal 40 ms step. Bending and straightening can both produce a large value. The measurements give neither joint angles nor independent device timestamps.

Fifty-two earlier trials supplied the fits. Twenty-three later trials from the same person’s development recording supplied the comparison. Each model and baseline received the same trial weight. The analysis normalized each finger’s absolute error by its training-target standard deviation before averaging the five.

Cue-only ridge had the lowest error, 0.28779. Adding the correctly paired cortical signal raised the ridge error to 0.35449 and the Transformer error from 0.28921 to 0.32079. The paired gains over cue alone were −0.06669 for ridge (95% interval −0.07675 to −0.05736) and −0.03158 for the Transformer (−0.05699 to −0.00814). A separate ridge using only past glove readings scored 0.40320. Only that comparator received past glove values.

Ten disjoint pairs from twenty of those later trials permitted a second question. Could the models predict how the measured motion differed between repetitions of the same cue? Zero predicted difference beat both combined models. There were two thumb-cue pairs, two index, three middle, three ring and no little-finger pair. All five sensors contributed outcomes. The page includes the same-cue earlier-trial control, paired 95% intervals and the model-family comparison. Neither family met all the prespecified criteria for an advantage within a cue. The experiment concerns one recording. Independent clock agreement, transfer to other people and live control remain open.

## Source and rebuild

The repository stores this companion under `docs/finger-motion/` and the study under `models/finger-motion/`. The source of each browser calculation is in `src/`. The build verifies the study input byte hashes in `src/inputs.sha256.json`, reads the published fitted parameters, constructs invented signal summaries and embeds everything in a single page. The decoder’s `METHOD.md` and `results.json` contain the complete design, individual-finger errors and paired intervals. [Study files](../../models/finger-motion/)

From this directory, with Python 3.11+ and NumPy installed, run

```sh
python -B build.py
```

To build from another extracted study directory, run `python -B build.py --model /path/to/finger-motion`. Opening the finished HTML requires only a browser. Use `sha256sum -c SHA256SUMS` to verify the published companion files on Linux.

Kai Joshua Miller deposited the source recordings in the Stanford Digital Repository. Fitted parameters, aggregate findings, model-derived outputs and the scientific account share the source’s CC BY-SA 4.0 licence. Original viewer code and the invented waveform generator use CC0 1.0. The original ethics statement and source conditions are in the page under **Methods, source and rights** and in the local rights file. [Data record](https://purl.stanford.edu/zk881ps0522) · [Original experiment](https://doi.org/10.1371/journal.pcbi.1002655) · [Rights and modifications](RIGHTS.md)
