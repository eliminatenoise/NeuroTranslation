# Can three people’s pinches help forecast a fourth person’s grip?

The gauge measures the force between two finger pads. A target rises to 50% of that person’s maximum voluntary contraction (MVC), holds, then falls. If the hand tracks the rising and falling cue differently, should a forecast change by the same amount in both directions?

## Try it

Extract the whole **CEMHSEY-Population-Forecasts.zip** and open the launcher for your operating system. You can also open **index.html** in a current Chromium-based browser. The reader uses local JavaScript, Web Crypto, a worker and the browser’s deflate decoder. The reader works offline. External links need an internet connection.

Choose **Run invented example**. The reader fits a shared correction on six invented trials from three people and forecasts one trial from a fourth invented person. The signals and original model weights in this example are invented. Move the issue-time slider with the arrow keys. Choose a forecast, read its value in the cutoff table, then reveal the gauge. **Score this repeat** compares every forecast at all 592 issue times. Select a phase to see when the errors grew or shrank. The scores describe just the repeat you opened.

## Use your own archive files

1. Choose **Local archive files** and select your compatible four-model 30% array-reader JSON. Keep the exact file for later. The browser checks the protocol, layout and numeric fields. The origin displayed for an external parent model is the file’s own claim. Check source and training membership against your original records. You can prepare a compatible model using the [30% array-reader fitting tool](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-arrays/fit/).
2. Enter the three participant numbers used to train the parent models. Choose both day-one repeats for each of three other people. All six recordings must be session 5, task 3, 50% MVC. Check the source labels, then choose **Fit six calibration trials**. The reader opens one file at a time and keeps the accumulated sums after each trial.
3. Choose **one test recording** at the same day, session and target from a person outside both groups. Either repeat works. Choose **Forecast the test trial**. The two models trained at 30% and all nine new gains stay fixed throughout the test. A different test file clears the previous forecast and score.
4. To reuse a correction in a fresh tab, choose **Save correction** and **Show key**. Keep the 32-character key separately. Select the same source and the byte-identical parent file, confirm its original training roster, then supply the key and saved JSON and choose **Reopen correction**. You can open a test recording immediately. There is no need to load the six calibration files again. Invented corrections reopen with the bundled invented source and parent.

Use original MATLAB Level 5 names such as `S4_Day1_Session5_Task3_Trial2.mat`. The reader rejects ambiguous names. If files were renamed, consult their originals. Each recording needs a real double 320 × 61,500 `data_sEMG` matrix, a row of at least 6,000 normalized `data_force` samples, and a positive scalar `MVC`. Force is already expressed as a fraction of daily MVC. Surface electromyography (EMG) measures muscle electrical activity through the skin.

The reader checks claimed participant identities and compares fingerprints of the decoded force and RMS inputs. It also uses parent-training packet fingerprints when supplied. Filenames and model labels cannot prove the identity of a person, and a fingerprint cannot detect every partial overlap. The saved correction contains nine unencrypted gains, the parent fingerprint, the protocol and keyed participant and recording checks. Keep it private. Anyone with the key and file can test candidate participant numbers. No raw recordings or participant numbers are saved in the profile. Reloading clears the browser’s in-memory selections. Downloaded files stay on your device.

## Eleven forecasts, one gauge

Predict 24 ticks ahead on the nominal 200 Hz clock, at ticks 60, 70, …, 5970. That gives a nominal 120 ms lead. The release indices alone do not measure physical synchronization or device latency. The controls are the last gauge reading and the scheduled target at the future tick.

Let *u* be the change in the **unit-height** scheduled cue over those 24 ticks. The simple parent takes the last force reading and adds 0.50 × *u*. The other parents use the original 30% force-history and five-grid forecasts, each adjusted by (0.50 − 0.30) × *u*. The five-grid parent adds forearm EMG amplitude and spatial contrasts. All inputs come from signals available by the issue time. The five-grid comparison changes both the force modelling and EMG inputs relative to the simple parent.

For each parent compare its unchanged forecast with two corrections. One uses the same gain throughout. The other uses one gain when *u* is positive and another when *u* is negative. Fit each gain by summing *u* × (future gauge − parent) across its calibration issues and dividing by the corresponding sum of *u*². Where the cue stays flat, neither correction changes the parent. The sign comes from the scheduled target, even when measured gauge force happens to move the other way.

Each of the three calibration people contributes both repeats and each repeat contributes 592 issues. A test participant supplies no personal practice for this fit. The separate measured study combines two test repeats per person and then averages its participant-level errors equally. Its evaluation participants had appeared on other recordings in earlier programme work. The browser’s single-repeat scores answer the narrower question about the selected recording.

[Measured study and aggregate results](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-phase/) · [CEMHSEY GRASP recording study and data access](https://doi.org/10.1038/s41597-025-05733-y)

Base reader revision `41d573cd908561a893d73c961d8a38a7e5e7cdac`. Population study protocol SHA-256 `e8d7cd2cb14e5546d42a07ea38aed134b456ab75a284e7e12bd3b5a09dbf8640`. Shared glossary revision 36, SHA-256 `40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406`.
