# Validation scores

The endpoint is the recorded change in handle position over the next 100 ms. Errors are in cm. Positive paired differences favor the correctly paired joint Transformer.

| Subset | Originals | Windows | Joint error | Added spikes, difference [95% interval] | Wrong-trial minus correct [95% interval] |
|---|---:|---:|---:|---:|---:|
| matched | 107 | 790 | 0.6042 | -0.1043 [-0.1385, -0.0627] | 0.0103 [-0.0174, 0.0390] |
| matched bump | 107 | 419 | 0.9305 | -0.1690 [-0.2267, -0.1053] | 0.0149 [-0.0363, 0.0669] |
| matched reach | 103 | 371 | 0.2289 | -0.0537 [-0.0649, -0.0435] | -0.0032 [-0.0137, 0.0062] |
| matched both epochs | 103 | 783 | 0.5679 | -0.1209 [-0.1450, -0.0964] | 0.0016 [-0.0247, 0.0295] |

| Model on matched recipients | Euclidean | x MAE | y MAE | x bias | y bias |
|---|---:|---:|---:|---:|---:|
| transformer_all | 0.6042 | 0.4225 | 0.3612 | 0.0210 | 0.0165 |
| transformer_movement_cue | 0.4999 | 0.3472 | 0.2919 | 0.0440 | 0.0345 |
| transformer_neural_cue | 0.7224 | 0.4907 | 0.4476 | -0.0068 | -0.0058 |
| transformer_cue_only | 0.5624 | 0.3927 | 0.3265 | 0.0679 | 0.0440 |
| transformer_movement_only | 0.5659 | 0.3856 | 0.3408 | 0.0672 | 0.0853 |
| transformer_neural_only | 1.2710 | 0.9484 | 0.6486 | 0.0499 | -0.0240 |
| transformer_wrong_neural | 0.6145 | 0.4184 | 0.3773 | 0.0175 | -0.0017 |
| ridge_all | 0.5363 | 0.3805 | 0.3053 | 0.0187 | 0.0063 |
| ridge_movement_cue | 0.4846 | 0.3405 | 0.2778 | 0.0391 | 0.0193 |
| ridge_neural_cue | 0.6087 | 0.4219 | 0.3580 | 0.0151 | 0.0112 |
| ridge_cue_only | 0.5642 | 0.3900 | 0.3311 | 0.0418 | 0.0273 |
| ridge_movement_only | 0.5607 | 0.4034 | 0.2991 | 0.0537 | 0.0134 |
| ridge_neural_only | 1.1711 | 0.8602 | 0.6005 | 0.0897 | -0.0174 |
| ridge_movement_cue_population_rate | 0.4908 | 0.3467 | 0.2802 | 0.0314 | 0.0178 |
| ridge_movement_cue_unit_rate | 0.5012 | 0.3579 | 0.2823 | 0.0238 | 0.0117 |
| ridge_wrong_neural | 0.5420 | 0.3849 | 0.3098 | 0.0210 | 0.0090 |
| stationary | 1.1054 | 0.7963 | 0.5736 | 0.0650 | 0.0389 |
| constant_velocity_40ms | 1.1770 | 0.8200 | 0.6919 | 0.0084 | -0.0044 |
| constant_velocity_100ms | 1.2892 | 0.8789 | 0.7753 | 0.0285 | -0.0047 |
| constant_velocity_200ms | 1.2534 | 0.8945 | 0.7142 | 0.0572 | -0.0042 |

Each original receives equal weight. Within an original, available epochs receive equal weight. Seeds, windows and paired epochs belong to a single recording from one animal. Intervals resample blocks of eight chronological originals and condition on the fitted models and fixed donor mapping. Bias is predicted minus recorded displacement.

scores.json includes directions available at cutoff, seed-specific results, both-epoch sensitivity, matched sizes and the separate donor-free comparison. matched-trial-epochs.csv contains the original-level epoch means used to reconstruct the estimates.
