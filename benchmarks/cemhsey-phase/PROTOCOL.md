# Do people follow a rising pinch cue the same way they follow a falling one?

Squeeze two fingertips against a gauge, then ease off. The target on the screen rises and falls at the same rate. The hand may follow it differently in each direction. Can three people's recordings teach us a correction that improves forecasts for three other people before they have given the model a single practice pinch?

The CEMHSEY GRASP study recorded adult volunteers pressing a P200 dynamometer between two digit pads. Force here is the released fraction of each person's maximum voluntary contraction (MVC) for this grasp on that day. Five forearm grids measure muscle electrical activity through the skin, or surface electromyography (EMG). The quantity we forecast is the force between the pads. [Source study](https://doi.org/10.1038/s41597-025-05733-y) · [GRASP Part I v2](https://doi.org/10.5281/zenodo.15077957) · [GRASP Part II v2](https://doi.org/10.5281/zenodo.15070187)

## A correction learned from other hands

Use both repeats of the 50% MVC pad-to-pad pinch on the first indexed day, session 5, task 3. Six trials from three people fit the corrections. Six trials from three different people test the forecasts. The six people's records here are distinct from the records used to train the original point models. The programme has seen these people on other records in earlier development or evaluation. The selected day-one 50% records are fresh for this question, and neither group supplied the original point-model training set. The public commitment to the ordered, nonce-bound private roster is SHA-256 `fdc8fbbc9f14ca518aa5bfdfa671bac39ccd043e7505112d59a34ff380cee678`. A missing or invalid record holds its stage.

The plan fixes the forecasts, comparisons and participant split before either role's numerical observations are opened. Seal and independently check the fit before admitting evaluation. Neither test repeat provides personal practice or changes any coefficient. The forecaster can still observe the current trial's force history and, in the grid model, the preceding EMG windows.

## What each forecast sees

At issue ticks 60, 70, …, 5970 on the nominal 200 Hz force clock, predict force 24 ticks ahead. Each repeat supplies 592 issues and the last outcome is at tick 5994. Both released records start at nominal index zero. The point models use the unchanged historical fit trained at a 30% cue. The force-history model uses current and previous gauge readings and the known cue phase. The five-grid model adds global amplitude summaries and contrasts across the five forearm grids. Its EMG windows are [i−60,i−40) and [i−40,i−20) in force ticks, with each boundary b mapped to ceil(2048b/200) on the EMG clock. The nominal 120 ms horizon gives no measured device latency, physical synchronization bound or physiological delay. [Frozen point model and feature definitions](https://github.com/eliminatenoise/NeuroTranslation/tree/d66fc10251fb3e04e6dcd8a9d2cda8c927ade408)

Let g(t) be the unit-height cue at tick t. It is zero through 1000, rises linearly to one at 2000, holds through 4000, falls linearly to zero at 5000, then stays there. Let u = g(i+24) − g(i). Its sign describes the **scheduled** change over the forecast horizon, including an issue whose horizon crosses a phase boundary. It does not depend on whether the measured force rises or falls. The two controls are the current gauge f[i] and the future scheduled target 0.50·g(i+24).

Three parent forecasts use the same schedule. The simple parent is f[i]+0.50·u. For the force-history and five-grid parents take the respective frozen point forecast and add (0.50−0.30)·u. For each parent p compare three versions.

| Version | Forecast at issue i |
| --- | --- |
| Unchanged | p |
| One coefficient | p + b·u |
| Separate rise and fall coefficients | p + bᵣ·u where u>0, p + b𝒻·u where u<0, and p where u=0 |

Fit each coefficient by least squares against the future gauge y = f[i+24]. For b use Σu(y−p)/Σu² across all six fit records. For bᵣ and b𝒻 use the same ratio restricted to strictly positive and strictly negative u respectively. Each issue carries equal weight, each record supplies the same 592 issues, and both repeats count equally for each person. Estimate these three coefficients separately for each parent. Keep all nine coefficients fixed through evaluation. Use no intercept, shrinkage, clipping or point-model refit. The fit yields one shared population profile. The earlier practice study instead fit a correction from the same person's own pinch.

## Who gained, and by how much?

The primary comparisons use whole-trial mean absolute error (MAE). Does splitting the simple parent's correction by direction reduce error against its unchanged version? Against its one-coefficient version? After both models get separate rise and fall coefficients, does adding the full history and grid forecast improve on the simple parent? This last comparison changes both force modelling and EMG inputs. It cannot isolate a contribution from EMG.

Report all eleven arms. For each parent compare one coefficient against unchanged, separate against unchanged, and separate against one. For each of the two history-based parents compare one coefficient against the simple parent's one, and separate against the simple parent's separate. These thirteen paired comparisons use identical issue support.

For each person pool the issues from both test repeats. Compute MAE, root mean squared error (RMSE), mean signed error (forecast minus gauge) and MAE divided by 0.50. Take the square root of that person's mean squared error after pooling their two repeats. Then average each of the four metrics equally across the three people. The first three metrics use fractions of MVC. Target-relative MAE is dimensionless. For each contrast subtract the candidate's MAE from the comparator's MAE within person. Report the mean, minimum and maximum of the three differences and counts of strictly positive, exactly zero and strictly negative gains. Determine signs before rounding. Round public numbers to nine decimal places.

Repeat the calculation overall and in five half-open issue-time phases with edges 0, 1000, 2000, 4000, 5000 and 6000. Initial rest, ramp up, hold, release and final rest contribute 94, 100, 200, 100 and 98 issues per repeat. Keep a boundary-crossing forecast in its issue phase. Overall this gives 3,552 held issue times. Overlapping windows give repeated observations of the same three people. The observed gain range describes them on this grasp, day and target. Further participants, tasks or independent online measurements would be needed to establish wider transfer or real-time performance. Release only independently reproduced aggregate scores and counts. Individual scores, observations, forecasts, coefficients and participant identities stay private.

Shared glossary revision 36, SHA-256 `40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406`.
