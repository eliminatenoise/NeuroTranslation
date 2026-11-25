# Finger-angle forecast

[Run online](https://eliminatenoise.github.io/NeuroTranslation/finger-angle-forecast/) · [Download the offline browser model](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/docs/finger-angle-forecast-offline.zip) · [Simple guide](SIMPLE.md) · [Technical guide](TECHNICAL.md) · [Exact errors](RESULTS.json)

The model estimates the change in four finger angles 320 milliseconds ahead. It runs on an invented example or a compatible file in your browser. The offline download includes launchers for Windows, macOS and Linux.

The recorded comparison used 5,532 forecasts per finger across four people who made the same index-finger movement. Each person’s recording was excluded from the fit that predicted it. For the index finger, the angle-only linear forecast averaged 20.78° of error. Adding ultrasound gave 44.38°. Subtracting the first ultrasound reading in each history reduced the combined error to 23.45°. The browser uses a fit on all four people and displays the separate recorded comparison below its example. [Original recordings](https://doi.org/10.5281/zenodo.21825018)
