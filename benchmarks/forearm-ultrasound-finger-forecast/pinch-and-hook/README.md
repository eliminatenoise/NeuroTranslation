# Finger forecasts during a pinch or hook

Run a forecast 320 milliseconds ahead from four seconds of finger angles. Compare the result of holding the last angle, replaying an earlier movement, or using a fitted model. The page accepts local files and runs offline. [Open the forecast](https://eliminatenoise.github.io/NeuroTranslation/finger-angle-forecast/gesture-replay/) · [Download the offline package](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/docs/finger-angle-forecast-offline.zip)

In 24 recordings from four people, replaying a similar movement averaged **4.03°** of error across four fingers. The angle-only linear model averaged **5.67°** and holding the last angle averaged **6.70°**. Holding the last angle led at the fastest recorded speed for both gestures. The browser examples use separate models fitted on all 40 development recordings. [Simple guide](SIMPLE.md) · [Technical guide](TECHNICAL.md) · [Aggregate scores](RESULTS.json)

The native checkpoint includes the calibration, three linear fits, six recurrent weight files and a Python runner. Run `python predict.py --example` from its folder after installing its listed packages. [Native checkpoint](checkpoint/)

Keshav Bimbraw published the original forearm ultrasound and finger-angle recordings under CC BY 4.0. [Source recordings](https://doi.org/10.5281/zenodo.21825018) · [Recording methods](https://doi.org/10.1109/TMRB.2023.3237774)
