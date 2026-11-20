# A heel marker and the plate beneath it

A walker steps barefoot onto a force plate. How far did the heel move in a tenth of a second, and how much upward force did the plate record at that instant? Cameras locate two skin markers on the right foot. The plate measures the upward force under that foot. The source reader brings the two measurements to the same instant. [Schreiber and Moissenet, study and supplement](https://doi.org/10.1038/s41597-019-0124-4)

Each row starts at a fixed time after the first right foot strike. It keeps the last 24 marker frames, four short summaries of right-leg muscle activity, and two measurements centred 100 milliseconds later. The first is the heel marker’s change in position along three laboratory axes, in millimetres. The second is the mean vertical load over 15 force samples from the plate assigned to the right foot, in newtons. Movement of a skin marker includes movement of the skin. The paper gives no measurement uncertainty for an individual sub-millimetre displacement. [Dataset, version 8](https://doi.org/10.6084/m9.figshare.7734767.v8)

## Build the development arrays

Download the original ZIP and the article’s second Word supplement. The commands below assume you saved them as `walking.zip` and `supplement.docx` in the working directory. The qualifier checks the release size, MD5 and SHA-256, reads the archive directory and checks the supplement’s SHA-256. It extracts only the selected recording payloads with an eligible contact code. Python 3.12 and the dependencies in this folder reproduce the measurements. [Walking ZIP](https://ndownloader.figshare.com/files/22295019) · [Supplementary Table 2 in the Word document](https://media.springernature.com/full/springer-static/esm/art%3A10.1038%2Fs41597-019-0124-4/MediaObjects/41597_2019_124_MOESM2_ESM.docx)

```sh
python -m pip install -r requirements.txt
python qualify.py --archive walking.zip --supplement supplement.docx --partition train --output prepared
```

The results are `prepared/development-v1.npz` and `prepared/development-v1-receipt.json`. Open the NPZ with `numpy.load(path, allow_pickle=False)`. The JSON gives the original trial names, quality codes, verified file hashes, contact and window exclusions, units through the protocol, and row counts. An existing directory of verified original recordings can be reused with `--staged PATH`. This route checks each decoded recording against its original SHA-256, length and CRC32 and checks the archive directory and supplement against their pinned identities.

| Array | Dimensions per observation | Source or use |
|---|---:|---|
| `person`, `repeat` | One each | Source participant code and C2 walking trial number |
| `offset`, `cutoff` | One each | Frames since first right strike and zero-based index in the cropped walking trial |
| `marker_mm` | 24 × 2 × 3 | Heel then forefoot, laboratory X, Y and vertical Z, in mm |
| `emg_uv` | 4 × 8 | Four 60 ms root-mean-square voltage bins in chronological order, eight right-leg muscles in μV |
| `heel_delta_mm` | 3 | Future heel position minus its position at cutoff, mm |
| `force_n` | 1 scalar | Mean upward force measured on the assigned platform, N |
| `privileged_force_n` | 2 | Two separate past-force measurements for baselines, ending at cutoff and 100 ms earlier |

The two marker labels are `R_FCC`, on the back of the heel, and `R_FM2`, over the head of the second metatarsal. The muscle channels are tibialis anterior, soleus, medial gastrocnemius, vastus medialis, rectus femoris, semitendinosus, gluteus maximus and gluteus medius. Surface electrodes measure muscle electrical activity. They do not record individual motor nerves. [Source field definitions](https://ndownloader.figshare.com/files/14870426)

## Which step landed on which plate?

The authors gave each walking trial a two-digit code. In code 12, the first digit assigns the right foot to plate 1 and the second assigns the left to plate 2. Code 21 reverses them. Only those two codes qualify. The reader checks the corners and calibrated force channel of that specific plate. A valid heel and forefoot marker must both fall within its outline at first right strike and again at the target. Between this strike and the next right strike there must be a single right foot-off. All 15 target force samples must occur before it. These tests identify eligible outcomes. The next strike, foot-off and target marker positions are unavailable to the predictor. [Study methods and contact table](https://doi.org/10.1038/s41597-019-0124-4)

The source counts point frames from 1. The arrays count from 0. Marker index `t` corresponds to analog sample `15*t+7`, at the centre of that 15-sample block. The last muscle-voltage bin ends at that centre, seven analog samples before the end of the block. Let `u=t+10`. The future force mean spans `15*u` through `15*u+14` inclusive, or 95⅓ to 104⅔ ms after cutoff. The plate’s local vertical axis points down. Its calibrated laboratory upward force matches the negative of the original scaled local Fz channel. A stored zero remains a zero. Missing forces and forces below the source’s processing threshold can both produce one. The methods describe a 5 N threshold and the linked export code applies 50 N. [Event export](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/exportEvents.m) · [Force processing](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/importTrialReaction.m)

The source already filled marker gaps and filtered the complete recordings in both temporal directions. The documented marker and force cutoffs are 6 and 15 Hz. Muscle voltage was centred over the trial and bandpass filtered from 30 to 300 Hz. The reader uses only stored input samples through cutoff. A live sensor would not yet have the future samples used by those original filters. Hardware latency and real-time performance remain unmeasured. [Marker processing](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/importTrialMarker.m) · [Muscle-voltage processing](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/importTrialEMG.m)

## Who supplies the rows?

Sorting the original 50 participant codes fixes the roster. The first 30 supply development data, the next ten form the historical assessment group, and the final ten remain in reserve. Each original partition uses the three lowest available numeric C2 repeats for each participant. The C2 protocol targeted a walking speed of 0.4–0.8 m/s using a metronome. The target speed describes the task. Actual speed is not supplied as a model input. [Study protocol](https://doi.org/10.1038/s41597-019-0124-4)

Of 90 development walks, 28 lacked an eligible two-plate assignment and one failed the marker check at strike. The remaining 61 walks supplied 244 candidate windows. Forty-one lacked a complete input history. The result is **203 paired measurements from 61 walks by 25 people**. The 14-frame cutoff survived in 20 walks. The 24-, 34- and 44-frame cutoffs survived in all 61. Overlapping histories in one walk share much of their information. A comparison across people must allow for repeated measurements within each walk and repeated walks by the same person.

For an assessment after both model families have been frozen, the reader accepts `assessment` for the original ten-person group and `later-repeats` for a separate set of 18 additional C2 walks by those same ten people. Of 30 original assessment walks, 16 qualified, giving 53 paired measurements from eight people. Of the 18 additional walks, eleven carried code 12 or 21. Ten passed the remaining checks, giving 31 pairs from six people. All six also contributed original assessment walks. These ten rostered people have already appeared in the assessment roster of earlier studies. Original and additional walks have separate results. Each assessment command also requires `--fit-seal PATH --fit-seal-sha256 DIGEST`, the joint fit manifest and its verified digest.

Florent Moissenet and Céline Schreiber released the measurements under CC BY 4.0. This reader derives marker histories, muscle-voltage summaries, heel displacement vectors and vertical plate-load means from their files. [Original versioned dataset](https://doi.org/10.6084/m9.figshare.7734767.v8) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
