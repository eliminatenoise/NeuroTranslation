# Fingertip touch

A plate presses against the finger, then moves sideways. An electrode records spikes from one sensory nerve fibre. This experimental edition uses the last 200 milliseconds of plate force and earlier spikes to forecast the number of spikes between 20 and 40 milliseconds ahead. An expected count can be a fraction. The example you can edit is invented.

Open **Touch study** for Windows, macOS or Linux from the top of the extracted NeuroTranslate folder. With Python 3.10 or later and NumPy installed, you can also run `python joint_demo.py --touch`. Choose any of the eight tasks and check the fingerprint under its forecast. [Results in your browser](https://eliminatenoise.github.io/NeuroTranslation/touch-feedback/) · [Full study PDF](https://eliminatenoise.github.io/NeuroTranslation/touch-feedback/fingertip-touch.pdf)

## Reproduce the result

1. Use the [source guide](data/README.md) to obtain the authors’ original files, prepare training and development windows, and create `held-features.npz` from the three test people. Keep the fourth, reserved participant separate.
2. To train from scratch, prepare the [seven earlier tasks](../inputs/README.md) and follow [the joint fitting recipe](fit/README.md). The [simpler models](controls/README.md) use elapsed time, earlier spike counts and, in two cases, force. The model for touch alone is included in `fit/touch-only.npz`.
3. To use the included weights, run `python held_forecasting.py predict held-features.npz predictions.npz` from this folder. Save the SHA-256 fingerprint the command prints. This file contains predictions for every eligible window before looking up its future count.
4. Run `python data/prepare_touch.py test-labels recordings held-labels.npz --features held-features.npz --predictions predictions.npz --prediction-sha256 RECORDED_DIGEST`, replacing the last word with your saved fingerprint. Run `python held_forecasting.py score predictions.npz held-labels.npz` and compare its scores with [the study results](study.json). Use new output filenames for a separate run.

Three test participants contributed 69,137 scored intervals. One additional forecast had a missing future reading. The touch-only model gave a lower average loss than the eight-task model for each test person. Substituting force from the previous slide changed the eight-task scores only slightly. The seven-task model remains the default launcher. The current experiment uses passive touch at the finger. Camera footage alone cannot supply the force and nerve readings required here.

The original data are by B. P. Delhaye, E. Jarocka, A. Barrea, J.-L. Thonnard, B. B. Edin and P. Lefèvre (2021), released under CC BY 4.0. This distribution includes derived population weights, aggregate results and preparation code. Obtain the recordings directly from the authors. [Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8169108/) · [Zenodo deposit](https://zenodo.org/records/4818439) · [Data licence](https://creativecommons.org/licenses/by/4.0/) · [Earlier model and software credits](../NOTICE.md)
