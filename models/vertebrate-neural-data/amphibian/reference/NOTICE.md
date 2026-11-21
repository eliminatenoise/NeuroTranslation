# Source and reuse terms

Justin Shin and Shantanu Jadhav (2024), *Single Day W-Track Learning*, DANDI Archive, version 0.240511.0307. DANDI lists the release under Creative Commons Attribution 4.0 International. Credit the authors, link the license, cite the release and identify further changes when reusing the recording or the derived material here. [Dataset DOI](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Release metadata](https://api.dandiarchive.org/api/dandisets/000978/versions/0.240511.0307/info/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

| Animal | NWB asset and archive SHA-256 |
| --- | --- |
| JDS-SingleDay-JS14 | [4b7c7959-04b3-4817-8f96-1af6f41888c1](https://api.dandiarchive.org/api/assets/4b7c7959-04b3-4817-8f96-1af6f41888c1/) · `6b8cf8ce3bbe34374e10a8a310592d1ae9762b20554569bc3c45fcfecdcf67b6` |
| JDS-SingleDay-ER1 | [b6425692-0f32-4087-8412-aebcfc37cd96](https://api.dandiarchive.org/api/assets/b6425692-0f32-4087-8412-aebcfc37cd96/) · `508f7f4e5c1ef2b49373aef815bc64e6591ed7889407a3d57089d38dd4e2dba4` |

The JS14 trial extraction selected trials 55–78 and 80–89 and converted their contents into per-trip files. The ER1 extraction selected trial rows 0–9 and copied their unit event times and trial bounds. The benchmark uses only those bounds, the sorted-unit table and event times. It groups the times on a one-millisecond clock and reports fitted coefficients, counts and summary scores from the observed events. Those data-derived files and result tables carry the original CC BY 4.0 attribution. The archive digests above identify the full objects. The sparse download verifies individual ranges and final extracted files. [JS14 extraction](https://github.com/eliminatenoise/NeuroTranslation/tree/3e43795adeb6c33b8302e952f45af03be5a71fb1/benchmarks/wtrack-neural-motion/recording)

The original benchmark code and authored fictional input are dedicated to the public domain under CC0 1.0. The displayed probabilities in the fictional example come from the fitted coefficients. The dataset authors retain credit for their recordings. [CC0 legal text](LICENSE-CODE)
