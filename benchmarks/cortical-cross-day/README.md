# Cortical forecasts across recording days

[Download and run the model](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/cortical-cross-day/Cortical-Cross-Day.zip) · [Simple guide](SIMPLE.md) · [Technical guide](TECHNICAL.md)

The model uses recorded brain activity to forecast where a hand will be 100 milliseconds later. Across three independently trained models, error on 20 reserved second-day trials averaged 27.33 mm with some training from that day and 42.94 mm with day-one training alone. The single checkpoint in the download averaged 28.31 mm. The study covers one macaque and two recording days. The package runs a generated example and can replay the original public recording. [Aggregate results](results.json)
