# Hand movement from identified electrodes

[Simple edition](SIMPLE.md) · [Technical edition](TECHNICAL.md) · [Aggregate measurements](results.json)

These experimental NeuroTranslate checkpoints take 200 milliseconds of recorded electrode activity and estimate how far and in which direction a hand moves over the next 100 milliseconds. On the held recording, keeping the electrode numbers gave 4.65 mm of ending-position error. The model that guessed no movement gave 9.23 mm of error. On the development recording, the no-movement forecast gave the lowest ending-position error.

The download contains three fitted models and runs a generated example. All measurements come from one animal recorded on separate days. The example uses invented counts. The original recordings are available through the cited public archive. See either edition for installation instructions and the format for supplying recorded counts.
