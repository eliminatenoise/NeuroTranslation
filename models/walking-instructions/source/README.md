# Where will the heel land 100 milliseconds from now?

A person walking “as usual” can already be moving quickly. How much does the instruction “fast but not running” add once we have seen that person move? Schreiber and Moissenet gave those two instructions on a 10 m level walkway. Ten cameras tracked skin markers at 100 frames per second as people walked barefoot. We take 21 successive camera frames and ask how far the pelvis and right heel will move in the next ten. Each instruction labels a whole walk. The source gives neither a recording of the speaker nor the instant when a particular word was spoken. [Original methods](https://doi.org/10.1038/s41597-019-0124-4)

## Read the measurements

Download the original ZIP from the version-8 release and save it as `walking.zip`. Use Python 3.12 in a local environment. The command checks the archive length, publisher MD5 and independently recorded SHA-256. It reconstructs the original participant split from the ZIP directory, checks the inventory, and inflates the selected recordings for the requested group. It checks each file’s length, CRC32 and SHA-256 before decoding it. [Original walking archive](https://ndownloader.figshare.com/files/22295019) · [Versioned dataset](https://doi.org/10.6084/m9.figshare.7734767.v8)

```sh
python -m pip install -r requirements.txt
python read_walks.py --archive walking.zip --partition development --output prepared
```

The result is `prepared/development.npz`, readable with `numpy.load(path, allow_pickle=False)`. The accompanying `development-receipt.json` records every scheduled trial and proposed sampling point, including those that failed a check. Both files are local research data. They contain original participant codes. This package distributes the reader and its checksums. Download the source measurements from the authors.

| Array | What one row means |
|---|---|
| `person`, `condition`, `repeat` | Source participant code, instruction 4 or 5, recording 1–3. Use the person code to keep all walks by one participant together. |
| `offset`, `cutoff` | Number of frames since first right strike and frame index at the end of the history. Both are integers. The first frame in the archive is physical frame 1, array index 0. |
| `history_mm` | 21 frames × 2 positions × 3 directions. In each frame the pelvis comes first, the right heel second. Both positions use the pelvis at cutoff as the origin. |
| `future_delta_mm` | 2 positions × 3 directions. Each position’s displacement from its own cutoff position to the frame 100 ms later, in millimetres. |

The pelvis position is the mean location of four reflective markers over the left and right, front and back, superior iliac spines (`L_IAS`, `R_IAS`, `L_IPS`, `R_IPS`). The heel marker (`R_FCC`) sits over the back of the right heel bone. Both follow the skin. The pelvis value is an estimate from its four surface landmarks. [Author channel definitions](https://ndownloader.figshare.com/files/14870426)

Walkers cross the room in either direction. Forward follows the horizontal line from the first to the last *observed* pelvis position in each history. If the horizontal unit vector along that line is `(x, y)`, the vector to its left is `(−y, x)`. The third direction points up. At least 10 mm of horizontal travel must define this line. We use the same axes to express the movement that follows. This calculation needs no future heading or whole-stride speed.

## Which walks count?

The original walking study supplied 50 participants. Sorting their source codes recovers the earlier partition. The first 30 form the development group, the next ten the historical assessment group, and the last ten remain in reserve. Only repeats 01, 02 and 03 of conditions C4 and C5 are selected. The earlier feasibility check examined both first-repeat conditions for one development person. The ten historical people had also belonged to earlier movement studies. In the earlier C2 paired heel-and-force study, eight of those ten contributed eligible original walks and six contributed eligible later walks. Repeated use of that group limits claims about new participants. [Dataset and recording scheme](https://doi.org/10.6084/m9.figshare.7734767.v8)

The four candidate cutoffs are 100, 200, 300 and 400 ms after the first annotated right foot strike. A window needs all 21 stored history frames and the target frame ten samples later, strictly before the next annotated right strike. Every required coordinate and residual must be finite and every residual nonnegative. No intervening frame between cutoff and target is needed. Keep all available qualified windows in the local output. The primary comparison uses only people with at least one qualified walk in both conditions. The receipt also counts people in each condition alone.

All 30 development people supplied all three walks in both conditions. Of 360 proposed windows per condition, 323 qualified for usual walking and 322 for fast walking. All 75 exclusions occurred at the earliest cutoff because the cropped record began too late to contain its 21-frame history. No invalid stored sample of the five selected markers was found across those 180 walks.

The authors reconstructed missing marker data and applied a fourth-order 6 Hz low-pass filter forward and backward before cropping each recording. Valid residuals in the stored file do not identify which original camera samples were reconstructed. The forecast uses past frames of that processed export. Live sensing would need its own timing and accuracy check. Neither a skin marker nor an instruction label measures a nerve signal. [Marker processing in the authors’ toolbox](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/importTrialMarker.m)

All ten historical people supplied three walks under each instruction. The usual condition yielded 112 of 120 windows and the fast condition yielded 104 of 120. More of the early windows lacked a full history in the fast condition (16, compared with 8 in the usual condition). All other proposed windows qualified. Across both groups, zero participants qualified under only one instruction.

Rebuild the historical arrays against the public checksum extract of the frozen model manifests with the command below. The extract identifies the original assessment release, the two fit manifests and the model files they covered. Reconstruction writes `historical.npz` and `historical-receipt.json` locally.

```sh
python read_walks.py --archive walking.zip --partition historical --output prepared --fit-seal fit-manifest.json --fit-seal-sha256 561e69cdc42f293bf4108c0a399e4c6c00a8f261c5aca5e9f712da3a78ab182c
```

Céline Schreiber and Florent Moissenet released the original measurements under CC BY 4.0. These derived arrays select two walking instructions, average the four pelvic landmarks, express the trajectories in walking coordinates, and calculate future displacements. [Original data and attribution](https://doi.org/10.6084/m9.figshare.7734767.v8) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
