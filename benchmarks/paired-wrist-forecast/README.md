# Adding forearm muscle signals made this wrist forecast worse

A person sees a target and turns their right wrist to move a cursor towards it. Two angle sensors record how far the wrist bends and how far it tilts sideways. A Transformer, a network that learns which earlier measurements matter to a forecast, used the wrist’s recent path to predict both angles a quarter-second later. **It missed by 5.432° using wrist motion alone. Adding the forearm’s electrical activity increased the error to 5.866°.** An earlier network that looks for short patterns in motion alone did better at **4.053°**.

## Try the fitted models

Open **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh** for the results. The summary opens in a browser and works offline. To calculate a forecast, use Python with NumPy and CPU PyTorch. From this directory run:

```sh
python -B predict.py --input example.json --mode all
```

The example contains invented measurements. The three sets of fitted weights come from recordings of six people. The command prints the future wrist angles in degrees and the model’s estimated variances in degrees squared. Change one set of inputs in a copy of the example to see which predictions move. [Input fields and reproduction](REPRODUCE.md) · [Expected example output](example-predictions.json)

## What the recordings showed

Electrodes on the skin of the forearm pick up electrical activity called surface electromyography (EMG). The scalp electrodes record another set of small voltage changes called electroencephalography (EEG). The same right-wrist movement supplied the voltages and both encoder angles. The visual target marked when to move. This task supplied a cue, with no accompanying speech.

| Earlier measurements and the time since the cue | Transformer | Linear fit |
| --- | ---: | ---: |
| Wrist angles | 5.432° | 6.530° |
| Wrist angles and forearm EMG | 5.866° | 6.174° |
| Wrist angles, forearm EMG and scalp EEG | 5.822° | 6.127° |
| As in the second row, with another trial’s EMG | 5.867° | 6.940° |
| As in the third row, with another trial’s EEG | 5.826° | 6.378° |

The table gives the error in degrees over both axes, with each person counting equally. We square the misses before averaging and take the square root at the end, so large misses count more. Simply repeating the last recorded angle missed by 7.924°. Each linear fit, called a ridge regression, read the same earlier measurements as the Transformer beside it.

Moving EMG from one trial to the next kept the person, wrist history and time after the cue fixed. The linear fit missed by another 0.766° when given the wrong muscle signal. The Transformer’s error moved by just 0.0009°. Adding scalp EEG reduced the Transformer’s error by 0.045°, but swapping another trial's EEG into that model changed the result by only 0.0046°. This fit showed little sensitivity to which movement supplied its electrical signals.

The three people used for evaluation had already appeared in earlier exploratory studies. Leaving out any one of them, EMG still made the Transformer’s error worse by 0.400° to 0.467°. Its nominal 95% ranges with all three inputs contained 89.3% of the measured extension angles and 93.5% of the sideways angles. This comparison covers 959 pointing trials, six forecasts per trial, on a stored recording clock. Instrument delay and performance on new people remain open. [All scores and uncertainty](results.json) · [Study plan](protocol.json)

Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz published the EEG-EMG-WristMotion Dataset, version 3. NeuroTranslation calculated the earlier movement and voltage features, fitted the three experimental Transformers, and compared their forecasts with the measured angles. [Original dataset](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Data descriptor](https://doi.org/10.1038/s41597-026-07287-z) · [Sources and rights](NOTICE.md)
