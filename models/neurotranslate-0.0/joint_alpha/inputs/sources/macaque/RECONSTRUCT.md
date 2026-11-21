# Rebuild a reach on the recording clock

A macaque slid a handle between targets while a camera tracked two points on its arm and electrodes in its brain counted electrical spikes. The animal returned a week later. Could a forecast learned from its earlier reaches still follow the movement and the later spike counts? These scripts recover the measurements that let you check. The researchers who recorded the animal, Raeed Chowdhury, Joshua Glaser and Lee Miller, released the processed recordings under CC0. [Recording and licence](https://doi.org/10.5061/dryad.nk98sf7q7) · [Area 2 study](https://doi.org/10.7554/eLife.48198)

## Rebuild the arrays

Use Python 3.11 or newer with NumPy and SciPy. Run these commands from the directory containing this guide. Allow about 420 MB for the two original MATLAB files, plus space for the small output archives.

```sh
python -m pip install numpy scipy
python fetch.py train input
python fetch.py held input
python reconstruct.py train --mat input/C_20170907_TRT_TD.mat --output arrays
python reconstruct.py held --mat input/C_20170914_TRT_TD.mat --output arrays
```

The first pair of commands reads just the two requested members from the official ZIP and checks their lengths, CRCs and SHA-256 digests. With a downloaded ZIP, add `--archive s1-kinematics.zip` to each fetch command. If you already have the two original MATLAB files, the last two commands work offline. Run `python coverage.py held --out arrays` to count available observations by electrode, workspace, and recording block. [Official ZIP](https://zenodo.org/records/5010943/files/s1-kinematics.zip)

The first recording contributes 519 windows from 198 rewarded trials in workspace 1, the same training cases used in the earlier reaching study. The later day has two physical recording blocks. Each restarts its clock and its trial numbering. Keep both `block` and `original` when identifying a trial. There are 113 candidate windows in block 1 and 380 in block 2. The three surfaces are `train.npz`, `block1.npz` and `block2.npz`. Read them with `numpy.load(path, allow_pickle=False)`.

## Follow one reach

Take training trial 2. Its second go cue appears at row 740. The early forecast starts five 10 ms rows later. Read rows 725–744 to see what that forecast could use. Rows 745–754 show what the arm actually did next. Rows 755–764 contain the subsequent cortical spikes. These are positions on the processed recording clock. Camera processing and spike sorting place limits on what a live device could know at the same instant.

| Array | What it records |
| --- | --- |
| `block, workspace, original, ordinal, k` | The recording block, workspace, original trial number, go cue number within that trial and first forecast row. Source row and column numbers start at one. |
| `history_rows, movement_rows, delayed_rows` | The 20 rows just before k, the first ten from k, then the next ten. |
| `pose, pose_labels` | Twenty positions before k. The first three coordinates track a hand marker and the next three a marker near the elbow. Both use shoulder-relative metres. The final two track the handle in its own plane, in centimetres. |
| `movement` | Ten displacements for each of the eight coordinates, measured from the last position before k. |
| `cue, cue_at_k` | At each earlier row, the number of go cues strictly before its start, seconds since the latest such cue and an indicator for whether one exists. At k the two fields are count and elapsed seconds. Elapsed time is zero in the absence of a prior go. |
| `all_history, all_concurrent, all_delayed` | Raw spikes per 10 ms bin in every exported source column, on each of the three time intervals. |
| `all_guide, all_columns` | The acquisition contact number and local sort label of every exported column, plus its original column number. Sort 0 contains spikes left unclassified by the source's sorter. |
| `spikes, concurrent, delayed, unit_guide, sorted_columns` | The same three count intervals and column identities for positive sort labels alone. |
| `fold, roster_fold` (training) | The original five chronological training groups, indexed 0–4, for every window and every training trial. The roster also records the original trial's start, end and acquisition block. |
| `source_member_sha256` | Digest of the MATLAB member used to build the array. |

To count activity at one electrode, find its contact number in that block's `all_guide`. Sum the chosen columns once each. Across both days, 37 contacts have a sort-zero column in every block. On these contacts an analysis can count every exported spike or just sort zero. Seventeen contacts have at least one positive sort in every block. A missing sort supplies no observation. An observed column with zero spikes supplies a count of zero. The number of positive sorts changes at contacts 15 and 53. Even when that number holds steady, the recordings do not establish that both days captured the same neuron.

The arrays preserve all candidate rows and their raw values. Each analysis can therefore report where a missing motion coordinate or invalid count makes its own comparison unavailable. Trial outcomes and subsequent cues determine whether a window qualifies for assessment. Predictors receive only their specified history. These recordings measure cortical responses and movement in one animal on two days. They provide no direct peripheral nerve measurement.
