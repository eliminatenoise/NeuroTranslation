# Where did the cylinder go?

A seated participant holds a small cylinder. A screen shows which of nine circles to aim for. A sound tells the participant when to move. Two reflective dots on the cylinder let cameras follow it across the table. This collection gives you the assigned target and the path the cylinder took, one hand and one trial at a time. The other hand performed its trials in a separate session. The cameras recorded the cylinder. Wrist, finger, muscle and neural activity would require other measurements. [Ruhr Hand Motion Catalog](https://doi.org/10.17605/OSF.IO/J3QC8) · [Study and apparatus photographs](https://doi.org/10.1038/s41597-025-05576-7)

## Read a recording

Open `gallery.json` to see 18 recorded paths from one participant, one per hand and target. For each one, `frames` gives the original optical frame number, elapsed seconds and three displacements in millimetres. A displacement of zero means the cylinder is at its initial measured position. The camera system sampled at 250 Hz, one frame every 4 ms. Display values are rounded to 0.001 mm. That rounding says how the numbers are stored. It cannot establish the accuracy of an individual measurement.

Target 1 was to the participant’s left, target 5 straight ahead and target 9 to the right. The nine circle centres were 250 mm from the start, separated by 22.5 degrees on a semicircle. These are the planned table positions. The trajectory retains the camera system’s original X, Y and Z axes. In the first left-hand trial for target 5, the final point lies about 177 mm along negative X and 158 mm along negative Y from the first point. Keep the table diagram and the camera axes distinct unless a measured coordinate transformation connects them. [Target diagram](https://www.nature.com/articles/s41597-025-05576-7/figures/4) · [Reference photographs and diagrams](references.json)

**The recording began before the cylinder moved.** For participant 01’s first left-hand visit to target 5, the optical frames span 7.856 seconds. The study’s separate start and stop timestamps span 3.660 seconds. The recorded variable delay before the sound was 1,425.95 ms. The authors describe a 1.5-second visual display, a variable 1–2-second wait, a 3.5-second reaching interval and a 3-second return interval. There is no per-frame record of the screen lighting up, the loudspeaker sounding or the hand lifting. The assigned target can be supplied to software, but the instant the participant saw it cannot be read from these frames. [Trial timing](https://www.nature.com/articles/s41597-025-05576-7/figures/6)

The gallery gives a second place to start watching. Follow the centre of the selected markers until it is at least 15 mm from its first position for three consecutive native frames. The clock for this view starts on the third frame. In the example above, it starts 4.708 seconds into the optical record. A missing coordinate or skipped frame breaks the run. This gives a repeatable way to examine transport once measurable displacement has occurred. The physical instant of movement onset remains unknown.

The two session times in each gallery entry are relative to its hand session’s first logged recording start. Their source timestamps have millisecond precision and specify no time zone. The variable delay comes directly from the study’s program. It is separate from acoustic latency and the interval measured by the optical camera.

## Rebuild the measurement subset

The public file is version 1 of the OSF archive, 1,928,361,942 bytes. The reader checks its published SHA-256 before extracting any measurement. Allow about 3 GB of local disk. Use Python 3.11 or later, NumPy and the command-line `gzip` utility. Run from the directory containing this file.

```sh
python -B stage.py
python -B build.py train
python -B build.py test
```

The first command downloads the archive once and streams the original optical CSV and trial metadata into a local cache. It keeps source code as plain text for inspection. It does not execute deposited code. Each subsequent command reads a distinct set of people. The development command also rebuilds the gallery from participant 01. To reproduce our saved array-file digests, use NumPy 2.5.5. [Pinned file and license record](provenance.json) · [Preselected source rows](selection.json)

The source has 31 participants, with IDs ordered by age. Every fourth participant in that list forms an age-distributed, participant-disjoint test group (4, 8, 12, 16, 20, 24, 28). The other 24 form the development group. In each hand session we take the first two assignments of every target, then apply the authors’ optical exclusions. Their list uses the zero-based *within-target* repeat index. A discarded assignment leaves a gap. It never makes a later trial eligible. The two hand sessions and all repeats of a participant stay together. Out of 864 assignments in the development group, 40 have a published optical exclusion and 824 are included. All 824 support both clocks and all three future times. The authors’ exclusions use whole-trial quality information, so the comparison concerns the recordings that passed this retrospective screen.

The reader takes XYZ from both complete markers at the first eligible frame, or the one complete marker if only one is present. It sticks with that marker set throughout the trial and averages their positions when both are used. A missing selected marker makes that frame unavailable. No gaps are bridged by this reader. The publisher’s optical reconstruction may already include pattern fills or short spline fills using adjacent frames. The exported measurements do not label these fills individually. For 823 of the 824 included development trials two markers were available at the start. One trial used a single marker. All included development centroids and their native frame numbers were continuous.

## Array fields

`train.npz` and `test.npz` use the first eligible optical frame as the anchor. The files with `-crossing` added to their names use the third consecutive frame beyond the 15 mm threshold. The coverage files identify every selected trial, its inclusion status on both clocks and any unavailable endpoint. No trajectory rotation, per-trial endpoint alignment or additional smoothing enters the arrays.

| Field | Meaning |
| --- | --- |
| `xyz` | Five native-world positions in metres, shape (trials, 5, 3). Each position is the latest eligible sample at or before 0, .050, .100, .150 and .200 s, with a maximum age of one native frame. |
| `time` | Actual input times in seconds from the selected anchor, normally 0, .048, .100, .148 and .200. |
| `y` | Three 3-D displacements in metres from the **last input position** to the first eligible sample at or after .400, .600 and .800 s from the anchor, within one frame. Shape (trials, 3, 3). |
| `valid`, `target_time` | One availability flag and actual future sample time per trial and horizon. Unavailable future coordinates and timestamps are NaN. A complete input history may have a missing future measurement. |
| `participant`, `hand`, `target` | Source participant number, “left” or “right,” and assigned target from 1 through 9. |
| `repetition`, `trial`, `member`, `anchor_frame` | Zero-based repeat within this target and hand, zero-based recording index within the hand session, archive member path relative to the deposit’s top folder, and source frame at time zero. |

**Attribution.** The measurements derive from the *Ruhr Hand Motion Catalog of Human Center-Out Transport Trajectories Measured Redundantly in 3D Task-Space* by Tim Sziburis, Susanne Blex, Tobias Glasmachers and Ioannis Iossifidis (2025). The authors released the data under CC BY 4.0. This adaptation selects trials, averages available object markers, samples defined time windows and expresses movement relative to a stated reference point. The original measurements and study design are credited to the named creators. [Dataset](https://doi.org/10.17605/OSF.IO/J3QC8) · [Article](https://doi.org/10.1038/s41597-025-05576-7) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
