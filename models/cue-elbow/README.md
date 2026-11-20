# Can scalp EEG improve a forecast of elbow movement?

A quarter of a second after a movement cue, we already know two things. We know whether the person was asked to bend or straighten their elbow, and we have the latest readings from their elbow sensor. What does an electrode over the left side of the scalp add? In 36 trials from one person, adding the electrode's early voltage changes **raised** the forecast error from **0.07237 to 0.07859 native elbow units**. Giving the model a different trial's EEG produced almost the same error, 0.07780. The correctly paired signal failed the prespecified test. [Frozen protocol](protocol.json) · [Development scores](scores.json)

## What was on the clock?

Ofner and colleagues seated each participant with their right arm supported by an exoskeleton. They logged the visual cue, recorded electrical activity at the scalp and measured the movement of the arm. We used the first three execution runs of the participant identified as S1. Each contained six elbow-flexion and six elbow-extension cues. These labels come from the experimenters' event table. The recording gives us the requested action and the measured response. It supplies no transcript or direct measurement of a participant's private intent. [Original study](https://doi.org/10.1371/journal.pone.0182578) · [Dataset](https://doi.org/10.5281/zenodo.834976) · [Event and channel tables](https://zenodo.org/records/834976/files/data%20set%20description.pdf)

At cue + 0.25 seconds, the forecast closes its inputs. The target is how much the elbow reading changes by cue + 1.00 second. At both ends we take the median of the last eight samples from the 64 Hz elbow sensor. This reduces the influence of a single unusual reading. The model sees the elbow's recent history and, where indicated, four short bins from the 512 Hz scalp or eye recording. A positive change means the stored elbow value increased. The file gives no physical units or calibrated anatomical sign for this channel. Display latency, sensor delay and cross-device drift are unknown. [Window and channel definitions](REPRODUCE.md)

## Which forecast came closest?

We fitted each model on two complete runs, scored the third, then rotated until all three had been scored. Each fit used 24 trials and scored 12. The table gives mean absolute error in native elbow units. Its balanced column gives equal weight to each of the six run-by-cue groups. Each group contained six trials, so the pooled error and balanced error agree to rounding.

| Available information | Balanced, 36 trials | Flexion, 18 | Extension, 18 |
| --- | ---: | ---: | ---: |
| Zero change | 0.07516 | 0.06468 | 0.08564 |
| Typical change for the requested action | 0.07432 | 0.05247 | 0.09617 |
| Cue and recent elbow history | 0.07237 | 0.05725 | 0.08750 |
| Same inputs plus C3 scalp EEG | 0.07859 | 0.06198 | 0.09521 |
| Same inputs plus eye channels | 0.09082 | 0.06573 | 0.11591 |
| C3 model given another same-cue trial's EEG | 0.07780 | 0.05229 | 0.10332 |
| Four-bin C3 attention plus cue and elbow history | 0.07122 | 0.05791 | 0.08453 |

The ordinary C3 model improved on the mechanical forecast in run 2 alone. In run 3 its error rose from 0.07098 to 0.09024. Across the three runs it worsened both cue groups. The eye channels did worse still. These electrodes provide one check on eye activity near the cue. Averaging all three can cancel some eye movements, and neither this check nor the EEG swap can establish the origin of the scalp voltage. [All seven methods by run and cue](scores.json)

| Withheld run | Task | Trials | Cue and elbow | Plus C3 | Four-bin attention |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Flexion | 6 | 0.07099 | 0.07320 | 0.07195 |
| 1 | Extension | 6 | 0.10850 | 0.10656 | 0.10654 |
| 2 | Flexion | 6 | 0.04987 | 0.04834 | 0.04890 |
| 2 | Extension | 6 | 0.06293 | 0.06299 | 0.06171 |
| 3 | Flexion | 6 | 0.05089 | 0.06439 | 0.05289 |
| 3 | Extension | 6 | 0.09107 | 0.11608 | 0.08533 |

A cue specifies an action. How much the elbow moves over the next three quarters of a second is a separate measurement. Twenty-five of the 36 changes had magnitude at most 0.1 native units. Seventeen had the opposite sign to the median for the corresponding cue in the two training runs. Both counts include flexion and extension. The 0.1 cutoff describes these recordings and carries no clinical or physical threshold. All 36 trials contributed to every method's score.

## What did attention buy?

The exploratory comparison gave the last C3 bin a way to weight the three earlier bins and itself. It passed one weighted value to the same regularized linear forecast. That reduced balanced error by 0.00115 relative to cue and elbow history. Error fell on extension and rose on flexion. The attention calculation used a fixed rule and a scale learned from training. The small output layer was fitted. A larger Transformer would introduce further parameters into folds with only 24 training trials. The matched EEG swap and eye controls were specified for the ordinary C3 model. The attention result has yet to pass those tests or a test on an independent person. [Attention calculation](REPRODUCE.md) · [Aggregate parameters](model.json)

One flexion example from the first run was known from an earlier source check when the protocol was fixed. The other outcomes were unopened by the fitting team. These runs are development data. Withholding a run from the same person gives no estimate of between-person uncertainty. We have no live performance measurement, inference of self-generated language, recording of muscle contraction, or evidence about movement outside this supported right-elbow task.

## Run it

The Linux, macOS and Windows launchers apply the six fitted methods to an invented input. The sample's four elbow medians begin at 44.0 native units. The cue-and-elbow forecast returns a change of +0.03316. Including C3 changes the estimate to +0.03225. These numbers illustrate software behavior. The model file contains the refit on all 36 development trials. The performance tables above come from the three separate withheld-run fits. [Run, edit inputs or rebuild from source](REPRODUCE.md) · [Attribution and licences](NOTICE.md)
