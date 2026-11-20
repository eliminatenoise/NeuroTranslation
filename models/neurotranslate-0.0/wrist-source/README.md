# Rebuild the wrist forecast windows

A participant steers a cursor by turning the right wrist. At a chosen point in the reach, the input stops. The question is where the wrist will be a quarter of a second later. A device on the wrist supplies two measured angles to check the forecast. Electrodes on the scalp and forearm record what happens during the same reach. [Study and apparatus](https://doi.org/10.1038/s41597-026-07287-z)

## Run the extraction

Use the six original ZIP files listed in `archives.json`. The manifest gives each Figshare file ID, filename, size and SHA-256. Place the intact files in a local folder called `archives`. From this recipe's directory, run the commands below in a Python 3.11+ environment. The verified run used Python 3.13.15 and NumPy 2.4.6 on Linux. Choose a private output folder on a filesystem that supports hard links, such as ext4 or NTFS. [Six archive identities](archives.json) · [Figshare version 3](https://doi.org/10.6084/m9.figshare.29666735.v3)

```sh
python -m pip install numpy==2.4.6
python -B extract_wrist.py --archives archives --output train.npz
```

The script checks the six archive hashes before decoding their respective runs. It checks the source electrode order and matches every encoder word between the electrical and motion tracks. At the end it checks the shape, data type and SHA-256 of all twelve output arrays. Keep the reconstructed participant records local. The public recipe contains code, file identities and checksums. [Expected array identities](array-hashes.json) · [Extraction code](extract_wrist.py)

## Read one forecast window

Let `T` be a target row in a single recording. Rows run at 512 Hz, or 1.953125 ms per row. After the movement cue we use targets at 384, 512, 640, 768, 896 and 1024 ticks. They correspond to 0.75 through 2.00 seconds in steps of 0.25 seconds. The final input row is `T-128`. Its measured angles are the anchor. The 256 rows from `T-383` through `T-128`, both ends included, give sixteen consecutive bins of sixteen samples each. Each bin covers 31.25 ms on the stored grid. The encoder updates at about 100 Hz, so repeated values on the 512 Hz grid stay repeated. Physical sensor and instrument delays remain unknown. [Timing in the source study](https://doi.org/10.1038/s41597-026-07287-z)

| Bin columns (zero-based) | What is stored |
| --- | --- |
| 0–1 | Mean wrist extension and radial deviation in degrees, each relative to its final measured anchor. Extension is positive on the first axis. Tilt towards the thumb is positive on the second. |
| 2–5 | Four forearm surface EMG amplitudes in microvolts. For each pair M1 through M4, subtract R from L at each of the sixteen source rows. Square those differences, average them, then take the square root. |
| 6–13 | Eight signed scalp EEG means in microvolts. The order is C3, C1, Cz, C2, C4, CP3, CPz, CP4. |

In the original EDF files, the eight scalp electrodes come first in the order above. The next eight channels are M1L, M1R, M2L, M2R, M3L, M3R, M4L and M4R. The source stores one microvolt per integer count on these channels. The encoder words use a different scale. For each unsigned 16-bit word `w`, compute `(25*w/65535 - 12.5) * 180/pi` degrees and reverse the sign of the second axis. A zero word or absolute angle above 180° is invalid. Each eligible trial must have valid encoder data throughout all six histories and target rows, finite scalp and muscle signals on all input rows, and all six targets within the cued movement interval. This selection uses the availability of all six target readings and is applied offline. Forecasts use only values available at the cutoff. One missing run and one invalid trial leave 47 runs, 1,879 complete trials and 11,274 forecast windows. [Source decoding](decode_source.py) · [Window and eligibility rules](features.py)

`anchor` and `target` hold the measured two-axis angles, in degrees, at the cutoff and target respectively. An angle-change model learns `target - anchor`. Add its predicted change to the measured anchor to score against the absolute target. `past` is the measured angle 64 stored rows before the anchor. All voltage bins, axis order and angle signs stay in the human wrist device's frame. Rat tracking and camera coordinates have their own units and frames.

`person`, `block`, `trial` and `slot` identify each row. People and slots start at zero, as do the original within-run trial indices. Task block 1 corresponds to archive run 03. `parent` identifies the recording. `cue` and `target_tick` count rows from the start of that recording. `donor` points to the next eligible trial of the same person and block at the same slot, wrapping on the last eligible trial. Swapping one stream to that donor provides a control for pairing. Keep all windows from a person together for fitting or scoring. For each leave-one-person-out fold, calculate input and target scales from its five fitting people. These six people came from the designated training set and have contributed to earlier development work.

To construct coarser input bins, group adjacent complete bins. Average their scalp or angle means. For a longer forearm RMS, square the short-bin RMS values, average the squares, and take the square root. These formulas use the equal number of source samples in each bin. Retain the common endpoint when forecasting from all streams. The anchor-relative angles use information available at that endpoint.

Scalp and forearm voltages are simultaneous observations. Movement and electrode contact can influence both. Spinal activity, peripheral nerve traffic, muscle force and sensory feedback were unmeasured. The source supplies neither a sequence of neural transmission events nor a language label for each movement. [Source study](https://doi.org/10.1038/s41597-026-07287-z)

## Attribution

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz published the EEG-EMG-WristMotion Dataset v3 under Creative Commons Attribution 4.0 International. NeuroTranslation converted the two encoder axes to signed degrees and computed time-windowed scalp means, forearm amplitudes and anchor-relative wrist angles. Attribute the authors and identify these changes when using the derived data. The deposit's CC BY 4.0 terms apply to the data. The original project code and documentation use CC0. [Source dataset](https://doi.org/10.6084/m9.figshare.29666735.v3) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Project code dedication](LICENSE)
