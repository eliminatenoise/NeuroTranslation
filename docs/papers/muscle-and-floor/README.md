# One stride, two force plates

This supplement accompanies the NeuroTranslation and Interoceptomics manuscripts. The first figure follows a stride in measurements from the training group. The next two comparisons ask how far a forecast missed the recorded load in walkers excluded from fitting. [Read the HTML](index.html) · [Download the four-page PDF](muscle-and-floor.pdf)

## Rebuild the supplement

The HTML contains its text, vector figure and styles. Open it in a browser to read it offline. Open the PDF in any PDF reader. The source links lead to the projects and the authors’ public materials online.

Keep `build.py`, `paper.html.in`, `numbers.json` and `DATA-LICENCE.txt` together. The JSON supplies the per-phase mean, sample standard deviation and distinct-person count for each plotted series, plus the aggregate model results and fingerprints of the original numerical sources. The HTML template contains the prose and table headings. The build uses the Python standard library for the HTML. PDF export additionally requires the Python package `pypdf`, Chrome or Chromium, and Liberation Sans.

```sh
python build.py --html-only
python -m pip install pypdf
python build.py
```

Use `--browser` to supply the path to Chrome or Chromium. The full command creates `index.html` and `muscle-and-floor.pdf`. The PDF includes searchable text, an embedded vector figure and links. All scoring and preprocessing choices are available with the underlying studies. [Stride reference and calculation](https://eliminatenoise.github.io/Interoceptomics/stride-signals/) · [Two-plate model, protocols, weights and results](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/walking-force) · [Right-contact CPU model](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/neurotranslate-0.0/right-plate)

## What distinguishes the two tests

The two-plate Transformer combines eight consecutive snapshots into a prediction. The marker-only, EMG-only and combined versions were fitted separately with one attention layer, three heads, width 24 and 400 training updates. A comparison that carries forward the earlier plate reading gets information unavailable to the other predictors. The fitted model and original source-to-score commands are available in the linked two-plate study.

The right-contact forecast accepts two right-foot markers inside the assigned plate at the annotated first strike. It requires a full 240 ms of input and a later target in the record. At elapsed times of 140, 240, 340 and 440 ms the assessment contributed 5, 16, 16 and 16 eligible forecasts respectively. Only five histories extended far enough back for the first cutoff. The model compares a simple regression with another regression that also receives features from the fixed shared movement encoder. Scrambling the encoder's stored values provides a control for its prior training.

For a claim of added muscle information this second experiment required lower average error and a strict majority of person-level wins against the time-only table, shared marker model, simple combined ridge and substituted-repeat control. It also required the upper end of the paired 95% interval to be below zero for the shared marker and substituted-repeat comparisons. For a benefit from the trained encoder the shared combined fit had to beat its scrambled counterpart in average error and in more than half the walkers. Both claims failed those criteria. Source-derived summaries, study settings and implementation details are linked above.

## Source and attribution

Céline Schreiber and Florent Moissenet (2019). *A multimodal dataset of human gait at different walking speeds established on injury-free adult participants*. Scientific Data 6, 111. We selected slow barefoot C2 walks, aligned strides, transformed coordinates and calculated group means, then compared forecasts in recordings from other people. The figure and numerical derivatives credit the authors’ version 8 release under Creative Commons Attribution 4.0 International. The repository dedicates its original text and code to CC0 to the extent of its rights. [Article](https://doi.org/10.1038/s41597-019-0124-4) · [Version 8 data](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Supplementary Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC6610108/#MOESM2) · [Author processing code](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/tree/e35dc90c1acd24da134897fd1b4241152cff6005) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [CC0](https://creativecommons.org/publicdomain/zero/1.0/)

The reserve group contributes no measurements to this supplement. Download the original recordings from the authors to reproduce the source studies.

The source archive’s original [licence file](DATA-LICENCE.txt) is also embedded in the HTML download link and in the PDF as an attachment named `DATA-LICENCE.txt`. All three copies preserve the authors’ original bytes.
