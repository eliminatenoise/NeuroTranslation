# Does the timing of a rat’s firing sharpen a movement forecast?

Watch a rat run along a W-shaped track. A camera gives you five positions from the last second. Simultaneous recordings also resolve dozens of firing units across two brain regions. Count their spikes in four quarter-second bins. Can that extra second of evidence tell you how far the rat will move in the next quarter-second?

**For one of three test rats, the timing helped on both checks.** KL8’s error fell from 2.423 cm with movement alone to 2.318 cm when we added firing. Give the same model firing from an earlier trip and its error rose to 2.425 cm. A simpler forecast still did better for KL8. Continuing at its last observed speed scored 2.296 cm. [Per-rat and per-trip errors](results.json)

| Test rat | Forecasts | Last speed | Previous direct ridge with firing | Shared movement only | Shared movement + firing | Same head, earlier trip’s firing | Scrambled encoder + firing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JS21 | 152 | 3.541 | 3.208 | 2.897 | 2.964 | 2.949 | 2.927 |
| JS34 | 130 | 3.739 | 3.033 | 3.096 | 3.053 | 3.038 | 3.032 |
| KL8 | 267 | 2.296 | 2.369 | 2.423 | 2.318 | 2.425 | 2.330 |
| **Equal weight per rat** | **549** | **3.192** | **2.870** | **2.805** | **2.778** | **2.804** | **2.763** |

Every entry after the forecast count is a mean absolute error in centimetres. Each of a rat’s 15 scored trips counts equally. JS21 did better on movement alone. JS34 improved when given firing, but firing from an earlier trip did a little better again. A single copy of the encoder with its learned numbers scrambled also scored slightly better across the three rats. This experiment gives little reason to credit the earlier training for the average improvement over the direct ridge. The previous benchmark had already reported these three rats’ results when we designed this comparison. The test is retrospective. [Frozen model and comparisons](protocol.json) · [All 549 observed distances and forecasts](predictions.csv)

## Change the timing

At 1,892.5563 s, the camera had last seen JS21 at (37.7362, 8.6715) cm, 30 ms before the cutoff. Its next scoring frame showed (38.8725, 7.2363) cm. The two positions were just **1.831 cm apart**. From the camera history the model predicted 6.424 cm. Firing recorded at the right time pushed the forecast to 6.998 cm. On this window the extra information moved the forecast further from the rat. The earlier direct ridge forecast was 8.455 cm from movement and 8.610 cm with firing. [Camera observations and aligned counts](example.json) · [Measured endpoint and all predictions](example-result.json)

The recording supplied 26 sorted units in dorsal CA1, part of the hippocampus, and 46 in the prefrontal cortex (PFC). The counts below span four consecutive quarters of a second, oldest first. The two positions in each pair are CA1 and PFC. For the timing check we kept the camera history, every model weight and both unit counts fixed. The substitute came from the same rat at the same elapsed time on the preceding trip, whose own cutoff was 1,841.3066 s. Substitution raised the forecast to 7.148 cm. Reversing the four aligned bins instead lowered it to 5.928 cm. [Earlier-trip input you can run](example-donor.json)

| Firing source | 1st pair | 2nd pair | 3rd pair | 4th pair |
| --- | --- | --- | --- | --- |
| Same trip | 34, 46 | 25, 64 | 26, 47 | 33, 61 |
| Earlier trip | 37, 38 | 30, 45 | 39, 47 | 31, 47 |

Across all 549 instants, reversing the bins changed 546 forecasts by more than 0.00000001 cm. The root-mean-square change was 0.898 cm. Substituting the earlier-trip counts changed 542 forecasts with an RMS change of 0.759 cm. The fitted model responds to which quarter contained the firing. Only the measured future positions tell us whether that response helped. [Changes by rat](results.json)

## Run the two inputs

From the package root, with Python 3 and NumPy installed, run both commands. Each returns a list of straight-line distances in centimetres. Set `mode` to `motion` for the fitted camera-only comparison. That mode also accepts just the cutoff, camera times and positions. The Python predictor and the [offline-capable track viewer](https://eliminatenoise.github.io/NeuroTranslation/population-motion/) run this same fitted mode. Use the viewer’s model choice to compare it with the direct linear forecast on the recorded trip.

```sh
python predict.py population/example.json
python predict.py population/example-donor.json
```

Supply `domain` as `rat_population` and `mode` as `combined` or `motion`. For one window, `cutoff_s` is a scalar. `prior_time_s` contains five native seconds and `prior_xy_cm` five `[x,y]` positions in centimetres in a single tracking frame. Take the last camera sample at or before each tap at −1, −0.75, −0.50, −0.25 and 0 seconds from cutoff. A tap may be at most 75 ms old. For a combined forecast also supply `regional_counts` as four integer pairs and `unit_counts` as one pair of positive integers, both in CA1/PFC order. Each count bin begins just after its left tap and includes its right tap. Camera and firing must share the recording clock. For a batch, give every field a leading window dimension. The prediction excludes absolute position, animal identity and clock time as learned features. The caller establishes recording continuity, clock agreement, source identity and anatomical mapping.

## What the shared model actually does

Each pair of successive camera positions gives a 2D displacement. From the last four displacements the model reads length, elapsed time, age of the terminal camera frame, two-step displacement, turn angle cosine and distance at that speed over 250 ms. The earlier spatial Transformer already learned to relate these four intervals. Its attention can look across the four observations in the supplied history. For each interval we keep the resulting movement state and run the original rat output on that state to obtain one number. On the same interval we take each region’s spike count, divide by unit count and 0.25 s, and take `log1p` of that rate. The new readout sees the four speeds scaled to 250 ms, the 24 numbers in the final movement state, all eight ordered rates and each rate multiplied by its interval’s rat output. These products allow a given firing rate to have a different effect depending on the observed movement. All four bins precede the cutoff. Regional firing enters at the readout. [Inference code](adapter.py) · [Shared encoder and model entry point](../predict.py)

Three animals (ER1, JS15 and JS17) supplied 824 fitting windows. Weighted least squares with a fixed ridge penalty of 0.03 fitted a movement-only head and a second head with firing. We standardized each feature on those training windows, weighted each rat equally, each included trip equally within its rat and each window equally within its trip. All original weights stayed frozen. JS21, JS34 and KL8 supplied the 549 evaluation windows. The base model’s earlier rat training used camera data from JS14. The six packets in the present study were the only animal data reopened. The first 16 complete trips in each selected epoch supplied the observations, with the first trip reserved for donor firing. The two models and controls use the same windows. [Train and score implementation](study_adapter.py) · [Six-packet source and window selection](https://github.com/eliminatenoise/NeuroTranslation/tree/425a36b10b1fafc9a062ceee3312ece8f8e53d20/models/population-motion)

This recording tracks the headstage LEDs. The forecast is a straight line connecting two observed positions, including when the path between them curves. The target is the first camera frame at or after cutoff + 250 ms, up to 50 ms late. The latest input frame can itself precede the cutoff. Through the target, the source study screens camera gaps exceeding 100 ms. Future camera availability therefore affects which trials can be scored offline. It never supplies an input feature. Seventeen training windows and two test windows exceeded a time bound of the earlier spatial study when checking all five camera taps (age up to 50 ms or interval 200–300 ms). The earlier runtime checks four interval-ending ages and durations. By that narrower check, 14 training windows and the same two test windows exceeded a bound. The new reader uses the six-packet study’s native ages and durations. [Timing ranges and counts](results.json)

Sorted units were identified retrospectively within each recording. Counts across rats pool by region without matching individual cells. The archive gives no per-unit observation interval, so an empty bin may conflate silence with detection loss. These data do not establish causal control of movement, limb trajectories or online performance. The biological replication unit for a between-rat comparison is the animal. It remains three, however many windows the camera supplies. [Recordings and source attribution](../NOTICE.md)

## Rebuild from the six released packets

Place the separate `population-motion` folder beside this package or supply its actual path. Download the original pre-adapter `movement-weights.npz` as `previous-weights.npz`. The original SHA-256 is `da243393b7a6f72558365a30f7361e45ef7af680538a7fb5a927e930d91b3458`. The new fit reads the three training packets only. Scoring reads the other three, verifies every comparison against the earlier forecast's rat, trip, cutoff, observed target and donor, then writes one prediction for each method and window. Use new output folders. [Previous checkpoint](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/c0d7f0538b8e3949d9d8614c48ebd3509d5fdd0d/models/neurotranslate-0.0/movement-weights.npz) · [Packet and code identities](source-hashes.json)

```sh
python -B population/study_adapter.py fit --source ../population-motion --base previous-weights.npz --out rat-fits
python -B population/study_adapter.py score --source ../population-motion --fitted rat-fits --out rat-scores
python predict.py population/example.json --checkpoint rat-fits/movement-weights.npz
```

The original fit used Python 3.14.8 and NumPy 2.5.5 on a Linux CPU with one BLAS thread. The score table reports one fixed, matched control. It independently shuffles entries inside each frozen weight tensor using seed 20261120, then fits both heads with the identical procedure. The main checkpoint contains only the original trained encoder and fitted deployment heads. `rat-fits/scrambled-heads.npz` contains the two comparison heads. The direct ridge and last-speed values come from the earlier study’s previously checked table. [Frozen study design](protocol.json) · [Source reuse terms](../NOTICE.md)
