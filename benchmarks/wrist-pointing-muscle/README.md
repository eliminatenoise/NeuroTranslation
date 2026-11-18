# How much does forearm EMG add to a wrist forecast?

[Download the interactive experimental preview ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/wrist-pointing-muscle/wrist-pointing-muscle-r1-preview.zip)

There are two traces of the same turn. The exoskeleton encoders tell us how the right wrist moved. Surface electromyography (EMG) picks up electrical activity at the skin of the forearm. To see what the muscle signal adds, we fit one ridge regression to cue time and recent wrist angles, then fit a second with the same inputs plus surface EMG.

We fit the regressions on six people and evaluated them on three different people. The development set has 960 pointing trials and 5,760 two-axis angle pairs. With surface EMG, the equal-person root mean square error fell from **6.530° to 6.174°**, a reduction of **0.355°** using the full-precision scores. Giving that same model EMG from the next eligible trial at the same cue offset in the same recording block raised error to **6.941°**. Adding scalp EEG after EMG brought overall error to **6.127°**. On the radial–ulnar axis, that last step raised error slightly, from 3.987° to 3.998°.

Each prediction takes aim at a pair of encoder measurements in degrees, one for flexion–extension and one for radial–ulnar deviation. The last input comes 128 stored rows before the target, a nominal **250 ms** at 512 Hz. Physical clock and signal delays remain unverified. The inputs can also reflect electrical activity from adjacent muscles, contact changes and movement artefacts. These offline measurements concern a specific task and three development participants. The reserved test cohort remains sealed.

The [companion temporal forecast](../wrist-pointing-temporal/) uses the same participants and trials to ask what EEG adds to a learned model of wrist history. Its stronger motion-only result comes from a different model class. The EMG study compares inputs within one class of ridge regression.

## Open the preview

Extract the whole ZIP and open `index.html` in a browser, or use the launcher for your operating system.

| System | Launcher |
| --- | --- |
| Linux | `sh Launch-Linux.sh` |
| macOS | Open `Launch-macOS.command` or run it in Terminal |
| Windows | Open `Launch-Windows.cmd` |

Choose an axis to see where error changed, or open **All scores** to see the baselines and trial controls. The browser view works offline without dependencies. With Python and NumPy, `python -B synthetic_model.py` runs the bundled fitted ridge heads on artificial inputs. The Linux launcher has been run from the archive. The macOS and Windows launchers are supplied for those systems and await native verification.

[Development aggregate](RESULTS.json) · [Sources and checksums](SOURCE.json)

## Data credit

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz deposited *EEG-EMG-WristMotion Dataset*, version 3, under CC BY 4.0. NeuroTranslation selected eligible pointing trials and derived features from the earlier encoder angles, scalp EEG and software differences between forearm electrodes. The project authored the analysis code, fitted ridge heads and interactive comparison. [Version 3 deposit](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Primary study](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
