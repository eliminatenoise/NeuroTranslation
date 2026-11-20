# One movement model, two tasks

Extract the complete ZIP and open the launcher for Windows, macOS or Linux. You can also open **index.html** in a browser with JavaScript. The fitted models, invented histories, group results and controls work without a server or network connection. The paper, atlas and source links open online.

Choose grasp and lift to follow a wrist marker, or balance to follow the sacrum. The two examples are independent. The solid green forecast comes from a temporal Transformer trained on both studies. The comparison uses a model trained on just the selected task, or a rule you can calculate directly from the history. The exposure-matched specialist saw the same number of training draws from that task as the shared model. The total-update specialist spent all of the shared model’s update budget on that task.

Under **Forecast comparison**, choose **Body part vs. time**. The green line comes from a model that chooses how to turn its internal signal into a path according to the body part. The orange line comes from a model that blends two output maps as time passes. Both have 3,975 fitted numbers. The reader uses the first of three training splits and a fixed starting seed (1641). The group comparison averages errors across all three seeds and holds each person out of training in turn. [Read the output-map study](https://eliminatenoise.github.io/NeuroTranslation/papers/cross-limb-movement/decoder-study/)

Each history contains 625 ms of signed muscle readings. The electrical trace and marker path use the same time axis relative to the cutoff. In **Edit the invented history**, change one full voltage channel or one coordinate at a time and apply the samples. The arm example permits three, four or five usable muscle channels. The balance example requires all eight. The first wrist marker sample brackets the start of the history at −626 ms. The model takes only the most recent position available when each input bin ends.

Move the time slider to read any of the 32 future marker positions. Open the numerical table for all three coordinates and each muscle’s predicted root-mean-square amplitude (RMS). In the three simple movement rules, the muscle forecast repeats its previous 125 ms RMS. A masked electrode has no forecast. The other task’s electrodes were never present. These invented examples have no measured future. The error tables come from the original recordings and report their own denominators.

The wrist study’s muscle signal keeps its original amplitude units. The balance signal uses microvolts. Both marker paths use millimetres in the coordinate frame of the selected study. Comparing the two studies cannot identify a single person’s coordinated arm and leg movement.

[Source and licence](NOTICE.md) · [File checksums](SHA256SUMS)
