# A quarter second ahead

Open **index.html** or the launcher for your operating system. The first example predicts the distance between a wrist’s last tracked position and its position about a quarter second later. Choose **Right-wrist angles (°)** to ask how far back the wrist will bend and how far it will tilt towards the thumb. **Rat displacement (cm)** predicts an endpoint distance on a maze. **Right and left knee angles (°)** forecasts both knees from 240 consecutive pairs of angles. Each task starts with an invented example. [Open the viewer](index.html)

## Forecast a walking step

Choose **Right and left knee angles (°)**. The earlier frames let the model look for the last second of the walk in a previous stride. Choose one of four methods to see where it places each knee a quarter second later. The built-in waves illustrate the format. For a recording, choose **Enter my own measurements**, supply 240 consecutive frames from one 60 Hz walk and put each right/left angle pair in degrees in `kneeDeg`. Your inputs stay in the tab.

The fitted shared model averaged 3.465° absolute error on 12 previously studied people walking at 0.5 m/s. The earlier-angle fit scored 3.460°, the shuffled-weight comparison scored 3.422° and repeating the stride scored 3.535°. The trained features did not beat both fitted alternatives. [Source and requested citations](https://doi.org/10.13026/r0ea-7161)

## Compare the wrist-angle forecasts

How far back will the wrist bend? How far will it tilt towards the thumb? Each row gives those two angles in degrees, 128 stored samples beyond the cutoff. That is a quarter second on the 512-Hz recording clock. The invented example has no measured outcome.

The first table shows three direct forecasts. Each fitted model takes the previous half-second of movement. The second also sees electrical activity at the forearm and the third sees the scalp voltages as well. The second table begins with the same movement-only forecast for both rows. One correction adjusts it using wrist movement. The other correction also sees the forearm signals. Reading down a column shows what changes when an adjustment has access to the electrodes.

Choose **Invented forearm example** to run the two corrections on the six-channel example supplied with the model. It contains wrist angles and four forearm channels. The forearm correction estimates 18.970° of extension and −2.058° of radial deviation at tick 1640. Negative radial deviation points away from the thumb. No person supplied the example.

To use measurements you have permission to supply, choose **Enter my own measurements**. **Fill with invented input** shows the exact JSON format. The input panel lists the channel order, units, timing rules and allowed cue slots. Enter only channels actually available, with `motion`, `emg` or `full` as the mode. The viewer compares every supported lower-channel model using that same history. For the distance tasks, the input panel accepts timestamped measured positions in centimetres. Your inputs stay in the tab. **Save offline copy** downloads the complete original examples, model and licences. Each copy starts fresh.

## What happened on measured movements?

Six previously studied people steered a cursor using their right wrist. Five supplied training data and the sixth supplied the test data, with every person taking a turn as the test case. Across 1,879 cued trials, the shared model’s direct forecasts had two-axis root-mean-square errors of 4.503° for wrist movement, 4.291° with forearm muscle activity (EMG) and 4.491° with scalp voltage (EEG) added as well. Each person counts equally. [Wrist-angle study, weights and aggregate scores](https://github.com/eliminatenoise/NeuroTranslation/tree/c60c12e3355b5d2ba3a50364a7f6d294ec59f48e/models/neurotranslate-0.0)

Start both corrections with the shared Transformer’s movement-only forecast. On the same windows the motion-only correction scored 4.175°. Giving the correction the forearm signals brought the error down to 4.054°. Four of the six people improved. The viewer runs final weights fitted using all six. Accuracy on new people remains unknown. [Forearm correction study](https://github.com/eliminatenoise/NeuroTranslation/tree/c8dfb5e641a4832a965f83469b3c38a601bfdb99/models/neurotranslate-0.0/forearm)

A separate wrist-specific convolutional network (CNN) learns short patterns in wrist movement. With its forearm correction it scored 3.549° on the same windows. That model runs in Python. The download contains the final fit from all six people, whose error on a new person has yet to be measured. [Download the wrist-specific Python model (ZIP)](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/c8dfb5e641a4832a965f83469b3c38a601bfdb99/models/wrist-specialist.zip)

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

To read the numbers directly, load the runtime once and call `await SharedMotion.forecastMovement(record)`. For a geometry history, supply `{domain,cutoffS,samples}` for `wrist` or `rat`. The result contains `distanceCm` and `unit: "cm"`. The angular input requires the explicit `wrist_angle` domain, mode, slot, cue tick, cutoff tick, sixteen bin end ticks, binned channels and two cutoff angles. Its result contains `angleDeg` in extension and radial-deviation order and `unit: "deg"`. To run a correction, set both `forearmResidual` and `mode` to `motion` for two columns or `emg` for six. Omit `forearmResidual` to run the original direct forecast.

## Credits and licences

- Rateb Katmah, Aamna AlShehhi, Doua Kosaji, Nour Al-Rahmani, Muhammad Abdullah, Abdul Aziz Vaqar Hulleck and Kinda Khalaf (2026), *A multimodal gait dataset of brain activity, muscle activity, kinematics and ground forces in young adults*, version 1.0.0, PhysioNet. NeuroTranslation used the reconstructed right and left knee angles from the 0.5 m/s walk to fit three corrections to a prior-stride forecast. Retain the original credit and CC BY 4.0 terms for the source, derived model parameters and numerical results. The example contains invented waves. [Source and requested citations](https://doi.org/10.13026/r0ea-7161) · [PhysioNet platform paper](https://doi.org/10.1038/s44360-026-00096-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz published the EEG-EMG-WristMotion Dataset v3. We used two measured wrist axes and aligned scalp and forearm voltages to form sixteen-bin histories. Attribution and CC BY 4.0 accompany the data, derived scales, fitted weights and reported results. [Version 3 data](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Study descriptor](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Justin Shin and Shantanu Jadhav published *Single Day W-Track Learning* (2024), version 0.240511.0307. The existing derived illustration uses JS14, session 01, epoch 5, trip 55. Camera measurements supply distances, timing, turn features and an endpoint comparison at the published cutoff. [DANDI dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Original example](https://github.com/eliminatenoise/NeuroTranslation/blob/4d046b86bfa797e28f29cd4f6b8445a1f4b90487/benchmarks/wtrack-neural-motion/fitted/example.json) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Xin Wang and colleagues published *HoloAssist* (ICCV 2023). The original spatial study converted tracked right-wrist positions into centimetres. The full author list and CDLA Permissive 2.0 agreement accompany the viewer. [HoloAssist](https://holoassist.github.io/)
- The fitted weights, comparison weights, scales and numerical results carry CC BY 4.0. NeuroTranslation contributed the angular projections, readouts and comparisons. The project’s original software, documentation and invented inputs carry CC0 1.0. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)

## Population firing on the track

The same runtime also reads four intervals of camera movement and CA1/prefrontal spike counts. Both its correctly timed predictions and an earlier-trip comparison run in the [population recording viewer](https://eliminatenoise.github.io/NeuroTranslation/population-motion/). This page keeps the earlier distance and wrist-angle examples.
