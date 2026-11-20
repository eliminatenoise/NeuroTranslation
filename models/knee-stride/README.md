# Forecasting both knees from the previous stride

Where will each knee be a quarter of a second from now? On a treadmill, look back one stride. A person rarely takes exactly the same step twice. This experiment asks whether a learned correction can predict some of that difference.

All three forecasts start with four seconds of the same right and left knee angles. The stride rule finds the earlier part of the recording that most closely matches the last second of movement. It copies the angles 15 frames farther into that earlier stride. Ridge regression and a small Transformer each estimate how far to adjust that answer. The prediction is a pair of angles in degrees.

## What happened on the recordings?

The models learned from 39 people. We returned to 12 other people who had already been studied using an earlier predictor. Across their 40,201 overlapping cutoffs, the Transformer gave the lowest average error for every participant. Each person counts equally in the table.

| Forecast | Both knees | Right knee | Left knee |
| --- | ---: | ---: | ---: |
| Previous stride | 3.535° | 3.566° | 3.505° |
| Previous stride + ridge correction | 3.411° | 3.422° | 3.400° |
| Previous stride + Transformer correction | **2.679°** | **2.719°** | **2.640°** |

The Transformer reduced mean absolute error by **0.856°** relative to copying the previous stride. A paired bootstrap over the 12 people gave a descriptive 95% interval of **0.628° to 1.089°** for that reduction. Its reduction relative to ridge regression was **0.731°** (0.579° to 0.891°). Ridge regression reduced average error by **0.124°** (0.041° to 0.206°), but raised it for four people, S43, S44, S45 and S49. Participant-level scores, signed differences and source checksums are available for inspection. [Full results](results.json)

These are forecasts of the angles stored by the Xsens system during treadmill walking at 0.5 m/s. Twelve previously examined people can describe how the methods compare in this recording set. We then ran the unchanged model on ten walkers recorded with optical markers at a nominal 0.8 m/s in another laboratory. The Transformer averaged 3.242°, stride replay 3.398° and the linear model 3.602°. It beat replay in six walkers and the linear model in nine. Only its comparison with the linear model cleared the prespecified criterion. Direct measurements of live accuracy and delay remain open. [Independent study and participant scores](external-optical/) The source contains other signals, but this experiment uses knee history alone for prediction. It provides no evidence about a person's intentions or neural activity.

## Try a forecast

With Python 3 and NumPy installed, open the launcher for your operating system or run this command from the extracted folder.

```sh
python predict.py example.json
```

The invented example has an estimated period of 86 frames. Copying the previous stride gives 20.28° right and 34.87° left. The Transformer's corrections give 17.43° right and 33.48° left. These numbers illustrate how the code runs. [Example input](example.json) · [Expected output](example-prediction.json)

For your own stored prefix, keep the example's channel order, supply 240 consecutive frame numbers and replace the 240 angle pairs. Only the final numbers returned under `prior_stride`, `ridge_residual` and `transformer_residual` are forecasts. All three already include the angle copied from the earlier stride. A missing frame breaks the input. The reference sample rate is 60 Hz.

The fitted parameters and both the training and evaluation code are included. The source recordings remain available directly from PhysioNet. [Reproduction guide](REPRODUCE.md) · [Dataset and reuse](RIGHTS.md)
