# Can the scalp signal tell us where the head moves next?

A person walks heel to toe along a narrow treadmill beam. The head-mounted display tilts the view 20 degrees. The camera tracks what the head and the sacrum do next. Give a forecaster the direction of the tilt, the movement already seen, and the voltage recorded around the eyes, neck and lower legs. How much more can it learn from the scalp? [Peterson and Ferris, recording methods](https://doi.org/10.1016/j.dib.2021.107635)

## Rebuild the event windows

Use Git and Python 3.12 in a clean environment. Run the commands from this directory. Allow roughly 3 GB for the local record cache and outputs. Each download is checked against its original Git blob or the size and checksum in its versioned Git-annex pointer. A second run checks the existing recording bytes and keeps them.

```sh
python -m pip install -r requirements.txt
python acquire.py development prepared
python extract.py development prepared
python verify.py development prepared
```

Open `prepared/development.npz` with `numpy.load(path, allow_pickle=False)`. The two accompanying JSON files record each original file hash and each participant's exclusions. These local outputs retain the source participant codes. Run the same commands with `assessment` in place of `development` when reproducing the fixed models' test. The software has no acquisition command for the reserve recordings.

The first participant in the numerically sorted catalogue supplied the original feasibility check and stays in development. For the others, sort by the hexadecimal SHA-256 digest of the UTF-8 string `balance-stance-20261121:` followed immediately by the source participant folder name. The first 17 join development, the next six form the assessment group, and the last six stay in reserve. Each person contributes only their unique visual-rotation walking session. The selection is reproducible from the published catalogue. [OpenNeuro release 1.0.3](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)

## What one row contains

Set the clock at the logged visual event. The first stored sample at or after that event is `a`. The observation ends 32 samples later. The forecast asks how far the two markers will move in the following 32 samples. At 256 Hz that makes the forecast exactly 125 ms long. The logged event can fall between samples, so the end of the observation lies 125 to just under 129 ms after it. That timestamp comes from the experiment software. Physical display latency and the delay of a live acquisition system would need independent measurements.

| Local arrays | Interpretation |
|---|---|
| `person`, `event`, `block`, `cutoff` | Source participant code, original one-based rotation ordinal, early/middle/late third of the original rotation list (0–2), and zero-based final observed sample. Keep these as grouping and audit fields. |
| `direction` | Clockwise (+1) or counterclockwise (−1) visual-field rotation. It labels the scene. |
| `motion_mm` | 160 observed samples including the cutoff, expressed relative to each marker's position at that cutoff. Sacrum first, head second. Components follow the stored mediolateral, superior–inferior and anterior–posterior axes. Their anatomical signs remain unverified. |
| `future_delta_mm` | Measured three-dimensional change from cutoff to 125 ms later for those same two markers, in millimetres. |
| `eeg_mean_uv`, `eeg_rms_uv`, `eeg_good` | Mean and root-mean-square scalp voltage in eight consecutive bins of 20 samples, in microvolts. Each Boolean mask identifies which of the 128 ordered channels contributed. |
| `nuisance_mean_uv`, `nuisance_rms_uv`, `nuisance_good` | The same summaries and masks for two neck, three eye and eight leg channels. The extractor specifies the full channel order. |

A zero on one optical axis is an ordinary coordinate. Three simultaneous zeros on either marker can mean the camera lost it. Screen the whole path from eight samples before the movement history through eight samples after the endpoint. Drop an event if a required marker is missing or flagged bad, a coordinate is nonfinite, all three coordinates of either marker are zero together, or either marker jumps more than 20 mm between successive samples. The 20 mm threshold screens tracking quality. An accepted forecast therefore describes events where the later movement could also be measured.

Only the observed electrical history enters the voltage summaries. Missing or author-rejected electrodes have a false mask and a zero placeholder. A nonfinite sample on an available voltage channel excludes that event. The authors' offline electrical processing and optical resampling precede this extraction. Resampled positions can depend on later original camera frames. The source supports a forecast on the stored clock. Scalp voltage during walking can also contain movement, muscle and ocular signals. [Signal processing](https://doi.org/10.1016/j.dib.2021.107635) · [Original balance study](https://doi.org/10.1523/ENEURO.0207-18.2018)

## Which events survive?

The 18 development recordings contain 2,682 logged rotations. Of these, 2,430 events from 17 people pass the checks. One person's head marker stays at zero throughout the recording. Across the group, 250 events contain a zero-filled marker and two further events cross the step threshold. A total of 20 cross that threshold when overlapping flags are counted.

All six assessment participants supply usable events in both directions. Of 894 logged rotations, 880 pass. All 14 exclusions contain a zero-filled marker, and three of those also cross the step threshold. The published protocol describes 150 rotations per session. The BIDS tables and matching EEGLAB events contain 149 per selected walk. The reason for the difference remains unknown. [Protocol](https://doi.org/10.1016/j.dib.2021.107635) · [Archived measurements](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)

## Data credit

Steven M. Peterson and Daniel P. Ferris recorded and released the measurements. Their dataset metadata specifies CC0. This package supplies the reader and the measurement definitions. The original data are available directly from OpenNeuro. [Versioned data](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Dataset licence and citation request](https://github.com/OpenNeuroDatasets/ds003739/blob/f15449b6aecb83044b49a1798955e8a212a68fc1/dataset_description.json)
