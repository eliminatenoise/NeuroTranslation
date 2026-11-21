# A turn of the cylinder, ten samples ahead

A person grips a cylinder and carries it toward a circle on a table. A sensor on the cylinder records acceleration and angular velocity. Take the twenty readings immediately before a given instant. Can they tell us how fast the cylinder will turn, on average, over the next tenth of a second? The sensor reports three components of angular velocity. Its axes travel with the cylinder. A turn about its X axis and a turn about its Y axis have different answers, even at the same speed. [Study and apparatus](https://doi.org/10.1038/s41597-025-05576-7)

Each hand performed separate trials to nine assigned targets. The published clock starts at the first exported inertial sample and advances by 10 ms. The time of the first sample does not establish when the participant saw the target, heard the sound or began to move. The optical cameras ran on a separate clock. The authors aligned their trajectories after the trial, using information from later movement. Here the cylinder carries the clock for both the prediction and the outcome. [Timing diagram](https://www.nature.com/articles/s41597-025-05576-7/figures/6)

## Read a clip

Pick a hand and target in `gallery.json`. Its rows give elapsed seconds, three accelerometer readings in m/s² including gravity, three gyroscope readings in rad/s, then the four components of the device’s orientation estimate. The quaternion starts with its scalar component (w, x, y, z). It rotates a vector from the device axes to the local earth reference. The target marks a place on the table. Relating the reported heading to that place would require a separate physical calibration. A wrist angle would require a measurement of the wrist. [Manufacturer’s manual, §§11.6–11.7](https://www.xsens.com/hubfs/Downloads/Manuals/MTw_Awinda_User_Manual.pdf) · [Target arrangement](https://www.nature.com/articles/s41597-025-05576-7/figures/4)

The 18 clips show the earliest eligible training recording available for each hand and target, ordered first by source participant number and then by recording number. All 18 are third assignments from the first eligible participant, with 6,421 measured rows in total. Their original member paths and hashes identify the source. Each clip preserves the native sample grid and all available numeric precision in the selected columns. The gallery requires a continuous clock, finite readings and an orientation quaternion within 0.001 of unit norm. Only the gallery checks the quaternion.

## Which recordings count?

The roster covers 24 people already observed in an earlier development study. For each hand and target, count assignments in native recording order before removing any recording. The third through sixth assignments enter training, the seventh and eighth enter validation, and the ninth and tenth form the reserved test. The first two assignments and seven separate participants stay outside the experiment. Repeats to different targets can interleave. The comparison asks whether the model transfers to another repetition by a familiar person.

The authors inspected complete trajectories. Their exclusions cover, among other things, movements ending more than 4 cm from the target, unusually high or absent lift, premature starts, corrections and instrument artifacts. They flagged recordings separately for optical and inertial quality. The prospective roster already required both checks. An optical flag can therefore exclude a trial despite our use of only the inertial instrument. Work from this selected population may differ from performance on every attempted movement. The `author_qc` column in `prospective-repetitions.csv` retains the original exclusions. [Author quality criteria](https://doi.org/10.1038/s41597-025-05576-7)

The clock check uses elapsed seconds and a tolerance of 0.0000001 s around the nominal 10 ms grid. No missing sample is filled. The files lack a hardware packet counter and per-packet arrival times. A regular exported grid cannot reveal an internal fill, instrument processing lag or wireless delivery delay.

| Split | Assigned recordings | Recordings passing both author flags | Usable windows | Earlier donor | No donor |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 1,728 | 1,634 | 11,438 | 8,414 | 3,024 |
| Validation | 864 | 803 | 5,621 | 2,604 | 3,017 |
| Test | 864 | 804 | 5,628 | 2,653 | 2,975 |

Every retained recording supplied all seven windows. The 24 people in each split are the same people.

## Windows and controls

| Field in each NPZ | Meaning |
| --- | --- |
| `time` | N × 20 elapsed times in seconds from the native first sample. |
| `accel`, `gyro` | N × 20 × 3. Native device X, Y, Z. Acceleration includes gravity (m/s²). Angular velocity is in rad/s. |
| `y_accel`, `y_gyro` | N × 3. Mean of the ten consecutive recorded rows starting at the cutoff, in each instrument’s original units. |
| `participant`, `hand`, `target` | Original numeric participant, left/right session and assigned visual target 1–9. Participant identity is for grouping and traceability. |
| `trial`, `repetition` | Zero-based recording number in this hand session and zero-based assignment number within hand and target. |
| `cutoff` | Nominal elapsed milliseconds. The seven cutoffs are 200, 600, 1000, 1400, 1800, 2200 and 2600. |
| `donor` | Zero-based row of the closest strictly earlier eligible recording from this split with the same participant, hand, target and cutoff. −1 means that no donor was available. |

At the 600 ms cutoff the twenty inputs run from 400 to 590 ms. The ten outcome rows run from 600 to 690 ms. The wrong-acceleration control replaces the twenty accelerometer readings with the twenty from the designated donor. The recipient keeps its own gyroscope history, hand, target, elapsed time and observed outcomes. Every valid window remains available for the full comparison, including those that lack an earlier donor.

The original raw file has 17 columns. Alongside time, acceleration and angular velocity it carries three free-acceleration components (m/s²), three magnetometer components (arbitrary units), and the four unitless quaternion components. The window builder uses the published acceleration with gravity. Free acceleration, magnetometer data and the orientation estimate do not enter the forecast. The authors acquired the MTw2 output through the proprietary SDK in Xsens MT Software Suite 2021.4 and report firmware 4.6.0. Onboard calibration and filtering separate the exported signals from direct access to the sensing elements. The source provides no per-trial bound on that processing delay. The deposited processed and rotated trajectories are separate products. [Published data record](https://doi.org/10.17605/OSF.IO/J3QC8) · [Manufacturer’s manual](https://www.xsens.com/hubfs/Downloads/Manuals/MTw_Awinda_User_Manual.pdf)

## Rebuild from the original deposit

Obtain version 1 of `Ruhr_HandMotion_CenterOutTask.tar.gz` from the public deposit, or reuse your existing copy. The archive is 1,928,361,942 bytes. Use Python 3.11 or later, NumPy and the command-line gzip utility. Our saved arrays used NumPy 2.5.5. Run these commands from the directory containing this file. The first checks the original SHA-256 and copies the selected raw inertial files during a single decompression. [Versioned archive](https://osf.io/download/4tq78/?version=1) · [File identity](https://api.osf.io/v2/files/68960c8dee9fc1bd9ef62e6f/)

```sh
python -B stage.py /path/to/Ruhr_HandMotion_CenterOutTask.tar.gz
python -B build.py train
python -B verify.py train
python -B build.py validation --release-dir releases
python -B verify.py validation --release-dir releases
python -B build.py test --release-dir releases
python -B verify.py test --release-dir releases
```

Each verification reads the original member for every eligible recording, checks every history and both means, then reconstructs donor order independently. Training verification also compares every displayed sample with the original CSV. The support JSON reports assigned, retained, usable, donor-matched and unmatched counts at each cutoff. The coverage CSV maps an original and a cutoff to a zero-based NPZ row or a reason for exclusion. Evaluation builds require the recorded release for that split.

**Attribution.** Tim Sziburis, Susanne Blex, Tobias Glasmachers and Ioannis Iossifidis released the *Ruhr Hand Motion Catalog of Human Center-Out Transport Trajectories Measured Redundantly in 3D Task-Space* in 2025 under Creative Commons Attribution 4.0 International. This adaptation selects recordings and channels, expresses elapsed time from the native first row, computes future ten-sample means and identifies earlier control recordings. The downloadable data and clips retain CC BY 4.0. [Dataset](https://doi.org/10.17605/OSF.IO/J3QC8) · [DataCite rights record](https://api.datacite.org/dois/10.17605/osf.io/j3qc8) · [License](https://creativecommons.org/licenses/by/4.0/)
