# Clock support for the count model

The original study design uses a separately deposited electrical clock to check each spike timestamp. Some development files omit that clock. The original two-clock population and the subsequent mixed-clock sensitivity study keep their own row sets, scales, training batches, checkpoints and held predictions. Each uses the fixed architecture, seed and optimizer settings in PROTOCOL.json. A prefix without eligible rows makes that population's three-prefix study unavailable.

The mixed-clock source adds only trials that pass the separately registered archive checks. For one-time-vector recordings these checks can establish internal consistency between the released event times, electrical sample count and common archived time axis. The archive supplies no independent electrical clock for those trials. A mixed-clock forecast is conditional on that interpretation. A change of population changes the training data, the held data or both.

Output paths identify the population. `strict/` is the original two-clock population. `mixed-clock/` is the separately admitted sensitivity study. The suffix of each checkpoint filename identifies which complete recording group was held out. The seed and active input combination follow it.
