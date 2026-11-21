# Recording credits

The checkpoint contains fitted parameters and population-scale statistics. The example inputs are fictional. The following researchers collected the recordings used to fit the model or test its forecasts. Retain their credits, source references, licence notices and the description of the transformations with redistributed copies.

- Raeed Chowdhury, Joshua Glaser and Lee Miller recorded macaque arm movement and cortical activity. The preparation converts motion to millimetres, combines spikes by acquisition contact and aligns the two measurements on a common clock. [Dryad recording, CC0](https://doi.org/10.5061/dryad.nk98sf7q7)

- Steven Peterson and Daniel Ferris recorded the human balance data. The preparation aligns scalp and leg muscle voltages with sacrum marker positions, then computes earlier-window features, future muscle RMS and marker displacement. [OpenNeuro ds003739 v1.0.3, CC0](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)

- Justin Shin and Shantanu Jadhav recorded rats navigating a W-shaped track. The preparation groups spikes on a one-millisecond clock and computes an activity history for every locally sorted candidate. [DANDI 000978 v0.240511.0307](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [CC BY 4.0](notices/CC-BY-4.0.txt)

- Adam Atanas, Jungsoo Kim and colleagues recorded nuclear fluorescence in adult worms. Martin Haesemeyer and Kaarthik Balakrishnan collected the larval zebrafish recordings. Four earlier fluorescence readings and the next timed observation use a fixed scale for each assay. The original imaging pipelines include retrospective processing. [Worm data](https://doi.org/10.5281/zenodo.19388374) · [CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/) · [Fish data](https://doi.org/10.48324/dandi.000235/0.230316.1600) · [CC BY 4.0](notices/CC-BY-4.0.txt)

- The SLEAP collection provided tracked points for training and assessment. John D’Uva, Mikhail Kislin and Samuel S.-H. Wang contributed the open-field mouse recording. Catalin Mitelut, Marielisa Diez Castro and Dan H. Sanes contributed the gerbil recording. Earlier points and the future displacement are expressed relative to the visible body radius at issue. Camera views supply two dimensions. The additional held recordings include tracks from SLEAP, Angela Albi and Daniele Carlesso’s locust tracks, and Avelino Javer and colleagues' worm tracking sources. The input builder lists recording-level acquisition credits and modifications. [Recording credits and changes](inputs/sources/landmark/SOURCES.md) · [SLEAP data collection](https://docs.sleap.ai/latest/reference/datasets/) · [Pereira et al.](https://doi.org/10.1038/s41592-022-01426-1) · [SLEAP Clear BSD licence](notices/SLEAP-LICENSE.txt) · [CC BY 4.0](notices/CC-BY-4.0.txt)

The model learns from these transformed histories. Human training uses pooled healthy-adult measurements across people. The released checkpoint has one set of learned weights and contains no participant-specific fitted branch. Preserve the applicable source-specific terms when reusing derived material.

