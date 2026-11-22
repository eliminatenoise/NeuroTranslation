# NeuroTranslate models

## Current downloads

A checkpoint is the set of weights a model saved after fitting. The downloads include those weights and a way to try them with invented readings.

| Download | What you can try |
| --- | --- |
| [NeuroTranslate 0.0 walking force preview](neurotranslate-0.0/recorded-force/expanded.zip) | Give two small models past muscle and floor-force readings. Each estimates whether the plate will start carrying load in the next 100 milliseconds and how much force will accumulate. [Setup and model card](neurotranslate-0.0/recorded-force/expanded/) |
| [NeuroTranslate 0.0](neurotranslate-0.0.zip) | Open the seven-task joint demo or try the new walking force experiment in the same download. [Walking force instructions](neurotranslate-0.0/recorded-force/) |
| [NeuroTranslate 0.1 Research Edition](neurotranslate-0.1/research-edition.zip) | Try two invented walking inputs with the repeated decoder and see its 100 ms force forecasts. The full example runs on Linux CPU and uses a separate Inkling checkpoint. [Setup and validation results](neurotranslate-0.1/research-edition/) |
| [NeuroTranslate 0.1](neurotranslate-0.1.zip) | Run the new walking force input and output layers with the separately downloaded Inkling 2 Mini model. [Setup and example](neurotranslate-0.1/) |
| [Walking force comparisons](force-baselines/) | Try simpler fits that read recent force, muscle activity, or both. The files contain multiple candidate settings for later evaluation. |

The walking force models use past muscle and force readings to look 100 milliseconds ahead. One output estimates the chance that a plate will start carrying load. The other estimates the signed vertical force added up over that time. The Research Edition guide reports a comparison on three people whose recordings were kept out of fitting. A separate group is reserved for the final test.

## NeuroTranslate 0.0 studies

**[NeuroTranslate 0.0 joint alpha](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/)** is the current joint model. [Download the model and local demo](neurotranslate-0.0.zip) or inspect [its source and results](neurotranslate-0.0/joint_alpha/). The earlier task-specific fits below retain the inputs from their own studies.

Forecast the next positions in a moving set of points, or the next detected spike among the recorded units. Each predictor has fitted weights of its own. Both run through the [normal Python download](neurotranslate-0.0.zip). The complete studies are available with their training and scoring code.

| Study | Run locally | Read the evidence |
| --- | --- | --- |
| [First use on an unfamiliar body](first-use-body/) | [Browser, model and paper](../docs/first-use-body-offline.zip) | [Optical tracking study](https://eliminatenoise.github.io/NeuroTranslation/papers/first-use-body/) |
| [Next Neuron Prediction](next-neuron-prediction/) | [Browser, model and paper](../docs/next-neuron-prediction-offline.zip) | [Sorted spike study](https://eliminatenoise.github.io/NeuroTranslation/papers/next-neuron-prediction/) |

The ordinary [NeuroTranslate 0.0 download](neurotranslate-0.0.zip) includes a cross-person wrist example. From the extracted folder, run `python predict.py cross_person_wrist/example.json`. [Try it in the browser](https://eliminatenoise.github.io/NeuroTranslation/cross-person-wrist/).

The [human wrist package](human-wrist/) includes the simulation used in the public reader and the code for learning from locally acquired recordings. [Run a wrist forecast](https://eliminatenoise.github.io/NeuroTranslation/human-wrist/) · [Read the cross-day results](https://eliminatenoise.github.io/NeuroTranslation/papers/human-wrist/)

The [one-week reach package](reach-feedback-week/) contains the trained models, a reader, and instructions for rebuilding the comparison from two recordings. [Open the later-day reader](https://eliminatenoise.github.io/NeuroTranslation/reach-feedback/one-week/)

The [reach feedback package](reach-feedback/) predicts hand, elbow and handle movement and estimates how much electrical activity follows in 23 recorded units of sensory cortex. [Try the model](https://eliminatenoise.github.io/NeuroTranslation/reach-feedback/) · [Compare the two workspaces](https://eliminatenoise.github.io/NeuroTranslation/papers/reach-feedback/)

The [cylinder-rotation package](cylinder-rotation/) contains fitted models that read a single moving sensor and forecast the next 100 ms. [Change a sensor reading and try the model](https://eliminatenoise.github.io/NeuroTranslation/cylinder-rotation/)

The [target-reach model and source](target-reach/) predict object displacement to three future times after an initial 200 ms of tracked motion. [Type a destination](https://eliminatenoise.github.io/NeuroTranslation/target-reach/)

[The next-day count model](contact-forecast/) estimates detected events at 26 shared contacts after a push. [Run the fitted models](https://eliminatenoise.github.io/NeuroTranslation/contact-forecast/)

[Forecast a push and a reach](https://eliminatenoise.github.io/NeuroTranslation/cortical-reach/) using recent handle movement, task cues and area 2 counts. The [cortical reach package](cortical-reach/) includes 18 fitted neural models and two sets of linear comparisons.

To forecast a sensory nerve fiber’s firing during a passive stretch, start with the [muscle spindle reader](https://eliminatenoise.github.io/NeuroTranslation/muscle-spindle/). The [training package](muscle-spindle/) includes 45 Transformer checkpoints, fitted count regressions, a separate forecast of future mechanical changes and source readers.

The current checkpoint also forecasts both knees 15 frames ahead from four seconds of walking. [Run the knee example](neurotranslate-0.0/knee/) · [Compare forecasts](https://eliminatenoise.github.io/NeuroTranslation/knee-stride/)

The same checkpoint forecasts tracked movement distance in centimetres, two right-wrist angles in degrees and displacement on a rat’s W-shaped track. Give it five earlier tracking points and, optionally, a second of firing counts from two brain regions. The movement encoder first reads the changes in position. A separate fitted calculation pairs the firing in each interval with the movement state from that interval. [Download the CPU model](neurotranslate-0.0.zip) · [Input examples and methods](neurotranslate-0.0/)

The movement viewer compares right-wrist angles with different combinations of movement, forearm and scalp input, and still runs the two original distance forecasts. The cross-animal track viewer lets you choose the direct linear benchmark or the shared movement encoder at the same forecast cutoff. [Wrist and distance viewer](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/) · [Track recording and both model families](https://eliminatenoise.github.io/NeuroTranslation/population-motion/)

[Download the browser predictor](movement-browser.zip) · [Rebuild the browser model and trace viewer](browser-source/)

### What did firing add to the shared model?

On the same 549 forecast instants compared in the linear benchmark, the shared movement model had an average error of **2.805 cm** with movement alone and **2.778 cm** with correctly timed CA1 and prefrontal firing. Substituting firing from an earlier trip gave **2.804 cm**. Only one of three rats improved over both controls. A comparison with scrambled movement-encoder weights scored **2.763 cm** with firing. These results establish that the fitted readout uses the firing signal. They give no evidence here that pretraining improved this forecast. A lower average error can hide a worse result in an individual animal. [Study and per-animal results](neurotranslate-0.0/population/)

## Wrist or sacrum, one shared forecast

A temporal Transformer reads 625 milliseconds of muscle and marker history. It predicts each available muscle’s electrical amplitude and the next 32 positions of the wrist or the sacrum. Across 882 lifts from three people, the shared model missed the wrist path by 4.870 mm. The arm specialist missed by 5.100 mm after the same number of arm updates and 4.394 mm when given the shared model’s full training budget. Across 1,759 visual rotations from six other people, the shared model missed the sacrum path by 2.169 mm and the exposure-matched balance specialist by 1.962 mm. [Try the forecast](https://eliminatenoise.github.io/NeuroTranslation/cross-limb-movement/) · [Training, source reader and scores](cross-limb-movement/) · [Download the full package](cross-limb-movement-model.zip) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/cross-limb-movement/)

## One model for the muscle and the movement

A turn of the virtual scene gives two clocks the same starting point. Electrodes record voltages over eight leg muscles. Cameras follow a marker near the base of the spine. The joint Transformer forecasts both for the next 125 milliseconds. The two specialists each forecast one. They had the lower average errors on 1,759 rotations from six people outside training. [Try the forecast](https://eliminatenoise.github.io/NeuroTranslation/muscle-and-motion/) · [Fit, score and run the models](muscle-and-motion/) · [Download the package](muscle-and-motion-model.zip) · [Compare the linear forecasts](https://eliminatenoise.github.io/NeuroTranslation/muscle-motion-controls/) · [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-and-motion/)

## Balance after a visual rotation

The walker sees the scene tilt. What can the voltage recorded at the scalp tell us about the next 125 ms of motion? Change the inputs to a Transformer trained on beam-walking recordings. On 880 qualifying rotations from six people outside the fit, the separately trained model without scalp voltage had the lower average error at both markers. [Try the forecast](https://eliminatenoise.github.io/NeuroTranslation/visual-balance/) · [Source, weights and scores](visual-balance/) · [Download the model](visual-balance-model.zip) · [Compare the shared model](https://eliminatenoise.github.io/NeuroTranslation/visual-balance-controls/) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/visual-balance/)

## What do two walking instructions add?

The walker crosses a level floor barefoot, with one instruction for each walk. A Transformer uses 200 ms of pelvis and right-heel motion and the instruction for that walk to forecast the next 100 ms. A second fit sees the movement alone. On the ten historical assessment participants the two fits differed by less than a tenth of a millimetre in average error at either landmark. [Try the forecast](https://eliminatenoise.github.io/NeuroTranslation/walking-instructions/) · [Source, weights and scores](walking-instructions/) · [Model download](walking-instructions-model.zip) · [Compare the general model](https://eliminatenoise.github.io/NeuroTranslation/walking-instruction-controls/) · [Study](https://eliminatenoise.github.io/NeuroTranslation/papers/walking-instructions/)

## Forecast the heel marker and the load underfoot

Two skin markers and eight muscle channels describe the same step. A small trainable Transformer predicts the heel’s displacement in three dimensions and the upward force on the plate 100 ms later. Two specialists use the same input, each learning one outcome. NeuroTranslate 0.0 answers the same question with a frozen movement encoder and fitted output layers. [Run the Transformer](https://eliminatenoise.github.io/NeuroTranslation/heel-and-force/) · [Weights, training code and results](heel-and-force/) · [Download the model](heel-and-force-model.zip) · [Try the general model](https://eliminatenoise.github.io/NeuroTranslation/shared-heel-and-force/) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/heel-and-force/)

## Pulling against a fixed pedal

A Transformer learns to forecast a signed change in the pedal sensor’s reading. A second model, NeuroTranslate 0.0, uses its existing movement encoder with a readout fitted to this question. Test what happens when each gets the muscle signal from the matching trial or from the other trial at the same pedal setting. [Try the specialist](https://eliminatenoise.github.io/NeuroTranslation/pedal-load/) · [Weights, code and results](pedal-load/) · [Download the specialist](pedal-load-model.zip) · [Try the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-pedal-load/) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/pedal-load/)

## Tracking a bundle of shin muscle fibres

Ultrasound gives us a view of the bundle’s changing length and its angle to a line of tissue in the image. A specialist Transformer and NeuroTranslate 0.0 ask how much longer or shorter it will look ten tracker steps later. Each has a separate length-only comparison. Millimetres here describe the image-plane length estimate. Some recordings contain ten times as many tracking rows as others. The elapsed time for ten steps has not been independently verified. [Try the specialist](https://eliminatenoise.github.io/NeuroTranslation/muscle-tracking/) · [Weights, code and results](muscle-tracking/) · [Download the specialist](muscle-tracking-model.zip) · [Try the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-muscle-tracking/) · [Study](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-tracking/)

## A tenth of a second of back sensor rotation

Two 32-electrode grids measured voltage at the skin while a sensor recorded which way it pointed. The models take a tenth of a second of history and forecast how many degrees the sensor will turn in the next tenth of a second. Each model gets the standing or walking instruction. Three of four new people had the required orientation labels, leaving the planned test incomplete. The specialist Transformer learned from four people. NeuroTranslate 0.0 uses a movement encoder with existing weights and fits a new readout to the same four people. [Try the specialist](https://eliminatenoise.github.io/NeuroTranslation/back-rotation/) · [Weights, source and results](back-rotation/) · [Download the specialist](back-rotation-model.zip) · [Try the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-back-rotation/) · [Study](https://eliminatenoise.github.io/NeuroTranslation/papers/back-rotation/)

## Predicting the neck electrode reading after a wrist stimulus

The Transformer takes five milliseconds of baseline and three milliseconds of early readings. Its target is the change in the neck electrode's voltage from baseline, four milliseconds after the early window closes. A second model starts from the last millisecond of neck voltage and estimates a correction. Compare the arm signal from the matching stimulus with one from the wrong stimulus. [Try the Transformer](https://eliminatenoise.github.io/NeuroTranslation/cervical-forecast/) · [Weights, source and scores](cervical-forecast/) · [Download the model](cervical-forecast-model.zip) · [Try the second model](https://eliminatenoise.github.io/NeuroTranslation/neck-voltage/) · [Study](https://eliminatenoise.github.io/NeuroTranslation/papers/cervical-forecast/)

## What can scalp electrodes add to an arm forecast?

A visual cue and early arm movements already give a model clues about where the arm is going. One experiment trains a small Transformer to use those clues alongside electrical recordings from the scalp and around the eyes. Another starts with the usual response to the cue and asks the shared NeuroTranslate movement model to correct it. Some forecasts remove the part of the scalp pattern a fitted equation can predict from the eye readings. Five people outside the fitting group supplied the test. [Try the Transformer](https://eliminatenoise.github.io/NeuroTranslation/scalp-forecast/) · [Weights, code and scores](scalp-forecast/) · [Download the Transformer](scalp-forecast-model.zip) · [Try the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#early-signals) · [Shared model method](neurotranslate-0.0/scalp-residual/) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/scalp-forecast/)

## Forecasting what a new person's arm sensors will read

The model sees which of seven instructions appeared and how three sensors changed over the last half-second. It predicts the next changes in their own instrument scales. One experiment trains a small Transformer on the arm task itself. Another fits new outputs to the shared NeuroTranslate movement encoder and tests whether one run from a new person improves the forecast on their later runs. Both compare predictions with measurements from the same five people outside the fitting group. [Try the arm Transformer](https://eliminatenoise.github.io/NeuroTranslation/arm-transfer/) · [Weights, fitting code and scores](arm-transfer/) · [Download the arm model](arm-transfer-model.zip) · [Try the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#arm-transfer) · [Methods and first-run correction](neurotranslate-0.0/arm-transfer/) · [Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/arm-transfer/)

## What an arm cue tells the model

The cue tells a person which movement to attempt. In the seven-cue experiment, knowing the cue improved the shared model’s forecast for the elbow, forearm and index-finger sensors at three future times. But the closest average forecast came from looking up the usual response to each cue. All three test runs came from the same person. [Type an instruction](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#cued-arm) · [Shared model and results](neurotranslate-0.0/cued-arm/) · [Download the offline shared predictor](movement-browser.zip)

In a separate comparison on 36 elbow trials, adding scalp electrode C3 to the cue and early elbow motion increased the average error from 0.07237 to 0.07859 native sensor units. On an invented example, change the scalp readings while keeping the cue and movement fixed to see what the fitted model does. [Try the elbow experiment](https://eliminatenoise.github.io/NeuroTranslation/elbow-cue/) · [Study, weights and source reader](cue-elbow/) · [Download the elbow model](cue-elbow-forecast.zip) · [Locate the sensors](https://eliminatenoise.github.io/Interoceptomics/scalp-and-arm/)

## Where a walking marker goes next

Cameras tracked the outer ankles, outer knees and thumb side of the wrists during slow overground walks. One model uses the recent paths of these six points and the pelvis to estimate each point’s movement over the next 200 milliseconds. Across ten test walkers its average miss was 18.22 mm from movement alone and 18.02 mm with right-leg muscle signals. A linear model using movement alone averaged 17.78 mm. The study found no reliable advantage from the extra muscle signals. [Try the six-point model](https://eliminatenoise.github.io/NeuroTranslation/walking-landmarks/) · [Methods, weights and results](walking-landmarks/) · [Download the offline viewer](walking-landmarks.zip)

A second experiment asked whether one motion rule could transfer to another part of the body. The shared NeuroTranslate model was given nine positions of one marker, 50 milliseconds apart. Tested on 46 other locations in ten walkers, it missed by 31.00 mm on average. A comparison that looked up similar paths among the training examples averaged 28.73 mm. [Try the single-point model](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#point-motion) · [Methods and results](neurotranslate-0.0/point-motion/) · [See the observed movements in Interoceptomics](https://eliminatenoise.github.io/Interoceptomics/stride-signals/)

The byte-for-byte reference fit for the single-point study ran on Linux with Python 3.12.14, NumPy 2.5.5, ezc3d 1.7.2 and `OPENBLAS_NUM_THREADS=1`. Using two threads changed individual fitted weights by about 5 × 10⁻¹². The six published prediction methods run from the saved weights in Python or JavaScript. Use the reference environment when reproducing the exact bytes of the fitted comparison models. [Reproduction procedure](neurotranslate-0.0/point-motion/README.md)

## Force underfoot

Two plates in a walkway measure the load where a foot lands on them. Six fitted models use recent marker positions, right-leg muscle activity, or both to estimate their combined reading 100 ms later on the recording clock. Across eight test walkers, adding muscle activity to the marker Transformer raised the average absolute error from 65.19 to 70.20 N. A separate task fits the shared model to the reading on the plate assigned to the right foot after heel strike. [Compare the six models](https://eliminatenoise.github.io/NeuroTranslation/walking-force/) · [Two-plate model and results](walking-force/) · [Shared right-foot model](neurotranslate-0.0/right-plate/) · [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-and-floor/)

## Predicting finger movement in a different person

The five people had different recording layouts. We grouped contacts by the brain area named in the source, recorded which areas were missing, then trained on four people at a time. A model based on the cue and its timing still had the smallest average error in the fifth person. [Test the model](https://eliminatenoise.github.io/NeuroTranslation/finger-transfer/) · [Calibrations, fitted weights and results](finger-transfer/)

## Predicting a knee's turning moment

The shared checkpoint now takes six sagittal joint angles to estimate both knee moments in N·m/kg. On three test walkers, the task-trained model gave 0.08874 average error, the linear fit 0.09761 and motion matching 0.09373. Their ranking varied by person. [Run the model](https://eliminatenoise.github.io/NeuroTranslation/knee-moment/) · [Angle-only and earlier-moment comparisons](neurotranslate-0.0/load/)

## Predicting the five glove sensors

How much will each finger move when the screen names one of them? In a single recording, the cue alone gave lower errors than a model that also received cortical activity. The target was the average size of the changes between four future glove readings. [Study and saved models](finger-motion/) · [Try the browser model](https://eliminatenoise.github.io/NeuroTranslation/finger-motion/) · [Complete offline download](finger-motion.zip)

A glove recorded how far each finger bent in the device’s own units. Recent glove readings and the word on the screen forecast readings three glove samples ahead. Keeping the last reading gave the lowest average error. Adding a recording from the surface of the brain worsened both fitted forecasts in this one-person experiment. [Study, source and fitted models](cortical-glove/) · [Try the offline-capable reader](https://eliminatenoise.github.io/NeuroTranslation/finger-signals/)

## Compare the same four seconds of knee movement

An earlier stride supplies the starting answer. A correction trained specifically for the knees averaged 2.679° of error, against 3.535° for stride replay. The new knee output on the shared movement model gave 3.465°. Both evaluations used the same 12 previously studied walkers. In ten walkers measured with optical markers in a second laboratory, the unchanged task-trained model averaged 3.242°, replay 3.398° and the linear correction 3.602°. The advantage over replay was uncertain. [External test](knee-stride/external-optical/) [Task-trained model](knee-stride/) · [Download the standalone predictor](knee-stride-model.zip) · [Offline reader](knee-stride.zip) · [Reader source](knee-stride-source.zip)

## Do the muscles and knees repeat at the same rate?

For 11 held-out walkers at 0.5 m/s, the strongest rhythms in the leg-muscle recordings and knee angles differed by 0.027 cycles per minute on average. Pairing each walk with another walker’s muscle recording raised the difference to 3.055. Each instrument supplied its own 40-second window. Agreement in rate leaves the timing of individual steps unresolved. The peaks landed on the same search frequency for nine people and one 0.15-cycle-per-minute grid interval apart for two. A 40-second window has a natural frequency spacing of about 1.5 cycles per minute. These comparisons measure agreement between estimates made with the same method.

[Compare the rhythms](https://eliminatenoise.github.io/NeuroTranslation/gait-rhythm/) · [Study and results](gait-rhythm/) · [Offline reader and source (ZIP)](gait-rhythm.zip) · [Read the supplement](https://eliminatenoise.github.io/NeuroTranslation/papers/walking-rhythm/)

## Where will the knees be 15 stored frames later?

Five snapshots of both hips, knees and ankles predict the two knee angles 15 frames later in a stored 60 Hz treadmill recording. On 40,201 forecasts from 12 held-out walkers, replaying a stride from four seconds of knee history gave 3.54° mean absolute error. The transformer, with 0.4 seconds of joint history, gave 4.46° on the same windows. At the same five input times, the transformer averaged 4.47° across all 42,781 eligible windows and a six-joint linear fit averaged 5.60°. Each walker counts equally.

Six of the 51 recordings used whole-file Xsens HD processing, including test recording S48. The other 45 carry the Live label. Physical prediction latency was never measured. Only reconstructed joint angles entered the forecast. The brain and muscle recordings from the source study belong to separate measurements.

[Try the knee forecast](https://eliminatenoise.github.io/NeuroTranslation/knee-motion/) · [Model and results](knee-motion/) · [Offline viewer and model (ZIP)](knee-motion.zip)

## Where will the next step land?

Give the model half a second of a measured walk or run. It predicts the next 0.60 seconds at 18 points on the body. Turn the figure, follow one foot and reveal where its markers landed. The walk or run label reduced average error at points measured relative to the pelvis from 71.9 to 69.1 mm across six fresh recording groups. A linear forecast tracked the pelvis through the room more closely. Only one of the six groups ran.

[Continue a measured stride](https://eliminatenoise.github.io/NeuroTranslation/stride/) · [Model and results](stride-continuation/) · [Offline viewer and model (ZIP)](stride-continuation.zip)

## Can brain activity sharpen a rat’s movement forecast?

Step through one recorded trip and compare how far a rat moved with forecasts that use its earlier movement alone or also use firing from two brain regions. Across three held-out rats the average miss fell from 2.898 to 2.870 cm when firing was added. Only one rat improved against both movement alone and firing from an earlier trip. For that rat, continuing at the last observed speed did better still.

[Explore a recorded trip](https://eliminatenoise.github.io/NeuroTranslation/population-motion/) · [Model and results](population-motion/) · [Offline viewer and model (ZIP)](population-motion.zip)

## Generate a walk or a run

Enter **walk** or **run**. A small network fitted to 31 motion-capture recordings generates the positions of 18 surface landmarks over 0.60 seconds. The viewer can overlay those points on a measured training example. Two walks and a run qualified for the held-out comparison. The model’s average error relative to the pelvis was 89.82 mm. Using the training average for each action gave 89.88 mm.

[Try the two commands](https://eliminatenoise.github.io/NeuroTranslation/word-motion/) · [Python and JavaScript inference, weights and study](word-motion/) · [Offline viewer and model (ZIP)](word-motion.zip)

## Which wrist forecast should I run?

Both downloads below forecast how far the right wrist will bend back and tilt towards the thumb a quarter-second later. Each accepts recent wrist motion and optional measurements of electrical activity at the forearm. Both run locally with Python and NumPy.

| Download | What it does | Two-angle error with forearm input |
| --- | --- | --- |
| [Shared Transformer](neurotranslate-0.0.zip) | Keeps the two distance tasks and all three earlier angle modes. For wrist angles, you can now add a learned correction to its motion forecast. | 4.054° |
| [Wrist specialist](wrist-specialist.zip) | Uses a network fitted specifically to wrist movements. It reports the motion forecast, the amount added or subtracted from each angle and the final prediction. | 3.549° |

We compared methods on 1,879 trials from six previously studied people. Each person took a turn as the test person. The shared model’s correction trained on movement alone had an error of 4.175°. Adding forearm activity lowered it to 4.054°, with improvement in four of six people. Using another trial’s forearm recording raised error to 4.419°. Both downloads contain final weights fitted using all six people. Their accuracy on a new participant is unknown. [Shared correction, controls and example](neurotranslate-0.0/forearm/) · [Specialist source and example](wrist-specialist/)

![Wrist forecast errors in degrees. All three methods had lower average error with forearm input. Among the corrected shared model’s timing tests, the forearm signal recorded alongside the movement gave the lowest error.](figures/wrist-correction.png)

[Download the comparison figure (PDF)](figures/wrist-correction.pdf) · [Recreate it from the published scores](figures/plot_wrist_correction.py)

The wrist models return numerical estimates. In an extreme invented example, the corrected shared model predicted about −1,692° of extension, far beyond the movement of a human wrist. Its output has no anatomical limit. To reproduce both angles, pass the invented input to the browser package’s Node.js command. [Boundary input](examples/wrist-angle-range-check.json) · [Command and input format](neurotranslate-browser/README.md)

### Three direct wrist-angle forecasts

In six tests, each leaving one of six training participants out, reading past wrist angles alone produced **4.503°** of two-axis error. Adding forearm measurements lowered it to **4.291°**. With scalp measurements included as well, it was **4.491°**. An earlier movement-and-forearm correction model reached **3.549°** on the same observations. A matched control with randomly initialized frozen temporal layers also performed at least as well in all three input conditions. The comparison supports running the added angle path but did not establish a predictive benefit from the pretrained core on this task. The fitter and source-data recipe preserve separate angle and distance units. [Angular study and methods](neurotranslate-0.0/README.md)

## A shared model for two tracking tasks

A headset tracks a wrist in three dimensions. A camera tracks a rat in two dimensions. Both can measure how far the point moved between observations. Give this model five earlier positions in the same coordinate system, or the four intervals calculated from those positions. It predicts the straight-line distance to the next position about a quarter-second later, in centimetres.

**[Run the shared model in a browser](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/).** Compare an actual rat training trip with an invented wrist history or enter your own earlier tracking samples. The model runs on your device. You can save the self-contained page for offline use.

The two tasks use **one fitted Transformer checkpoint**. The same attention layers learn from both kinds of movement. A small final readout for each task turns the shared representation into a distance. The result gives a magnitude. The positions along a path and its direction require other predictions. [Download the model and source (ZIP)](shared-motion-distance.zip) · [Usage and reproduction](shared-motion/README.md)

The original two-domain browser module remains available for reproducing the comparison below. It accepts four motion intervals or derives them from time-stamped tracking points. Its two distributed examples are invented. [Browser runtime and API](shared-motion-browser/) · [Download the standalone JavaScript package](shared-motion-browser.zip)

## Did learning together help?

| Quarter-second forecast | Human wrist | Rat position |
| --- | ---: | ---: |
| Shared Transformer | 1.725 cm | 1.310 cm |
| Single-task Transformer, equal exposure to its own recordings | 1.782 cm | 1.342 cm |
| Single-task Transformer, equal total training updates | 1.759 cm | 1.388 cm |
| Best of the two linear baselines | 1.922 cm | 1.119 cm |

Each entry is mean absolute error. Smaller is better. Each of six acquisition groups for the human wrist and each of nine held-out trips for the rat had equal weight within its task. The comparison used 583 wrist windows and 106 rat windows. Both evaluation collections had been examined in earlier work, and all the rat trips came from one animal. Windows from the same group or trip can contain related movements.

The shared model’s average errors were slightly lower than those of the separately trained attention models. On both tasks the uncertainty interval for the equal-exposure comparison included zero. The linear baseline also beat the shared model on the rat recordings. Neither task passed the full decision rule for a transfer benefit. The weights demonstrate joint learning on these two collections. Additional people, animals and movements remain to be tested. [Frozen protocol and complete results](shared-motion/shared-motion-model/README.md)

![Mean absolute error and uncertainty for the shared model compared with single-task models. The paired intervals for both tasks include zero.](figures/transfer-comparison.png)

[Download the figure as a PDF](figures/transfer-comparison.pdf) · [Figure source](figures/plot_transfer.py)

## Vertebrate neural recordings

[Browse the recording sources](https://eliminatenoise.github.io/NeuroTranslation/vertebrate-neural-data/) by animal and measurement. The fitted next-spike model has separate evaluations on [turtle cortex](vertebrate-neural-data/turtle/) and [salamander retina](vertebrate-neural-data/amphibian/). The original [two-rat study](next-neuron-prediction/) includes the fitted coefficients and controls.

A separate [calcium fluorescence experiment](vertebrate-neural-data/worm-transfer/) fits otherwise identical forecasts with and without recordings from eight worms. [Compare the errors in seven held-out zebrafish](https://eliminatenoise.github.io/NeuroTranslation/worm-to-vertebrate/).

## Neural signals, muscle and movement

[Compare the measured outcomes](https://eliminatenoise.github.io/NeuroTranslation/neural-and-muscle-composites/) or [run the macaque models and examine the three studies](neural-and-muscle-composites/). The human study includes source code to fit models on independently obtained data.
