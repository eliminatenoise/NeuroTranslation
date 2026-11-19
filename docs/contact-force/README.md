# Grip after contact

The plates register a squeeze. At each issue time, how much grip force will they register 120 ms later? Run two fitted NeuroTranslation models on the same past readings and check where their forecasts part ways.

## Open the preview

Extract the whole ZIP first. Use the launcher for your system or open `index.html` in a modern browser. The preview needs no server, Python installation or internet connection.

| System | Launcher |
| --- | --- |
| Windows | Open `Run-Windows.cmd`. |
| macOS | Open `Run-macOS.command` or run `sh ./Run-macOS.command` in Terminal. |
| Linux | Run `./Run-Linux.sh` or `sh ./Run-Linux.sh` in a terminal. |

If your system blocks a launcher, open `index.html` without changing its security settings. Chromium on Linux was used for live browser checks. Windows and macOS launcher files are supplied for those systems, with native runs pending.

Start with an invented pinch lift. Move **Issue after confirmation** from 0 to 400 ms to change the last sample both models receive. The plot stops the sensor traces at that cutoff. The separate forecast markers share the same target time. **Read a history sample** moves along the trace without changing which samples the model receives. Switch **Trace** to see individual tracker coordinates or channels. **Reveal target sample** shows only the grip at the target row, when the capture includes it. That value goes into the comparison display.

**Model inputs** switches fitted variants. Ridge turns the measured history into features such as force taps, rates and finger aperture. The causal convolutional neural network (CNN) reduces the 200 sensor rows to fifty consecutive four-row averages and uses convolutions over those bins. Both can add scalp electroencephalography (EEG), which measures scalp potentials. The ridge preview also includes two variants with surface electromyography (EMG), which measures muscle activity through skin electrodes. The timed controls use the selected offset and seconds since the LED go cue. The fixed baselines keep the current grip or carry forward the 80 ms backward force slope.

## Supply signals from your own recording

The browser reads one local JSON object under 16 MiB. There is no upload, account, transmission or persistent browser storage of the file. Include only the keys documented here. Use finite numbers and the same channel order, calibration, synchronization and numerical scales used in the original experiment. The viewer checks shape and clock spacing. Signal provenance and hardware setup are supplied by the user.

### Through the go cue and into the lift

Include the first sample at or after the LED go cue and enough history before each issue. Extra rows may extend through the target.

| Key | Value |
| --- | --- |
| `rate_hz` | 500, optional for a clocked capture |
| `clock_s` | Up to 16,000 consecutive 500 Hz timestamps in seconds, in chronological order |
| `led_on_s` | Captured LED go timestamp on that clock |
| `grip_n` | One mean normal force for each timestamp, in N, with compression positive |
| `load_n` | One total vertical load per timestamp, in N, with upward positive |
| `position` | One array of four XYZ triples per timestamp in object, index finger, thumb and wrist order |
| `eeg` | Optional. One array of 32 scalp amplitudes per timestamp in the source order |
| `emg_clock_s` | Optional with `emg`. Up to 128,000 aligned, consecutive 4 kHz muscle timestamps in seconds on the same time origin |
| `emg` | Optional with `emg_clock_s`. One array of five surface EMG amplitudes per muscle timestamp in the source order |

The prepared WAY records store the mean normal force with compression negative. Use the negative of `ws.win.kin` column 42 for `grip_n` and the original signed column 39 for `load_n`, counting columns from one. Position, EEG and EMG retain the numerical scales used in the released recordings.

The first sample at or after the cue must be below 0.5 N. After that, count consecutive samples at or above 0.5 N and reset the count whenever force falls below it. The tenth sample fixes the schedule, 18 ms after the first threshold sample in that run. The schedule uses offsets of 0, 100, 200, 300 and 400 ms from confirmation. Each issue needs 200 rows through issue, a 398 ms span, and predicts the mean normal grip force in N exactly 60 samples later on the 500 Hz clock. The ridge muscle branches need 1,600 aligned rows through the last muscle sample at or before issue, within one muscle tick of the issue. An unavailable issue or optional channel is marked in the viewer.

### Already prepared at an individual issue

The exact 200-row CNN window JSON also opens here. Supply `rate_hz` of 500, `offset_from_confirmation_ms` of 0, 100, 200, 300 or 400, and finite `elapsed_since_go_cue_s` at least as large as the offset in seconds. Supply exactly 200 chronological rows of `grip_n`, `load_n`, and `position`, and optionally 200 rows of `eeg`, in the layout above. The last row is the issue sample. The viewer uses the supplied offset and elapsed time. Use the continuous capture format to verify that confirmation occurred.

You may also supply `issue_time_s`. It defaults to the elapsed time since the go cue, with the cue at zero. Optional `emg_clock_s` and `emg` use the same time origin as `issue_time_s` and the alignment rule above. A prepared window has a single fixed issue and ends at that issue, so no target value can be revealed.

EEG order is Fp1, Fp2, F7, F3, Fz, F4, F8, FC5, FC1, FC2, FC6, T7, C3, Cz, C4, T8, TP9, CP5, CP1, CP2, CP6, TP10, P7, P3, Pz, P4, P8, PO9, O1, Oz, O2, PO10. EMG order is anterior deltoid, brachioradial, flexor digitorum, common extensor digitorum, first dorsal interosseus.

## What happened in the study

Using the same 4,410 development rows from 882 lifts by three previously explored healthy volunteers, the measured grip force agreed most closely with ridge using past force and motion. Its mean participant root mean square error (RMSE) was 0.677 N. The corresponding CNN value was 0.978 N. Adding aligned scalp EEG increased mean RMSE by 0.018 N in ridge and 0.016 N in the CNN. The descriptive 95% paired intervals span zero in both families (ridge −0.003 to +0.040 N, CNN −0.136 to +0.167 N). Substituting EEG from another lift at the same stage after force confirmation scored 0.692 N in ridge and 0.987 N in the CNN. These results supply no evidence of incremental EEG value for this task. Participants count equally, and trials and scored issue times count equally within their respective groups.

The frozen models were fitted on six training volunteers. Final held-out participants were kept reserved. The two fitted families differ in representation and tuning, and the comparison does not isolate either design choice. The app's synthetic signals are separate from all original study measurements. Force confirmation is a proxy, first anatomical touch was not measured, and 120 ms here is a horizon on the recorded clock. Device readiness, prospective sensor delay, clinical validity and a cortical mechanism remain unestablished.

## Sources

Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin recorded WAY-EEG-GAL. The paper describes the force plates, position sensors, EEG, EMG and alignment of their clocks. The data descriptor describes data and utilities as CC BY 4.0. The companion Figshare collection records item-level terms. The preview contains derived fitted parameters, aggregate results and synthetic signals. [Data descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/) · [Figshare collection](https://doi.org/10.6084/m9.figshare.c.988376.v2).

The European Commission’s WAY project (Wearable interfaces for hAnd function recoverY, FP7-ICT-288551) was the primary funder of the original study. [Original acknowledgments](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/#ack1).

See `MANIFEST.json` for the two source ZIPs, individual source member hashes, glossary revision, and file hashes for this edition. Browser calculations ship as readable JavaScript.
