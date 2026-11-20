# Muscle and knee rhythm

Open `index.html` or the launcher for Windows, macOS or Linux. Choose one of 11 treadmill walks at 0.5 m/s. For that walk, the page shows the strongest repeating rates in 12 surface muscle amplitude channels and two inertial-sensor knee angle estimates. Both numbers are unilateral cycles per minute. They describe how often a pattern repeats. Matching rates cannot identify which burst of muscle activity accompanied a particular knee bend.

The earlier cohort supplies a fixed median knee rate across 38 other people. A separate control takes the muscle rate from the next held-out study ID with a valid recording, wrapping to the first ID after the last. The same-person muscle rate had a mean absolute difference of 0.027 cycles/min across the 11 walks, compared with 2.550 for the cohort median and 3.055 for the other person. The frequency grid advances by 0.15 cycles/min. At 40 seconds, the natural frequency scale is about 1.5 cycles/min. These figures measure the spacing between estimated spectral peaks. Biological step counts, onset timing and coordination remain unverified.

## Calculate the spectra from original files

Download the selected walk's muscle CSV and the study’s IMU archive (3.92 GB) using the links on the page. For S41, for instance, choose `EMG_S41_0.5.csv` in the first picker and the extracted `IMU_S41_0.5/Joint_Angles_ZXY.csv` in the second. A byte-for-byte SHA-256 check binds each file to its instrument and the selected walk. Renaming a file preserves the original bytes. Resaving a CSV may change them. The page sends no files over the network. A recent browser with Web Crypto and Web Workers is required to verify and read originals. No server is needed for the standalone HTML.

Each instrument supplies its own 40-second interval, starting five seconds after its first available row. EMG uses the source time in seconds and the mean absolute voltage. Knee angle uses consecutive frames at 60 Hz and degrees. Each channel is centered, tapered and projected onto the frequency grid at the observed sample times. Its power is divided by the total in-band power before channels are averaged. The first strongest bin is the peak. The page checks the peak rates and sample counts against the public study. Raw observations and personal metadata are absent from the package. [Protocol, analysis and per-walk results](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/gait-rhythm)

## Rebuild

In a repository checkout, run `python docs/gait-rhythm/build.py`. The builder uses Python’s standard library and verifies the source study hashes before rendering. With another study directory, run `python build.py --model /path/to/models/gait-rhythm --out rebuilt.html`. The standalone HTML can be copied away from the checkout.

## Attribution

Derived peak rates and local spectrum visualization from Katmah, R., AlShehhi, A., Kosaji, D., Al-Rahmani, N., Abdullah, M., Hulleck, A. A. V., and Khalaf, K. (2026), *A multimodal gait dataset of brain activity, muscle activity, kinematics and ground forces in young adults*, version 1.0.0. The original recordings are available separately. [PhysioNet dataset](https://physionet.org/content/multimodal-gait-dataset/1.0.0/) · [Dataset licence, CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

PhysioNet platform citation: Pollard et al. (2026), *PhysioNet as a global platform for biomedical research*, Nature Health. [Platform paper](https://doi.org/10.1038/s44360-026-00096-z)

The derived study rates retain the dataset's CC BY 4.0 attribution. Original viewer code and text use [CC0](LICENSE).
