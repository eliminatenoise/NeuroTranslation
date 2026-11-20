# Test scores

The endpoint is the recorded change in handle position over the next 100 ms. Errors are in cm. Positive paired differences favor the correctly paired joint Transformer.

| Subset | Originals | Windows | Joint error | Added spikes, difference [95% interval] | Wrong-trial minus correct [95% interval] |
|---|---:|---:|---:|---:|---:|
| matched | 105 | 778 | 0.6044 | -0.1070 [-0.1445, -0.0755] | -0.0102 [-0.0576, 0.0300] |
| matched bump | 105 | 411 | 0.9076 | -0.1469 [-0.1915, -0.1021] | -0.0081 [-0.0691, 0.0544] |
| matched reach | 102 | 367 | 0.2368 | -0.0470 [-0.0591, -0.0358] | 0.0080 [-0.0007, 0.0165] |
| matched both epochs | 102 | 775 | 0.5490 | -0.0880 [-0.1087, -0.0662] | 0.0101 [-0.0175, 0.0395] |

| Model on matched recipients | Euclidean | x MAE | y MAE | x bias | y bias |
|---|---:|---:|---:|---:|---:|
| transformer_all | 0.6044 | 0.4229 | 0.3622 | -0.0449 | -0.0166 |
| transformer_movement_cue | 0.4974 | 0.3337 | 0.3019 | 0.0156 | 0.0389 |
| transformer_neural_cue | 0.7132 | 0.4659 | 0.4637 | -0.0585 | -0.0329 |
| transformer_cue_only | 0.5752 | 0.3907 | 0.3466 | 0.0225 | 0.0377 |
| transformer_movement_only | 0.5528 | 0.3653 | 0.3404 | 0.0343 | 0.0770 |
| transformer_neural_only | 1.2640 | 0.9288 | 0.6733 | -0.0626 | -0.0605 |
| transformer_wrong_neural | 0.5941 | 0.4165 | 0.3544 | -0.0152 | 0.0086 |
| ridge_all | 0.5342 | 0.3643 | 0.3179 | -0.0207 | 0.0050 |
| ridge_movement_cue | 0.4880 | 0.3317 | 0.2930 | 0.0016 | 0.0199 |
| ridge_neural_cue | 0.6063 | 0.4173 | 0.3632 | -0.0309 | 0.0077 |
| ridge_cue_only | 0.5685 | 0.3860 | 0.3448 | -0.0067 | 0.0177 |
| ridge_movement_only | 0.5571 | 0.3859 | 0.3157 | -0.0002 | 0.0205 |
| ridge_neural_only | 1.1183 | 0.7894 | 0.6066 | -0.0078 | -0.0125 |
| ridge_movement_cue_population_rate | 0.4929 | 0.3376 | 0.2939 | -0.0123 | 0.0160 |
| ridge_movement_cue_unit_rate | 0.5027 | 0.3484 | 0.2957 | -0.0190 | 0.0098 |
| ridge_wrong_neural | 0.5402 | 0.3743 | 0.3173 | -0.0260 | 0.0057 |
| stationary | 1.0892 | 0.7618 | 0.5900 | -0.0269 | 0.0425 |
| constant_velocity_40ms | 1.1664 | 0.7951 | 0.7031 | -0.0166 | -0.0230 |
| constant_velocity_100ms | 1.3014 | 0.8584 | 0.8058 | -0.0172 | -0.0233 |
| constant_velocity_200ms | 1.2501 | 0.8650 | 0.7385 | -0.0245 | 0.0038 |

Each original receives equal weight. Within an original, available epochs receive equal weight. Seeds, windows and paired epochs belong to a single recording from one animal. Intervals resample blocks of eight chronological originals and condition on the fitted models and fixed donor mapping. Bias is predicted minus recorded displacement.

scores.json includes directions available at cutoff, seed-specific results, both-epoch sensitivity, matched sizes and the separate donor-free comparison. matched-trial-epochs.csv contains the original-level epoch means used to reconstruct the estimates.
