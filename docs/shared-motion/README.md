# A quarter second ahead

Open **index.html** or the launcher for your operating system. The first example predicts the distance between a wrist’s last tracked position and its position about a quarter second later. Choose **Right-wrist angles (°)** to ask how far back the wrist will bend and how far it will tilt towards the thumb. **Rat displacement (cm)** predicts an endpoint distance on a maze. Each task starts with invented measurements. [Open the viewer](index.html)

## Compare the wrist-angle forecasts

The three rows use the same half-second of invented wrist movement. Read down each column to see how the forecast changes when a separately fitted model also sees forearm electrical activity and then scalp voltages. The first column of numbers gives absolute extension in degrees. The second gives absolute radial deviation, positive towards the thumb. All three aim 128 stored samples beyond the cutoff, a quarter second on the 512-Hz recording clock. The invented example has no measured outcome.

To use measurements you have permission to supply, choose **Enter my own measurements**. **Fill with invented input** shows the exact JSON format. The input panel lists the channel order, units, timing rules and allowed cue slots. Enter only channels actually available, with `motion`, `emg` or `full` as the mode. The viewer compares every supported lower-channel model using that same history. For the distance tasks, the input panel accepts timestamped measured positions in centimetres. Your inputs stay in the tab. **Save offline copy** downloads the complete original examples, model and licences. Each copy starts fresh.

## What happened on measured movements?

In the angle study, five people supplied training data for each forecast method and the sixth supplied its test data. Every person took a turn being held out. Across 1,879 cued right-wrist trials, movement alone gave 4.503° root-mean-square error on the two axes. Adding forearm EMG reduced it to 4.291°, and adding scalp EEG to both gave 4.491°. An earlier wrist-specific convolutional network with a forearm correction scored 3.549° on the same windows. The six people had already contributed to method development. The example runs the final fits trained on all six, which await independent testing. [Wrist-angle study, weights and aggregate scores](https://github.com/eliminatenoise/NeuroTranslation/tree/c60c12e3355b5d2ba3a50364a7f6d294ec59f48e/models/neurotranslate-0.0)

The wrist and rat distance tasks supplied one temporal Transformer core. All three angle models use the same 5,016 fixed temporal values, with a separately fitted input projection and angle readout for each input set. One matched randomly initialized core had a lower error for all three input sets. The angle comparison therefore provides no evidence that training on the distance tasks improved angle forecasting. Forearm and scalp electrical activity can include movement and contact artifacts. These recordings cannot establish intent, force, peripheral nerve signals or causal transmission.

The original distance comparison remains on the page. The group-averaged absolute errors of the shared model were 1.725 cm on six wrist acquisition groups and 1.310 cm on nine later trips by the same rat. Neither task passed its predeclared test for a benefit from the other task’s training data. Select **Recorded maze trip** to compare one separately credited training example with its observed 2.940 cm endpoint distance. This is the only built-in recording-derived example. [Original spatial study](https://github.com/eliminatenoise/NeuroTranslation/tree/1cc81b20a14b81aebfb1f47d13d75b8d79c6e6ce/models/shared-motion)

## Rebuild and embed

The checked-in HTML is self-contained. The standard-library builder needs the unified JS scorer, its illustrative inputs and the two licence texts. From a release checkout with the viewer at `docs/shared-motion/` and the matching runtime at `models/neurotranslate-browser/`, run the command below. For another runtime location, pass `--runtime PATH`. The builder verifies each consumed runtime and data asset against the digests in the source manifest. [Source identities](src/sources.json)

```sh
python -B docs/shared-motion/build.py
```

The viewer can open from a local file or a secure context supporting Web Crypto (including localhost). It runs without dependencies, a server, device access or a network connection. Use one iframe in a host page. Allow script execution, Web Crypto and local downloads in the host’s embedding policy. With stricter host policies, link to the standalone file directly.

```html
<iframe src="./shared-motion/index.html" title="Forecast movement distance or wrist angles"
        style="width:100%; height:48rem; border:0"></iframe>
```

For a game that consumes numbers, use the same scorer as the viewer. Load the runtime once and call `await SharedMotion.forecastMovement(record)`. For a geometry history, supply `{domain,cutoffS,samples}` for `wrist` or `rat`. The result contains `distanceCm` and `unit: "cm"`. The angular input requires the explicit `wrist_angle` domain, mode, slot, cue tick, cutoff tick, sixteen bin end ticks, binned channels and two cutoff angles. Its result contains `angleDeg` in extension and radial-deviation order and `unit: "deg"`. In either case the model forecasts the recorded movement. The game chooses how it presents the forecast.

## Credits and licences

- Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz published the EEG-EMG-WristMotion Dataset v3. We used two measured wrist axes and aligned scalp and forearm voltages to form sixteen-bin histories. Attribution and CC BY 4.0 accompany the data, derived scales, fitted weights and reported results. [Version 3 data](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Study descriptor](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Justin Shin and Shantanu Jadhav published *Single Day W-Track Learning* (2024), version 0.240511.0307. The existing derived illustration uses JS14, session 01, epoch 5, trip 55. Camera measurements supply distances, timing, turn features and an endpoint comparison at the published cutoff. [DANDI dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Original example](https://github.com/eliminatenoise/NeuroTranslation/blob/4d046b86bfa797e28f29cd4f6b8445a1f4b90487/benchmarks/wtrack-neural-motion/fitted/example.json) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Xin Wang and colleagues published *HoloAssist* (ICCV 2023). The original spatial study converted tracked right-wrist positions into centimetres. The full author list and CDLA Permissive 2.0 agreement accompany the viewer. [HoloAssist](https://holoassist.github.io/)
- The fitted weights, comparison weights, scales and numerical results carry CC BY 4.0. NeuroTranslation contributed the angular projections, readouts and comparisons. The project’s original software, documentation and invented inputs carry CC0 1.0. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)
