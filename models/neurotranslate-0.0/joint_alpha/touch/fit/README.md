# Does adding touch improve the shared forecast?

A plate moves against a fingertip. An electrode records the impulses from one sensory nerve fibre. Give the model the preceding 200 milliseconds of force and nerve activity, plus the time elapsed in the trial. How many impulses will that fibre send between 20 and 40 milliseconds from now?

We trained two models to answer that question. One learned touch alongside the seven earlier forecasts. The other learned touch alone. They began with identical touch weights, saw the same 61,440 sampled touch windows in the same order, and took the same 1,920 optimizer steps. The joint model also saw 32 cases from each of the seven earlier tasks on every step. Each of its eight losses contributed equally to the update. All touch parameters were fitted across seven people. The models take neither participant nor nerve-fibre identity as an input.

## What the eighth task changed

On 41,416 eligible windows from two development participants, the joint model improved on a constant rate learned from the training recordings. The touch-only model did better for both people. The figures below give each person equal weight. Lower is better for both scores. The first score measures how much probability the model assigned to the observed spike counts. The second measures the size of the error in spikes per 20 ms bin.

| Forecast | Poisson log loss (nats/bin) | Mean absolute error (spikes/bin) |
| --- | ---: | ---: |
| Constant training rate | 0.236795 | 0.155885 |
| Joint, measured force | 0.192603 | 0.105715 |
| Joint, preceding trial’s force | 0.192609 | 0.105713 |
| Touch-only, measured force | 0.182312 | 0.097584 |
| Touch-only, preceding trial’s force | 0.182300 | 0.097617 |

Where did force help? We replaced the three force channels with values from the same instant in the preceding trial, under the same material and direction. Spike history and elapsed time stayed intact. Measured force improved the joint model’s log score for one participant and worsened it for the other. Two people give little evidence about whether the model can distinguish the force specific to a given trial. Plate force measures the load on the instrument. Local skin deformation would require a separate measurement.

The seven earlier tasks provide a second check. The eight-task model reduced error on five previously assessed partitions and increased error on six. On the two macaque cortical count partitions, for instance, log loss rose from 2.3670 to 2.4584 and from 2.4711 to 2.5117 nats. The seven-task checkpoint remains the default. The separate touch experiment lets you run all eight forecasts and inspect the trade-off. All eleven comparisons include group counts, original units, paired differences and descriptive uncertainty. [Complete results](fit-results.json)

## Refit the two models

Start in the extracted `joint_alpha/touch/fit` directory. For fitting, use Python 3.12 or later with NumPy and PyTorch. Prepare the seven-task manifest from the published recording recipes, then prepare `touch-train.npz` from the 21 designated touch training recordings. The training script checks the ordered arrays that the optimizer consumes, so differences in compression or the order of unrelated archive members leave the comparison intact. [Seven-task preparation](../../inputs/README.md)

```sh
python train_touch.py packed/manifest.json reproduced --touch-train touch-train.npz
```

The first argument points to your prepared manifest. Paths to its training arrays are relative to that manifest. The second is a new output directory. The command writes `eight-task.npz` and `touch-only.npz`. It locates the seven-task model two directories above the script. If you arranged the files differently, pass `--seven-dir path/to/joint_alpha`. To reproduce the seven-task comparator, add `--mode seven` and choose a separate output directory.

The joint model has 21,830 trainable parameters. Of these, 8,576 belong to the shared attention block. A 32-wide state, four attention heads and one block follow the earlier seven-task capacity study. The touch-only fit uses the same block and has 8,961 parameters. The fit uses AdamW with peak learning rate 0.0015, a 5% warmup, cosine decay, weight decay 0.001 and gradient norm limit 2. Each task’s recorded gradients reach the shared weights on the first and last update. Model inputs, initialization, sampling checksums, fit times and checkpoint sizes accompany the results. [Training evidence](fit-results.json) · [Recording credits](NOTICE.md)
