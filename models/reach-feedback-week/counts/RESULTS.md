# The movement update helped in one workspace and hurt in the other

The macaque returned a week after training and reached in two parts of the apparatus. In workspace 1, using the last 100 milliseconds of measured arm movement improved the forecast of the next 100 milliseconds of cortical spikes. In workspace 2, keeping the earlier forecast gave a lower error. The model anticipated the second recording less consistently than the prespecified test required. [Source recordings](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original reaching experiment](https://doi.org/10.7554/eLife.48198)

Each table entry gives the change in error when the forecast receives the measured movement, in mean Poisson deviance per acquisition contact per 100 ms. Negative values favour that update. The first comparison asks whether the update improves the earlier forecast. The second asks what happens if it instead receives the movement residual from a different earlier trial. Brackets give 95% intervals from resampling eight consecutive trials at a time.

| Count endpoint | Workspace | Update minus earlier forecast | Update minus wrong movement |
| --- | ---: | ---: | ---: |
| All exported spikes on 37 contacts | 1 | −0.201 [−0.322, −0.056] | −1.042 [−1.378, −0.697] |
| All exported spikes on 37 contacts | 2 | +0.103 [+0.042, +0.167] | −0.598 [−0.749, −0.454] |
| Sort zero on the same 37 contacts | 1 | −0.075 [−0.140, −0.014] | −0.730 [−0.905, −0.530] |
| Sort zero on the same 37 contacts | 2 | +0.102 [+0.050, +0.157] | −0.429 [−0.537, −0.331] |
| Positive sorts pooled on 17 contacts | 1 | −0.225 [−0.350, −0.061] | −1.276 [−2.072, −0.666] |
| Positive sorts pooled on 17 contacts | 2 | −0.325 [−0.827, +0.082] | −3.645 [−5.264, −2.186] |

For the primary 37-contact endpoint, the update, earlier forecast and wrong-motion forecast scored 3.824, 4.026 and 4.867 in workspace 1. Predicting the same training mean every time scored 3.852. In workspace 2 those four scores were 4.783, 4.680, 5.381 and 4.118. The fixed training mean also outperformed both fitted positive-sort models in both workspaces. This comparison matters when asking whether a movement-dependent forecast would be worth using on another day.

The selected recording contained 512 trials in two blocks. Three trials had no assigned workspace. Workspace 1 had 241 assigned trials, 111 rewarded, with 201 candidate windows. Workspace 2 had 268 assigned trials, 166 rewarded, with 292 candidates. All candidate windows passed the numerical checks on every endpoint. In each workspace four windows lacked an eligible earlier same-ordinal donor. The shared comparison therefore covers 197 windows from 109 trials in workspace 1 and 288 from 161 in workspace 2. All assigned trials remained in the resampling roster. Only second and third go signals occurred among the eligible later-day windows.

Discarding trial order and resampling individual trials within each physical block gave primary update-minus-earlier intervals of [−0.326, −0.040] in workspace 1 and [+0.041, +0.168] in workspace 2. For the wrong-motion comparison those intervals were [−1.515, −0.661] and [−0.789, −0.419]. The machine-readable results include both interval calculations, the two count-persistence references, values for each contact, and denominators by recording block. The companion reproducibility instructions describe the clock and the fitted heads.

This comparison covers one animal on one later recording day. Electrode labels permit a comparison of exported contact counts. They cannot establish which individual neurons the array picked up on both days. The apparatus supplied measured arm positions and cortical events. The study did not record the peripheral sensory traffic that might contribute to those events.
