# Which voltage did the model see?

Every input row uses the five original names below. Each voltage was measured on the same 10 kHz sampling clock. The reference electrode differs by channel. The BIDS channel table labels “Biceps” as `MISC` and “Thumb” as `EMG`. The electrode placement in the recording methods identifies what these labels mean.

| Input | Recorded site and reference |
|---|---|
| Biceps | Left axilla over the median nerve, referenced to BicepsN about 3 cm proximal. Only the early arm window enters the full Transformer. |
| SC6 | Neck surface over the sixth cervical vertebra, referenced to TH6 over the sixth thoracic vertebra. This is also the forecast site. |
| Thumb | Surface muscle voltage from abductor pollicis brevis, relative to a proximal electrode. |
| CP4 | Scalp voltage at CP4 relative to the right mastoid behind the ear. |
| ECG | Chest voltage at the left costal margin relative to a right subclavicular electrode. |

The earlier eight-event calculation used the same neck-to-back reference but a two-millisecond baseline. The model uses five milliseconds. Electrical activity at either end of a reference pair can change a reading. [Original methods](https://doi.org/10.1371/journal.pbio.3002828) · [Source channel table](https://github.com/OpenNeuroDatasets/ds004388/blob/ab5f0cb559249cb6d82b6f763767c6fe99292886/sub-001/eeg/sub-001_task-median_run-03_channels.tsv) · [Source reference metadata](https://github.com/OpenNeuroDatasets/ds004388/blob/ab5f0cb559249cb6d82b6f763767c6fe99292886/sub-001/eeg/sub-001_task-median_run-03_eeg.json)
