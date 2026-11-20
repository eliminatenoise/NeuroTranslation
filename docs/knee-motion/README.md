# Where will each knee be?

Open **index.html**, or use the launcher for your operating system. Five samples from the right and left hips, knees and ankles give the model a short history of a step. It estimates both knee angles 15 stored frames beyond the last sample. The browser runs the fitted transformer and two fitted linear models alongside two simple rules. Change **Forecast to plot** to compare their endpoints. The two plots share a degree scale. The diamonds mark predictions at one frame.

The opening example is invented. For the recorded comparison, download the study’s 3.92 GB IMU archive and extract `IMU_S41_0.5/Joint_Angles_ZXY.csv`. Choose that CSV using **Open a local angle file**. The viewer verifies its SHA-256 fingerprint, selects the earliest complete window and shows the actual input and target frame numbers. Move **Input cutoff** with the arrow keys. **Reveal recorded angles** compares the prediction with the file’s later knee readings. The other eleven admitted held-out CSVs at 0.5 m/s work the same way. A local file stays in browser memory. **Save offline copy** downloads a standalone HTML page, with the fitted model and invented example. [Study files and citation](https://physionet.org/content/multimodal-gait-dataset/1.0.0/)

Under **Which files can I open?**, download the sample JSON to try another five-row history. Frame offsets from cutoff are −24, −18, −12, −6 and 0. Columns are right hip, left hip, right knee, left knee, right ankle and left ankle in degrees. The Xsens export labels the hips and knees by flexion/extension and the ankles by dorsiflexion/plantarflexion. Keep the signs, column order and frame spacing. The only required key is `history_degrees`. The optional `feature_order` and `frames_before_cutoff` must match the template. Optional `origin` supplies a description. The page never treats a user-supplied JSON endpoint as a verified measurement.

## What the comparison means

Katmah and colleagues recorded adults walking on a treadmill. A model fitted with 39 people estimated future knee angles on 12 other people at 0.5 m/s. Each person counts equally. On the five input frames, the transformer's mean absolute error was 4.47° and the all-joint linear model's was 5.60°. On windows long enough to use four seconds of knee history, replaying an earlier stride did better than the short-history transformer, 3.54° against 4.46°. The example window was fixed by participant order and frame continuity, independently of forecast error. Consecutive windows overlap. The test covers one speed and these participants.

The reference is an angle reconstructed from wearable inertial sensors. All 51 files report 60 Hz. Six used Xsens HD whole-file processing and 45 carry a “Live” label. A future stored frame is separate from the five inputs, although later raw observations may already have contributed to the vendor's reconstruction. Live prediction latency, independent joint-angle ground truth and synchronization to brain or muscle electrical signals remain unverified. The viewer estimates angles from recordings. It cannot drive a limb. [Xsens manual, HD reprocessing](https://www.xsens.com/hubfs/User_Manual_Xsens%202025.pdf) · [Model, study and limitations](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/knee-motion)

## Rebuild

Python 3's standard library is sufficient. From this folder in the repository run `python -B build.py --model ../../models/knee-motion`. The build checks the hashes in `src/inputs.sha256.json`. It incorporates the frozen model parameters, invented input, aggregate study scores and held-member identifiers. Its only output is `index.html`. A copied standalone HTML file works without a web server, installation or network access.

## Credits

Rateb Katmah, Aamna AlShehhi, Doua Kosaji, Nour Al-Rahmani, Muhammad Abdullah, Abdul Aziz Vaqar Hulleck and Kinda Khalaf (2026). *A multimodal gait dataset of brain activity, muscle activity, kinematics and ground forces in young adults*. PhysioNet, version 1.0.0. The forecast, aggregate comparison and viewer are derived work. The PhysioNet material retains its CC BY 4.0 license. No participant angle trace is bundled. [Dataset](https://doi.org/10.13026/r0ea-7161) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The original viewer code is distributed under CC0 1.0. The source-derived results retain the dataset attribution above. [CC0 dedication](LICENSE) · [PhysioNet platform paper, Pollard et al. (2026)](https://doi.org/10.1038/s44360-026-00096-z)
