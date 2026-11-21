# Calcium recordings from worms and zebrafish

The training set combines eight baseline recordings of freely moving adult *C. elegans* and one recording of a larval zebrafish, Fish01. Seven further zebrafish supply the test set. Each recording contributes up to 32 regions of interest (ROIs) and the first three minutes of archived fluorescence. ROI numbers refer only to positions in each recording’s trace matrix. The experiment tests the transfer of a predictive prior between these optical assays.

## Worms

Atanas, Kim and colleagues recorded nuclear GCaMP7f in worms moving on agar under a spinning-disk confocal microscope. WormWideWeb identifies each source HDF5 file as an individual animal’s recording. The eight selected files come from eight different dates. The imaging protocol used day-one adults. The authors’ manifest supplies recording identifiers and checksums. It does not supply persistent animal identifiers or pedigrees. The first eight recording identifiers in lexical order carrying the authors’ baseline annotation determine membership. The selection excludes GFP controls and heat-stimulus recordings. [Experimental methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC10836760/) · [Per-animal source description](https://wormwideweb.org/about/datasets/) · [Frozen author manifest](https://github.com/flavell-lab/WormWideWeb-data/blob/0422546192ef58d0de4740a0aa91fd38de22da2e/activity/raw/atanas_kim_2023.csv)

The input field is `gcamp.trace_array_original` in the author’s per-animal JSON export. ANTSUN registered images across time and traced nuclear ROIs. The study reports background subtraction, low-signal exclusions, interpolation of missing ROI links, activity/reference-channel division and correction for recording-wide bleaching. “Original” identifies the exported trace before the additional per-neuron z-score. The source therefore includes retrospective processing. The physical clock comes from `timing.timestamp_confocal`. Differences in native timing survive extraction, including any gaps. [Trace fields and clock](https://github.com/flavell-lab/WormWideWeb/blob/main/dataset_json_readme.md) · [ANTSUN methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC10836760/#S23)

Credit Adam Atanas, Jungsoo Kim and colleagues for the optical recordings, analysis and data archive. Their Zenodo deposit, *CePNEM model analysis data and ANTSUN and microscopy neural network weights*, is licensed under Creative Commons Attribution 3.0 United States. This extraction selects an early time interval and the first ROI columns and transposes the worm traces to time by ROI. [Archive](https://doi.org/10.5281/zenodo.19388374) · [Registered license](https://api.datacite.org/dois/10.5281/zenodo.19388374) · [License terms](https://creativecommons.org/licenses/by/3.0/us/)

## Zebrafish

Martin Haesemeyer and Kaarthik Balakrishnan deposited forebrain recordings from eight *Danio rerio*. Two-photon imaging recorded the green nuclear GCaMP6s indicator while the larvae were mounted with tails free and subjected to a changing temperature stimulus. Each published file names a different fish. Fish01 and Fish02 share one recording date; Fish31 and Fish32 share another. The source filenames label dorsal or ventral forebrain acquisitions. Animal age in filenames and the deposited participant field can disagree. The ROI forecast uses neither stimulus nor behavior. [DANDI collection](https://dandiarchive.org/dandiset/000235/0.230316.1600) · [Experimental methods](https://elifesciences.org/articles/83289)

Only plane Z0 and the archived CaImAn `processing/ophys/Dff_Z0/DffUnitResponses_Z0/data` series enter the experiment. Its units are fractional fluorescence change (ΔF/F₀). The starting-time and rate fields in each NWB series supply its seconds clock. ROI detection, segmentation and baseline estimation were performed on recorded data. Indicators, optics, stimulus context, tissue preparation, preprocessing and native sampling differ between species. Time-matched prediction can reflect indicator kinetics, measurement processing or temporal autocorrelation. It cannot by itself identify a shared neural mechanism. [Data and license, CC BY 4.0](https://doi.org/10.48324/dandi.000235/0.230316.1600) · [License terms](https://creativecommons.org/licenses/by/4.0/)

## Reproducing the slices

Use Python 3.12 with numpy 2.5.5, h5py 3.16.0, fsspec 2026.9.0, aiohttp 3.14.5 and requests 2.34.2, or a compatible environment. Put `extract.py` beside `roster.json`. Run ordinary Python with assertions enabled.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B extract.py train
```

The script writes one NPZ per recording beneath `private/train`. Each has `time_s` (float64 seconds since the first recording frame), `fluorescence` (float64, time by ROI) and `roi_index` (int64, zero-based source column positions). It retains samples at times greater than or equal to zero and strictly less than 180 seconds, with the first 32 ROI columns if available. It keeps constants and nonfinite measurements for the declared downstream eligibility rules. The manifest includes SHA-256 for each NPZ and each field’s contiguous little-endian bytes.

For worms, the extractor checks the recording identifier and the publisher’s HDF5 checksum embedded in the corresponding author JSON. It hashes the compressed response and expanded JSON. For fish, it checks the archive’s SHA-256, asset URL, size and subject identity, validates the NWB storage type, indicator, series, clock and units, then requests exactly the selected ROI bytes per frame. Reproducing the whole-file archive checksum locally would require reading the complete NWB asset; this slice workflow verifies the selected payloads and uses the archive’s stated whole-file digest. HDF5 header reads can cache adjacent uninterpreted bytes. No raw image, behavior or inferred-calcium series is indexed.

The test extractor requires a frozen fit and a local release record. Its JSON fields are `authorization` (“held ROI slices only”), `roster_sha256`, `fit_manifest_path`, `fit_manifest_sha256` and `ids` (the held fish IDs in roster order). After locking the fit and scoring rules, run the following command. Its outputs go under `private/held`.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B extract.py held --approval release-record.json
```

The separate fish-image and songbird protocols use different observables. The bounded ROI test shares target fish with the fish-image protocol. Any subsequent assessment that calls those donors entirely unseen must account for this exposure.
