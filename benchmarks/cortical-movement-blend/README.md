# A movement blend for NeuroTranslate

[Simple guide](SIMPLE.md) · [Technical guide](TECHNICAL.md) · [Measurements](results.json)

This offline example runs three fitted hand movement models. It also shows what each forecast becomes when mixed with a prediction of no movement. The blend reduced both average errors compared with the original models on two archival recording days for one calibrated animal. Predicting no movement still gave the lowest ending-position error on August 19. The included model and installer requirements run a generated example. The guides explain the measured comparison and how to supply prepared archive counts.

On a third recording day, the published blend gave the lowest average ending-position error. Giving larger reaches more weight during calibration improved the blend on larger movements and raised its error near rest. [Simple report](third-recording/SIMPLE.md) · [Technical report](third-recording/TECHNICAL.md)

The position-history comparison adds forecasts based on the hand’s recent speed and direction. Compare six forecasts on the same three recorded days and try the equal blend with your own numbers. [Interactive comparison](https://eliminatenoise.github.io/NeuroTranslation/hand-position-forecast/) · [Replay code and offline download](position-history/)
