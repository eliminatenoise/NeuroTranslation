# How much movement can one word predict?

Type **walk** or **run**. A small neural network produces 0.60 seconds of movement for the head, trunk, arms and legs. Every 25 milliseconds it places 18 points in three dimensions and supplies a separate position for the pelvis. The two words produce different strides. Enter either word again and the same stride returns.

The model learned from 31 recordings in the Carnegie Mellon motion archive. Cameras tracked markers attached to people’s skin. Each recording came with a short catalogue description, written about the action. We fitted the network to predict the measured movement from that description. A new request gives it just the action word and an internal clock. It computes the coordinates with its fitted weights. [CMU motion capture and file formats](https://mocap.cs.cmu.edu/info.php) · [Marker placement](https://mocap.cs.cmu.edu/markerPlacementGuide.pdf)

## How close did it get?

Averaged over two held-out catalogue subject IDs, the generated body points missed the measured points by **89.82 mm**. The average recorded walk or run from the training set missed by **89.88 mm**. Ignoring the action word raised the error to **102.51 mm**.

| Method | Body marker error, mm | Pelvis path error, mm |
| --- | ---: | ---: |
| Word-conditioned decoder | 89.82 | 185.03 |
| Training average for the requested action | 89.88 | 185.19 |
| Same decoder with a constant input | 102.51 | 299.80 |
| Average of all training clips | 102.52 | 299.77 |
| Same decoder trained with shuffled words | 114.13 | 341.21 |

Word conditioning helped on this comparison. The **0.06 mm** difference between the network and the action average gives little reason to prefer one to the other. We had two eligible walks and just one eligible run. Five more test recordings listed at 120 Hz in the catalogue carried a 60 Hz clock inside the file. We kept the preselected 120 Hz rule. Ten further recordings from two reserved groups remained unopened. CMU cautions that the same person can have different subject IDs. Identity beyond the recorded groups is unknown. [Results by recording, group and action](results.json) · [Frozen split](split.json) · [CMU archive notes](https://mocap.cs.cmu.edu/)

We gave each clip the same rough starting point in the stride by finding where the right heel led the left near the middle of the recording. That timing comes from the measured clip during preparation. The word itself reveals neither which foot a person will lead with nor how fast they will move. The fixed orientation follows the walkway direction estimated from the whole recording. Two training windows moved against that direction. One word can describe many bodies, speeds and starting poses. This first decoder supplies only one trajectory per action. The study contains no participant commands, brain recordings, muscle signals or feedback measurements.

## Generate coordinates

The easiest executable uses JavaScript and the supplied weights. In Node.js, run the following command in this folder.

```sh
node --input-type=module -e "import {generateMotion} from './inference.mjs'; import {readFileSync} from 'node:fs'; console.log(JSON.stringify(generateMotion('walk', JSON.parse(readFileSync('weights.json','utf8')))))"
```

For Python with NumPy, run `python generate.py walk --out movement.json`. Both implementations accept *walk*, *walking*, *run*, *running*, *run/jog*, *jog* and *jogging*, ignoring case and surrounding spaces. Unknown phrases return `null` in JavaScript and a usage error in Python. The catalogue’s “run/jog” maps to the run token. The other spellings are explicit aliases; the decoder learned two tokens.

`positionsMm[frame][site][axis]` gives positions relative to that frame’s pelvis. `rootMm[frame][axis]` gives the displacement of the pelvis from its first displayed position. Add the two to see the body travel. The coordinates run to the right of the recording’s net horizontal course, along that course, and up. The head is the midpoint of two forehead markers. Each wrist is the midpoint of its two markers. The waist landmarks approximate the pelvis, and all other named sites are skin markers. The lines a viewer draws between them are guides. Skin markers and internal joint centres can move differently. [Landmark definitions and connections](schema.json)

The two generated examples can open directly as JSON files. Two separate measured excerpts show what the archive actually captured. Both reference excerpts come from the training group. [Generated walk](walk.json) · [Generated run](run.json) · [Measured walk, CMU 07_01](reference-walk.json) · [Measured run, CMU 09_01](reference-run.json)

[Reproduce the fit and evaluation](REPRODUCE.md) · [Source rights and project license](RIGHTS.md)
