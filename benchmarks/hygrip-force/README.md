# Does scalp EEG improve a grip forecast?

A person squeezes a hand-held transducer in time with a visual cue. The cue tells the model when the squeeze should rise. The transducer tells it what the hand has done so far. Can scalp EEG improve a forecast of the transducer reading 120 ms later?

**It did not.** On the three people set aside for the first test, a forecast from the cue timing and the recent voltage missed by 0.360 mV on average. Adding EEG raised that to 0.461 mV, and it was worse for all three. [The result](results-2026-11-19/README.md) · [The same forecast with forearm EMG added](forearm-results/README.md) · [With the fit allowed to change with the cue](cue-phase/README.md) · [Replay a trial in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/)

The rest of this page is the plan, as it was published on 19 November 2026 before any test recording was opened. The split of people and the design were fixed before any waveform was read. A clock check on the fitting recordings led to a written amendment before fitting. [The plan in machine-readable form, with its checksums](DESIGN.json)

## A different grip task

Pablo Ortega, Tong Zhao and A. Aldo Faisal recorded HYGRIP at Imperial College London with 14 healthy right-handed volunteers. The study cued one hand per trial in pseudorandom order. This benchmark uses right-hand trials. In [the earlier WAY study](../way-contact-force/), the two fingertips pinch and lift a free object, and the instrument also measures load and position. HYGRIP tests the same question about adding EEG in a different task, with its own split and fits. The two datasets have separate acquisition histories. Participant overlap cannot be checked from the releases. Compare the direction of the EEG effects across studies. WAY's newton errors and HYGRIP's voltage errors measure different quantities. [HYGRIP methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC7649364/) · [WAY methods](https://doi.org/10.1038/sdata.2014.47)

The outcome is the released signed transducer voltage. The source screen found no usable volts-to-newtons conversion factor, so the primary analysis uses volts throughout. The ten scheduled cycles have 1.55 s of contraction instruction and 0.55 s of rest. The known schedule supplies timing features. The released signals supply the measured voltage target. The original task gave visual feedback around a target range of 25–50% of each hand's maximum voluntary contraction. The displayed reference waveform and delivery time were unavailable for verification. [HYGRIP data deposit, version 1, MIT](https://doi.org/10.6084/m9.figshare.12383639.v1) · [Publisher file and license metadata](https://api.figshare.com/v2/articles/12383639/versions/1)

## Which recordings qualify?

The frozen split assigns eight people to TRAIN, three to DEV and three to FINAL. An adjacent interval between paired Go markers differed by **249.5 ms** across the force and EEG clocks in one TRAIN run. The prespecified gate holds an entire run when any discrepancy exceeds **40 ms**. That run stays assigned to TRAIN. Seven eligible TRAIN participants supplied **79 right-hand trials and 16,195 scheduled issue rows** with the required source coverage. These counts measure available input and target coverage before fit and scoring. No participant was reassigned.

Forecasts start 400 ms after the nearest 50 Hz force-grid Go sample and recur every 100 ms through 20.8 s. Each target is the force transducer voltage six samples after issue. The 24 scalp channels use the last 400 samples on their 1 kHz grid. The EEG window ends at or before its own Go-relative issue time minus a fixed **20 ms** margin. This is an offline cutoff, with physical skew, filter phase and acquisition-to-output latency still unmeasured. A matching Go sequence and a passed interval screen support the recorded clock calculation.

## What has to beat what?

- **Baselines.** Carry the latest voltage forward, extend its backward 80 ms slope, or fit a ridge regression to task timing alone.
- **Force-history ridge.** Use the same timing with 20 measured voltage samples through issue and backward slopes over 80 and 200 ms.
- **Aligned EEG ridge.** Add four descriptors per channel to the same force-history features. Use common-average referenced mean, centered root mean square amplitude, and tapered power in 8–13 Hz and 13–30 Hz.
- **Two EEG controls.** One takes EEG from the next right-hand trial within the same person and protocol at the equivalent issue phase. The other ends the EEG window 400 ms earlier in the same trial. The rotation is an offline control. All primary branches use the same scored rows.

Scale features inside each training fold. Choose the ridge penalty separately for each branch from the same fixed grid using leave-one-person-out TRAIN validation, then refit on seven eligible people. Score each participant by taking the square root of their mean trial squared error, with issues weighted equally within each trial. The headline is the equal-person mean of those RMSEs, in V. Report paired aligned-minus-comparator changes for force history, rotated EEG and earlier EEG, with the two-sided exact sign test and a descriptive 95% paired t interval. The directional criterion requires a lower mean error against all three comparators. TRAIN fold scores guide penalty selection. DEV and FINAL supply later checks under the frozen split. A scalp signal can include eye, muscle and movement effects, so a lower error would leave its source unresolved.

The version-1 data DOI identifies the deposit. [DESIGN.json](DESIGN.json) records the sealed data file's digest and the original split, protocol and amendment commitments. Original participant assignments, waveform data and individual outcomes remain private.

### Does the cue change what a rising grip signal predicts?

The next comparison fits three voltage models on the same 20 recent readings and known cue schedule. One lets the relation between recent voltage and its forecast vary across the scheduled contraction and relaxation phases. The prespecified comparison uses the original training split and the three previously studied development participants. [Read the frozen design](cue-phase/PROTOCOL.md). In development, the full history model retained the lowest mean error. [See the cue-phase comparison](cue-phase/README.md).
