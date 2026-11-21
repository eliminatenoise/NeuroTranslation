# Animal landmark recordings

Where will a bee's antenna be in the next frame? These files let you ask that question about points on a bee, fly, locust, worm, mouse or gerbil. Each file follows several points on one animal. The 30 tracks come from 16 recordings across three phyla. Animals filmed together share one recording ID.

## Reproduce the coordinates

With Python 3.11 or newer, NumPy and h5py installed, run the following from this folder.

```sh
python fetch_tracks.py --output bodyplan-data
```

The download is about 145 MiB. The program checks each file's SHA-256 against `source-inventory.json`. To fetch one recording, append `--group gerbils`. Use a fresh output folder each time. The optional `--cache` argument can point to a previous raw download directory.

Each NPZ file contains `xy`, with a pair of coordinates for each point at each time. It also contains `seconds`, `frame` and the point `names`. A missing position has the value NaN. The manifest gives the units, track label, recording method and source credit. Worm recordings supply their own times in seconds. Their `frame` column counts successive samples. In the other recordings, elapsed time comes from the camera frame count and the published recording rate. Each video has its own clock.

## Rodents, fruit flies and bumblebees

Use the continuous **Tracking (.slp)** example for each of the six datasets. The study's rates are 80 Hz for open-field mice, 40 Hz for home-cage mice, 25 Hz for gerbils, 100 Hz for single flies, 150 Hz for paired flies and 100 Hz for bumblebees. All six demonstration MP4s encode playback at 25 Hz. Five native tracking files store label-type points without point confidence, so the amount of manual editing is unknown. The single-fly file includes scored predictions. The tracks identify recorded positions in the image. Tracking or identity errors can propagate to the forecast target. [SLEAP datasets](https://docs.sleap.ai/latest/reference/datasets/) · [Pereira et al., Nature Methods, 2022](https://doi.org/10.1038/s41592-022-01426-1)

| Recording | Acquisition contributors |
| --- | --- |
| Open-field mice | John D’Uva, Mikhail Kislin, Samuel S.-H. Wang |
| Home-cage mice | Eleni Papadoyannis, Mala Murthy, Annegret Falkner |
| Gerbils | Catalin Mitelut, Marielisa Diez Castro, Dan H. Sanes |
| Single fruit fly | Talmo Pereira, Gordon Berman, Joshua Shaevitz |
| Paired fruit flies | Junyu Li, Shruthi Ravindranath, Talmo Pereira, Mala Murthy |
| Bumblebees | Grace McKenzie-Smith, Z. Yan Wang, Joshua Shaevitz, Sarah Kocher |

The SLEAP project applies its BSD license to the datasets. The license text supplied with the mirrored tracks is the Clear BSD License. Retain `SLEAP-LICENSE.txt`, the paper citation and the relevant acquisition credits when redistributing these data. [Maintainer's data-license statement](https://github.com/talmolab/sleap/discussions/2906#discussioncomment-19503747)

## Desert locusts

Angela Albi and Daniele Carlesso provided tracks for five animals recorded together. The seven indexed pixel coordinates come from a TRex/YOLO pose export. Its internal time column reflects playback at 30 Hz. The video was acquired at 5 Hz. The movement sample archive matches the five original files at the historical Git revision below. The current GitHub branch has different tracks. The study's calibration of the 60 cm arena does not establish a pixel-to-body-length conversion for each animal. Credit Angela Albi, Tristan Walter and Daniele Carlesso for the video. The tracking data and video are licensed under CC BY 4.0. [Original tracks](https://github.com/albiangela/TRex-tutorials-data/tree/e3423e3920e89d6018bc123371b7fb9cdd47f2f5/TRex-tracking-output/locusts-5/data) · [Source license](https://github.com/albiangela/TRex-tutorials-data/blob/e3423e3920e89d6018bc123371b7fb9cdd47f2f5/dataset-info-files/LICENSE) · [Original video record](https://doi.org/10.17617/3.7F5MGE)

## Nematodes

Each of these nine adult *Caenorhabditis elegans* recordings contains an optical segmentation with 49 head-to-tail centreline samples, measured times in seconds and coordinates in micrometres. Samples at corresponding fractional positions along the body can move relative to the tissue. Local worm ID 1 identifies only the animal within that recording. Each of the three recordings per strain has a distinct capture date. A cross-day individual identifier is unavailable. The archive credits Avelino Javer, Michael Currie, Jim Hokanson, Chee Wai Lee, Kezhi Li, Eviatar Yemini, Laura J. Grundy, Chris Li, Quee-Lim Ch’ng, William R. Schafer, Rex Kerr and André E. X. Brown. Each record licenses its data under CC BY 4.0. [Acquisition methods](https://doi.org/10.1038/nmeth.2560) · [Tracking and database](https://doi.org/10.1038/s41592-018-0112-1) · [WCON format](https://github.com/openworm/tracker-commons/blob/master/WCON_format.md)

| Strain | Recording records |
| --- | --- |
| N2 | [September 2009](https://doi.org/10.5281/zenodo.1032845), [January 2010](https://doi.org/10.5281/zenodo.1005864), [July 2009](https://doi.org/10.5281/zenodo.1032915) |
| CB1282 dpy-20(e1282) IV | [25 August 2011](https://doi.org/10.5281/zenodo.1024230), [24 August 2011](https://doi.org/10.5281/zenodo.1019605), [19 August 2011](https://doi.org/10.5281/zenodo.1025134) |
| CB678 lon-2(e678) X | [19 August 2011](https://doi.org/10.5281/zenodo.1013091), [4 August 2011](https://doi.org/10.5281/zenodo.1011834), [9 August 2011](https://doi.org/10.5281/zenodo.1018179) |

## Conversions and scope

The converter unpacks the original point order, groups by source track, emits paired x/y values in float32, and keeps absent or nonfinite points missing. It preserves native source scales and all available time rows. All animals sharing a video remain in the same recording group. Motion is observed through different optical tracking systems, with different projections, landmarks and error profiles. A lookup of released source names does not establish anatomical homology across species. The sources and acquisition contributors do not endorse a downstream forecaster or its results. Include `CC-BY-4.0.txt` and the applicable source credits and modification description with copies or adaptations of the CC-licensed data. [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)

The points in this collection were tracked in camera images. For neural measurements, use the [vertebrate neural data register](https://eliminatenoise.github.io/NeuroTranslation/vertebrate-neural-data/). [Fly and worm wiring maps](../../../docs/when-fly-and-worm-data-help.md) offer a separate source for questions about structure and development.
