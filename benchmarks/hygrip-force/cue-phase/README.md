# Cue phase did not beat grip history

Just before a relax cue, rising grip voltage could mean something different from a rise during a squeeze. We gave a forecast six extra coefficients to express that difference. They helped the compact model on the training folds. On the three previously studied development participants, that gain disappeared and the original ridge using the full voltage history again had the lowest mean error. [Protocol posted before fitting](https://github.com/eliminatenoise/NeuroTranslation/blob/71c196dd10aabdc1b0fe2750b87a1df3f2edb96e/benchmarks/hygrip-force/cue-phase/PROTOCOL.md).

The measurement was the released right-hand grip transducer voltage in the HYGRIP task, sampled at 50 Hz. Every forecast used the same issue grid and target six samples later, or 120 ms on the release clock. Each comparison uses the same 16,195 issues from 79 trials in seven eligible TRAIN participants and 7,995 issues from 39 trials in three previously studied DEV participants. One of the eight assigned TRAIN runs remained clock-held before waveform access (13 right-hand trials and 2,665 planned issues). All issues in the eligible runs were scored. The prior force-history ridge, persistence and backward-slope scores were reproduced exactly at the reported split and phase cells. [HYGRIP descriptor](https://doi.org/10.3389/fnins.2020.00919), [earlier benchmark](https://github.com/eliminatenoise/NeuroTranslation/tree/6fcd4d79894f7844ece20108cdd3bc728f193f74/benchmarks/hygrip-force).

| Predictor | TRAIN mean RMSE (mV) | DEV mean RMSE (mV) |
| --- | ---: | ---: |
| Persistence | 0.531851 | 0.516850 |
| Backward slope | 0.558423 | 0.496622 |
| Original force-history ridge | **0.393763** | **0.360083** |
| Compact residual ridge | 0.410521 | 0.373600 |
| Phase-conditioned residual ridge | 0.402769 | 0.374083 |

Each participant contributed equally to the mean RMSE. Within a participant, each trial contributed equally and each issue within that trial contributed equally. The TRAIN folds selected the penalties (0.01 for the force-history and compact residual models, 0.1 for the phase-conditioned model), so TRAIN errors include selection optimism. DEV applied the locked refits once. Its participants had already been studied under the earlier comparison. The three FINAL participants stayed sealed.

Against the matched compact residual model, phase lowered mean TRAIN error by 0.007752 mV (6 of 7 participants improved, descriptive 95% interval −0.017523 to +0.002020 mV). On DEV, phase raised the mean by 0.000482 mV (1 of 3 improved, interval −0.011141 to +0.012105 mV). Against the original 27-feature ridge, phase raised mean error by 0.009005 mV on TRAIN and 0.014000 mV on DEV. None of the three DEV participants improved on that original ridge (interval −0.017095 to +0.045094 mV, exact two-sided sign-test p = 0.25). The prior ridge fits the upcoming voltage directly and gets all 20 history readings as separate inputs. Its advantage answers which forecast did better here. The matched compact comparison is the one that isolates the addition of phase interactions.

The two DEV transition strata favoured the phase-conditioned model over the full ridge on average. They had 540 and 390 issues, compared with 5,505 during the scheduled on-to-on phase and 1,560 during off-to-off. The transition differences are descriptive, and every stratum comes from the same three participants. A scheduled switch identifies the intended cue phase. It supplies no observation of the exact visual or physical switch. Voltage is the released signal unit, so there is no calibrated Newton error, physical timing claim, or basis for attributing these results to neural dynamics.

The prespecified screen required lower mean error than all four comparators on both splits and a majority of participants improving against both fitted comparators. The phase-conditioned model failed and stays an experimental comparison. The original 27-feature ridge remains the benchmark. The downloadable aggregate table includes each phase denominator, the paired contrasts against all four comparisons and the TRAIN grid.

[Prespecified protocol](PROTOCOL.md) · [Training aggregates](TRAIN.json) · [Development aggregates](DEV.json) · [Download the comparison](HYGRIP-Cue-Phase-Aggregates.zip)

Glossary revision 36, SHA-256 `40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406`.
