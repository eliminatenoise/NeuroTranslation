# Held recording-group forecast

**strict-afferent**. Exploratory held-afferent forecasts in three original two-clock members, all from filename prefix 0. The registered three-prefix evaluation was unevaluable in both populations.
The source contains 16,262 scored windows in 94 trials and 3 afferent members. The nonoverlapping lag comparison retains 15,792 windows. All counts refer to detected spikes per 20 ms.

| Model | Held mean deviance | Held count MAE | Mean observed | Mean forecast | Observed / forecast |
| --- | ---: | ---: | ---: | ---: | ---: |
| constant | 1.6996 | 1.1163 | 1.1418 | 1.1418 | 1 |
| recent_one | 1.7061 | 0.3254 | 1.1418 | 1.1419 | 0.9999 |
| recent_five | 1.3302 | 0.40445 | 1.1418 | 1.142 | 0.99983 |
| recent_smoothed | 0.58804 | 0.4794 | 1.1418 | 1.142 | 0.99986 |
| glm_history | 0.83596 | 0.72883 | 1.1418 | 1.2112 | 0.94271 |
| transformer_history | 0.44618 | 0.38749 | 1.1418 | 1.1001 | 1.038 |
| glm_force | 2.3477 | 1.5481 | 1.1418 | 1.9513 | 0.58516 |
| transformer_force | 0.92334 | 0.60455 | 1.1418 | 1.0095 | 1.1311 |
| glm_position | 0.9654 | 0.77566 | 1.1418 | 1.1421 | 0.99973 |
| transformer_position | 0.95126 | 0.64983 | 1.1418 | 1.0365 | 1.1016 |
| glm_mechanics | 1.9923 | 1.642 | 1.1418 | 2.2133 | 0.5159 |
| transformer_mechanics | 1.2892 | 0.66829 | 1.1418 | 0.99191 | 1.1511 |
| glm_all | 1.01 | 0.80241 | 1.1418 | 1.1035 | 1.0347 |
| transformer_all | 0.49893 | 0.43518 | 1.1418 | 1.0243 | 1.1148 |
| glm_afferent | 1.01 | 0.80241 | 1.1418 | 1.1035 | 1.0347 |
| glm_sampled | 1.0133 | 0.8046 | 1.1418 | 1.1255 | 1.0145 |

## Exploratory held-afferent comparisons

| Comparison | Passed | Unmet conditions |
| --- | --- | --- |
| glm_conditional | no | all member deviance vs history, macro mae vs history, all seed macro deviance vs history, all member deviance vs mechanics, macro deviance and mae vs recent smoothed |
| glm_timing | no | all member deviance |
| transformer_conditional | no | all member deviance vs history, macro mae vs history, all seed macro deviance vs history |
| transformer_timing | yes | none |
| transformer_over_primary_glm | yes | none |

## Between-recording spread

The entries below subtract the comparator loss from the combined model loss. Negative differences indicate a lower error for the combined model. These held groups describe archive records. Independent-animal identity is unverified.

| Contrast | 0/aff004 Δ deviance | 0/aff015 Δ deviance | 0/aff017 Δ deviance | Macro Δ MAE | Members with lower deviance |
| --- | ---: | ---: | ---: | ---: | ---: |
| glm_combined_vs_history | -0.018442 | 0.44088 | 0.099845 | 0.073587 | 1 / 3 |
| glm_combined_vs_mechanics | -0.11069 | -2.8428 | 0.0068332 | -0.8396 | 2 / 3 |
| glm_current_vs_stale_mechanics | -0.77022 | 0.015481 | -0.11697 | -0.14209 | 2 / 3 |
| transformer_combined_vs_history | 0.082075 | -0.0010093 | 0.077161 | 0.047699 | 1 / 3 |
| transformer_combined_vs_mechanics | -0.51647 | -0.15257 | -1.7017 | -0.23311 | 3 / 3 |
| transformer_current_vs_stale_mechanics | -0.51727 | -0.41711 | -0.081651 | -0.1207 | 3 / 3 |
| transformer_vs_glm_joint | -0.64023 | -0.76891 | -0.12423 | -0.36723 | 3 / 3 |
| transformer_vs_glm_afferent | -0.64023 | -0.76891 | -0.12423 | -0.36723 | 3 / 3 |
| transformer_vs_glm_sampled | -0.65695 | -0.75569 | -0.13035 | -0.36941 | 3 / 3 |

## Calibration and replication

The fixed calibration bins in calibration-bins.csv.gz report observed and predicted counts, absolute window counts and balanced mass. The largest errors can be inspected by afferent and trial in group-scores.csv.gz. The three Transformer seeds repeat the same source splits. Overlapping windows share spike history within trials. The reported ranges across held records and seeds describe these recordings and fits. The available archive groups cannot establish population uncertainty, cross-animal transfer or a biological feedback loop. The original prefix-5 reserve remains outside every fit and result.
