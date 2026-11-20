# Will the fascicle shorten over the next ten tracking steps?

A seated volunteer draws the foot upward. Ultrasound follows a fascicle, a bundle of muscle fibres, in the tibialis anterior at the front of the shin. Each tracked point gives us two numbers, the length of that bundle in millimetres and the published pennation angle, which describes the fascicle’s orientation relative to its reference. We ask how much shorter or longer the bundle will look ten tracking steps later. Could we predict that change from its recent length alone? Does seeing how its angle changed help? [AnkleImage dataset](https://doi.org/10.6019/S-BIAD1482) · [Task 3 methods](https://doi.org/10.1038/s41597-024-04285-x)

## What the predictor sees

Take 21 consecutive measured lengths. Put the first four changes in one bin, the next four in the next bin, and so on. Each of the five bins records the ending length and the change during those four steps. The angle-aware model also sees the mean and change in angle from the four earlier knots in that bin. Its last angle is one step older than its most recent length. A single Transformer block learns how to weight the five parts of that history. Its output is a signed change in millimetres. Subtract 0.3 mm from the current length for a prediction of −0.3 mm.

The simpler forecasts help identify what the network learned. Holding the current length predicts a change of zero. A second forecast repeats the last ten-step change. A third always gives the typical training increment. Ridge regression fits a linear combination of the same past length features. A separate straight-line approximation uses the recorded angle to project fascicle length onto the chosen reference line and extrapolates the recent change in that projection. Curvature, a moving reference and the fact that we only see a two-dimensional section can all break this approximation.

To test the contribution of angle, the evaluator supplies the full model with the angle history from the volunteer’s *other recording*, taken at the same relative position among eligible cutoffs. The length history and fitted weights stay fixed. Both angle and length come from image tracking. Agreement may reflect how the tracker estimates the two quantities. This experiment measures forecast error for those estimates. It supplies no independent measurement of neural drive, muscle force, or the timing of electrical activity.

## What happened when we left out each person?

We trained on three volunteers and predicted both recordings of the fourth, repeating the fit until everyone had been left out once. Every eligible recording contributed equally. That matters because 1,978 of the 2,560 windows came from the same person.

| Forecast | Mean absolute error (mm) |
|---|---:|
| Hold the present length | 0.3635 |
| Repeat the last ten-step change | 0.2203 |
| Typical training change | 0.3636 |
| Ridge regression on length | 0.1848 |
| Transformer on length | 0.1997 |
| Transformer on length and earlier angle | 0.2204 |
| Same fit, angle from the other recording | 0.2806 |
| Straight-line projection | 0.2564 |

The length-only Transformer improved on repeating the recent change for three people out of four. Ridge regression had the lowest mean error. Adding the correct angle to the Transformer increased each person’s error, from 0.0029 to 0.0454 mm. Yet giving that angle-aware network someone’s other recording increased the four-person mean error by a further 0.0602 mm, with three people worse and one slightly better. Correct pairing helps that particular fit. Length alone still made the better Transformer forecast in every fold. The separate fresh-person assessment uses a final pair of models trained on all four development people.

## Run a forecast

The portable predictor requires Python and NumPy. Each input is JSON containing 21 finite values in `length_mm` and 20 finite values in `angle_deg`, all in chronological order within one qualified native tracking segment. For length-only prediction, omit the angles and add `--variant length`. The examples in `synthetic.json` are invented. To reproduce the prediction for the second example from the directory containing this README, run the following commands.

```sh
python -c "import json; print(json.dumps(json.load(open('synthetic.json'))['cases'][1]))" > example.json
python portable.py model.json example.json
```

The development exports differ. Two recordings provide 9,920 native tracking rows apiece while most provide 992. Ten native steps can therefore span different portions of a contraction across recordings. Each person and each of their two trials carries equal weight. The source has different orientation conventions for the reference lines, and some exports supply a published pennation series without a separately recoverable reference line. See the per-member derivation in the source receipts. The tracking labels order recorded rows. The physical interval between rows, particularly across acquisition blocks, has not been independently established for this study. The ten-step forecast therefore has no promised duration in milliseconds. Both histories and targets use released offline tracking estimates. Their construction can involve corrections or information available only after acquisition. There is no accuracy or latency evidence here for a live tracker.

## Reproduce fitting and assessment

The prospective protocol fixes the participant split, two recordings per person, a ten-step stride, identical windows for all primary forecasts, equal trial and participant weights, and the decision gates. The held assessment applies weights fitted to the four development people. Each leave-one-person-out development result instead uses a separate set of weights fitted to the other three. The held assessment is a separate operation.

The fitter needs Python, NumPy and PyTorch. Supply the original MAT file, the five qualified native knot arrays and their verified receipt for each trial in the source owner’s layout `Axx/trial-N.mat`, `Axx/trial-N.knots.npz`, `Axx/trial-N.source.json`. Raw recordings can be obtained from the archive linked above. From this directory, with a new output directory for each run, use the following commands.

```sh
OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=4 OMP_NUM_THREADS=4 python -B fit.py /path/to/development /path/to/new-fit --threads 4
python -B test_study.py
OPENBLAS_NUM_THREADS=1 python -B assess.py /path/to/authorized-assessment /path/to/new-fit EXPECTED_SEAL_SHA256 /path/to/new-assessment
```

The expected digest is the independently retained SHA256 of the development seal before opening any assessment recording. The scorer verifies the protocol, inference implementation, fitter, exported results and all eight fresh source receipts. It writes participant and trial diagnostics to a private directory and an aggregate result separately. Four independent assessment people allow only coarse comparisons. Even four improvements in four people give a two-sided exact sign-test value of 0.125.

## Attribution

Qiang Zhang, Noor Hakam, Oluwasegun Akinniyi, Ashwin Iyer, Xuefeng Bao and Nitin Sharma released *AnkleImage* under CC BY 4.0. This model uses derived chronological histories of the tracked fascicle lengths and pennation angles from Task 3. The shared product contains trained coefficients, aggregate results and invented examples. Original participant trajectories remain with the archive. [Dataset and licence information](https://doi.org/10.6019/S-BIAD1482) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
