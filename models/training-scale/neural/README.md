# How much training predicts the next spike?

A model that learned from 1,024 examples picked the same winner as one that learned from 54,578 on each of two held recordings. The winners were different. Thirteen fitted coefficients gave the closest probability forecasts for a second rat. Five gave the closest forecasts for a turtle. Changing which turtle clusters counted changed the winner again. [Predictions recorded before the largest new fits](prediction.json) · [Results](results.json)

Each example starts just after an occupied millisecond closes. The model sees which recorded units fired, then assigns each unit a probability of firing next. A *unit* is a cluster of spikes the original sorting procedure grouped together. We can check the forecast when the next occupied millisecond holds just one spike. A millisecond with several spikes still updates the history. We leave its firing order unresolved. [Study protocol](protocol.json)

## What did the small fits predict?

Each fit learned from one rat alone, or from an equal number of examples divided evenly between that rat and a salamander retinal data collection. Each saw either the original five history features, or the same five plus eight bends at fixed points on their response curves. These extra terms let the effect of recent firing change as the count rises. The table gives average log loss in natural-log units, assigning each held trial equal weight and then averaging the three training draws. A smaller loss means the model assigned more probability to the unit observed next. [Fitted coefficients](models.json)

| Held recording | Examples per fit | Rat, 5 | Rat, 13 | Mixed, 5 | Mixed, 13 |
|---|---:|---:|---:|---:|---:|
| ER1 rat | 1,024 | 3.3805 | **3.3012** | 3.3819 | 3.3145 |
| ER1 rat | 4,096 | 3.3832 | **3.3005** | 3.3767 | 3.3110 |
| ER1 rat | 16,384 | 3.3799 | **3.2963** | 3.3745 | 3.3076 |
| ER1 rat | 54,578 | 3.3798 | **3.2968** | 3.3755 | 3.3077 |
| Turtle, earlier observed clusters | 1,024 | **4.0175** | 4.0679 | 4.0279 | 4.0464 |
| Turtle, earlier observed clusters | 4,096 | **4.0128** | 4.0723 | 4.0178 | 4.0326 |
| Turtle, earlier observed clusters | 16,384 | **4.0110** | 4.0712 | 4.0151 | 4.0301 |
| Turtle, earlier observed clusters | 54,578 | **4.0115** | 4.0711 | 4.0164 | 4.0323 |

We wrote down the predicted scores for 54,578 examples after scoring the smaller fits. Carrying the 16,384-example scores forward gave an average absolute error across the four choices of **0.0004 nats on ER1** and **0.0010 on the turtle**. It also got all six pairwise orderings right in each recording. Extending the slope from the previous two sizes gave larger errors of 0.0032 and 0.0027. Carrying forward just 1,024 examples gave errors of 0.0045 and 0.0087, with five of six orderings right on ER1 and six of six on the turtle. Both recordings and the original full-rat five-coefficient result had appeared in earlier work. These are retrospective curves on familiar evaluations. [Forecast seal](prediction-seal.json) · [Predictions and residuals](results.json)

## When did a different training source help?

At the largest budget, replacing 27,289 rat examples with salamander examples made the thirteen-coefficient model worse on the second rat by 0.0108 nats (paired trial interval 0.0072 to 0.0143). The same replacement improved it on the turtle by 0.0388 nats (0.0200 to 0.0647). The five-coefficient model showed the opposite direction on both recordings. Its estimated turtle change was small enough to include zero. There is no single answer here to whether a second training source helps. The answer depends on the scoring rule and the recording it must predict. [Paired source and model comparisons](results.json)

On ER1 the best fit reached 3.2968 against 3.4841 for a simple count-and-recency rule. On the turtle it reached 4.0115 against 4.0273. The paired 95% interval for that turtle difference ran from −0.0328 to +0.0032. Even a stable ordering across training sizes can leave the size and direction of a benefit uncertain across trials. Correct first choices tell a different story again. ER1’s winning model picked the right unit 19.39% of the time when each trial counted equally. Giving each of the 79 target units equal weight across pooled events brought its accuracy down to 1.38%. [Trial results for all seeds and events grouped by issue history](by-trial-scores.json.gz)

A second way to weight the result gives each scored unit equal weight *within its own trial*, then gives every trial equal weight. On this measure a uniform guess had lower log loss than all four largest fits on the rat and on both turtle rosters. ER1’s uniform score was 4.8040, against 4.8113 for the rat-only thirteen-coefficient fit. For the turtle’s earlier observed roster the corresponding figures were 4.6347 and 5.1527. How well we forecast many spikes and how well we forecast the typical recorded unit are different biological questions. [Trial and unit-weighted scores](by-trial-scores.json.gz)

## Which turtle clusters counted?

Twenty earlier windows established 103 observed clusters. The next 20 supplied 6,978 scored events. Eight windows ended early when a new cluster appeared. In a second analysis all 109 clusters named in the original recording were eligible from the start. The same 20 test windows then supplied 10,298 events. On this roster the mixed thirteen-coefficient fit came first at every size, reaching 3.9580 at the largest budget. Carrying the four 16,384-example scores forward gave mean absolute error 0.0012. The two turtle analyses share an animal and a recording. Both the cluster roster and the events scored change together. [Trial counts, unit IDs and source windows](source-groups.json.gz)

## What did more examples mean?

The 24 original JS14 training trips supplied 54,578 resolved transitions from 72 sorted units. The three salamander stimulus experiments supplied 34,490 transitions across 28 qualifying ten-second windows. Two repeated-movie windows failed the original timestamp-order check. The checkerboard and moving-bar windows passed. The archive does not establish a distinct animal for every experiment. ER1 supplied 56,926 held transitions from ten trips, with 122 candidate units. Every turtle window stayed out of fitting. JS14 trips 79 and later stayed out of this study. [Sources and licenses](RIGHTS.md)

A sampling seed chose a nested set of unique forecast origins within each training source. Each smaller set sits inside its corresponding larger one. The three seeds describe variation in which labeled transitions we picked. Many transitions share the same trip and unit, and each forecast can use all earlier observed spikes in its trial. More examples here means more training labels from the same recordings. It does not mean more animals or more independent histories. The intervals resample entire held trials within each recording. Species, circuit, stimulus, animal and recording equipment change together across collections. The experiment gives no measured prediction for a larger Transformer, another animal, a million examples or hardware power use. [Training memberships](training-membership.json.gz) · [Exact sampling and fitting rules](protocol.json)

## Reproduce the curves

Use Python 3.13 and the pinned packages. From this directory run the following commands. The first data command downloads the source files and checks their hashes. The second accepts those files offline and creates a new output directory. Its `report` folder contains the forecast, final scores, fitted coefficients and per-trial results. `--jobs 3` runs up to three independent fits at a time, with one BLAS thread per fit. Each full rat-only fit uses the same 54,578 examples across all sampling seeds. Its coefficients are reused at that size. [Source identities](sources.json) · [Reproduction entry point](reproduce.py)

```sh
python -m pip install -r requirements.txt
python get_inputs.py data
python reproduce.py data rebuilt --jobs 3
```

A clean rebuild from the verified local recordings took 64.78 seconds on a 16-core AMD Ryzen AI Max+ 395 using three concurrent single-thread CPU fits. All seven numerical output files matched byte for byte. The GPU did no training or scoring. The wall clock includes preparation, fitting, scoring and writing the report. It excludes downloads and package installation. Concurrent host activity was uncontrolled and per-run electricity use was unmeasured.
