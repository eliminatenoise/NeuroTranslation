# Forecasting the next 100 ms on 13 September 2017

A macaque holds a robotic handle. When the robot pushes, does the movement of the handle help predict how many events each of 26 contacts in sensory cortex will register next? The model learned from the early push trials on 12 September. It gets the preceding 200 ms of movement, cortical counts and available cues.

Of 2,452 candidate push windows from 613 originals, 2,452 windows survived signal checks. An earlier original with a matching push, timing and cue history supplied a substitute movement for 2,436 windows from 609 originals. The two comparisons below use those same windows.

| Input for comparison | Full minus comparison, Poisson deviance | Paired 95% interval |
|---|---:|---:|
| Past counts and cues | -0.002610 | [-0.006967, +0.001317] |
| Movement borrowed from another trial | -0.003184 | [-0.006099, -0.000713] |

Lower deviance means a closer count forecast. For movement to pass this test, both intervals must fall entirely below zero.
The held-day result falls short of that requirement.

| Phase and donor-matched sample | Originals | Windows | Full-model deviance | Mean absolute error, counts/contact/100 ms |
|---|---:|---:|---:|---:|
| Push before target | 609 | 2436 | 1.987496 | 1.039200 |
| Go cue after push | 597 | 2367 | 2.104095 | 1.233804 |
| Go cue without a push | 655 | 2616 | 1.876191 | 0.831602 |

Each original trial has equal weight. The three fits contribute their individual errors equally. Intervals resample consecutive groups of 12 originals and hold the fits fixed. The go-cue phases extend beyond the push windows used for training.

The instrument records unsorted events at each named contact. The recordings on these two dates come from one animal. A contact can pick up different cells from one day to the next. These errors measure agreement with the deposited counts. Perception, motor commands and performance in a live feedback loop remain unmeasured.
