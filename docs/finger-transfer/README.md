# Finger movement across people

A screen names one finger. A glove independently measures all five. Across five development recordings, a table that knew the cue and the time made the smallest average error. The models that read brain activity did slightly better with the correct electrical recording than with a preceding trial’s signal, yet neither passed the predeclared transfer test.

## Open the experiment

Open `index.html` in a recent browser or use the launcher for Windows, macOS or Linux. The page contains all the weights, instructions, results and license texts. It works offline from an extracted folder or by itself. It needs no account, file upload, local server, Python installation or network request. External source links are optional.

Change the named finger, switch to the following blank screen, or move the time slider. Pick a brain area and change either rhythm. Open **Which areas have electrodes?** and remove the area you selected. The two band inputs turn to zero and the region changes from present to absent. Choose **Cue only** to feed only the finger and clock to the two trained decoders. The lookup table always uses the finger and clock. The numeric table under the bars gives all 15 estimates.

The synthetic inputs start after contact calibration and regional pooling. For the selected area the four successive band values are one quarter, one half, three quarters and all of the requested strength. Other known areas have zero centered band values. Availability is an independent input. Each input window ends 120, 80, 40 or 0 ms before the cutoff. The cue basis uses the actual time of each of those four windows within the invented phase. The table uses the current phase and exact cutoff tick. The five outputs are unsigned average changes over three steps between four future glove samples, 40, 80, 120 and 160 ms after the cutoff. Choosing invented counts multiplies the calibration-unit estimates by illustrative thumb-to-little gains of 12, 20, 15, 16 and 10.

## Read the recorded results

The interactive estimates use a separate deployment fit trained on all five people. To see how well the models did on a different person, open **See the results**. The early 80 seconds of each person's electrode and glove recordings calibrated that person's scales. Following an eight-second gap, the scored person contributed no training examples to that fold. The four other people provided training examples. Choose a test person to see who taught the model, which regions had contacts, and the gains from using the right recording.

The five folds supplied 246 scored trials and 56 disjoint comparisons between repeats of the same cue. Each person counted equally. The cue-and-clock table scored 0.4770 mean absolute error, the cue-plus-cortex ridge fit 0.5011 and the cue-plus-cortex Transformer 0.5134, in personal calibration units. In all five people, predicting zero change between repeats beat either combined decoder. The five-person transfer criterion failed for both models. These results describe development recordings with subject-specific calibration. Individual hardware timing, joint angles and physical actuation remain untested. [Stanford collection](https://purl.stanford.edu/zk881ps0522) · [Original experiment](https://doi.org/10.1371/journal.pcbi.1002655)

## Rebuild

The page is generated from checked source code, seven public fitted parameter files, published summaries and notices. The input manifest pins each source artifact by SHA-256. From `docs/finger-transfer/`, run the following command with Python 3 and NumPy installed.

```sh
python -B build.py
```

The default model directory is `../../models/finger-transfer/`. For another layout, use `--model PATH`. Use `--out PATH` to preserve the original HTML during comparison. The builder uses neither original recordings nor private calibration arrays. With CPU PyTorch and Node.js also installed, run `python -B verify.py` to compare every cue, phase and timing cell against the released Python implementation. It recreates 340 invented packets, checks all 85 inputs at all four times and compares all seven readouts. The complete companion file checksums are in `SHA256SUMS`. [Attribution, original ethics statement and privacy terms](RIGHTS.md)
