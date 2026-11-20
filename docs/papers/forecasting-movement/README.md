# What helps predict the next movement?

This two-page supplement accompanies the NeuroTranslation and Brain2Body papers. A cue naming a walk or a run improved the average forecast of where body markers went next. A second experiment asked whether counts of firing in two brain regions improved a rat’s movement forecast. The correctly timed counts beat both controls in only one of three test animals. [Read the note](index.html) · [Download the PDF](movement-forecast.pdf)

The two figures read the aggregate results in `evidence.json`. Its source-file hashes identify the complete score tables in the two model packages. The two experiments use different sources, units, clocks and outcome measures. No error or participant count has been pooled between studies.

To reproduce the figures with Python and Matplotlib, then build the HTML with the Python standard library, run the following commands from this directory. Pass an installed Chromium executable to print the two-page PDF. The exported file uses Liberation Sans.

```sh
python plot.py
python build.py --chromium chromium
```

The human motion data were obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. See the [CMU archive](https://mocap.cs.cmu.edu/) and [source reuse terms](https://mocap.cs.cmu.edu/faqs.php). Justin Shin and Shantanu Jadhav contributed *Single Day W-Track Learning* to the DANDI Archive under CC BY 4.0. This reanalysis aggregates spikes by recorded region, fits movement forecasts and compares mean errors. [Versioned dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The project-authored analysis scripts and original explanatory writing use CC0. Source materials retain the terms given above.
