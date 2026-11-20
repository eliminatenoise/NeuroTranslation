# Reproduce the two-word locomotion study

## Try the fitted model first

Open a terminal in this folder. With Node.js installed, `node test_generate.mjs` checks both supported actions against the Python output, coordinate by coordinate, and tests unsupported words. It needs no downloads. For Python inference, install NumPy and run `python generate.py run --out run-output.json`.

## Prepare the original recordings

For a complete fit, install Python 3.13, NumPy, PyTorch with CPU support, and ezc3d. The original preparation used ezc3d 1.7.2 and NumPy 2.5.5 under Python 3.14.8. Training used PyTorch 2.14.1+cpu and NumPy 2.4.6 under Python 3.13.15. Assessment used the preparation environment. The numerical comparisons below report the precision observed with those versions. Other versions may round differently.

Start in a fresh working directory containing the package files. Run these commands in order. All raw files stay under `local/`. Each download is checked against the published SHA-256 for that original. Download requests go only to the selected CMU trial URLs; the reserve has no acquisition command. [Original catalogue entries](split.json) · [Source hashes](source-hashes.json) · [Frozen method](protocol.json)

```sh
python -m pip install numpy torch ezc3d
python acquire.py train --local local
python prepare.py train --local local
python fit.py --local local --threads 2
python acquire.py assessment --local local
python prepare.py assessment --local local
python assess.py --local local
python export.py --local local --out reproduced
python -m unittest test_study.py
```

The fit writes its three checkpoints, two averages, train-only predictions and a SHA-256 lock before assessment acquisition. The assessment step verifies the lock, recreates the predictions from the numerical weights and scores the independent recordings. It writes trial-level, class-level and equally weighted group results to `local/results.json`. The export writes the fitted conditional weights, two predicted movements and a short walk and run excerpt from training. Source labels, frames and acquisition hashes identify the measured excerpts.

## What was frozen

We selected recordings from the original CMU “walk” and “run” catalogue searches. The manifest preserves each original spelling. For the selected subject numbers and actions it takes up to the first four matching trial numbers in numeric order. Training comprised 17 walks and 14 runs across six subject IDs. Three held-out subject IDs contributed eight candidate recordings. The 120 Hz files were CMU 113_25 (walk), 113_07 (run) and 139_28 (walk). The headers in 139_10, 139_30, 143_01, 143_32 and 143_42 all reported 60 Hz. Excluding these five left two subject IDs in the score. Subjects 08 and 141 supplied reserve catalogue entries only. The source states that a person can have more than one subject number. [Catalogue source](https://mocap.cs.cmu.edu/) · [Frozen groups](split.json)

The first 12 and last 12 available pelvis positions establish a fixed forward course for each recording. Subtract the first median position from the last, discard the vertical component and normalise. Rotate the measurements into this fixed horizontal frame. In the central half of the recording, find the largest distance by which the right heel leads the left along the course, requiring valid marker samples for all the output positions. The first such maximum fixes the centre frame. Sample frames −36 to +36 relative to that centre, every third native frame. This yields 25 positions per landmark at 40 Hz. The rule needs the whole recording to establish course and phase. It does not test whether words predict either timing or heading from a standing start. Downsampling selects frames directly without a frequency filter. Source marker locations, tracking noise and speed above the display bandwidth can affect the curves. [Marker guide](https://mocap.cs.cmu.edu/markerPlacementGuide.pdf) · [Exact preparation](prepare.py)

The neural decoder has 6,025 adjustable numbers. It learns an eight-coordinate representation for each word. At each requested instant it combines those eight numbers with the normalised time and four sine–cosine pairs, then computes two successive layers of 48 units with tanh activation. A final linear layer produces the 54 body coordinates and three pelvis coordinates. The translation starts at zero. The network learns by minimising squared coordinate error across the 31 recordings. We used all training examples for each of 500 Adam updates, a learning rate of 0.006 and random seed 3429. It predicts Cartesian positions directly, with freely varying distances between sites. It enforces neither fixed bone lengths nor foot contact. [Fit](fit.py) · [Python inference](generate.py) · [JavaScript inference](inference.mjs)

The constant-token control receives the same recordings, network, initial parameters and updates. A second control shuffles the two action labels among training recordings using seed 11273. Averages from all training recordings and from each action separately supply two simpler comparisons. The primary error is the average 3D distance between matching model and measured body markers, first across time and sites, then across trials within each subject ID and finally across eligible subject IDs. The pelvic path has its own 3D distance error. The speed measure compares the mean magnitudes of consecutive body-relative marker velocities at 40 Hz. Each class score averages only over groups represented in that class. [Assessment code](assess.py) · [Complete numerical results](results.json)

With the released weights, JavaScript double-precision arithmetic and the Python NumPy export differed by less than 0.00028 mm across all 2,850 generated coordinates. These are checks on arithmetic and file conversion. Biological accuracy is measured against the three eligible source recordings and is far lower. [Runtime regression](test_generate.mjs)
