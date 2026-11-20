# Can six scalp electrodes improve an arm forecast?

A screen asks a person to bend the elbow. The model sees the instruction and the elbow, forearm and finger readings available a quarter of a second later. Give it the scalp recording as well. Does it come any closer to the movement that follows?

The forecast has nine numbers. Each gives the predicted *change* from the last observed movement bin, for one instrument and one time ahead. The instruments record elbow angle, forearm rotation and a glove reading on the index finger. The file leaves their units blank. The three times are 0.5, 1 and 1.5 seconds after the cutoff. A negative value means the stored reading is predicted to fall. The same sign need not have the same anatomical meaning for every participant.

On the five assessment runs the error was **0.50856** with scalp input and **0.50853** with only the cue and movement history. The typical training response for each cue scored **0.49278**. Lower is closer. [Results and controls](RESULTS.md)

## Try an invented example

Extract the entire package and open the launcher for your operating system. On Linux, run `./Launch-Linux.sh`. On macOS, open `Launch-macOS.command` in Terminal. On Windows, open `Launch-Windows.cmd`. The launchers use an installed Node.js runtime or Python 3 with NumPy. A terminal prints three rows, one time per row, with the three instruments in the order above. The inputs in `example.json` are invented. The fitted weights come from recordings. The model runs offline.

To change the example, copy the JSON, edit a signal bin or select another instruction, then give its path to a launcher or to either command below. Every signal uses four bins in chronological order. Each history bin has three instrument medians followed by their three within-bin changes. Each scalp bin holds FC3, FC4, C3, C4, CP3 and CP4. Each eye bin holds acquisition channels 62, 63 and 64. The files leave electrical units blank too. The forecast is illustrative outside the recorded task.

```sh
node run-example.cjs example.json
python predict.py example.json
```

The default method, `scalp`, uses the cue, mechanics and six scalp signals. Use `history` for cue and mechanics, `eye` to add the three eye channels to those inputs, or `scalp_eye` to include all four sources. `scalp_only` and `eye_only` ignore the instruction and all movement history. `cue_median` needs just the instruction. Supply the inputs used by the method you choose. The forecast can also be called from JavaScript as `EarlyScalpArm.predict(model, request)`. [Model and scoring rules](PROTOCOL.md)

## Reproduce the study

Obtain the checksum-verified originals using the source guide. Fitting needs NumPy and PyTorch. Python and NumPy alone can score an existing full freeze. The original fit used Python 3.14, NumPy 2.5.3, PyTorch 2.14 and four CPU computation threads. Open a terminal in the extracted folder. Substitute your local recordings directory and two new output directories. The fitting command reconstructs the original trial windows, fits the seven development folds, fits all seven people together, and writes the complete frozen model and source identities.

```sh
python study.py train arm-recordings my-fit my-folds --threads 4
```

The terminal prints a SHA-256 fingerprint. Retain it before opening the fourth runs. Use the completed fit folder and its own fingerprint to score S8–S12 run 4. Project the resulting comparisons to a shareable file. The public reports include each person's paired difference independently sorted within a comparison. They omit identifiers that would join one person's different movement-error profiles together.

```sh
python study.py assess arm-recordings my-fit/freeze.json YOUR_RETAINED_SHA256 my-assessment.json
python project_report.py my-assessment.json my-assessment-summary.json --freeze my-fit/freeze.json
```

To score the shipped weights directly, run the following command with the five original fourth runs. It verifies the recorded code and model fingerprints before opening a recording and writes a cohort-only report. No training installation is needed.

```sh
python assess_released.py arm-recordings my-released-assessment.json
```

The distributed freeze has a detached Ed25519 signature. The signed record identifies the original program, coefficients, detailed fitting output and seven fold checkpoints. The companion public reports summarize the underlying outputs and retain their SHA-256 fingerprints. The original study freeze is `619c8bef297757cebe5acfbe47647d6c017f56a8a56b14bdcd42db3bd724cf33`.

```sh
openssl pkeyutl -verify -pubin -inkey freeze-public.pem -rawin -in freeze.json -sigfile freeze.sig
```

The recordings are from Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz (2017). This analysis adds the clocked comparison, trained weights, controls, numerical results, example and offline prediction implementations. The data-derived weights and results use CC BY 4.0. The analysis code and invented example use CC0. [Source and acquisition](SOURCE.md) · [Original data](https://doi.org/10.5281/zenodo.834976) · [Data license](CC-BY-4.0.txt) · [Code dedication](CC0.txt)
