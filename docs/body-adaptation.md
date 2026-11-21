# How do we test a model on an unfamiliar body?

A new user should be able to move naturally from the start. A tall person and a short person can make the same gesture while their hands travel different distances on camera. A fish bends its trunk to swim. A fly walks on six legs. The project aims to use the movements and sensing points actually available on each body. Reaching that goal requires tests on bodies the model has never seen.

In the wrist experiment, the model measures shoulder direction and width from the preceding half-second of video tracking. That gives it a scale and a reference point without a calibration gesture. It then forecasts each wrist eight and fifteen camera frames ahead. A second person, reaching with the opposite wrist, supplied an independent test. The camera measures motion projected into an image. Depth, muscle contraction and nerve activity require other evidence. [Wrist experiment](papers/cross-person-wrist/index.html).

## What counts as a different body?

Keep every recording from a test person or animal together. Otherwise a model can recognize an individual during training and appear to generalize when it sees another clip from the same individual. Keep related recordings together when they share a camera view or the same animals. Report the number of independent people, animals and recording sites alongside the number of frames. Check error for each group, and give sparse groups their true counts.

For the expanded human comparison we assigned all 55 AJILE12 recording days before using the new participants’ movement data. Six people (27 recording days) form the training group. Three people (13 days) form the group for choosing model settings. Three further people (15 days) form the final test group. Both implant sides occur in each group. These are planned memberships. A usable pair of wrist positions still has to be found in each included window. The archive describes people observed in one clinical setting. A different hospital, a different task and a different species each pose another question. [Archive and original methods](https://doi.org/10.1038/s41597-022-01280-y).

## What counts as adapting on first use?

Record how much earlier movement was visible, how long the first forecast took, which tracked points were available and how far the forecast landed from the next observation. Compare with holding position and continuing the recent movement. Test changes in scale, build, shape, tracking quality and the number of points. For the neural studies, keep whole vertebrate species and, where suitable recordings permit, whole clades or classes out of training. Report which vertebrates actually supplied neural signals, how those signals were measured, and which individuals, sites and tasks were held out. Optical tracks supply a separate test of projected movement. Invertebrate recordings are optional. To test their value, train otherwise matched models with and without them, then compare their predictions on the same held-out vertebrates. State which kinds of bodies and which movements were actually observed. A model that learns quickly from a person can still fail on a body plan it has never encountered.

## What happened when a model met other tracked animals?

One fit learned from mouse and gerbil recordings. A second also learned from fly and worm recordings. Both watched only the points visible in the past of the new recording. Adding the extra training recordings improved the slower locust forecast and worsened the mean on the common shorter-horizon comparisons. The endpoint measures position in the camera plane. Projected size and shape depend on camera angle and posture. [Try the forecast](https://eliminatenoise.github.io/NeuroTranslation/first-use-body/) · [Read the animal study](https://eliminatenoise.github.io/NeuroTranslation/papers/first-use-body/) · [Code, weights and sources](../models/first-use-body/).

## Where can I find neural recordings?

The [vertebrate neural data register](https://eliminatenoise.github.io/NeuroTranslation/vertebrate-neural-data/) describes each measurement and links to the original deposit. The [fly and worm comparison](when-fly-and-worm-data-help.md) asks what a wiring diagram or developmental reconstruction can contribute to a vertebrate test.
