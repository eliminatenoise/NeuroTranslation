[The studies](../README.md) › Studies 11 to 13 · Paced grip

# Scalp EEG made the paced-grip forecast worse for all three people

A person squeezes a hand-held sensor in time with a cue on a screen. The cue tells a model when the squeeze should rise; the sensor tells it what the hand has done so far. For the three test people, a straight-line fit on the cue timing and the sensor's recent voltage forecast the reading 120 ms ahead with an error of **0.3601 mV**. Adding scalp EEG raised it to **0.4613 mV**, and it was worse for all three. Forearm EMG lowered the error a little, to 0.3455 mV, but for one person of three, and EMG moved to the wrong moment did better still. Letting the fit change with the cue did not help either: 0.3741 mV.

Every score here is the measure that punishes large misses (root mean squared error), worked out for each person and averaged over the three, in millivolts of the sensor's output. The dataset gives no conversion from volts to newtons, so these are errors in voltage, not in force. EEG is electrical activity of the brain, picked up on the scalp; EMG is electrical activity of muscle, picked up on the skin.

- [Study 11 · Paced grip: brain signal](results-2026-11-19/README.md): the result in full, with the two EEG controls.
- [Study 12 · Paced grip: muscle signal](forearm-results/README.md): the same forecast with forearm EMG added.
- [Study 13 · Paced grip: a fit that changes with the cue](cue-phase/README.md): a forecast allowed to read the voltage differently during squeeze and rest.
- [Replay a trial in the browser](https://eliminatenoise.github.io/NeuroTranslation/hygrip-force/).

The rest of this page is the plan for study 11 as it was published on 19 November 2026, before any test recording was opened, in the past tense of a plan that was then carried out. Its exact wording, with the checksums that fix it, is [DESIGN.json](DESIGN.json).

## A different grip task

Pablo Ortega, Tong Zhao and A. Aldo Faisal recorded HYGRIP at Imperial College London with 14 healthy right-handed volunteers. Each trial cued one hand, in a shuffled order, and this study used the right-hand trials. In the WAY-EEG-GAL studies ([study 10](../way-contact-force/)), two fingertips pinch and lift a free object, and the instrument also measures load and position. HYGRIP asked the same question about EEG in a different task, with its own split of people and its own fits. The two datasets were recorded separately, and the releases do not allow a check for people who took part in both. What can be compared across the two is the direction of the EEG effect: WAY's errors in newtons and HYGRIP's errors in volts measure different things. [HYGRIP methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC7649364/) · [WAY methods](https://doi.org/10.1038/sdata.2014.47)

The target was the released, signed voltage of the sensor. Checking the source found no usable factor from volts to newtons, so the whole analysis used volts. Each trial had ten scheduled cycles of 1.55 s of squeezing and 0.55 s of rest. The known schedule supplied the timing inputs; the released signals supplied the measured target. The original task showed the person feedback around a target range of 25–50% of each hand's hardest squeeze. The reference waveform shown on the screen, and when it was shown, could not be checked. [HYGRIP data deposit, version 1, MIT](https://doi.org/10.6084/m9.figshare.12383639.v1) · [Publisher file and licence metadata](https://api.figshare.com/v2/articles/12383639/versions/1)

## Which recordings counted

The plan split the 14 volunteers before any waveform was read: eight to fit the models, three to test them and three to be set aside. The plan's own names for the three groups, kept in its files, are TRAIN, DEV and FINAL. In one fitting run, the interval between two paired Go markers differed by **249.5 ms** between the force clock and the EEG clock. The plan held back any whole run with a difference over **40 ms**, so that run was withheld, and its person stayed counted among the fitting people; the plan recorded this as a written amendment before fitting. Seven usable fitting people supplied **79 right-hand trials and 16,195 scheduled forecasts**. Those counts measured how much input and target data was there before any fit or score. Nobody was moved to another group.

Forecasts started 400 ms after the nearest Go sample on the 50 Hz force grid and came every 100 ms up to 20.8 s. Each target was the sensor's voltage six samples after the forecast. The EEG input was the last 400 samples of the 24 scalp channels on their 1 kHz grid, ending at least **20 ms** before the forecast's own time from Go. That margin is a cutoff on the stored clocks: the physical skew between them, the phase of the filters and the delay from recording to output were never measured. A matching sequence of Go markers and a passed interval check supported the clock arithmetic.

## What had to beat what

- **Simple forecasts.** Repeat the latest voltage, carry its last 80 ms of change forward, or fit a straight line (a ridge regression) to the task timing alone.
- **The fit on the sensor's history.** The same timing, with the 20 measured voltage samples up to the forecast and the backward changes over 80 and 200 ms.
- **The same fit with EEG timed to the forecast.** Four numbers per channel added to those features: the average after subtracting the average of all channels, the size of the signal (root mean square around its mean), and the power in the 8–13 Hz and 13–30 Hz bands, measured through a taper.
- **Two EEG controls.** One took EEG from the next right-hand trial of the same person and protocol at the same stage of the cue. The other ended the EEG window 400 ms earlier in the same trial. Moving EEG between trials is possible only after the fact. Every main version was scored on the same rows.

Features were scaled inside each fitting fold. Each version's penalty was chosen from the same fixed grid by leaving one fitting person out at a time, then the fit was made again on all seven. Each person's score was the square root of their average squared error per trial, with forecasts counting equally within a trial; the headline was the average over people, in volts. The plan asked for paired changes, EEG timed to the forecast minus each comparison (the history fit, other-trial EEG, earlier EEG), with a two-sided exact sign test and a descriptive 95% paired t interval. EEG passed only if its average error was lower than all three. The fitting people's scores chose the penalties; the test people and the set-aside people were for the checks that came later under the fixed split. A scalp signal can carry eye, muscle and movement effects, so even a lower error would not have said where the signal came from.

The version-1 data DOI identifies the deposit. [DESIGN.json](DESIGN.json) records the digest of the data file and the original split, plan and amendment. Which person went to which group, the waveforms and the results of single people are not published.

### The cue-phase follow-up

The next comparison fitted three voltage models on the same 20 recent readings and the known cue schedule; one let the link between recent voltage and the forecast change between the scheduled squeeze and rest. It used the original fitting split and the three test people already scored. Its plan, [cue-phase/PROTOCOL.md](cue-phase/PROTOCOL.md), was fixed before fitting. The fit on the full history kept the lowest average error: [study 13](cue-phase/README.md).
