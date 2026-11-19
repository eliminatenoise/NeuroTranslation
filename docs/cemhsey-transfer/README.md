# Practice a different pinch

Can yesterday’s practice help with today’s pinch? Try it on an invented example, or open your own compatible CEMHSEY recording locally. The bundled force, electrode signals and parent model weights are invented.

Extract the whole ZIP, then open the launcher for Windows, macOS or Linux. You can also open `index.html` directly in a current Chromium-based browser. The reader runs offline. It uses Web Crypto for file checks and the browser’s deflate decoder for compressed MATLAB files.

## Start with one day

Pick 10%, 30% or 50% of maximum voluntary contraction (MVC). Move the cutoff in the second repeat. The reader forecasts the gauge 120 nominal milliseconds ahead using three simple controls and two models, each with frozen and target-adjusted forecasts. Fit on the first repeat to add one correction per model. The table now has nine forecasts. Reveal a gauge reading, or choose **Score repeat 2** for errors across all 592 cutoffs.

## Carry one practice pinch into the next day

1. Choose **Day 9 · earlier practice** in the invented example. For your own recordings, choose the target and open day 9 repeat 1 in the practice slot. That file alone supplies both corrections.
2. Choose **Fit on repeat 1**. Open **Compare day 9 practice with day 10 practice** and select **Keep day 9 fit in this tab**.
3. Switch the example to **Day 10 · comparison**. With local files, remove either remaining day 9 file and open day 10 repeats 1 and 2 for the same participant and target. Fit on repeat 1 again. This second fit belongs to day 10.
4. Choose **Compare both practice days**. Follow day 9 practice and day 10 practice for each parent in the plot, the point table or the whole-trial score table. All eleven forecasts face the same reading on day 10 repeat 2. The gauge is normalized against the maximum for its own day. A given fraction of MVC can represent a different physical force on the two days.

Seven forecasts use neither practice repeat. The two day 9 forecasts and the two day 10 forecasts each add a fitted coefficient times the upcoming change in the scheduled cue. The two practice days are never pooled. The reader uses every cutoff of the relevant first repeat. At 30% the target adjustment is exactly zero. Either practice fit can still change the forecast where the cue rises or falls.

## Reopen a private fit

To carry a fit into a fresh tab, choose **Save private fit to file** after keeping it on day 9. Under **Reopen a saved fit or view its private key**, show the key and keep it somewhere separate from the file. In a fresh tab choose the same target, source type and exact parent model, then open the saved practice-fit JSON and enter its key. Load and fit day 10 as above. The private key is required for reuse. Closing or reloading the reader clears its in-memory selections. The **Forget earlier fit and key** button also clears them for the earlier day. Saved downloads remain on your device.

The JSON contains two unrounded fitted numbers, the indexed day, repeat and target, the protocol and parent-file fingerprints, and keyed checks for the participant, decoded recording and file contents. It omits raw signals, participant numbers, filenames and the private key. A fresh random 128-bit key is generated each time you keep a day 9 fit. Keys and profiles are never sent by this reader. The file is not encrypted. Anyone with the file can read the coefficients. Someone with both the key and file can test possible participant numbers against it. Keep both private.

## Open local recordings

Use adult CEMHSEY GRASP pad-to-pad pinch, Session 5. Tasks 1, 2 and 3 prescribe 10%, 30% and 50% MVC, respectively. Use compatible MATLAB Level 5 originals with normalized `data_force`, a 320 × 61,500 double `data_sEMG` matrix and positive scalar `MVC`. The recorded gauge gives one normalized force between the digits. The surface electrodes record electrical activity through the skin.

Each archive name describes an expected participant, day, task and repeat. The MAT contents cannot verify those identities. If you renamed the files, check the originals, enter the participant’s archive number and day, and confirm each assigned repeat role. Known conflicting names or repeated decoded signals block the comparison. Fingerprints distinguish exact decoded force and RMS inputs. They cannot identify all related or partly overlapping source recordings.

To use a different parent fit, open a compatible four-model JSON from the [30% array reader](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/fit/). The origin label for imported weights is reported by the file. Check the training sources yourself before using an imported parent on local recordings. When training fingerprints are present the reader also checks for exact training reuse. A change in model or target clears both practice fits. Use the identical parent file to reopen a saved profile.

Scores describe the selected second repeat. The gauge lead uses nominal release indices. The measured studies report separate results across four people. [Single-day measured study](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-transfer/results/) · [Two-day measured study](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-carry/) · [CEMHSEY GRASP recording study and data access](https://doi.org/10.1038/s41597-025-05733-y)

This reader extends the transfer reader at NeuroTranslation revision `ab12fccc18709c3d56227984a410809957959228`. Its two-day protocol has SHA-256 `38c0551d464f5bbc3d2c4e8a712dfb47fe2f212f7527428c3ec829ad772eac71`. Shared Brain2Body glossary revision 36, SHA-256 `40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406`.
