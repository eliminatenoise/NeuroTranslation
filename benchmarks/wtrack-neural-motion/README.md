# Can brain-cell firing improve a rat’s movement forecast?

A camera has already told us where the rat is and how fast it is moving. Would a second of recorded brain activity tell us where it will be a quarter of a second later? On nine later trips around a W-shaped track, adding spikes increased the average error from **2.010 to 2.237 cm**. The movement-only forecast was more accurate on seven of the nine trips.

**[Open the forecasts and trip explorer](results.html)** or double-click the launcher for your operating system. The viewer works offline. Each point in the plot is a sparse forecast or its measured camera target, with their separation drawn to scale. To run a fitted prediction or repeat training, see [Reproduce the study](REPRODUCE.md).

## What we measured

Justin Shin and Shantanu Jadhav recorded rat JS14 moving among reward wells. The archive gives the rat’s position in centimetres relative to the centre well and the firing times of 72 sorted units from two brain regions, hippocampal CA1 and prefrontal cortex. A unit is a group of electrical spikes assigned to a putative neuron. We used a single running period in one recording so the unit IDs retain their original meaning. [Data and attribution](NOTICE.md)

The models trained on 201 of 216 scheduled forecasts from 24 whole trips. Trip 79 separated training from the next ten trips. Trip 80 supplied earlier firing for a control. We scored 123 of 126 scheduled windows from trips 81–89. The last tracking frame was too old in three windows. Each trip counted equally. One more trip separated these observations from five reserved trips whose position and spiking series were never extracted or scored. [Frozen study design](protocol.json)

At two-second intervals, a model saw one second of history. The movement inputs contained four positions, X and Y velocities derived from positions selected roughly a quarter-second apart, the age of the most recent frame at each step, and time elapsed since the start of the trip and run. The combined models also saw the number of times each unit fired in four successive quarter-second bins. The target was the first available camera sample at least 250 milliseconds after the forecast cutoff. Actual delays ranged from 250.0 to 290.4 milliseconds. The prediction used the nominal 250-millisecond delay. The target timestamp was available only for scoring.

## Which forecast came closest?

| Information available | Forecast | Mean trip error |
| --- | --- | ---: |
| Last position | Repeat it | 3.106 cm |
| Last two historical positions | Continue at the last velocity | 2.217 cm |
| Position and movement history, elapsed times | Movement-only ridge regression | **2.010 cm** |
| Same movement inputs and 72 firing histories | Combined ridge regression | 2.237 cm |
| Movement inputs, spikes from a different earlier trip | Same fitted combined ridge | 2.429 cm |
| Movement inputs, firing bins rotated within each unit | Same fitted combined ridge | 2.172 cm |
| Position and movement history, elapsed times | Small temporal attention model | 2.218 cm |
| Same movement inputs and 72 firing histories | Combined temporal attention model | 2.484 cm |
| Movement inputs, spikes from a different earlier trip | Same fitted combined attention model | 3.262 cm |
| Movement inputs, firing bins rotated within each unit | Same fitted combined attention model | 3.011 cm |
| Earlier firing alone | Predict the absolute future position | 26.042 cm |
| Mean target position in training | Constant location | 41.669 cm |

The ridge model learns a weighted combination of inputs. It can change its expected movement according to where the rat is on the track. The attention model learns how to weight the four time steps. Both received the same earlier measurements and predicted a change from the rat’s last measured position. The spikes-only model had a harder job. It had to locate the rat with no starting position.

The combined ridge had to beat every registered movement comparison and the earlier-trip control to pass. It missed that criterion. Replacing the aligned spikes with those from an earlier trip worsened its error by 0.192 cm. That tells us the timing of the spikes mattered to this fitted model. The camera inputs alone still gave a better forecast. The separate spikes-only model beat the training-centre estimate by 15.627 cm, which shows a positional association worth distinguishing from the incremental forecast question. [Complete scores and paired differences](fitted/scores.json)

The mean increase in error from adding spikes was 0.227 cm. A descriptive 95% interval obtained by resampling neighbouring groups of four trips was 0.100 to 0.389 cm. Nine successive trips provide only about two nonoverlapping groups of four. That interval describes limited variation inside one run. A fresh rat, recording and task would each test a different claim.

## What the archive can tell us

The target is one point for the rat’s tracked location. There are no limb coordinates, muscle or force measurements here. Thirteen of the 72 units have no recorded spikes in the selected trips. The archive gives no per-unit observation intervals, so a zero count alone cannot establish that a cell was being observed reliably. The camera pipeline’s original filtering, interpolation and acquisition delay remain unknown. Both streams were processed offline. The comparison measures predictive association within this run and leaves causal mechanisms, action selection and performance in a live system open.
