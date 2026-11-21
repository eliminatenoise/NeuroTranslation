# Does the small experiment predict the large one?

[How far do a few people predict the full training group?](human/README.md) · [How much training predicts the next spike?](neural/README.md)

“Soup stew principle” is an informal name for an empirical question. More kinds of evidence may help a movement model discover something that carries over to a new body. The units matter. Ten thousand additional frames from the same participant provide many more observations, but only one participant. Another vertebrate, a new recording site, a different body build, an independent force measurement and a longer trace change different parts of the question.

## Count what is growing

Keep separate counts of independent people or animals, acquisition sites, recordings, tasks, windows and neural events. Also record target types, parameter count, training examples consumed, optimizer steps and runtime. Replacing a quarter of a fish training set with worm recordings changes the mixture under a fixed sample budget. Adding those recordings on top changes both the mixture and the budget. The two experiments can give different answers.

Small experiments are good at detecting a leak, an incorrect time unit, an impossible target or a baseline that the proposed model struggles to beat. An early loss curve can also help predict a larger training run within a stable family and distribution. That use itself needs a test: fit or choose the scaling trend using smaller runs, seal its prediction, then compare against the actual next size. In language modeling, compute-optimal scaling was studied across hundreds of training runs, and small proxy models have sometimes helped choose a data mixture for a larger model. Neither result gives a universal numerical rule for vertebrate physiology. [Compute-optimal training study](https://arxiv.org/abs/2203.15556) · [Data-mixture study](https://arxiv.org/abs/2305.10429)

## What should enter the combined model?

Keep relevant, licensed measurements eligible for evaluation. Preserve what was actually measured, its time and units, what a simulation supplied, and which signals share an animal and a recording clock. The model can learn from separate acquisitions with masked inputs, a shared set of weights and output heads suited to their targets. It cannot verify a complete physiological event by stitching unrelated samples together.

Evaluate new inputs against a matched alternative on different individuals or recordings. Increase the study size when the smaller experiment leaves a meaningful uncertainty, particularly when architecture rankings disagree across groups. Compare whole-group error, rare events, latency and data coverage. Keep a simpler specialist available as a reference, and accept a common model's improvement only on the tasks where the measured comparison supports it.
