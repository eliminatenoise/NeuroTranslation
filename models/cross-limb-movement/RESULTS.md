# The wrist gain depends on the training budget

Six people contributed 1,759 balance rotations. Three different people contributed 882 light-cued lifts across 27 numbered series. All nine were outside these fits and had already appeared in earlier assessments of other targets. Each usable event has a future marker path and muscle amplitude. A comparison across all five arm muscles was impossible because the original authors reported electrode faults in every historical arm participant. The arm results describe the named usable channels on that event. Neither study measured the other study’s people or coordinate system.

Each row gives the mean absolute error in muscle RMS, the mean distance across 32 future marker positions, and the distance at the last point, 125 milliseconds later. Negative differences favour the first model. Compute these means within a participant’s task conditions before averaging participants.

| Fit or control | Leg RMS (µV) | Sacrum path (mm) | Sacrum end (mm) | Arm RMS (native) | Wrist path (mm) | Wrist end (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Joint, 192 updates per study | 10.279 | 2.169 | 4.919 | 0.007845 | 4.870 | 11.524 |
| Single study, 192 | 10.272 | 1.962 | 4.336 | 0.007783 | 5.100 | 12.265 |
| Single study, 384 | 10.273 | 1.981 | 4.363 | 0.007637 | 4.394 | 10.259 |
| 192 foreign + 192 target | 10.272 | 2.059 | 4.652 | 0.007987 | 4.857 | 11.426 |
| 192 foreign, target history scales | 10.376 | 68.559 | 142.508 | 0.008531 | 8.436 | 21.176 |
| 192 shuffled foreign + 192 target | 10.272 | 2.059 | 4.698 | 0.007909 | 4.993 | 11.936 |
| 192 aligned foreign + 192 target | 10.272 | 2.059 | 4.652 | 0.007987 | 4.857 | 11.426 |
| Previous RMS + stationary marker | 10.274 | 4.491 | 8.494 | 0.008488 | 17.198 | 37.649 |
| Previous RMS + repeated path | 10.274 | 3.265 | 5.894 | 0.008488 | 14.716 | 29.428 |
| Previous RMS + last-two-knot velocity | 10.274 | 2.041 | 4.651 | 0.008488 | 8.391 | 21.083 |

The 192-update specialist has exactly the same target batches as the joint fit. The 384-update specialist spends the entire joint update budget on its target study. The joint fit improved the wrist path over the shorter specialist in each of three people, then lost that advantage against the longer specialist in all three. All six balance participants had greater sacrum path error with the joint fit than either specialist. Lower-limb RMS was close to simply repeating the previous 125 ms of amplitude.

## How uncertain is the difference?

| Joint minus target-only | Outcome | Mean difference | Paired 95% interval | 98.75% upper bound | People lower |
| --- | ---: | ---: | ---: | ---: | ---: |
| 192 target | Balance RMS (µV) | 0.0074 | -0.0056, 0.0173 | 0.0182 | 2/6 |
| 192 target | Balance path (mm) | 0.2068 | 0.1666, 0.2421 | 0.2453 | 0/6 |
| 192 target | WAY RMS (native) | 0.0000622 | -0.0000404, 0.0001136 | 0.0001136 | 1/3 |
| 192 target | WAY path (mm) | -0.2300 | -0.2935, -0.1737 | -0.1737 | 3/3 |
| 384 target | Balance RMS (µV) | 0.0060 | -0.0138, 0.0272 | 0.0290 | 3/6 |
| 384 target | Balance path (mm) | 0.1879 | 0.1459, 0.2315 | 0.2455 | 0/6 |
| 384 target | WAY RMS (native) | 0.0002085 | 0.0000427, 0.0003822 | 0.0003822 | 0/3 |
| 384 target | WAY path (mm) | 0.4767 | 0.4019, 0.5996 | 0.5996 | 0/3 |

The four primary upper bounds had to fall below zero together for the prespecified joint-advantage claim. Neither comparator met that condition. Three arm participants cannot support a precise population bound. At that sample size the bootstrap can take at most ten distinct means, and the largest participant difference sets the extreme percentile. More trials from the same three people would leave this limitation intact.

## What transferred?

Starting from the lower-study weights and adapting on the arm fitting participants reduced wrist-path error by 0.243 mm versus a fresh 192-update target fit, while increasing arm RMS error by 0.000204 native units. The 384-update arm-only fit did better on both outcomes. In the other direction, pretraining on lifts and adapting on balance increased the mean sacrum-path error by 0.098 mm versus the 192-update balance specialist and 0.079 mm versus the 384-update specialist. A foreign-frozen model with target-calibrated scales missed the sacrum path by 68.56 mm. Its unused target name/segment embeddings and different source frame make it a diagnostic of the unadapted model. This test concerns transfer between fitted numerical models. It supplies no direct measure of a person transferring a skill.

The shuffled-source check changes which source trial supplies both future outcomes while preserving the pairing of muscle and path labels. Its training exposure is matched to an aligned-source control. The aligned-source and ordinary adapted fits coincide here because every fitted source row admitted a disjoint donor. Shuffling the source task before target adaptation changed the wrist path error from 4.857 to 4.993 mm and the sacrum path error from 2.0595 to 2.0593 mm.

## Whose muscle history is it?

Swap muscle inputs between nonoverlapping trials of the same person and task condition, hold marker history fixed and keep the channel intersection. The primary control admits all 1,759 balance and 882 upper events. The table gives wrong-trial minus intact error. A positive difference means the correct trial helped.

| Input change | Leg RMS (µV) | Sacrum path (mm) | Arm RMS (native) | Wrist path (mm) |
| --- | ---: | ---: | ---: | ---: |
| Swap muscle patches and previous RMS | 7.1506 | 0.0034 | 0.0012248 | 0.1054 |
| Swap patches, retain true previous RMS | 0.0044 | 0.0034 | 0.0000083 | 0.1054 |

Restoring the true RMS bypass removed nearly all the muscle-amplitude penalty. The shuffled patches alone changed the sacrum path by +0.0034 mm (paired 95% interval −0.0005 to +0.0068) and the wrist path by +0.1054 mm (+0.0080 to +0.2548). A swap changes a predictor in the recorded trial. These differences cannot establish that changing a muscle would physically cause the predicted movement.

## Which measurements contributed?

The joint model had 4.803 µV muscle error and 0.986 mm path error across 879 standing events, and 15.756 µV and 3.351 mm across 880 walking events. Both figures average the same six people. For the hand, all nine numbered series positions contributed, with all three people represented at each position.

| Muscle | Available events | Contributing people | Joint MAE | Signed error | Unit |
| --- | ---: | ---: | ---: | ---: | ---: |
| left tibialis anterior | 1759 | 6 | 10.671 | -0.024 | µV |
| left soleus | 1759 | 6 | 4.485 | 0.136 | µV |
| left medial gastrocnemius | 1759 | 6 | 14.382 | -1.316 | µV |
| left peroneus longus | 1759 | 6 | 11.654 | 0.344 | µV |
| right tibialis anterior | 1759 | 6 | 13.142 | 0.195 | µV |
| right soleus | 1759 | 6 | 4.130 | -0.279 | µV |
| right medial gastrocnemius | 1759 | 6 | 11.988 | -0.593 | µV |
| right peroneus longus | 1759 | 6 | 11.782 | 0.586 | µV |
| right anterior deltoid | 294 | 1 | withheld | withheld | native |
| right brachioradialis | 882 | 3 | 0.006671 | 0.003734 | native |
| right flexor digitorum | 588 | 2 | 0.004335 | 0.000813 | native |
| right common extensor digitorum | 588 | 2 | 0.013130 | 0.005809 | native |
| right first dorsal interosseous | 588 | 2 | 0.004293 | 0.001784 | native |

Signed error is forecast minus observation. The anterior deltoid has a single historical contributor, so its numeric channel result stays private. Its available observations still count in the frozen group error. The 32-offset mean signed coordinate errors for the joint model are -0.189, -0.060, 0.449 mm in ML/SI/AP for balance and -0.489, 0.451, -0.919 mm in the WAY X/Y/Z frame.

## Before the historical assessment

Three development folds kept each participant entirely on one side of the split. The two studies provided 5,179 rotations in 18 people and 1,764 lifts in six people. Each development event received one prediction from a model fitted on other people.

| Development fit | Leg RMS (µV) | Sacrum path (mm) | Arm RMS (native) | Wrist path (mm) |
| --- | ---: | ---: | ---: | ---: |
| Joint | 11.360 | 2.655 | 0.010607 | 3.937 |
| Single study, 192 | 11.362 | 2.502 | 0.010090 | 3.943 |
| Single study, 384 | 11.365 | 2.497 | 0.010496 | 3.552 |
| Foreign + 192 target | 11.361 | 2.575 | 0.010278 | 3.912 |

The held-person errors, conditional transfer comparisons and donor interventions by study, posture and available channel are reported in the two group summaries. [Historical assessment](scores.json) · [Development](development.json) · [Methods and training budgets](EXPERIMENT.md)
