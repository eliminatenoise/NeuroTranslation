# Reproduce the decoder scores

The supplied aggregate results compare three training seeds on two development studies. Each participant contributed held-out predictions from one fold. Use the scoring script with the development windows prepared by the two source readers and the directory written by the training replay. It needs Python 3.12 or newer and NumPy. Keep PROTOCOL.md alongside score_decoder.py.

```sh
python score_decoder.py --data development.npz --fit replay-output --output reproduced-scores.json
```

The script verifies the development input, row order, fold assignment, masks, training budgets, published scoring rule and prediction receipts. Read `studies.balance` for balance and `studies.way` for grasp-and-lift. Each study has a `primary` table of paired separate-minus-common error differences. `seed_means` follows the order in the top-level `seeds` field. `methods` gives equal-person score levels. `separate_minus` compares the separate decoders with each control. `subgroups` and `participant_tradeoffs` describe variation across tasks and people. `channel_support` gives the number of eligible people and events per named muscle. Axis numbers follow each study's `axis_labels`. Positive bias means the forecast exceeds the measured source coordinate or muscle amplitude.

The `compute` table includes actual optimizer-loop times reported by the replay. Those times will differ on a second run. Times for specialist exposure checkpoints include just the first half of their corresponding longer fits. The score file contains cohort aggregates. Source event arrays and participant identities remain in your local replay inputs.

The balance measurements came from Steven M. Peterson and Daniel P. Ferris. The grasp-and-lift recordings came from Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin. [Balance recordings](https://doi.org/10.18112/openneuro.ds003739.v1.0.3) · [Grasp-and-lift recordings](https://doi.org/10.6084/m9.figshare.c.988376.v2)
