# A quarter-second of balance

Tilt the scene around someone balancing on a narrow beam. Eight electrodes on the lower legs pick up changes in muscle voltage. Cameras follow a marker near the base of the spine, over the sacrum. Can the same short history tell us how much electrical activity comes next in each leg muscle and where the marker will go? Steven M. Peterson and Daniel P. Ferris recorded the two signals while the same people stood and walked. The source dataset is available under CC0. [Recordings, version 1.0.3](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Methods and equipment](https://doi.org/10.1016/j.dib.2021.107635) · [Original balance study](https://doi.org/10.1523/ENEURO.0207-18.2018)

## Rebuild the measurements

Use Git and Python 3.12. Run these commands from the reader directory in a clean Python environment. Allow 6 GB of disk space for both stages. The download checks the Git tree and compares every recording with the size and checksum stored in its versioned Git-annex pointer. The extraction checks the bytes again. All participant-level records stay under the local directory you supply.

```sh
python -m pip install -r requirements.txt
python acquire.py development prepared
python extract.py development prepared
python verify.py development prepared
```

These commands produce `prepared/development.npz`, an inventory of source files in `development-files.json`, and the event exclusions and coverage in `development-qc.json`. Load the arrays with `numpy.load(path, allow_pickle=False)`. To reproduce the final evaluation after freezing the model and scoring code, run the same three commands with `assessment` in place of `development`.

The split follows whole people. Sort the 30 source participant folders by number. The first person supplied the original feasibility check and remains in development. For each remaining person hash the UTF-8 string `balance-stance-20261121:` followed by the folder name using SHA-256. Sort the hexadecimal digests in ascending order. Assign the first 17 to development and the next six to assessment. The remaining six stay in reserve. The acquisition commands select only the unique visual-rotation standing and walking sessions in the requested group. Earlier work examined the six assessment participants’ walking recordings for a different outcome. Their standing recordings and the muscle and path targets were new to this study.

## What the model can see

Each row starts from a clockwise or counterclockwise visual rotation. Call the first stored sample at or after the logged onset `a`. Observation ends at `c = a + 32`. The two targets share the following 32 samples, from `c + 1` to `c + 32`. At the archived 256 Hz, that forecast spans 125 ms. Thus the last forecast sample falls about a quarter of a second after the logged rotation. The scene's physical display time is uncertain.

| Array | Meaning |
|---|---|
| `sacrum_mm` | The 160 observed marker positions through sample `c`, relative to the position at `c`, in millimetres. The axes follow the stored mediolateral, superior–inferior and anterior–posterior order. Their anatomical signs remain unverified. |
| `leg_uv` | The same 160 samples of signed surface muscle voltage in microvolts. Read the four left muscles first, then the four right muscles. Within each leg the order is tibialis anterior, soleus, medial gastrocnemius and peroneus longus. |
| `posture`, `direction` | Standing (0) or walking (1), and the direction of the imposed visual tilt, clockwise (+1) or counterclockwise (−1). |
| `future_rms_uv` | One amplitude per muscle. Square its next 32 voltage readings, average them, then take the square root. For a previous-amplitude baseline, repeat the calculation on the final 32 observed readings. |
| `future_path_mm` | All 32 subsequent three-dimensional sacrum positions relative to the position at `c`, in millimetres. |
| `person`, `event`, `cutoff`, `block` | Local grouping and audit fields. These give the source participant code, original one-based rotation ordinal, zero-based sample `c`, and early/middle/late third of the unfiltered rotation list (0/1/2). |
| `posture_qualified`, `paired` | Analysis masks. The first requires usable events in both directions in the row’s posture. The second requires both directions in both postures for that person. |

Only the first three table rows supply predictors. Surface electrodes measure voltage at the skin. Muscle force, a spoken instruction and a person's intended movement would require other observations. The source combined filtered electrical signals and resampled optical positions on one stored clock. The forecaster therefore operates on an offline record. [Signal processing](https://doi.org/10.1016/j.dib.2021.107635)

## Which rotations count?

The recorded channel names, types and units must agree between the BIDS channel table and EEGLAB header. Check the visual event against the original code and one-based sample latency, the tabulated zero-based sample and the onset in seconds. The clocks must agree within 0.01 sample and identify the same first stored sample at or after onset.

All eight leg channels and all three sacrum axes must be present and marked good by the authors. Keep a row only when its 160 observed samples are finite on every author-approved electrical channel, and its leg voltages stay finite across both history and target. Exclude an event when all eight leg channels are zero at any one sample or any single leg channel holds one exact value for at least 32 consecutive samples touching that interval.

Check the marker from eight samples before the first observed position through eight samples after the last forecast position. Reject nonfinite coordinates, three simultaneous zeros, any step over 20 mm or any run of at least 32 identical nonzero positions touching this interval. A zero on one axis can be a valid position. The local QC ledger retains every applicable flag for each excluded rotation and uses its first flag as the primary reason. The head marker plays no part in eligibility.

This test describes events whose later movements and muscle activity could both be measured. Losing a marker during a large movement can change which events survive. The subjects also stood before they walked for each type of perturbation, so a difference between postures can include time, fatigue or adaptation. [Experimental design](https://doi.org/10.1016/j.dib.2021.107635)

## How much of the record was usable?

| Group | People with both directions in both postures | Standing rotations kept / logged | Walking rotations kept / logged |
|---|---:|---:|---:|
| Development | 18 of 18 | 2,600 / 2,682 | 2,579 / 2,682 |
| Assessment | 6 of 6 | 879 / 894 | 880 / 894 |

Each selected session contained 149 logged rotations. The protocol describes 150 per session. The cause of that difference is unknown. Every one of the 29 excluded assessment rotations included a zero-filled sacrum position somewhere in the screened interval. In 28, all eight leg channels also read zero together. Three walking rotations also crossed the 20 mm step threshold. An event can fail several checks at once. [Source protocol](https://doi.org/10.1016/j.dib.2021.107635) · [Archived sessions](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)
