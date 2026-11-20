[The studies](../README.md) › Study 2 · Wrist pointing: muscle signal on a straight-line fit

# Forearm EMG lowered the wrist forecast's error by 0.355°

Three people turned a wrist towards a target. A straight-line fit, made on six other people from the wrist's recent angles and the time since the cue, forecast both wrist angles 250 ms ahead and missed by **6.530°**. Given surface EMG from the forearm as well, it missed by **6.174°**, 0.355° better. Given EMG from the next trial of the same person and recording block, at the same time after the cue, it missed by **6.941°**: wrongly timed EMG did worse than no EMG at all. Whichever one of the three people is left out, the gain stays between 0.232° and 0.469°.

Every score here is the measure that punishes large misses (root mean squared error), over both wrist axes, with each person counting equally. EMG is electrical activity of muscle, picked up on the skin over it: a recording of muscle, not of nerve. A *straight-line fit* is the plainest kind of model, a weighted sum of its inputs; this one has a penalty that keeps the weights small.

## What was forecast

Two records of the same turn: the exoskeleton's encoders measure how the right wrist moved, and four pairs of electrodes on the forearm pick up the muscles' electrical activity. Each forecast aims at two encoder angles in degrees, bending up and down (flexion–extension) and tilting side to side (radial–ulnar deviation). The test is 960 pointing trials and 5,760 pairs of angles from three people the fit never saw. Six more people were set aside when the dataset was split, and their recordings are unopened.

The last input comes 128 stored samples before the target, which is 250 ms on the 512 Hz clock. The physical delays of the clocks and signals were never measured. Electrodes on the skin also pick up nearby muscles, changes in contact and movement itself.

Adding scalp EEG after EMG brought the error to 6.127°. On the side-to-side axis that last step made it slightly worse, 3.987° to 3.998°.

[Study 1](../wrist-pointing-temporal/) uses the same people and trials to ask what scalp EEG adds to a learned forecast of the wrist's history. Its stronger result without any signal, 4.053°, comes from a different kind of model. This study compares inputs within one straight-line fit.

## What it does not show

One pointing task, three people, stored recordings scored after the fact. The same three people are the test group of studies 1 and 3 as well, so the three studies are three looks at one group, not three groups.

## The plan

The plan, `DESIGN.json` inside the [study ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/wrist-pointing-muscle/wrist-pointing-muscle-r1-preview.zip), fixed the comparison before scoring, calls the study exploratory, and says plainly that the three test people are not a new, independent group. It set no pass threshold.

## Run it yourself

[Download the study ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/wrist-pointing-muscle/wrist-pointing-muscle-r1-preview.zip), extract all of it and open `index.html` in a browser, or use the launcher for your system.

| System | Launcher |
| --- | --- |
| Linux | `sh Launch-Linux.sh` |
| macOS | Open `Launch-macOS.command` or run it in Terminal |
| Windows | Open `Launch-Windows.cmd` |

Choose an axis to see where the error changed, or open **All scores** for the simple forecasts and the wrong-trial controls. The page works offline with nothing to install. With Python and NumPy, `python -B synthetic_model.py` runs the fitted models on invented inputs. The Linux launcher has been run from the archive; the macOS and Windows launchers have not yet been run on those systems.

[Results file](RESULTS.json) · [Sources and checksums](SOURCE.json)

## Whose recordings

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz deposited the *EEG-EMG-WristMotion Dataset*, version 3, under CC BY 4.0. NeuroTranslation selected the usable pointing trials and worked out features from the earlier encoder angles, the scalp EEG and the differences between pairs of forearm electrodes. The project wrote the analysis code, the fitted models and the interactive comparison. [Version 3 deposit](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Primary study](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

A later study asked whether EMG still helps once a learned forecast already knows the wrist's recent motion. Added to a correction on top of that forecast, it lowered the error from 3.957° to 3.853°, on the same three people: [Study 3 · Wrist pointing: muscle signal on the learned forecast](../wrist-forearm-transfer/).
