# How the forearm comparison was made

The KIN-MUS UJI study recorded healthy adults carrying out 26 activities of daily living. It used a glove to estimate wrist angles and seven surface electrodes to record electrical activity on the forearm. Participants supplied a zero-reference posture. The published angles are in degrees. The source did not establish a separate accuracy figure for the two wrist axes used here. [Dataset](https://doi.org/10.5281/zenodo.3469380) · [Data descriptor](https://doi.org/10.1038/s41597-019-0285-1)

## What the model can see

Both fitted models receive an activity label and elapsed time from the beginning of the stored movement segment. Together these can describe the typical course of an activity using the training recordings. The second model also receives 112 muscle features. For each of seven electrodes, the preceding half-second of raw EMG is divided into 16 bins. The root mean square amplitude in each bin describes the size of the electrical signal while allowing positive and negative readings. Squaring happens before averaging. All the bins end at least 250 ms before the target on the stored clock.

The released raw EMG has a nominal 1,000 Hz clock and the glove angles a nominal 100 Hz clock. We selected a target every fifth original glove sample, nominally every 50 ms, beginning 750 ms after the first stored glove sample. The EMG windows use the actual timestamps. The authors filtered the glove angles in both time directions before release. That matters even for samples labelled “past”: their filtered values can depend on later movement. We therefore withheld the entire wrist-angle history from both models. The two targets are the later, retrospectively filtered glove angles, with positive values denoting extension and radial deviation. The timed recording alone does not determine when a live device could have produced those target values.

## Who contributes to the comparison

The 22 participants were assigned to fitting (14), testing (4) and a group set aside (4) before the numerical data were inspected. All activities from a participant stay together. The source contains a documented missing activity. Records with ambiguous identities or a backwards boundary between movement phases are excluded in their entirety. A repeated boundary timestamp is collapsed only if the two recorded angles match. A forward time gap can invalidate individual candidate windows. No phase is shifted to make the signals line up.

We fit two straight-line models with a penalty that keeps their weights small (ridge regression), on the fitting participants alone. Each fitting participant has equal total weight. Scaling is computed on the training rows, and both output angles are fit in degrees. At scoring, the main error is the square root of the mean squared error with equal weight across the test participants and the two axes. A third comparison uses the fitted EMG model but moves the muscle features to a different time within the same person and activity. The task label, elapsed-time features and measured targets stay fixed.

The earlier WristMotion models used a pointing cue, earlier wrist angles and four differently placed forearm electrode pairs. The UJI recordings have different tasks, features and measurement methods. This experiment tests a related question on other people, using two models fitted for that question.

Data credit: Néstor J. Jarque-Bou, Margarita Vergara, Joaquín L. Sancho-Bru, Verónica Gracia-Ibáñez and Alba Roda-Sales. NeuroTranslation selected the two wrist axes, derived historical muscle features and fitted the comparison models. [Versioned UJI record and licence](https://zenodo.org/records/3469380) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
