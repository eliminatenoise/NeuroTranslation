# Which recordings can supply a measured turn?

Four new people each supplied two standing-and-walking trials, 02 and 03. Three people's files (S12, S13 and S14) identify all four parts of the orientation reading. In both S10 trials the stored labels read `Quaternion (2)[A.U]`, `Quaternion (3)[A.U]`, `Quaternion (4)[A.U]` and `BufferChannel[A.U.]`. The first quaternion component could not be verified. These files cannot establish the sensor's turn for S10, so the registered four-person comparisons remain incomplete. Six trials from the remaining three people supply the descriptive scores. [Original dataset](https://doi.org/10.5281/zenodo.19065545) · [Eight-file label check](../label-eligibility.json)

Place `assessment-source.json` beside `acquire.py`. Run the following commands from this source directory. The first reads only the selected trial members from the authors' archives and checks their bytes. The second inspects one original recording's clock, labels, electrode layout and quality flags, writing its report beside the local MAT file.

```sh
python acquire.py recordings --metadata assessment-source.json
python qualify_assessment.py recordings/S10/trial-02.mat
```

The assessment checker also distinguishes a missing `filtered_data` field in S12 from an empty field in other files. This field contains an optional processed output. The forecasts use the raw surface voltages. Availability of those raw samples does not resolve S10's orientation labels.

Desirée Irene Gracia Laso, Eduardo Iáñez, Mario Ortiz and José M. Azorín released the original data under Creative Commons Attribution 4.0. The package adds acquisition checks, forecasts and a descriptive comparison. [Original methods](https://doi.org/10.1038/s41597-026-07592-7) · [Licence](https://creativecommons.org/licenses/by/4.0/)
