# Forecast a finger angle

Start with the knuckle where your index finger meets your hand. As you bend that finger, the angle at the knuckle changes. The page uses four seconds of earlier angles to estimate what the angle will be 320 milliseconds later, about a third of a second. It does this for the index, middle, ring and pinky fingers.

## Try a movement

1. Open the forecast. For offline use, extract the whole ZIP, open the launcher for your system, then choose **Pinch and hook forecasts** on the opening page.
2. Under **Movement history**, choose an invented pinch or hook and a speed. Under **Forecast 320 ms ahead**, choose a finger and method. Follow the line to the last reading and read the predicted angle below the plot.
3. Choose **Replay an earlier movement**. The highlighted stretch shows the earlier part of the motion that most resembled the latest ten readings. Replay follows what the finger did after that earlier stretch. Try **Hold the last angle** to see what the forecast would be if the finger stayed at its present angle.
4. Select **Include ultrasound readings** to try the models that use a forearm image. The example supplies invented measurements from sixteen parts of each image. **Restore invented example** returns to the medium-speed index pinch with ultrasound off. You keep the selected finger, any method still available, and the filters for the recorded results.

## Use a recording of your own

Choose **Use a local recording** to download an example file or open one from your computer. The file stays in your browser. Each row gives the angles of the index, middle, ring and pinky fingers, in that order and in degrees. Supply 101 rows under `history`, with the oldest first. At one row every 40 milliseconds, the first and last rows are four seconds apart. If you also have compatible ultrasound measurements, append sixteen values to each row. The Technical guide gives the image conversion.

The browser download includes a Python version for people who want to inspect the saved model weights or use the forecasts in another program. The Technical guide gives the commands.

## How the methods use the readings

Imagine that the last angle was 40°. **Hold the last angle** forecasts 40°. **Continue the recent trend** follows the direction and speed of the last five readings. If those five readings rose steadily, the trend forecasts a larger angle. **Replay an earlier movement** looks for a similar bend in the four seconds you supplied. If the finger reached 52° a third of a second after that earlier bend, replay forecasts 52° now. Each finger gets its own match.

The fitted models learn from recordings. A linear model learns how much weight to give each earlier reading when it predicts the next change. A recurrent model reads the history in order and updates an internal summary as each new measurement arrives. The page lets you choose which type of model to run and which measurements to give it. The ultrasound option uses sound-wave images of the forearm. The models receive one number from each of sixteen regions in an image. The methods marked **Ultrasound** use those numbers to predict the *change* in angle, then add that change to the last measured finger angle.

The browser and the downloadable Python program carry the same learned weights. We ran both on 27 invented movement histories to check how accurately the browser reproduces the calculation. Their largest disagreement for the fitted forecasts was about two hundred-thousandths of a degree (0.0000221°). The much larger errors in the study below measure something different. They compare a forecast with what a person's finger actually did.

## Read the recorded results

The results table compares forecasts with measurements from four people who repeatedly pinched or hooked their fingers at three speeds. Each of the eight tests left out one person and one gesture during training. For example, when the test scored a person's pinch, each fitted model had learned from 21 recordings of the other three people, using gestures other than the pinch. There were 33,192 possible moments to predict. Across the 24 recordings, 2,184 fell too close to the start of a recording to supply four seconds of history. All methods predicted the remaining 31,008 moments. The interactive example uses a separate set of models trained on 51,680 short stretches from all 40 development recordings.

An error of 5° means the forecast missed the measured angle by five degrees in either direction. Across 31,008 forecast times per finger, replaying an earlier movement averaged **4.03°** of error. A model that learned how to combine earlier angles averaged **5.67°**. Holding the last angle averaged **6.70°**. Choose **Fast** under **Recorded speed** and the order changes. Holding the last angle averaged **3.81°**, compared with **4.25°** for replay. The filters under the table's heading change the study results. The movement controls above them change the example.

**Choose replay or hold** looks at nine earlier forecasts whose answers are already available. It uses whichever rule had the lower recent error for that finger, choosing hold on a tie. It averaged **4.00°** overall and **3.94°** on the fast movements. This rule was developed after the earlier comparison and checked on the same recordings.

Adding the sixteen ultrasound measurements increased the linear model's average error from **5.67°** to **9.61°**. The recurrent model's average error rose from **9.75°** to **10.08°**. These figures describe the images, the way they were reduced to sixteen measurements, and the repeated movements in this study.

The same person supplied many readings only 40 milliseconds apart. Two successive forecasts therefore share nearly their entire history. The table gives each person equal weight. It is evidence about how the methods handled these four people's movements. Testing the saved models on additional people is a separate step. Running the example also tells you nothing about how long a live camera or ultrasound device would take to deliver its next reading.

Keshav Bimbraw published the original recordings under CC BY 4.0. The recorded targets are angles measured with an optical tracking system. [Source recordings](https://doi.org/10.5281/zenodo.21825018) · [Recording methods](https://doi.org/10.1109/TMRB.2023.3237774)
