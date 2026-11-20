# What a finger cue can predict

A screen names a finger. A glove independently measures how the five fingers move. These four pages compare a near-future glove reading, the amount of movement during the next three glove steps, and the attempt to estimate that movement in a person whose later trials supplied no training examples. They are a companion to the NeuroTranslation and Brain2Body papers. [Read the HTML](index.html) · [Download the PDF](finger-cues.pdf)

## Supplementary information

The [numerical supplement](evidence.json) identifies the sources and records the units, time windows, summary errors, per-person and per-finger results, anatomical sampling and all six transfer comparisons. It includes additional descriptive block-resampling intervals for the five fixed people from an independent calculation. The primary cohort intervals resample people. Those two calculations describe different kinds of variation.

The first two experiments used the same 52 fitting trials and 23 later trials in one familiar development recording. The cohort analysis used each of five people in turn for calibrated assessment. All numerical examples in the three browser companions use invented inputs. The trained deployment model for the cohort used all five people and has no further evaluation cohort here.

| Study | Code, methods and results | Browser companion |
| --- | --- | --- |
| Later glove reading | [Cortical glove](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/cortical-glove) | [Finger signals](https://eliminatenoise.github.io/NeuroTranslation/finger-signals/) |
| Future movement size | [Finger motion](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/finger-motion) | [Finger motion](https://eliminatenoise.github.io/NeuroTranslation/finger-motion/) |
| Five-person transfer | [Finger transfer](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/finger-transfer) | [Finger transfer](https://eliminatenoise.github.io/NeuroTranslation/finger-transfer/) |

## Read and reproduce

Open `index.html` locally. All four pages and their table values are inside this editable file. The optional links open public references and experiment companions. To regenerate the searchable, linked A4 PDF, install Python 3 with `pypdf`, Chromium or Chrome and Liberation Sans. In this directory run `python build.py`. Use `--browser` for a particular browser or `--output` for a different destination. The per-study instructions above reproduce the fits from separately obtained source data.

## Source and reuse

Kai Joshua Miller deposited *A library of human electrocorticographic data and analyses* in the Stanford Digital Repository. Miller, Hermes, Honey, Hebb, Ramsey, Knight, Ojemann and Fetz reported the original experiment in 2012. This adaptation selects early portions of the recordings, derives forecasts and contrasts of model and reference errors, and presents aggregate numerical results and their interpretation. Obtain original recordings separately from Stanford. This supplement distributes aggregate results and contains no recordings or personal calibration arrays. The derived scientific account, tables and supplementary evidence are available under CC BY-SA 4.0. Credit the source, identify changes, preserve share-alike terms and respect the participants’ privacy and confidentiality. The original ethics paragraph is reproduced unchanged in Methods on page four. [Stanford collection and conditions](https://purl.stanford.edu/zk881ps0522) · [Library descriptor](https://doi.org/10.1038/s41562-019-0678-3) · [Original experiment](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1002655) · [Licence text](CC-BY-SA-4.0.txt)
