# Rebuild the reaching windows

A macaque moved a handle toward a succession of visual targets. Which way did the hand move after the next go cue? How many spikes did each recorded cortical unit produce in the tenth of a second that followed that movement? These files put the two questions on the recording's clock.

Chowdhury, Glaser and Miller released the movements, controller events and spike counts under CC0. This reconstruction uses one macaque, C, on 7 September 2017. The source MATLAB file is `reaching_experiments/C_20170907_TRT_TD.mat`. The unit names and physical measurements apply to this recording. [Data and CC0 dedication](https://doi.org/10.5061/dryad.nk98sf7q7) · [Study of area 2 of primary somatosensory cortex](https://doi.org/10.7554/eLife.48198)

## Get the recording

Use Python 3.11 or newer with NumPy and SciPy. From the directory containing `extract.py` and `selection.json`, run the commands below. Keep the original recording in a directory with at least 212 MB of free space. Decoding the compressed MATLAB structure also needs memory. The measured training extraction used about 300 MiB of resident memory.

```sh
python -m pip install numpy scipy
python fetch.py input
python extract.py train --mat input/C_20170907_TRT_TD.mat --output arrays
```

The downloader requests just bytes **123 through 211140492 inclusive** of the 4,016,198,198-byte ZIP. It checks the 211,140,370-byte member against CRC32 `a656c1ec` and SHA-256 `6062b7e8dacdf46f7eee465bd844ffe1fb3b7ce0793c34d3e4d106be357f4746`. If your connection cannot fetch byte ranges, download the data ZIP and run `python fetch.py input --archive s1-kinematics.zip`. An existing local copy of the correct MAT also works directly with `extract.py`. [Official ZIP](https://zenodo.org/records/5010943/files/s1-kinematics.zip)

To reproduce an assessment in a completed release, pass the directory that contains its numerical release receipts. The validation receipt opens validation alone. The test receipt opens both assessments under one freeze.

```sh
python extract.py validation --mat input/C_20170907_TRT_TD.mat --output arrays --releases releases
python extract.py within --mat input/C_20170907_TRT_TD.mat --output arrays --releases releases
python extract.py transfer --mat input/C_20170907_TRT_TD.mat --output arrays --releases releases
```

The script generates the original membership, trial boundaries, go ordinals and five training groups directly from the recording's metadata. It checks their hashes before selecting any numerical windows. The MATLAB container requires inflation of the full structure in memory. Only signal slices belonging to the requested split enter the calculation. The sorted spike columns and marker names also have fixed checks. Array files contain numeric arrays and load with `numpy.load(path, allow_pickle=False)`.

## Find a window on the clock

Each recording bin spans 10 ms. Original 2's second go cue occupies MATLAB row 740. Its forecast cutoff is row 745. History therefore runs from row 725 through 744. At the start of row 740 the cue supplied to the model still describes the previous go. Row 741 is the first token allowed to register the new one. The three cue values count earlier go events, give the time in seconds since the latest earlier go, and say whether any earlier go exists. Elapsed time is zero when none exists. Only the go words within that original contribute. The release omits target coordinates and the exact instant a target became visible. [Task-table parser](https://github.com/limblab/ClassyDataAnalysis/blob/3d23730956b05aa19594cbfc6dcb2b4ab8833f34/%40commonDataStructure/getTRTTaskTable.m) · [TRT conversion](https://github.com/raeedcho/preprocess-from-limblab/blob/d7b78757bdfdd82cbc99aeeec549c763cc76ad17/convertTRTfiles.m)

The ten positions for that example occupy rows 745–754. Their offsets from cutoff are 0–90 ms. Subtracting the last history position at row 744 makes the tenth displacement a 100-ms endpoint. The later cortical count bins occupy rows 755–764, the half-open interval from 100 to 200 ms after cutoff. A second count array covers the movement itself and supports a concurrent description. The pipeline preserves every positive-sort electrode/unit column in native order. [Published spike-binning code](https://github.com/limblab/TrialData/blob/83c2d680e9f1122b7f29e5bd171b705e5b4a18df/DataProcessing/convertDataToTD.m)

| Array | Shape per archive | Meaning |
| --- | --- | --- |
| `pose`, `movement` | N × 20 × 8, N × 10 × 8 | History positions and later displacements. The first six values are XYZ in metres for the hand marker (Marker_1) and elbow/ulna marker (Pronation_Pt1). The last two are encoder handle XY in centimetres. |
| `spikes`, `concurrent`, `delayed` | N × 20 × 23, N × 10 × 23, N × 10 × 23 | Counts in history, during the movement, and during the following 100 ms. |
| `cue` | N × 20 × 3 | Number of prior go events, elapsed seconds, prior-go indicator. |
| `unit_guide`, `sorted_columns` | 23 × 2, 23 | Native electrode and sort label for each count column, and that column's one-based MATLAB index. |
| `original`, `block`, `ordinal`, `k` | N each | Native identifiers, go ordinal and one-based cutoff. A window belongs to exactly one original. |
| `history_rows`, `movement_rows`, `delayed_rows` | N × 20, N × 10, N × 10 | Explicit one-based source rows. Concurrent counts occupy the movement rows. |
| `workspace`, `fold`, `donor` | N each | Workspace for reporting, training group 0–4 (−1 outside training), and zero-based candidate donor **in this split's archive**. A donor of −1 means none exists. |
| `roster_original`, `roster_block`, `roster_start`, `roster_end`, `roster_fold` | One entry per original assigned to this split | Full chronological original roster, including recordings that contribute zero usable windows. |

The shoulder-relative camera coordinates and the robot handle coordinates have different origins and units. Compare hand and elbow distances in their own frame, then score the handle separately. Centered marker processing, interpolation and bidirectional handle filtering used later samples upstream. The common 10-ms grid does not establish end-to-end acquisition latency. Offline spike sorting also limits real-time claims. [Marker transformation](https://github.com/limblab/KinectTracking/blob/f656ab81dd0ea2072c642f02afbe8f8fc472c3db/functions/transformForOpenSim.m) · [Encoder filtering](https://github.com/limblab/ClassyDataAnalysis/blob/3d23730956b05aa19594cbfc6dcb2b4ab8833f34/lib/decimateData.m)

## Count the trials that survive selection

The recording contains 622 originals. Seventeen were unrewarded. Original 494 was rewarded but its recorded workspace value, about 5.88 × 10⁻³⁹, does not identify a workspace. These 18 remain in the metadata as unused. Among rewarded workspace-1 originals, chronological order gives 198 for training, 42 for validation and 43 for the later test. Workspace 2 contains 321 rewarded originals. Its trials were interleaved in recording time with those in workspace 1. The transfer test therefore examines a change of physical workspace in this animal on this day. [Authors' workspace analysis](https://github.com/raeedcho/s1-kinematics/blob/e6363cf724d88467d06d472563221a9c85d4dd1b/twoworkspace_analysis.m)

The earlier first-target rule yielded just three training windows and zero validation windows. The present selection requires agreement between the first target and first go, then takes each eligible second, third or fourth go. For a go at row e the cutoff is k = e + 5. Require k − 20 at or after the original start, k + 20 at or before the original end, and every subsequent go strictly later than k + 20. Before numerical quality checks this leaves 519, 113, 116 and 825 windows across 198, 42, 43 and 316 originals respectively. Reward, later cue timing and the recording endpoint determine which forecasts enter the evaluation; the predictors receive none of these future facts.

A usable window has finite coordinates on every required axis and finite, nonnegative integer counts in every required unit and bin. Small displacements, large displacements and all-zero counts remain eligible. Within each split the wrong-movement donor is the latest earlier eligible original in the same block at the same go ordinal. During training a second-stage forecast must also have genuine forward-fold predictions for both receiving and donor rows. The first 40-original group supplies the fitting history for the next 40. The remaining chronological groups contain 40, 39 and 39 originals. All windows from an original stay together.

The output includes `original-metadata.json` for all 622 originals, one quality report per split (including all candidates, reasons for exclusion and chronological roster), and the first metadata-selected example per split. The fixed examples remain the same even if one fails numerical checks.

All 1,573 metadata-eligible windows passed the numerical checks. The later workspace-1 assessment contains 116 windows from 43 originals, with an earlier same-ordinal donor for 113. Workspace 2 contributes 825 windows from 316 of its 321 assigned originals, with a donor for 822. The other five originals remain in the chronological roster. A separate reader compared every released coordinate and spike count with the corresponding byte offsets in the MATLAB file.
