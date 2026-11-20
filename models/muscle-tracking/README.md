# Can a muscle bundle’s angle help predict its length?

A seated volunteer draws the foot upward while ultrasound follows a fascicle, a bundle of fibres in the muscle at the front of the shin. A specialist Transformer sees the last 21 image-tracked lengths and the 20 angles preceding the cutoff. It predicts the signed change in length ten tracking steps later. A negative change means shortening. The source grids differ between recordings, so those ten steps have no verified common duration.

Four new volunteers supplied two recordings each and 776 eligible forecast windows. With length alone the specialist Transformer missed by 0.236 mm on average. Adding the correct earlier angle gave 0.233 mm, and supplying the same model with angles from the other recording gave 0.270 mm. The correct angle beat the length-only Transformer for 3 of four people and the swapped-angle control for 4 of four. It fell short of its prespecified criterion for an advantage from angle. Each volunteer has the same weight in these averages.

The angle and length come from the same two-dimensional images. They can share tracking errors. A straight-line projection is one comparison, and requires a stable reference direction. These forecasts do not measure force, neural drive or rehabilitation outcomes. The original study also recorded electrical signals, but this experiment has no verified alignment between tracker rows and muscle-voltage samples. [Complete held results](assessment.json) · [Development results](development.json) · [Forecast definitions and decision criteria](PROTOCOL.md) · [Model details](METHOD.md)

## Try the model

Extract the folder. With Python 3 and NumPy installed, open the launcher for Windows, macOS or Linux. It runs the eight methods on the invented history in `example.json`. Or run the following command in the extracted folder.

```sh
python -B forecast.py example.json
```

Replace the lengths and angles in a copy of the example to test another history. Lengths are positive millimetres, angles are degrees, and both arrays run from earliest to latest. Supply 20 alternate angles to see how the same fitted Transformer responds to a different angle history. Omit `other_angle_deg` to leave out that comparison. The projection prints `null` when the reference direction makes its divisor too small. [Offline browser reader](https://eliminatenoise.github.io/NeuroTranslation/muscle-tracking-offline.zip) · [Shared movement model](https://eliminatenoise.github.io/NeuroTranslation/shared-muscle-tracking/) · [Illustrated study](https://eliminatenoise.github.io/NeuroTranslation/papers/muscle-tracking/)

## Reproduce the results

Download and verify the original Task 3 tracking arrays using the two commands in the [source guide](SOURCE.md). To score the released weights on the four assessment people, run the following command from this folder with Python and NumPy. Start with an unused output directory. The scorer writes aggregate results and individual diagnostics into separate files on your computer.

```sh
python -B assess.py ../ankle-data . 8c74c9dc8e7772ec42a9c21f39d11972cf9af0cd49cc5d23f27eaed662328cef ../new-assessment
```

To repeat the four leave-one-person-out fits and the final fit, install PyTorch as well. The released fitter ran on Linux with NumPy 2.4.6, PyTorch 2.14.1+cpu, four CPU computation threads and one OpenBLAS thread. Use the development command in [the model methods](METHOD.md). Compare the weights and aggregate scores with the hashes in `seal.json`. [Files frozen before assessment](PRETEST-SHA256.json) · [Dataset credits](NOTICE.md) · [Package checksums](SHA256SUMS)
