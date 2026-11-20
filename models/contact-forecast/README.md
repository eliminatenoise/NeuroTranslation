# Forecast activity at 26 sensory-cortex electrodes

A macaque held a movable handle. For each electrode, the models forecast how many electrical events will be recorded over the next 100 milliseconds. They learn on one day and make forecasts on the next. Open the launcher for your operating system, or open `reader/index.html` in a browser. The reader works offline and lets you move between a recorded push, a reach after a push and a reach without a push.

On 2,436 matched push windows from 609 second-day trials, the full Transformer gave lower count deviance with the correct movement history than with movement borrowed from a matched trial. Its difference from past counts and cues alone remained uncertain. The cue-only count regression had the lowest measured deviance among the tested models. Both dates come from one animal.

## Start with a single forecast

With Python and NumPy installed, run this command from the extracted archive. It reads the included past measurements and prints one expected count for each of 26 recorded contacts.

    python models/predict.py models/weights/all-17.json models/example.json

The 18 Transformer fits and six count regressions are in [models/weights](models/weights/). The [fitting guide](models/README.md) gives the input order, original-unit definitions, optimizer, numerical checks and training commands. The source contains filtered handle positions, and the electrode IDs do not establish stable neurons across days.

## Reproduce the experiment

1. Follow the [source guide](source/README.md) to obtain the two original recordings and reconstruct the training, validation and second-day arrays. The included `source/train-for-fit.npz` is the checksum-verified training input.
2. Use the [model instructions](models/README.md) to fit the models on the first day and generate all forecasts locally. The included validation and held-day forecast archives can also be scored as distributed.
3. Follow the [scoring instructions](scoring/README.md) to regenerate the trial, contact, direction and timing tables with their paired intervals. [Full second-day scores](scoring/test/summary.json) · [First-day validation](scoring/validation/summary.json)
4. To separate error in the total activity from its distribution over electrodes, run `python decomposition/components.py rebuilt/source/test.npz models/test-transformer.npz models/test-poisson.npz components.json`. See the [breakdown](decomposition/README.md).

[Read the study](https://eliminatenoise.github.io/NeuroTranslation/papers/contact-forecast/) · [Rotate the measured arm](https://eliminatenoise.github.io/Interoceptomics/contact-forecast/) · [Original study](https://doi.org/10.7554/eLife.48198) · [Original data](https://doi.org/10.5061/dryad.nk98sf7q7)
