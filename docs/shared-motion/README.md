# Motion across two recordings

Open **index.html** in a browser and choose a movement history. The same temporal Transformer reads a second of a wrist’s movement or a rat’s movement across a maze. It estimates the straight-line distance between the last observed position and an endpoint sampled about a quarter second later. The answer is a distance in centimetres. [Open the viewer](index.html)

The rat example is the first eligible training window, two seconds into trip 55 of JS14’s W-track session. Choose **Reveal the rat’s measured distance** to compare the model’s estimate with the camera measurement. The wrist example uses invented positions. To try your own past positions, choose **enter samples** for the correct domain. The on-page practice samples demonstrate both input formats. The page verifies the checkpoint and computes all three estimates locally. **Save offline copy** downloads the complete viewer with its original examples.

The shared Transformer had a group-averaged absolute error of 1.725 cm on the wrist and 1.310 cm on the rat. The linear fit on log distance reached 1.922 cm and 1.119 cm respectively. Neither domain met the study’s predeclared transfer criterion. Six wrist recording groups and nine trips from one rat supplied the reused assessment histories. The transfer test, units, sample timing and comparison methods appear below the live forecast. [Study, sources and scores](https://github.com/eliminatenoise/NeuroTranslation/tree/1cc81b20a14b81aebfb1f47d13d75b8d79c6e6ce/models/shared-motion)

## Build from the public repository

Run this from a checkout containing this directory at `docs/shared-motion/` and the browser runtime at `models/shared-motion-browser/`. The builder uses the Python standard library. It takes the published runtime and two licence texts from that directory, checks their SHA-256 digests, and inserts the saved weights, controls, approved example inputs and terms into one HTML file.

```sh
python docs/shared-motion/build.py
```

To use a different location for the same released runtime, pass its directory with `--runtime`. To write to a different file, pass `--out`. This edition’s complete HTML has SHA-256 `1c8eaed7b3f1a595fd202b968993da9eee66845938063746bbb369b054e8e258`.

The curated inputs are included in `src/inputs.json`. To reconstruct them from the scientific release, use Python with NumPy and the original public trip-55 recording. From the repository root, run the command below. It reads the fixed fits and public summary, rebuilds the four intervals and future measurement from the rat recording, and selects the invented wrist fixture. It fits no weights. The public source identities and expected hashes are in `src/sources.json`.

```sh
python -B docs/shared-motion/src/derive.py --out reproduced-inputs.json
```

### Use in another page

Serve the standalone file over HTTPS or localhost, or open the saved file directly. Checkpoint verification uses Web Crypto. A link to the file works without any host-page code. To reuse the panel in a compatible host page, use one iframe with an accessible title.

```html
<iframe src="./shared-motion/index.html" title="Forecast movement distance"
        style="width:100%; height:48rem; border:0"></iframe>
```

The viewer carries its own styles and model. A host with a stricter content-security policy can serve the original file in a compatible document context and link to it. External source links lead to the named research materials when selected.

## Credits and licences

- **Rat data.** Justin Shin and Shantanu Jadhav (2024), *Single Day W-Track Learning*, version 0.240511.0307. The viewer shows derived distances, times and turns for JS14, session 01, epoch 5, trip 55. The original camera positions supplied an observed displacement of 2.940 cm over 0.2403 s. We computed this endpoint and the new forecasts at the earlier public example’s cutoff. [DANDI dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Original example identity](https://github.com/eliminatenoise/NeuroTranslation/blob/4d046b86bfa797e28f29cd4f6b8445a1f4b90487/benchmarks/wtrack-neural-motion/fitted/example.json) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Wrist training data.** Xin Wang and colleagues (2023), *HoloAssist*. The fits use movement features derived from tracked right-wrist positions, converted from metres to centimetres. The human examples built into this viewer are invented. The full author list and CDLA Permissive 2.0 text travel with the HTML. [Publisher](https://holoassist.github.io/) · [Data credits](../../models/shared-motion/shared-motion-data/NOTICE.md)
- **Model and viewer.** NeuroTranslate’s jointly fitted weights, fitted comparison weights and numeric summaries carry CC BY 4.0. The browser scorer packs the shared checkpoint’s original 5,234 float32 values. The viewer exports the standardization parameters and log-distance coefficients of the two domain-specific ridge fits. Original code, documentation and invented examples carry CC0 1.0. [Rights notice](../../models/shared-motion/shared-motion-model/NOTICE.md) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)
