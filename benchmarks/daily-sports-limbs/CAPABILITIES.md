# What each body part can do

A camera sees an arm swing. A sensor strapped to that arm records acceleration along its own three axes. Those are different measurements of the same kind of movement. The walking recordings here contain no camera images, so they can test a forecast of the next sensor reading. Converting that forecast into a bend at the elbow would need synchronized, independently measured joint motion.

| Body part | NeuroTranslate 0.0 walking study | NeuroSurge game controls in the reviewed preview | Camera control in that preview |
|---|---|---|---|
| Right arm | Right-arm XYZ acceleration | Select the arm, bend or straighten the elbow or wrist, open or close the hand | Estimates right shoulder elevation and elbow flexion from visible landmarks |
| Left arm | Left-arm XYZ acceleration | Select the arm, bend or straighten the elbow or wrist, open or close the hand | No left-arm control tested |
| Right leg | Right-leg XYZ acceleration | Select the leg, bend or straighten the knee | No right-leg control tested |
| Left leg | Left-leg XYZ acceleration | Select the leg, bend or straighten the knee | No left-leg control tested |
| Torso | Torso XYZ acceleration | The avatar displays a trunk | No torso control tested |
| Individual fingers, toes, head, face or organs | No corresponding sensor channel in this checkpoint | The game includes hand and finger actions and a gaze control | No control for these parts tested |

**Model.** Choose one sensor. A single network reads that sensor's previous 16 XYZ samples and forecasts its next three-axis reading at a lead of 120 milliseconds. Each placement has its own input and output layers, local axes and TRAIN normalization. The five placements share the temporal network. The checkpoint consumes neither video nor game state. Its test here is descriptive training-set performance in two walking conditions. A finger, a wrist angle and a walking arm sensor pose three different measurement problems. Separate studies in this repository address some of the others. [Study results](README.md) · [Wrist pointing with forearm signals](../wrist-forearm-transfer/)

**Game.** NeuroSurge maps selected controls to simulated actions. The reviewed preview's movement box accepts named actions such as “bend my right elbow”. A control moving an avatar demonstrates the mapping in the game. Accuracy on a participant requires separate measurement. [NeuroSurge project](https://github.com/eliminatenoise/NeuroSurge)

**Camera.** In the reviewed right-arm preview, a local model estimated shoulder elevation and elbow flexion from exercise footage fed through a browser's video interface. The game visibly moved both joints. This test used a file-backed camera in Chromium. Physical webcam operation, depth accuracy and agreement with instrumented joint angles remain unverified. The snapshot reviewed was NeuroSurge revision `c35d787`.

**Small Vision.** The two demonstrations can sit side by side. To ask whether a camera and a wearable agree on a particular action, both must observe the same person performing that action, with matched timing, sensor placement, calibration and an independently defined comparison quantity. The DSADS walking archive cannot supply that pairing. [UCI source and sensor layout](https://archive.ics.uci.edu/dataset/256/daily)
