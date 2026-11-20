# Read the walking recordings

A barefoot walker crosses two force plates set into the middle of a ten-metre walkway. Cameras trace the movement of 52 skin markers. Electrodes record activity in eight muscles of the right leg. The plates measure the load under the feet that reach them. A step elsewhere on the walkway can carry weight while both plates read zero. [Study and methods](https://doi.org/10.1038/s41597-019-0124-4)

## Reproduce the selection

Download the walking archive from version 8 of the dataset and the Word supplement from the article. Keep both in a private working directory. The supplement contains trial-by-trial foot assignments as well as participant information. [Walking archive](https://ndownloader.figshare.com/files/22295019) · [Article supplement](https://media.springernature.com/full/springer-static/esm/art%3A10.1038%2Fs41597-019-0124-4/MediaObjects/41597_2019_124_MOESM2_ESM.docx)

Run the following from this package with Python 3.10 or newer. The two source paths are examples. The preparation script uses only the Python standard library.

```sh
python prepare_source.py walking.zip supplement.docx private-output train
```

The script checks the 381,392,112 archive bytes against the publisher's MD5 and the independently recorded SHA-256. It rebuilds the original split from the archive directory and checks the CRC of every selected recording. The 50 original participant folders are sorted by identifier. The first 30 supply training trials, the next 10 supply assessment trials and the last 10 form an unopened reserve. Each person contributes the three lowest numbered available trials at speed condition C2. The metronome set a pace intended to produce 0.4–0.8 metres per second. The authors checked the speed of the first trial in that condition.

The output contains the selected C3Ds, a private split manifest and a private table of contact codes. In that table the first digit identifies the right foot's plate and the second identifies the left foot's plate. Digits 1 and 2 identify plates. A zero means the authors judged the ground-reaction information for that foot unavailable or unreliable. A missing exact participant match leaves both assignments unknown. The combined-plate comparison admits codes 12 and 21. That choice selects trials with reliable contacts on both plates.

After fitting the study, pass the completed fit manifest and its SHA-256 to extract assessment files. The script has no reserve extraction option. Store all generated participant-level files privately.

```sh
python prepare_source.py walking.zip supplement.docx private-output assessment --fit-seal fit-seal.json --fit-seal-sha256 EXPECTED_SHA256
```

## What a sample means

The 100 Hz cameras produce one marker frame every 10 milliseconds. Each frame has 15 analog samples at 1,500 Hz. Force is in newtons, marker coordinates in laboratory millimetres, plate moments in newton-millimetres and muscle voltage in volts. The eight signed surface recordings come from the right tibialis anterior, soleus, medial gastrocnemius, vastus medialis, rectus femoris, semitendinosus, gluteus maximus and gluteus medius. A muscle-voltage envelope requires a separate calculation. The source provides no corresponding left-leg electrodes. [Stored field definitions](https://ndownloader.figshare.com/files/14870426)

The laboratory Z axis points up. Both plate Z axes point down and the two plates have opposite horizontal orientations. Read each platform's corner coordinates and channel map before using its force. In the verified recordings, the upward lab component equals the negative of the scaled, signed local Fz channel on each plate. Adding the two upward components gives the combined vertical load **recorded on these two plates**. The release reports source-coded zeros below the export floor and the original code also turns missing force samples into zeros before filtering. A recorded zero can have either origin. The paper describes a 5 N threshold. The linked export code uses 50 N, and all 124 platform traces in the 62 qualified training trials first become nonzero at or above 50 N. [Author processing code](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/importTrialReaction.m) · [C3D corner convention](https://www.c3d.org/HTML/Documents/forceplatformcorners.htm)

The authors synchronized the instruments in Qualisys Track Manager. Their processing fills marker gaps, smooths markers at 6 Hz, smooths plate force at 15 Hz and bandpasses muscle voltage between 30 and 300 Hz after subtracting its trial mean. Their filters run forward and backward. The exporter crops around operator-labelled gait events and forms equal analog margins around their marker times. With a 15-sample block, the middle sample lies seven sample periods from either end. This establishes a stored clock on which to compare measurements. It leaves sensor latency and live prediction unverified. [Marker processing](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/importTrialMarker.m) · [EMG processing](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/importTrialEMG.m)

The source event labels identify the side and type of event in seconds relative to the cropped recording. A complete annotated stance runs from that foot’s strike to its following foot-off before the next same-side strike. A cropped partial stance needs its own treatment. The operator used the vertical force when available and otherwise inferred the event from marker movement. Supplementary Table 2 identifies the plate for a foot in a trial. The contact code alone gives no interval or assurance that later steps landed on that plate. [Article and supplementary methods](https://doi.org/10.1038/s41597-019-0124-4)

## Check one recording

The readers were verified with Python 3.12. Install the reader dependencies if you want to verify the decoded data. The checker compares two implementations on every marker coordinate, residual and scaled analog sample in the selected file. It also checks the sign against force reconstructed from the plate geometry. Replace `selected-trial.c3d` with one of your admitted recordings.

```sh
python -m pip install -r requirements.txt
python check_trial.py selected-trial.c3d
```

The original file counts its first point frame as 1. The ezc3d array starts at index 0. The supplied right-foot helper reads exactly one labelled first right strike and projects two markers onto the assigned platform in the laboratory plane. The markers lie at the back of the heel and the head of the second metatarsal. It uses their recorded coordinates and residual flags. The authors reconstructed missing marker positions before export, so these flags cannot recover the original gap mask. The same helper reads any requested slice of right-leg muscle voltage with a finite-sample flag for each channel. The historical export code marks certain unusably low channels with missing values. [Event export](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/exportEvents.m)

## Attribution

Florent Moissenet and Céline Schreiber released *A multimodal dataset of human gait at different walking speeds established on injury-free adult participants*, version 8, on Figshare under Creative Commons Attribution 4.0. Their associated article credits Céline Schreiber and Florent Moissenet. This package contains independently written source readers, selection rules and verification instructions. It points to the authors’ original files for download. Its whole-trial and foot-specific checks use the authors’ measurements and identify the processing applied here. [Figshare record](https://doi.org/10.6084/m9.figshare.7734767.v8) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Study article](https://doi.org/10.1038/s41597-019-0124-4)
