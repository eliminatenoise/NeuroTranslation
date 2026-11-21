# How do we test a model on an unfamiliar body?

A new user should be able to move naturally from the start. A tall person and a short person can make the same gesture while their hands travel different distances on camera. A fish bends its trunk to swim. A fly walks on six legs. The project aims to use the movements and sensing points actually available on each body. Reaching that goal requires tests on bodies the model has never seen.

In the wrist experiment, the model measures shoulder direction and width from the preceding half-second of video tracking. That gives it a scale and a reference point without a calibration gesture. It then forecasts each wrist eight and fifteen camera frames ahead. A second person, reaching with the opposite wrist, supplied an independent test. The camera measures motion projected into an image. Depth, muscle contraction and nerve activity require other evidence. [Wrist experiment](papers/cross-person-wrist/index.html).

## What counts as a different body?

Keep every recording from a test person or animal together. Otherwise a model can recognize an individual during training and appear to generalize when it sees another clip from the same individual. Keep related recordings together when they share a camera view or the same animals. Report the number of independent people, animals and recording sites alongside the number of frames. Check error for each group, and give sparse groups their true counts.

For the expanded human comparison we assigned all 55 AJILE12 recording days before using the new participants’ movement data. Six people (27 recording days) form the training group. Three people (13 days) form the group for choosing model settings. Three further people (15 days) form the final test group. Both implant sides occur in each group. These are planned memberships. A usable pair of wrist positions still has to be found in each included window. The archive describes people observed in one clinical setting. A different hospital, a different task and a different species each pose another question. [Archive and original methods](https://doi.org/10.1038/s41597-022-01280-y).

## What counts as adapting on first use?

Record how much earlier movement was visible, how long the first forecast took, which tracked points were available and how far the forecast landed from the next observation. Compare with holding position and continuing the recent movement. Test changes in scale, build, shape, tracking quality and the number of points. Keep an entire species or phylum out of training to test that particular transfer. State which kinds of bodies and which movements were actually observed. A model that learns quickly from a person can still fail on a body plan it has never encountered.
