# Research Edition walking force evaluation

The expanded fit reduced validation impulse error from **3.23650 to 2.89490 N·s** at three passes. At five it rose to **3.11755 N·s**. Five passes lowered Brier error by 0.00003202 relative to three and increased median CPU time per simultaneous plate pair from 0.68699 to 1.04563 seconds. [Simple report](SIMPLE.md) · [Checkpoint](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)

## Inputs, targets and fitting

Use 200 ms of earlier recorded signals in ten 20 ms bins. The inputs are RMS voltage from six named surface muscle channels (`LBF`, `LERS`, `LGAS`, `LRF`, `LST`, `RERS`) and mean signed vertical plate force in newtons. The new-load event starts at the first crossing of +20 N after 20 native samples in the unloaded range ±10 N, with at least 20 samples at or above +20 N. The onset must fall at ticks +1 through +100. Confirmation can use samples through tick +119. The force outcome is the signed sum of only the first 100 future samples at 1 kHz multiplied by 0.001 s, in N·s. Both endpoints use real force measurements. [Data and methods](https://doi.org/10.1038/s41597-023-02767-y) · [Original archive](https://doi.org/10.6084/m9.figshare.24192480.v1)

The physical reference holds the latest available force for 100 ms and uses the fitting population’s new-load rate. The model predicts a correction to the impulse and to the new-load logit, which converts to a probability. The full 24-layer, width-2304 Research Edition runs layers 6 through 17 three times during training, using zero-based layer indices. Train 28,670,978 values across the numeric input and output layers, sensor messages and original recurrent layers. One epoch completed 547 updates across 4,793 simultaneous pairs from 36 walks and 12 people. [Pinned base](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/tree/657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2)

## Score and timing

A fresh restore matches the fitting anchor bit for bit. At 864 fitting issue times, joint support covers 1,647 plate rows. The reference scores 0.033523 Brier and 3.435879 N·s mean absolute error. At three passes the scores are 0.032643 and 2.842759 N·s. A convex blend calibrated on the same 12 fitting people gives each learned prediction weight 1.0, using least squares for the event and a weighted absolute loss for the impulse.

Validate on the previously used subset of three people and nine walks. Three of six assigned people qualify for the exact muscle labels. Use the same 216 one-time plate pairs for both pass counts, alternating call order with fixed weights and the same arithmetic. Average endpoint errors across eligible plates at each issue, then within walks, then equally across people. Brier error is squared probability error. The 427 event rows include 18 positive rows from eight distinct onsets. The 432 impulse rows use absolute error.

| Forecast | Brier error | Impulse MAE |
| --- | ---: | ---: |
| Fitting prior and force persistence | 0.039950 | 3.237 N·s |
| Trainable attention core, NeuroTranslate 0.0 | 0.038311 | 10.867 N·s |
| Earlier six-update Research Edition | 0.462322 | 11.472 N·s |
| Expanded fit, three passes | 0.038625 | **2.895 N·s** |
| Expanded fit, five passes | 0.038593 | 3.118 N·s |

The five-pass impulse error was higher than the three-pass error for all three people. Median warm times used four CPU threads. This is a descriptive comparison on an already-used validation subset. The separate test group stayed closed. [Aggregate results](RESULTS.json)

## Run the checkpoint

The archive restores 213 prediction tensors in their stored BF16 or FP32 format over the pinned 19.53 GB base. Start with `python -B launch.py --self-test`. For forecasts, use the pinned Linux x86-64 environment with Python 3.13 and 64 GiB of available memory. Run `python -B launch.py --forecast --batch-layout two-invented-rows --base-dir PATH --passes 3`. The extracted setup covers dependency and base-file checks. [Checkpoint and setup](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)
