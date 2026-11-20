# How far will it move in a quarter of a second?

A headset tracked a person’s right wrist while they handled a device. A different camera followed a rat around a W-shaped track. Take five sightings from the past second. How far from its last observed position will the wrist or the rat be a quarter of a second later? Both recordings give an answer in centimetres. A wrist that traces a loop and returns to its starting point has zero displacement, however far it travelled along the way. [HoloAssist](https://holoassist.github.io/) · [Single Day W-Track Learning](https://doi.org/10.48324/dandi.000978/0.240511.0307)

The wrist calculation uses three dimensions. The rat’s uses the two dimensions of the track. Each calculation stays inside one recording. At four successive quarter-second intervals the model gets the distance moved, elapsed time, age of the last observation, distance across the last two steps, and a measure of how sharply the path turned. The turn value is the cosine between two successive directions. A straight path gives 1, a right angle 0 and a reversal −1. The first interval has no preceding step, so both two-step quantities start at zero. A stationary step also gets zero for the undefined direction comparison. Distances refer to the measured wrist or the tracked animal location. The rat recording supplies no limb trajectory. [Timing and feature rules](contract.json)

## Which observations count?

Every two seconds within one recording or trip, we look back a second. Each of the five sightings must come at or before its appointed time, within 50 milliseconds. The same rule applies to the future observation. We use the wrist sensor’s original clock and the rat camera’s recorded times. Copies of one hand reading occupy several frames in the released video grid. We take its first appearance, checking that the headset marked the hand active and the wrist valid and tracked. Missing readings produce gaps. A gap greater than 100 milliseconds anywhere between the observations removes that window. A discrepancy greater than 50 milliseconds between local elapsed times on the hand clock and its video grid also removes it. Absolute timing alignment, sensor delay and positional error across the two devices are unknown. [Publisher’s synchronization guide](https://holoassist.github.io/data_links/README.html) · [Source rules](contract.json)

| Role | Source | Recordings or trips | Scheduled | Usable past | Measured future retained | Actual last-to-future observation time |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Fit | Wrist | 17 | 1,315 | 637 | 606 | 214–294 ms |
| Fit | Rat | 24 | 222 | 200 | 188 | 210–282 ms |
| Assessment | Wrist | 11 | 934 | 597 | 583 | 208–293 ms |
| Assessment | Rat | 9 | 131 | 115 | 106 | 229–290 ms |

For example, 337 of the 934 scheduled assessment wrist forecasts lacked a usable past. Another 14 had a usable past and an unusable future. Error estimates apply to the 583 with both. For rat trips we also retain the original end-of-trip buffer. Across both domains no input or target crosses a recording or trip boundary. [Fixed selection and tolerances](contract.json)

The wrists cover 16 acquisition codes across six equipment tasks. All recordings with one code stay together. The six assessment codes had served in an earlier study of instructor language. The 28 recordings all came from the training collection of a still earlier hand-caption study. The previously illustrated R031 recording is excluded, as are that earlier study’s assessment and reserve recordings. We read the optical trajectories without speech or event annotations. The rat assessment reuses nine previously scored trips from one animal, in the same session and running period as training. Trips 79 and 90 separate the original partitions, trip 80 had served as a comparison donor, and trips 91–95 remain reserved. The public demonstration of trip 0 belongs to a different run. These assessments revisit known recording groups. They cannot establish performance on a new person, new rat or new device. [Source membership and prior exposure](contract.json)

## Rebuild the local packets

Run the following from the directory containing this README. Python 3.13, NumPy 2.5.5 and Requests 2.34.2 were used. The first command retrieves the selected training wrists from the publisher and the rat trip files and converter from a pinned NeuroTranslation release. Each file is checked against its recorded digest. Existing matching files are reused. A conflicting file stops the reconstruction. The second command produces the training arrays in the current directory. [Pinned source checkout](https://github.com/eliminatenoise/NeuroTranslation/tree/4d046b86bfa797e28f29cd4f6b8445a1f4b90487/benchmarks)

~~~sh
uv run --no-project --with numpy==2.5.5 --with requests==2.34.2 python -B restore.py train --root ./local-sources
uv run --no-project --with numpy==2.5.5 python -B prepare.py train --root ./local-sources --workers 2
~~~

For experiments on these cohorts, seal the model, fit and scoring code before restoring the assessment. Then run the same two commands with `assessment` in place of `train`. An existing compatible NeuroTranslation checkout can supply the converter and W-track trip files via `restore.py --benchmarks /path/to/NeuroTranslation/benchmarks`. The hand converter requests a missing right-hand member directly from the HoloAssist archive. The licensing notice identifies the authors and original terms. [Data credits and changes](NOTICE.md)

| Local file | Rows | Original study run SHA-256 |
| --- | ---: | --- |
| `train.npz` | 794 | `2b7991fe685c05bf5edb9c9a9de002034bacb5ce96d03281d0cdedcf835d8194` |
| `assessment.npz` | 689 | `b47fbbf9fe14f49effc35fc63ab14087aa8f74555115beef0d1c64695c24c8c8` |

`x` contains four intervals and five features per interval, `y` the measured future displacement in centimetres, and `domain` the source (`wrist` or `rat`). The other fields identify the acquisition group, recording, times and source rows for local checks. In wrist packets `history_grid_s` uses the exported video grid and `history_s` the native hand clock. Rat times are relative to the annotated trip start. The public model can be used without restoring individual observations. [Source terms](NOTICE.md)
