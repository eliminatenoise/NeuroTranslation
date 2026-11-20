# Rebuild the two movement records

A light comes on. A hand reaches for an object. In a different experiment, the scene tilts around someone balancing on a beam. Each recording contains two things we can check 125 milliseconds later: the strength of electrical activity at the muscles and the path of a marker. The arm study tracks the right wrist. The balance study tracks the base of the spine. Each example keeps one person's measurements together. The two experiments have different people, coordinate frames and electrical instruments.

Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin recorded the hand lifts in WAY-EEG-GAL. Their Figshare participant records carry CC0, and their paper gives a CC BY 4.0 notice for the data and scripts. Steven M. Peterson and Daniel P. Ferris recorded the balance data and released them under CC0. The package supplies readers and file checksums. It downloads recordings from the two original deposits to a directory you choose. [WAY collection](https://doi.org/10.6084/m9.figshare.c.988376.v2) · [WAY methods and supplements](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/) · [Balance recordings, version 1.0.3](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Balance methods](https://doi.org/10.1016/j.dib.2021.107635)

## Reproduce the observations

Run the commands below from this directory using Git, Python 3.12 and Poppler's `pdftotext` on your PATH. Provide at least 15 GB of storage for both stages. The first command installs the two Python libraries. The next two retrieve and read the original balance recordings using the source reader distributed with the muscle-and-motion model. The last two obtain the selected WAY deposits, check both studies' inputs and write the combined development file. [Versioned balance reader](https://github.com/eliminatenoise/NeuroTranslation/tree/a0716992efc24ff02db7e805ce85e72b34889f03/models/muscle-and-motion/source)

```sh
python -m pip install -r balance-source/requirements.txt
python balance-source/acquire.py development private/balance
python balance-source/extract.py development private/balance
python prepare.py acquire development --way private/way --supplement private/supplement-1.pdf
python prepare.py prepare development --way private/way --supplement private/supplement-1.pdf --balance private/balance --output private/windows
```

For a verified local copy, point `--way` and `--supplement` at those originals. The balance reader can also use an existing download. The default extractor uses one worker. Pass `--jobs 2` to the last command to decode two independent WAY archives at a time. After fixing the prediction methods and scoring code, repeat the last four commands with `assessment` in place of `development`. The reader has no reserve-stage command. The two studies retain their original participant assignments. The assessment participants have been studied before on related outcomes.

The output is `private/windows/development.npz` or `assessment.npz`. Open it with `numpy.load(path, allow_pickle=False)`. The adjacent JSON records original series, exclusions for each lift and source identifiers. Keep the measurements and event-level records in local working storage. WAY archive identities, sizes, checksums and released numbered member identities are in `way-catalogue.json`. The download and reader each verify SHA-256. The balance reader checks the original files and their typed output arrays against a versioned catalogue.

## What one row measures

Each row contains 20 consecutive bins of 31.25 ms before a cutoff. The last bin ends at the cutoff. For the hand, the cutoff is 400 ms after the reach light. For balance, it falls 32 samples after the first stored sample at or after the visual rotation. Each bin gives the root mean square (RMS) of the muscle voltage and the last available three-dimensional marker position. RMS squares each voltage sample, averages the squares and takes the square root. It measures electrical amplitude. One arm bin contains 125 samples at 4,000 Hz. A balance bin contains eight at 256 Hz.

The lower eight channels are the left and then right tibialis anterior, soleus, medial gastrocnemius and peroneus longus, in that order on each side. The upper five are the right anterior deltoid, brachioradialis, flexor digitorum, common extensor digitorum and first dorsal interosseous. Keep lower-limb amplitudes in microvolts. WAY exported its electrical amplitudes without an established gain into volts. Keep its original units and estimate its errors separately. Anatomical channel names keep their own identities across both studies.

| Array | Meaning |
|---|---|
| `patch_rms`, `muscle_mask` | Twenty bins by thirteen named channels. The mask marks channels actually usable in this event. A zero in a masked slot is a placeholder. |
| `patch_xyz_mm`, `age_s` | Marker position in millimetres relative to its observed cutoff position, and the time from each bin's last stored marker sample to the bin end. The balance frame is the archived mediolateral, superior–inferior, anterior–posterior order. The hand frame is the wrist tracker's X, Y, Z. Anatomical sign equivalence has not been established. |
| `past_rms`, `future_rms` | RMS for each qualified channel over the final 125 ms of observation and the following 125 ms, respectively. |
| `repeat_path_mm`, `future_path_mm` | Repeat the previous 125 ms relative path, or measure the following path, at 32 offsets spaced 1/256 s apart. Each path starts from its own interval origin. |
| `domain`, `session`, `direction` | Balance is 0 and hand is 1. Balance sessions 0 and 1 mean standing and walking, with clockwise +1 or counterclockwise −1. Hand sessions are the original numbered series with direction coded 0. Only the common light-cued lift task supplies context in the hand experiment. |
| `person`, `event`, `block`, `cutoff`, `cutoff_s` | Source-qualified anonymous identity, original event ordinal, original series third, cutoff sample and cutoff seconds from the series start. These support splitting, balancing and checking that controls use distinct nonoverlapping records. They do not enter the model as measurements. WAY sample indices use 500 Hz and balance uses 256 Hz. |
| `complete` | All five arm channels or all eight leg channels qualify under the complete-channel rule. |

## How a lift qualifies

The WAY reader opens the nine numbered windowed series listed for each permitted participant. Supplement 1 gives both the experimental order and the numbering used in the released files. The second table on page 5 maps the actual numbered files. The additional Weight 6 series contains EEG alone. Practice and EEG-only recordings supply no muscle-and-wrist pair. Each numbered lift supplies one observation at most. [Supplement 1, pages 5–6](https://pmc-oa-opendata.s3.amazonaws.com/PMC4365902.1/sdata201447-s1.pdf)

The reader checks the native wrist and muscle clocks, signal dimensions and support on both sides of the cutoff. Wrist columns 21, 25 and 29 (zero-based) refer to tracker 4. The authors differentiated these coordinates in seconds and defined their speed threshold in cm/s, so the reader converts position differences to mm. The stored wrist rows are 2 ms apart and sometimes repeat a position. A future query at 125 ms falls between rows at 124 and 126 ms. Linear interpolation supplies that reference. The history uses only wrist rows through the cutoff. [Source analysis of wrist velocity](https://github.com/luciw/way-eeg-gal-utilities/blob/c81320ab5da20de83b09ec62167200abdcf8c88c/Utilities/WEEG_FindEvents.m#L440-L450)

Both arm analyses require finite wrist coordinates across the full observed and target interval, including the bracketing positions. They reject a simultaneous zero on all three axes or a constant position lasting 125 ms. For the strict analysis, all five muscle channels must be finite and free of a constant run of at least 125 ms. A simultaneous zero on all five, or an author-recorded fault on any channel, disqualifies the lift. For the second analysis, the reader extracts every named unreliable channel from Supplement 1, page 6. It omits those channels for that person's series, then omits any locally nonfinite or flat channel. A lift still requires at least three usable channels and no instant when all retained channels are zero. Unavailable muscles contribute to neither inputs nor errors. All three historical hand participants have a reported fault, leaving no strict five-channel assessment group.

Eligibility uses signal quality through the target interval. An event can drop out because the marker or electrodes fail during the movement being predicted. Report accuracy for the events that remain. The accompanying balance reader gives its original clock, signal and marker rules and exclusions. [Balance reader and criteria](balance-source/README.md)
