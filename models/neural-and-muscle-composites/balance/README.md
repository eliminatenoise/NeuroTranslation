# What should a movement model combine first?

Tilt the scene around a person standing or walking on a balance beam. Electrodes record voltage on the scalp and over eight lower-leg muscles. A camera follows a marker at the base of the spine. Give a model the last 625 milliseconds of those recordings. Can it predict the marker’s path and the strength of the muscle signals over the next 125 milliseconds? Steven Peterson and Daniel Ferris recorded both outcomes directly. [Original recordings, CC0](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Methods](https://doi.org/10.1016/j.dib.2021.107635)

Pairing scalp voltage with muscle voltage, and the measured marker positions with a simple projection of where they might lead, gave the smallest **movement error** of the three complete networks. Mixing all inputs earlier gave the smallest **muscle-voltage error**. The study therefore found no single winner for both outcomes.

| First combination | Muscle error, µV | Mean 3D path error, mm | Final position error, mm |
|---|---:|---:|---:|
| Scalp + muscle, position + projected movement | 10.102 | **2.055** | **4.304** |
| All four mixed early | **9.863** | 2.119 | 4.369 |
| Scalp + position, muscle + projected movement | 10.045 | 2.128 | 4.455 |
| Previous muscle amplitude, stationary marker | 10.274 | 4.491 | 8.494 |
| Previous muscle amplitude, constant marker velocity | 10.274 | 2.769 | 5.894 |

Each score gives the same weight to each of six people excluded from fitting. It averages 1,759 eligible rotations, three fixed training seeds, and both rotation directions. The networks trained on 5,179 other rotations in 18 people, with 2,600 standing and 2,579 walking. Six additional participants stayed in reserve. Earlier studies had already examined the six comparison participants, so this is a retrospective comparison on known recordings. [Earlier eligibility and split](https://github.com/eliminatenoise/NeuroTranslation/tree/a0716992efc24ff02db7e805ce85e72b34889f03/models/muscle-and-motion/source)

## Where the simple forecast wins

| Condition | Recorded events | Paired path error, mm | Early path error, mm | Crossed path error, mm | Constant velocity, mm |
|---|---:|---:|---:|---:|---:|
| Standing | 879 | 0.833 | 0.904 | 0.919 | **0.674** |
| Walking | 880 | **3.278** | 3.333 | 3.337 | 4.864 |

The camera supplies a strong clue while someone is standing. Continue the marker’s recent velocity and the average error is under seven tenths of a millimetre. During walking, pairing the inputs reduced error by about 1.59 mm against that same rule. For muscle voltage, repeating the previous amplitude gave 4.782 µV error during standing, compared with 4.844 µV for early mixing. During walking, early mixing reduced error from 15.766 to 14.882 µV. Both conditions involved the same six people. Standing preceded walking, so the difference can also reflect order, fatigue or practice. [Acquisition methods](https://doi.org/10.1016/j.dib.2021.107635)

The uncertainty matters at this scale. Across both postures, the paired network reduced path error against early mixing by 0.063 mm (95% paired interval 0.028–0.095 mm) and against crossed pairs by 0.073 mm (0.048–0.095 mm). It *increased* muscle-voltage error against early mixing by 0.239 µV (0.205–0.275 µV). The prespecified requirement for an advantage on both outcomes failed. These intervals resample whole people. They describe six people in one experiment.

## Which recording carried the prediction?

On 1,687 rotations with an eligible earlier event, exchanging the two electrical histories together raised muscle error from 10.016 to 14.182 µV. Exchanging the measured and projected movement histories together raised path error from 2.056 to 6.166 mm. Each donor came from the same person, posture, tilt direction, third of the session and pattern of usable scalp channels. The clocks verify that donor and recipient windows did not overlap.

Exchange the scalp trace alone and the differences shrink to 0.004 µV and 0.003 mm in magnitude, with paired intervals spanning zero. A separately trained model that kept scalp-channel availability but removed scalp-voltage values achieved 9.972 µV and 2.024 mm, lower on both outcomes in all six people. Removing the leg voltage instead raised muscle error to 13.460 µV. These controls identify recent muscle voltage and marker motion as useful for their respective outcomes. They provide no evidence of extra predictive information from the three measured scalp sites in the paired network. [All comparisons, including exact matched denominators](results.json)

There is one camera trajectory. From its recent history, estimate the marker’s velocity over 8, 16, 32 or 64 samples. Multiply each velocity in mm/s by 0.125 s. That gives four possible future displacements in mm under the assumption of constant velocity. The model gets those estimates on one input and the original positions on another. Removing the velocity projections increased paired-network path error by 0.045 mm, although their entire information content was already present in the measured position input. The projections change how easily a small model can use the data.

The muscle electrodes measured electrical activity at the skin, once per channel. Peripheral nerve spikes, muscle shortening, tendon strain and force each require other measurements. The three scalp sites also mix electrical sources. A good short forecast cannot establish which neural circuit caused a movement. The archived voltages were filtered, camera positions resampled, and event eligibility checked the later measurement window. The results describe these retained offline recordings. [Source design](https://doi.org/10.1523/ENEURO.0207-18.2018) · [BioSemi cap layout](https://www.biosemi.com/download/Cap_coords_all.xls)

## Reproduce the comparison

The source reader rebuilds version 1.0.3 from the original recordings. Its frozen selection chooses 18 people for development and six for historical assessment. Each standing or walking session has one immutable recording and one clock. The local preparation checks original-file digests, the source registry of events, direction, cutoff, marker coordinates, muscle units and electrode names. Keep reconstruction files and event arrays in a private work directory. The fit command creates weights and training-set scale factors in your local work directory. The result table contains group summaries. [Pinned source reader](https://github.com/eliminatenoise/NeuroTranslation/tree/a0716992efc24ff02db7e805ce85e72b34889f03/models/muscle-and-motion/source)

Install NumPy, SciPy and PyTorch in a Python environment with support for those packages. The source reader has its own pinned requirements. From this directory, set WORK to a private directory and READER to the pinned source reader directory. Preparing both stages requires approximately 6 GB of free disk space. If the verified source recordings and muscle/path archives already exist, begin with the two prepare.py calls.

```sh
export WORK=/path/to/private-work
export READER=/path/to/NeuroTranslation/models/muscle-and-motion/source
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$WORK"
python "$READER/acquire.py" development "$WORK"
python "$READER/extract.py" development "$WORK"
python "$READER/verify.py" development "$WORK"
python prepare.py development "$WORK" "$WORK/paired-development.npz"
python fit.py "$WORK/paired-development.npz" "$WORK/refit.npz"
python "$READER/acquire.py" assessment "$WORK"
python "$READER/extract.py" assessment "$WORK"
python "$READER/verify.py" assessment "$WORK"
python prepare.py assessment "$WORK" "$WORK/paired-assessment.npz"
python evaluate.py "$WORK/paired-assessment.npz" "$WORK/refit.npz" "$WORK/results.json" "$WORK/timing.json"
```

The last command scores the fit saved in your local work directory. The reported run used Python 3.14.8, NumPy 2.5.3, SciPy 1.18.1 and PyTorch 2.14.0+rocm10.1.0 on CPU. Model arithmetic uses float32 and the score reductions use float64. Small numerical differences can follow a change of backend or package version. [Frozen analysis choices](protocol.json) · [Fit and inference timings](runtime.json)

Each network has 6,244 trainable parameters. The encoders first map each input to 16 numbers. Each pair contributes both original projections and their componentwise product to a learned branch. The two branch outputs meet in a final learned layer, alongside their product, posture and direction. Early mixing applies a fixed orthogonal transform across all four encoded inputs before either branch, so every branch sees contributions from every input. Crossed pairing changes which streams meet first. All three use identical initialization and batches within each seed, 384 updates of 128 examples, and the same two losses. The comparison covers these three constructions and this forecast horizon. [Model implementation](model.py)
