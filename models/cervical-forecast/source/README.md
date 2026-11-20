# Read the original neck-voltage recordings

A volunteer lay still while electrodes recorded the response to a pulse at the left wrist. This reader retrieves three short stretches of voltage around each recorded pulse. You get the same stretches from five electrodes on the same clock, so you can compare the signal at the armpit with the signal a few milliseconds later at the neck.

Birgit Nierula and colleagues collected the recordings and released them under CC0. The reader uses version 1.0.0 of their OpenNeuro dataset *Somatosensory evoked potentials in the human spinal cord to mixed nerve stimulation*. [Dataset and authors](https://doi.org/10.18112/openneuro.ds004388.v1.0.0) · [Original study and recording methods](https://doi.org/10.1371/journal.pbio.3002828)

## Get the data

Open a terminal in the folder containing `acquire.py`. Use Python 3.10 or later with NumPy installed. Run the first command for the four people used to develop the models. Run the second for the six people reserved to assess them. Both commands use the same output directory. Replace `python` with `python3` or `py` if that is the Python launcher on your computer.

```sh
python acquire.py --group development --output ./recordings
python acquire.py --group assessment --output ./recordings
```

For a single recording, add `--participant sub-001` to the development command. An interrupted download can resume from the same directory. Add `--offline --workers 1` to check the saved ranges and rebuild each file without a network connection. A different file at an existing output path triggers an error. A fresh directory starts a separate copy.

## Read one file

Each `.npz` file contains 80 pulse events for one person. The three voltage arrays have axes **event, time, channel**. The column order is **Biceps, SC6, Thumb, CP4, ECG**. Time advances by 0.1 milliseconds per row. `event_samples` gives the starting frame of each pulse in the continuous recording, counted from zero.

| Array | Time relative to pulse | Shape |
|---|---|---|
| `baseline` | −15 to before −10 ms | 80 × 50 × 5 |
| `early` | +5 to before +8 ms | 80 × 30 × 5 |
| `late` | +12 to before +14 ms | 80 × 20 × 5 |

```python
import numpy as np

with np.load("recordings/development-sub-001.npz", allow_pickle=False) as data:
    first_event_neck_microvolts = data["late"][0, :, 1]
    print(first_event_neck_microvolts)
```

The name `Biceps` marks where the researchers placed the electrodes. That channel records surface nerve voltage at the left armpit. `SC6` records the voltage between the skin over the sixth neck vertebra and the skin over the sixth thoracic vertebra. `Thumb` records muscle voltage, `CP4` scalp voltage and `ECG` the heart’s electrical activity. The recorded values retain their original references, signs and units of microvolts. Heart, muscle and stimulus-related fields can reach the neck electrode. These recordings alone cannot identify which tissue produced a particular voltage or establish a direction of conduction. [Recording methods](https://doi.org/10.1371/journal.pbio.3002828)

## Check what was read

`sources.json` lists the ten chosen recordings, their source URLs and their expected SHA-256 hashes. The selection used median-nerve run 03 wherever it existed and otherwise the lowest numbered median-nerve run. In each recording the reader takes the first 80 matching events. It compares the channel order and event times in the publisher’s tables with those in the native recording header. It requests only the needed header sections and the complete interleaved frames for the three windows. The five columns enter the output without additional filtering, rejection or scaling.

Each `.npz` has a matching `sub-XYZ-receipt.json` with the output hash, channel order, electrode references and exact versioned byte ranges. The publisher supplies the hashes of its full recording files. The reader separately hashes every downloaded slice and checks the final file against the expected output. Verify the displayed hash to confirm which file you have.
