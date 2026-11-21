# Which recorded neuron fires next?

Stop a recording after a spike. Give each recorded neuron a probability of producing the next one. Then play the recording forward. On ten trips by a second rat, a model fitted to the first rat assigned more probability to the unit that fired next than a running count did. Its first choice was right about once in five. A simple rule that favored recently active units picked the winner just as often.

The electrodes recorded groups of spikes that the experimenters attributed to individual neurons. Each group is called a *sorted unit*. The target here is the next unit observed among those listed in that recording. An unrecorded neuron could have fired between any two observations. These two animals share a species, an experiment and a laboratory. Tests in another species, body plan or recording system remain open. [Dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307)

## Two rats, two sets of units

JS14 ran along a W-shaped track. The model learned five numbers from 54,578 resolved transitions on trips 55–78. Trip 79 separated training from the ten held trips, 80–89. Those ten trips had appeared in an earlier study of movement. Here the target is which unit fires next. Trips 90–95 contributed no observations. [Earlier movement study](https://github.com/eliminatenoise/NeuroTranslation/tree/3e43795adeb6c33b8302e952f45af03be5a71fb1/benchmarks/wtrack-neural-motion)

The second rat, ER1, had 122 units in its recording. Its unit 6 and JS14’s unit 6 are just two entries in different tables. On ER1’s first ten trips the model started each trial with empty counters and used the five numbers learned from JS14. From the first occupied millisecond onward it could update the forecast whenever an event arrived. Its coefficients stayed fixed. [Frozen study design](protocol.json)

| Rat and method | Log loss ↓ | First choice correct | Mean rank ↓ | Log loss, equal weight per unit ↓ | First choice, equal weight per unit |
| --- | ---: | ---: | ---: | ---: | ---: |
| JS14 · uniform | 4.277 | 1.39% | 36.50 | 4.277 | 1.39% |
| JS14 · rates from training | 3.074 | 25.05% | 10.02 | 4.911 | 1.69% |
| JS14 · running rates | 3.028 | 24.98% | 9.26 | 4.638 | 1.70% |
| JS14 · running rates and recency | 3.039 | 25.11% | 8.32 | 5.037 | 1.76% |
| **JS14 · fitted history model** | **2.872** | **25.15%** | **7.48** | **4.285** | **1.87%** |
| ER1 · uniform | 4.804 | 0.82% | 61.50 | 4.804 | 0.82% |
| ER1 · running rates | 3.483 | 19.48% | 13.98 | 4.974 | 1.32% |
| ER1 · running rates and recency | 3.484 | 19.50% | 12.55 | 5.297 | 1.35% |
| **ER1 · fitted history model** | **3.379** | **19.49%** | **11.51** | **4.645** | **1.35%** |

Log loss penalizes a forecast according to how little probability it gave the recorded unit. It uses natural logarithms. Rank 1 means the unit was the first choice. Tied probabilities share credit and take their mean rank. Each ordinary score gives every resolved event equal weight. The last two columns give each unit with a scored target equal weight. On JS14, the model’s equal-unit log loss was slightly worse than uniform. A few often-recorded units can account for many correct first choices. The rates learned for JS14’s units have no counterparts in ER1. [JS14 results](js14-results.json) · [ER1 results](er1-results.json)

Averaging the ten trips equally, the model reduced log loss against running rates by 0.159 on JS14 and 0.108 on ER1. The 95% intervals from resampling trips were 0.141–0.178 and 0.095–0.121. Each set contains consecutive trips from one animal. The intervals describe variation among those trips and give no estimate of variation among animals.

The first few spikes tell a different story. For forecasts issued at the end of occupied bins 1 through 10 in each trial, the model’s log loss was 3.789 on JS14 and 4.338 on ER1. The fixed recency rule did better on both, with 3.680 and 4.237. Only 95 and 93 resolved forecasts respectively fell in that early group. A fresh recording can update the model immediately. How much those first updates help depends on which comparison you use.

## One millisecond to separate events

The recorder supplies a clock for every sorted spike. Split each trial into complete one-millisecond bins. At the end of an occupied bin, count everything that has arrived, including a spike exactly on the closing boundary. Issue the forecast there. A spike has to occur strictly later to become a target. Empty bins leave the forecast in place. The next occupied bin gives a single answer only if it contains one spike. Two spikes in that bin leave the forecast unresolved at the chosen resolution. Both still contribute to the following forecast.

| Trials scored | Listed units | Units with a scored target | Occupied bins | Resolved targets | Multi-spike targets | Forecasts censored at trial end | Spikes in incomplete edge bins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JS14 · 80–89 | 72 | 59 | 34,885 | 32,866 | 2,009 | 10 | 1 |
| ER1 · 0–9 | 122 | 79 | 62,657 | 56,926 | 5,721 | 10 | 2 |

The first occupied bin supplies history. The final forecast in each trial has no observable target before the trial ends. The recording lists no per-unit intervals of reliable detection. An empty bin could mean silence or a missed event. The original sorting used the acquired recording. The archive gives no time at which a live sorter would have supplied the identity of a spike. These scores describe offline replay.

The running-rate rule starts with one count for each unit and adds the spikes seen so far in the trial. The recency rule also favors a unit with recent spikes, with their weight decaying over 100 milliseconds. The fitted model gives every candidate the same five questions. How many spikes has it supplied in this trial? How much activity remains on each of three decaying traces, covering 10, 100 and 1,000 milliseconds? Did it fire in the latest occupied bin? A shared weighted sum followed by softmax gives the probabilities. The future event time, the rat’s position and the candidate’s identity are absent from the inputs. [Fitted coefficients](weights.json) · [Scoring code](benchmark.py)

## Try it

Three fictional units, Amber, Birch and Cedar, show how a prediction changes. At 1 ms Birch has supplied the only spike. The fitted model gives Birch 57.7% and the other two 21.2% each. At 5 ms Amber has fired too. Birch still leads with 45.1%. The next occupied bin contains both Birch and Cedar, so the forecast made at 5 ms is unresolved. Both observed spikes count toward the forecast at 9 ms. [Fictional worked example](fictional-case.json)

From this directory, use Python 3.12 or 3.13 in a virtual environment. The fictional example and scoring with the saved weights need NumPy. The full reproduction uses the pinned packages below. Each data command writes into the directory you specify.

```sh
python -m pip install -r requirements.txt
python benchmark.py example
python get_inputs.py js14 input-js14
python get_inputs.py er1 input-er1
python benchmark.py train --packets input-js14/train --output fitted.json
python benchmark.py js14 --packets input-js14/test --model fitted.json --output my-js14.json
python benchmark.py er1 --packets input-er1 --model fitted.json --output my-er1.json
python benchmark.py timing
```

JS14 downloads the 34 checked trip packets from the earlier movement study. ER1 reads the sorted-unit field and trial metadata in checked byte ranges of the original NWB. It exports only the first ten trips and verifies their digests. For an existing full ER1 file, run `python prepare_er1.py recording.nwb input-er1`. It checks the archive’s SHA-256 before extraction. The public benchmark contains weights, aggregate scores, code and a fictional example. Downloading inputs is optional.

On one AMD Ryzen AI Max+ 395 CPU, an update and a probability vector took a median 10.1 microseconds for 72 fictional units. The 95th percentile was 10.4 microseconds over 2,000 updates after 100 warm-up updates. This measures the scorer alone. Electrode acquisition, spike sorting, transport and display delays remain unmeasured.

Justin Shin and Shantanu Jadhav released *Single Day W-Track Learning* under CC BY 4.0. Their experiment supplied the spike times. This benchmark selected trials, grouped spikes on a millisecond clock, fitted the model and measured forecast errors. [Source and reuse terms](NOTICE.md)

## Millisecond boundaries

After evaluation, we corrected how the scorer assigns timestamps that fall exactly on a millisecond boundary. Refitting gave the same five coefficients, and both held result files were byte-identical.
