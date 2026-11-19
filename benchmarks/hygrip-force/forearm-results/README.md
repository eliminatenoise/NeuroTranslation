# Does forearm activity sharpen the grip forecast?

The grip sensor samples at 50 Hz. Given the cue and the sensor's recent voltage, predict its reading six ticks later. In this secondary HYGRIP analysis, we added four channels of forearm surface EMG and tested whether their timing mattered.

| Mean participant error (mV) | Seven training participants, leave one out | Three previously studied development participants |
| --- | ---: | ---: |
| Cue timing and recent sensor voltage | 0.394 | 0.360 |
| Add aligned forearm EMG | 0.409 | 0.345 |
| Add aligned scalp EEG as well | 0.423 | 0.474 |

On the development recordings, adding EMG lowered the average error but helped just one of the three people. Moving the EMG to a different point in the same trial lowered mean error further, to **0.343 mV**. The shifted signal beat the aligned signal for all three. This offline timing control can use samples later in a trial. Its role is to test whether matching the muscle activity to the forecast moment matters.

Neither the training nor the development comparison met the prespecified criteria for an advantage specific to aligned EMG. Adding aligned EEG to the voltage-and-EMG forecast increased error for all three development participants. The descriptive interval for that mean change was −0.229 to +0.486 mV. Participants, trials and forecast cutoffs contributed equally at each respective averaging level. [Training results](TRAIN.json) · [Development results](DEV.json)

The 79 training trials contributed 16,195 common forecast cutoffs. The 39 development trials contributed 7,995. The development participants had already been evaluated in the [primary EEG study](../results-2026-11-19/). The final cohort remains reserved. Errors are reported in millivolts of recorded transducer output. Calibration in newtons and the timing of a live implementation remain open.

[Download the frozen design, aggregate tables and offline checker](HYGRIP-Muscle-Train-and-Dev-Aggregates.zip) · [HYGRIP source study](https://doi.org/10.3389/fnins.2020.00919) · [Original data deposit](https://doi.org/10.6084/m9.figshare.12383639.v1)
