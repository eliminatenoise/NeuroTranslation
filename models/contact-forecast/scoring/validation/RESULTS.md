# Forecasting the next 100 ms on 12 September 2017, the validation block

A macaque holds a robotic handle. When the robot pushes, does the movement of the handle help predict how many events each of 26 contacts in sensory cortex will register next? The model learned from the early push trials on 12 September. It gets the preceding 200 ms of movement, cortical counts and available cues.

Of 432 candidate push windows from 108 originals, 432 windows survived signal checks. An earlier original with a matching push, timing and cue history supplied a substitute movement for 416 windows from 104 originals. The two comparisons below use those same windows.

| Input for comparison | Full minus comparison, Poisson deviance | Paired 95% interval |
|---|---:|---:|
| Past counts and cues | +0.000497 | [-0.006059, +0.006198] |
| Movement borrowed from another trial | -0.001482 | [-0.005144, +0.002789] |

Lower deviance means a closer count forecast. For movement to pass this test, both intervals must fall entirely below zero.
These trials come from the training date and serve as a development check.

| Phase and donor-matched sample | Originals | Windows | Full-model deviance | Mean absolute error, counts/contact/100 ms |
|---|---:|---:|---:|---:|
| Push before target | 104 | 416 | 1.036048 | 0.716802 |

Each original trial has equal weight. The three fits contribute their individual errors equally. Intervals resample consecutive groups of 12 originals and hold the fits fixed. The go-cue phases extend beyond the push windows used for training.

The instrument records unsorted events at each named contact. The recordings on these two dates come from one animal. A contact can pick up different cells from one day to the next. These errors measure agreement with the deposited counts. Perception, motor commands and performance in a live feedback loop remain unmeasured.
