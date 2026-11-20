# Rebuild the cortical count windows

A macaque holds a robotic handle. A brief push moves its hand. Can the last 200 milliseconds of handle motion help forecast what electrodes in the arm area of sensory cortex will record over the next 100 milliseconds? These files rebuild the measurements for that comparison. Each outcome gives the recorded event count at each of 26 named electrodes.

Raeed H. Chowdhury, Joshua I. Glaser and Lee E. Miller released the recordings under CC0 1.0. The two sessions come from the same animal, C, on 12 and 13 September 2017. Contact numbers identify channels on its array. The deposited sort code 0 identifies exported unsorted events. The files contain counts in 10-millisecond bins. They provide no spike waveforms or evidence that an individual neuron was recorded on both dates. [Dataset](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original study](https://doi.org/10.7554/eLife.48198) · [Deposit licence](CC0-1.0.txt)

## Run the extraction

Use Python 3.11 or later with NumPy and SciPy. The reference run used Python 3.13.15, NumPy 2.5.5, SciPy 1.18.1 and zlib 1.3.2. Run these commands from this directory.

```sh
python -m pip install numpy scipy
python fetch.py 2017-09-12 raw
python extract.py train raw/C_20170912_COactpas_TD.mat rebuilt
python training_archive.py rebuilt/train.npz rebuilt/train-for-fit.npz
python extract.py validation raw/C_20170912_COactpas_TD.mat rebuilt
python fetch.py 2017-09-13 raw
python extract.py test raw/C_20170913_COactpas_TD.mat rebuilt --release-test
```

The downloader takes just the two named members from the authors’ ZIP (179 MB and 367 MB, respectively) and checks each complete file against its SHA-256 fingerprint. You can also extract the two MAT files from the archive’s `reaching_experiments` folder yourself and put them in `raw`. Both routes use the same member checks. Each stage writes an array archive, a record of window eligibility and exclusions, and measured examples for the reader. The training step checks every original training field against its previously verified digest. The second command on the training data rebuilds the exact archive that the fitting program reads, including its file fingerprint. [Original archive](https://zenodo.org/records/5010943/files/s1-kinematics.zip) · [Fingerprints and byte ranges](identities.json)

## What each row contains

One row comes from one original trial and one time offset. The September 12 training stage uses the first 324 assigned rewarded trials. Two fail the event criteria, leaving 1,288 windows from 322 trials. The following 108 trials supply 432 validation windows. The final 108 from that date were studied previously and stay outside this comparison. The September 13 study reserves original IDs 2 through 1,388. Original 1 had already been inspected. Code 0 marks the push before the target appears. Code 1 marks the go cue on a trial with a preceding push. Code 2 marks the go cue on a trial without a push. Day one contributes only phase 0. The first-day assignments and second-day row list are included. [September 12 assignments](first-day-split.json) · [September 13 windows](held-day-membership.json)

| Array | Meaning and units |
| --- | --- |
| `trial`, `phase`, `k`, `offset`, `direction` | Original trial ID, phase code, first predicted MAT row (one-based), offset in 10-ms bins, and actual push or reach-cue direction in degrees. These identify comparisons. |
| `position_history_cm` | Twenty recorded handle positions, XY in centimetres, at source rows k−20 through k−1. The encoder positions have upstream offline filtering. |
| `movement_tokens_cm` | Five blocks of four samples. Each holds the final XY position and final-minus-first XY change. Sample labels within a block span 30 ms. |
| `count_history`, `count_tokens_40ms` | Twenty rows of earlier 10-ms counts and their five consecutive four-row sums, per contact. |
| `cues`, `cue_elapsed_s` | At each block’s right edge, seven numbers give push flag and XY direction, target flag and XY direction, then go flag. Three elapsed times in seconds refer to push, target and go. A cue becomes visible only after its recorded row. |
| `prior_count_100ms`, `target_count_100ms` | Per-contact sums for the last ten completed bins (k−10 through k−1) and the next ten bins (k through k+9). The second vector is the outcome. |
| `donor` | A zero-based row in the same archive, or −1 when no eligible earlier trial exists. Only its five movement blocks replace the recipient’s. |
| `contact_id`, `matlab_column` | The 26 common electrode labels and their one-based source columns for that date. |
| `original_ids`, `bump_direction_deg` | All assigned trial IDs, even when a trial contributes no window, and the source push direction for each retained row (−1 when missing). |

The wrong-movement comparison searches backward for the closest different trial from the same split. Its phase, actual direction, offset and visible cue flags and directions in **all five** blocks must match. Elapsed cue times, prior counts and target counts remain the recipient’s. The QC record lists each numerical exclusion and each phase’s counts before and after matching. A recorded zero is a valid outcome. A missing encoder sample or invalid count excludes the window.

The sample JSON keeps the first eligible original in each phase and the first original with any matched earlier movement. All retained offsets from each selected original are included, along with the matching row in the full archive. These examples are selected by recording order. They cannot establish how the models performed across the session.
