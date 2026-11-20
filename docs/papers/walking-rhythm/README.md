# The next knee angle and the rhythm of a walk

This standalone research note accompanies the NeuroTranslation and Interoceptomics projects. The original studies use Xsens knee angles at 0.5 m/s. A separate acquisition supplies a transfer test on ten walkers measured with optical markers at a nominal 0.8 m/s. The fixed Transformer beat the linear correction for nine of ten. Its advantage over replay remained uncertain. The first four pages preserve the angle and muscle-rhythm studies. A fifth page asks what can be inferred about each knee’s signed turning moment from four seconds of recorded joint angles. [Read the HTML](index.html) · [Download the PDF](gait-clocks.pdf)

## Reproduce the note

Open `index.html` in a browser. The text, table values, bar lengths and styles are in this file, which also works offline. The [evidence file](evidence.json) contains the source fingerprints and aggregate values behind the four tables and the external comparison on page two. The mechanics test uses the same optical cohort, with seven people for fitting and three for evaluation. The third table reports absolute differences between trial-level estimated rates. Each rate analysis uses 40 seconds on its own instrument’s clock.

To regenerate the PDF, place the HTML and [build script](build.py) in one folder. Install Python 3, the Python package `pypdf`, Chrome or Chromium, and the Liberation Sans font family. Run:

```sh
python build.py
```

Use `--browser` to select a browser executable or `--output` to choose a destination. The verified export used Chromium 155, pypdf 6.21.2 and Liberation Sans on Linux. The [matched four-second study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/knee-stride) tests a trained correction against replay. The [shared encoder](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/neurotranslate-0.0/knee) tests transfer from earlier movement recordings. The [knee-angle study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/knee-motion) and [gait-rhythm study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/gait-rhythm) provide the underlying analysis code and study results. The [four-second knee forecast](https://eliminatenoise.github.io/NeuroTranslation/knee-stride/), [short-history knee forecast](https://eliminatenoise.github.io/NeuroTranslation/knee-motion/) and [rhythm comparison](https://eliminatenoise.github.io/NeuroTranslation/gait-rhythm/) open their browser companions. The [mechanics model](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/neurotranslate-0.0/load) and [turning-moment companion](https://eliminatenoise.github.io/NeuroTranslation/knee-moment/) cover the new endpoint.

## Source and reuse

Rateb Katmah, Aamna AlShehhi, Doua Kosaji, Nour Al-Rahmani, Muhammad Abdullah, Abdul Aziz Vaqar Hulleck and Kinda Khalaf (2026). *A multimodal gait dataset of brain activity, muscle activity, kinematics and ground forces in young adults*, version 1.0.0. PhysioNet (RRID SCR_007345). The authors released the recordings under CC BY 4.0. This note selects one speed, compares methods and reports aggregate errors. Obtain participant recordings from PhysioNet. [Dataset DOI](https://doi.org/10.13026/r0ea-7161) · [Dataset licence](https://creativecommons.org/licenses/by/4.0/) · [PhysioNet platform paper](https://doi.org/10.1038/s44360-026-00096-z)

The repository’s original contributions carry its CC0 dedication to the extent of its rights. Source-derived results retain the dataset attribution above. [Repository licence](https://github.com/eliminatenoise/NeuroTranslation/blob/main/LICENSE)

Reznick E, Embry K, Neuman R, Bolívar E, Fey N and Gregg R (2021). *Human lower-limb kinematics and kinetics during continuously varying locomotion.* We selected continuous level walking from their CC0 streaming data and computed 250 ms forecasts of the two reconstructed knee angles. The fifth page reports a separate fit to estimate both future net internal knee moments, in N·m/kg, from joint-angle history. [External source](https://doi.org/10.6084/m9.figshare.14558181.v1) · [Acquisition and reconstruction](https://doi.org/10.1038/s41597-021-01057-9) · [External evaluation and participant-level scores](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/knee-stride/external-optical)
