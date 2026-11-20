# What the scalp recorded during a lift or a change of balance

A hand moves toward an object. In another experiment, a person balances on a beam while the room in their headset appears to tilt. In each experiment, the investigators recorded voltage at the scalp while other instruments recorded muscles and movement. This reader retrieves the scalp history for the very same person and movement already identified by the muscle-and-motion reader. The two studies involve different people, tasks and recording systems. [Grasp-and-lift recordings](https://doi.org/10.6084/m9.figshare.c.988376.v2) · [Perturbed balance recordings](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)

## Whose movements are represented?

Matthew Luciw, Ewa Jarocka and Benoni Edin recorded the grasp-and-lift trials. Six development participants supplied 1,764 paired lifts in 54 numbered series. All 1,764 have usable voltage at the nine requested scalp sites. The supplement lists 1,968 trials across all ten series for these people. The last released series, Weight 6, supplies EEG alone and accounts for the other 204 trials. The paired release covers the remaining nine series. Practice recordings fall outside this count. The source participant notes report gel added before a second series and early electrode and battery problems in another participant. They give no individual scalp lead or exact failure interval to mask. Eye, muscle and movement artifacts can remain. [Luciw, Jarocka and Edin](https://doi.org/10.1038/sdata.2014.47) · [Experiment schedule and quality notes, pp. 5–6](https://pmc-oa-opendata.s3.amazonaws.com/PMC4365902.1/sdata201447-s1.pdf)

Steven Peterson and Daniel Ferris recorded the balance trials. Eighteen development participants contributed both a standing and a walking session. The logged rotations total 5,364, with 149 per session. Previous muscle-and-motion checks admitted 2,600 standing and 2,579 walking events. The other 185 had unusable muscle or marker measurements. Each of the 5,179 admitted events retains 100 to 120 of the 128 scalp electrodes and all five recorded eye or neck controls. The original protocol expected 150 rotations per session. The data files and checked event logs support 149. [Data and processing](https://doi.org/10.1016/j.dib.2021.107635) · [Original experiment](https://doi.org/10.1523/ENEURO.0207-18.2018)

The original muscle-and-motion reader checked whether later muscle and movement measurements were usable. These rows therefore describe a retrospectively eligible group. The scalp reader uses only earlier voltage samples on those rows. A live system would need a separate test of eligibility, processing and latency.

## What the numbers mean

For each event, divide the last 625 milliseconds into 20 intervals of 31.25 ms. In each interval compute the signed mean and root mean square (RMS) of the recorded voltage. The first preserves whether the signal was mostly positive or negative relative to its recording reference. The second measures its amplitude. Absent, author-rejected, nonfinite and flat channels have individual flags and contribute no measurement. A flat channel has an exactly unchanged run that spans at least 125 ms within the allowed history. On these development rows the only excluded channels were those in the balance authors’ rejection masks, which were established retrospectively. Short gaps, blinks and signals from moving muscles can survive these checks.

**Hand.** The observation ends 400 ms after the light cue on the recorded clock. The wrist and scalp share a stored 500 Hz grid, and the muscle stream has its own 4,000 Hz clock. The authors report up to 2 ms of uncertainty between the acquisition systems. Each scalp interval drops 2 ms at both edges. A retained sample can then move by the stated uncertainty and still belong to that interval. The interval is open at its lower bound and closed at its upper bound. This leaves 273 samples in all, 13 or 14 per interval. The final stored scalp sample precedes the cutoff by 2 ms. The cache keeps the exported values in their native amplitude units. The source plots use microvolts, and the authors’ EEGLAB import utility scales the separate whole-series EEG signal by 0.1. Its applicability to the windowed matrix requires separate evidence. The forehead sites Fp1 and Fp2 can register eye activity. The hand recording has no separate eye channel here. [Source methods and utilities](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/)

**Balance.** The observation ends 32 stored samples after the first sample at or after the logged rotation. At 256 Hz that places the cutoff 125 to just under 129 ms after the logged onset. Each interval contains eight samples. All scalp, eye and neck amplitudes use the source-declared microvolts. The archived scalp data have a 1 Hz high-pass filter, common-median reference and line-noise removal. Optical and other streams were aligned offline. The resulting sample times describe the stored recording. They cannot quantify display delay, a live decoder’s latency or the contribution of later original samples to the offline filters and interpolation. [Peterson and Ferris, processing methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC8711048/)

## Which electrode is C3?

A name can mean two different things on the two caps. The grasp-and-lift cap follows standard site names. The balance cap uses four banks of 32 leads. Its channel C3 means the third socket on bank C. The manufacturer's 128-channel map places the standard C3 site at **D19**. The manufacturer explicitly marks four nearby positions as approximate. The nine comparisons below describe nominal cap placement. An individual scalp contact samples a mixture of electrical sources. [BioSemi, 128-channel cap coordinates](https://www.biosemi.com/download/Cap_coords_all.xls)

| Hand site | Balance bank | Manufacturer description | Balance rows available, out of 5,179 |
|---|---|---|---:|
| C3 | D19 | C3 | 4,887 |
| Cz | A1 | Cz | 3,713 |
| C4 | B22 | C4 | 4,330 |
| FC1 | C24 | Approximate FC1 | 4,596 |
| FC2 | C11 | Approximate FC2 | 4,302 |
| CP1 | D16 | Approximate CP1 | 2,254 |
| CP2 | B2 | Approximate CP2 | 4,300 |
| Fp1 | C29 | Fp1 | 4,010 |
| Fp2 | C16 | Fp2 | 2,885 |

All nine balance contacts survive together in 541 events from two of the 18 people and four of the 36 sessions. Keep the per-event masks when comparing other events. The 128 balance contacts each have a named position in the BIDS electrode table. Those coordinates agree numerically with the corresponding EEGLAB header up to rounding in all 36 sessions. The release sidecars give millimetres, whereas the study describes the tables in metres. The reader preserves both pieces of evidence and uses no physical distances or inter-head coordinate transform. [Archive, version 1.0.3](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Data dictionary](https://pmc.ncbi.nlm.nih.gov/articles/PMC8711048/)

## Rebuild from the original files

Use Python 3.12, NumPy and SciPy. Supply the exact development inputs generated by the companion muscle-and-motion readers, the original WAY archives and their versioned catalogue. The balance directory contains its development file receipt, the original files under `raw` and the checked-out version 1.0.3 Git catalogue. Output goes to a private directory. The source deposits list the participant records under CC0. The WAY descriptor also carries a CC BY 4.0 notice for its data and scripts. Credit the investigators when reusing the measurements. [WAY collection](https://doi.org/10.6084/m9.figshare.c.988376.v2) · [Balance release](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python prepare.py \
  --cohort private/joint/development.npz \
  --way private/way --way-catalogue way-catalogue.json \
  --balance private/balance --out private/scalp

python verify.py --cohort private/joint/development.npz \
  --cache private/scalp/development.npz \
  --walk-development private/walk/development.npz --output private/scalp/verified.json
```

Use `numpy.load(path, allow_pickle=False)`. The top-level arrays `person`, `domain`, `session`, `event`, `direction`, `block`, `cutoff` and `cutoff_s` preserve the joint cohort’s row order. Person, session, trial, block and absolute clocks support grouping and auditing. A future modeling study must keep participants separate and train scales within each fitting fold. The archive contains no future outcomes.

| Arrays, prefixed with `way_` or `balance_` | Contents |
|---|---|
| `rows`, `names` | Indices into the common row order and the native channel labels. Balance has 128 scalp channels in bank order followed by left and right neck EMG, right and left horizontal EOG and left vertical EOG. WAY has the nine sites in the table above. |
| `mean`, `rms` | Float32 values indexed by source row, chronological interval and channel. Source-amplitude units differ between studies. |
| `good`, `reason` | Boolean availability and unsigned reason bits by source row and channel. Missing = 1, author-rejected = 2, nonfinite history = 4, sustained flat history = 8. Zero denotes no recorded reason. Zero-valued placeholders on masked channels must be excluded from analysis. |
| `bin_samples`, `bin_first_offset`, `bin_last_offset` | Number of retained samples and the first and last native sample offsets from cutoff in each interval. |
| `source_session`, `source_ordinal` | Source-numbered series or BIDS session and original one-based event ordinal. |
| `source_anchor`, `source_issue_s`, `original_event_tick` | Source sample index at cutoff, cutoff time in seconds and recorded cue/rotation time in native ticks. In WAY, the sample index is relative to the first row of that lift’s matrix, and the time fields use that lift’s local clock. In balance, all three use the continuous session clock. |
| `latest_minus_cutoff_s` | Signed difference in seconds from cutoff to the last usable time point requested by the reader. |

The accompanying private source audit contains hashes for original members, session events, coordinates, units and source channel decisions. `verify.py` checks row identity and the timing and masks for every event. It also compares 40-sample summaries against an earlier independent walking extraction wherever both movement screens admitted the same event.
