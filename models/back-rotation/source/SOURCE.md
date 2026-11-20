# Where the back recordings come from

A volunteer walks, stands still, then walks again. At the same instant, two grids record tiny voltages at the skin and a sensor strapped to the back records which way it points. The shared clock lets us ask how far the sensor turns in the next tenth of a second. It cannot tell us which joint moved or which tissue generated a voltage. [Study methods](https://doi.org/10.1038/s41597-026-07592-7)

Experiment 2 places one grid over the upper back near C4 and the other over the lower back near L2. Each grid has 32 electrodes spaced 10 mm apart. The authors report the raw voltages in microvolts. The orientation sensor supplies four numbers describing its orientation together, called a quaternion. Both grids and the four orientation channels share 2,000 stored samples per second. The orientation sensor updates internally about 100 times per second, so successive stored values often repeat. [Dataset and channel descriptions](https://zenodo.org/records/19065545)

## Get the development records

Use Python 3.11 or newer. Keep `source.json` beside `acquire.py` and run the following command from that directory. The destination holds the eight native MATLAB files, byte-range cache and verification receipts. To fetch fewer records, add `--people S01` or another listed development participant. To share the connection with other work, use `--workers 1`.

```sh
python acquire.py recordings
```

The selection covers trials 02 and 03 from one session each for S01, S02, S03 and S05. The downloader checks the original Zenodo catalog for the version, licence, archive sizes, checksums and addresses. It also checks the authors’ list of missing or shortened trials before reading the selected bytes from their session ZIPs. For each MATLAB file it checks the central directory against the member header, verifies the ZIP checksum and length, and compares SHA-256 hashes with those in `source.json`. The publisher’s MD5 applies to the whole ZIP. Checking it would require the entire archive. For offline verification of previously cached ranges, add `--catalog-directory DIRECTORY` and supply the original Zenodo API response as `record.json` alongside `trial_integrity_manifest.csv`.

With NumPy and SciPy installed, this command checks one record’s clock, original task labels, quaternion dimensions, electrode layout and quality flags. Its JSON output goes next to the MATLAB file.

```sh
python qualify.py recordings/S01/trial-02.mat
```

Quality flags count channels or samples the authors marked as null, noisy or outlying. These counts can overlap. The forecasts use preceding raw measurements. Some published preprocessing uses data on both sides of a sample, which could bring later information into a prediction.

Desirée Irene Gracia Laso, Eduardo Iáñez, Mario Ortiz and Jose M. Azorin collected and released the source dataset. Version 2 is distributed under Creative Commons Attribution 4.0. The downloader preserves the original MATLAB bytes and adds checksums and measurement summaries. [Dataset](https://doi.org/10.5281/zenodo.19065545) · [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/)
