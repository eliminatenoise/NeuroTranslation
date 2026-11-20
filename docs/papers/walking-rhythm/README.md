# The next knee angle and the rhythm of a walk

This standalone research note accompanies the NeuroTranslation and Interoceptomics projects. It reports secondary analyses of treadmill walking in healthy young adults at 0.5 m/s. Both analyses use the published Xsens knee angles as a reference. The note supplies the results and their timing limits in four pages. [Read the HTML](index.html) · [Download the PDF](gait-clocks.pdf)

## Reproduce the note

Open `index.html` in a browser. The text, table values, bar lengths and styles are in this file, which also works offline. The [evidence file](evidence.json) contains the source fingerprints and aggregate values behind the three tables. The third table reports absolute differences between trial-level estimated rates. Each rate analysis uses 40 seconds on its own instrument’s clock.

To regenerate the PDF, place the HTML and [build script](build.py) in one folder. Install Python 3, the Python package `pypdf`, Chrome or Chromium, and the Liberation Sans font family. Run:

```sh
python build.py
```

Use `--browser` to select a browser executable or `--output` to choose a destination. The verified export used Chromium 155, pypdf 6.21.2 and Liberation Sans on Linux. The [matched four-second study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/knee-stride) tests a trained correction against replay. The [shared encoder](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/neurotranslate-0.0/knee) tests transfer from earlier movement recordings. The [knee-angle study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/knee-motion) and [gait-rhythm study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/gait-rhythm) provide the underlying analysis code and study results. The [four-second knee forecast](https://eliminatenoise.github.io/NeuroTranslation/knee-stride/), [short-history knee forecast](https://eliminatenoise.github.io/NeuroTranslation/knee-motion/) and [rhythm comparison](https://eliminatenoise.github.io/NeuroTranslation/gait-rhythm/) open the three browser companions.

## Source and reuse

Rateb Katmah, Aamna AlShehhi, Doua Kosaji, Nour Al-Rahmani, Muhammad Abdullah, Abdul Aziz Vaqar Hulleck and Kinda Khalaf (2026). *A multimodal gait dataset of brain activity, muscle activity, kinematics and ground forces in young adults*, version 1.0.0. PhysioNet (RRID SCR_007345). The authors released the recordings under CC BY 4.0. This note selects one speed, compares methods and reports aggregate errors. Obtain participant recordings from PhysioNet. [Dataset DOI](https://doi.org/10.13026/r0ea-7161) · [Dataset licence](https://creativecommons.org/licenses/by/4.0/) · [PhysioNet platform paper](https://doi.org/10.1038/s44360-026-00096-z)

The repository’s original contributions carry its CC0 dedication to the extent of its rights. Source-derived results retain the dataset attribution above. [Repository licence](https://github.com/eliminatenoise/NeuroTranslation/blob/main/LICENSE)
