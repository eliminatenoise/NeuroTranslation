# Could the arm forecast predict a change in muscle–tendon length?

The original researchers used OpenSim to calculate how long each of 39 paths was as the arm moved. Each reference here is a change in that calculated length over the next 100 ms. The movement tracks also contributed to the OpenSim calculation. The experiment has no measured muscle force, activation, fascicle shortening or peripheral nerve signal against which to check this readout.

A ridge regression learned how arm displacement and starting position related to the 39 length changes on September 7. Feed it the predicted movement on September 14 and compare the endpoint with the source model. A second regression predicts length changes directly from earlier motion and cues. All 39 paths exceeded the training threshold of 0.1 mm for the moving subset. The data retain the source's label order and measured axes. [Model and timing](DESIGN.md) · [Path labels](names.json)

| Input or reference | Workspace 1 | Workspace 2 |
|---|---:|---:|
| Count-informed arm forecast | 1.047 | 1.539 |
| Pose-and-cue arm forecast | 1.055 | 1.494 |
| Earlier reach's cortical history | 1.040 | 1.539 |
| Frozen body-and-cue Transformer | 0.986 | 1.324 |
| Linear correction with counts | 1.003 | 1.471 |
| Linear pose-and-cue correction | 1.030 | 1.572 |
| No length change | 0.689 | 0.540 |
| Continue recent arm velocity | 1.509 | 2.481 |
| Measured arm path, available retrospectively | 1.087 | 1.783 |
| Direct length regression | 0.925 | 0.764 |

Values are endpoint mean absolute error in mm over all paths. Each neural seed is scored before averaging. The table compares methods on the same 197 and 288 windows. The 95% paired intervals for adding counts rather than pose alone were [−0.048, +0.031] and [−0.004, +0.097] mm. The intervals for each reach's counts against another reach's counts were [−0.022, +0.030] and [−0.035, +0.032] mm. Both paired controls were required to improve in both workspaces. The length readout missed that criterion. The results also give each named path's endpoint and trajectory errors and the available and donor-matched denominators. [Full numerical results](results.json)
