# Rat muscle-spindle recordings

When a muscle stretches, one of its sensory fibres can fire a train of spikes. Blum and colleagues recorded these spikes from individual group Ia axons in rats while an actuator moved the muscle and a sensor measured force at the tendon. This reader takes nine healthy recordings and asks how many spikes followed each 100 ms of measured history. The two healthy prefix-5 recordings remain in reserve. The healthy filenames yield four prefixes, while the paper reports five animals. Grouped results therefore use filename prefixes. [Data and CC0 dedication](https://doi.org/10.5061/dryad.vdncjsxsw) · [Article](https://doi.org/10.7554/eLife.55177) · [Original archive](https://zenodo.org/records/4315453/files/spindle_data.zip)

The tested environment used Python 3.13.15. From this directory run

```sh
python -m pip install -r requirements.txt
python -B fetch.py
python -B check_reader.py
python -B prepare.py
python -B summarize.py
python -B sensitivity.py
```

The fetcher stores only approved members of the original ZIP in `private/members`. A complete reproduction needs approximately 1.2 GB of download and at least 3 GB of available disk space for the original MAT files and verified compressed range cache. Separate cohorts in the archive underwent treatment and fall outside this study. A failed range or identity check stops the affected download. Rerunning verifies existing members and reuses complete compressed range chunks with matching hashes. A custom data location can be supplied with `--directory` to both fetch and prepare. The summary command uses the default output directory.

`SOURCE-FREEZE.json` gives the eligibility criteria and the exact window calculations. `member-manifest.json` identifies the selected original files by size, CRC32 and SHA-256. `QC-SUMMARY.json` gives group counts and exclusions. The preparations below stay local; their hashes are in the summary.

| File under `private/` | Contents |
| --- | --- |
| `windows.npz` | Five completed 20 ms history bins per row, the detected count in the next bin, and separate following-bin mechanical changes. `X` has the last native force and position, their within-bin backward rates, and the detected count in that order. `mech_mean` has mean native force and position in each history bin. |
| `bin-mask.npz` | Afferent, original trial and zero-based bin index for each mechanically complete bin of structurally eligible trials, raw event count and separate electrical-coverage and signal-validity masks. |
| `member-metadata.json` | All source protocol labels in their deposited order, recorded internal names and trial counts. |
| `quarantined-measurements.json` | Native sample and event checks for the two files excluded by their name or trial-label mismatch. Neither contributes a model input. |
| `trial-qc.json` | Original identities and trial labels, actual sample clocks/timing, ranges, finite-sample checks, event-coordinate checks, full/trailing exposure, exclusion reasons and counts for each trial. |
| `aff015-trial1-native.npz` | Raw force, position and electrical samples on their original timestamps plus archived event times for the one illustration selected during the earlier pilot. |
| `fetch-receipts.json` | Exact byte ranges and verified size, CRC32 and SHA-256 of each member fetched by this run. |

Load NPZ files using `numpy.load(..., allow_pickle=False)`. Row identity is the combination of `afferent`, one-based source `trial`, and zero-based target `bin_index`. `cutoff_s` is the left edge of the target bin in original seconds. A trial starting at a nonzero archive time keeps that origin. `current_mech` and `y_delta` each have two columns in the order force and position. No physical-scale calibration was supplied for each channel. Pooling repeated windows as independent animals would overstate certainty.

`SINGLE-CLOCK-SENSITIVITY.json` registers an additional analysis after field inspection revealed that some member files omit `time_PotMem`. Where a recording supplies only `time`, all candidate trials must pass the array-length, time-grid, spike-time and stored-interval checks. Each member must also show a larger average raw voltage transient at the detected events than at three prespecified wrong times on the same trials. These checks can support a common recorded time basis. An independent electrical clock remains undocumented for these files. The added analysis writes separate outputs in `private/sensitivity/` and a separate `SENSITIVITY-QC-SUMMARY.json`. The per-row `clock_route` labels distinguish `two_clock` and `one_deposited_time`.

The three-prefix comparison could not be run on either set. The sole filename under prefix 4, `aff406_proc.mat`, names its recorded axon `aff106` inside the file. In another file, `aff021_proc.mat`, 39 trial labels accompany 38 trials. Both failed the registered identity checks. The strict set contains 94 eligible trials from three afferents in prefix 0. The additional analysis reaches 474 trials from seven afferents in prefixes 0 and 1. The two prefix-5 files remain unopened.

Blum KP, Campbell KS, Horslen BC, Nardelli P, Housley SN, Cope TC, Ting LH (2020). *Diverse and complex muscle spindle afferent firing properties emerge from multiscale muscle mechanics*. eLife 9:e55177. [Dataset](https://doi.org/10.5061/dryad.vdncjsxsw)
