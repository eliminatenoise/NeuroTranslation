# Sources and terms

[Results](README.md) · [Results, Simple edition](README-SIMPLE.md) · [Protocol](PROTOCOL.md) · [Protocol, Simple edition](PROTOCOL-SIMPLE.md) · [Run code](README-CODE.md) · [Run code, Simple edition](README-CODE-SIMPLE.md)

This file credits the recordings behind the walking-force quantity ladder, says what this track did with them, names the sources that the scored published checkpoints inherit, and gives the terms of the files in this folder.

## The recordings

Tamaya Van Criekinge, Wim Saeys, Steven Truijen, Luc Vereeck, Lizeth H. Sloot and Ann Hallemans collected the gait recordings and released them on figshare under CC0 1.0 Universal, a public-domain dedication. [Data on figshare](https://doi.org/10.6084/m9.figshare.24192480.v1) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)

The authors describe the acquisition in: Van Criekinge T., Saeys W., Truijen S., Vereeck L., Sloot L. H., Hallemans A. (2023). A full-body motion capture gait dataset of 138 able-bodied adults across the life span and 50 stroke survivors. *Scientific Data* 10, 852. The article is distributed under Creative Commons Attribution 4.0 International. [Article](https://doi.org/10.1038/s41597-023-02767-y) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

This track read only the healthy cohort, from the archive `138_HealthyPiG.zip` of that release (figshare file 42450060, 463,159,769 bytes, md5 `85235c73455d4df8434810d61517efbb`). The recordings of people after a stroke, which the same release holds, have never been accessed by the project.

## What this track did with the recordings

The dataset authors recorded the walks. Everything below is this project's processing, and the authors did not produce these models, forecasts or results.

- **Header probe.** It read the first 8,704 compressed bytes of 241 walk files to see which channels each file declares. No recorded sample was read at this step.
- **Downloads.** It fetched 105 walks of the 35 training-pool people and 60 walks of the 20 evaluation people as byte ranges of the archive. The receipts in [receipts/](receipts/) give each range and the sha256 of the bytes received. The 36 walks of the 12 earlier fit people were not downloaded again: they were read from the private copy that the project's earlier work on this archive had made, and checked against their recorded sizes and checksums.
- **Extraction.** From each walk it decoded the vertical force of force plates 1 and 2 and six named surface EMG channels, both sampled 1,000 times per second. Surface EMG is the voltage that muscles produce at the skin; it is not a nerve recording.
- **Rows and targets.** Every 20 ms it formed one row per plate from the last 200 ms, in ten 20 ms bins. From the plate force over the next 100 ms it derived the two targets: the signed vertical impulse in newton-seconds and the label of a new load.
- **Fits and scores.** It fitted 1,742 models on 12 to 47 people, issued their forecasts for the 20 evaluation people and computed the errors that the results editions report.

This folder holds no recording, no extracted array, no forecast and no target. It holds counts, hashes, byte ranges, the channel facts read from the file headers, aggregate results, and per-person errors under the participant codes that the archive itself uses (`SUBJ…`).

## Published checkpoints that were scored

The results also score models that the project had published earlier ([protocol](PROTOCOL.md) section 8). The scored files are the published ones; no refit replaced them, and none is redistributed in this folder. Two of them were also refitted, and the refits replaced no scored file. A gate before the run refitted the F4 baselines and reproduced the published file array for array ([protocol](PROTOCOL.md) section 13). The ladder's M3 at 12 people is this track's own refit of the model that F2 exports; it is scored as M3, beside F2. Scoring a checkpoint is not training on its sources: the sources named below that lie outside the Van Criekinge healthy cohort enter none of the ladder's fits.

- **F1**, the three-pass checkpoint of the [walking neural-scaling benchmark](../../benchmarks/walking-neural-scaling/README.md), was fitted on the 12 earlier fit people and on 8 people recorded in İzmir. The İzmir data are under CC BY 4.0 (`10.48623/aperta.286865`).
- **F2** (the same benchmark's tree models as ONNX files) and **F4** (the linear [force baselines](../force-baselines/README.md)) were fitted on the 12 earlier fit people of the Van Criekinge healthy cohort only.
- **F3**, the NeuroTranslate 0.0 walking-force preview, was fitted on the same 12 people. Its core carries shared weights from earlier training on other sources, among them worm imaging (Zenodo `10.5281/zenodo.19388374`) and SLEAP sample tracks. [Its notice](../neurotranslate-0.0/recorded-force/NOTICE.md) lists those sources and their licences.
- **F5**, the NeuroTranslate 0.1 Research Edition, was not issued, so no result here depends on it.

## Weights

The protocol (sections 17 and 18) provides for the release of the ladder's weights at 47 people under CC0 1.0 with this notice: the compact recurrent model of seed 20261124, the boosted trees as ONNX, and the ridge and logistic coefficients. They are not published yet, and this folder holds no fitted weights. Those weights were fitted only on Van Criekinge CC0 recordings.

## This folder's own files

The project dedicates its original code, prose and results in this folder to the public domain under CC0 1.0 Universal, to the extent of its rights. Source-derived material retains its applicable attribution terms. CC0 does not require attribution; the project credits the dataset and the article above and asks that reuses of these results do the same. [CC0 dedication](../../LICENSE)

Python, NumPy, PyTorch, safetensors, scikit-learn, joblib and ONNX Runtime are separately installed dependencies under their own terms. [README-CODE.md](README-CODE.md) gives the exact versions.
