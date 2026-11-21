# Neural signals, muscle and movement

Two recorded tasks put different forecasts to the test. In one, small Transformers predict a macaque’s next reach and cortical spike counts. In another, matched neural networks group electrical and motion histories in different ways to predict a person’s leg-muscle voltages and the path of a marker over the sacrum. A third calculation tests what simulated muscle–tendon geometry adds to the macaque reach forecast.

[Open the results](https://eliminatenoise.github.io/NeuroTranslation/neural-and-muscle-composites/) · [Download the report, models and code](https://eliminatenoise.github.io/NeuroTranslation/neural-and-muscle-composites/study.zip)

## Start with one forecast

Extract the ZIP fully. Open **Open on Windows**, **Open on macOS** or **Open on Linux** for the report. The same report opens directly as **index.html**. Open **study.pdf** to read or print it offline.

For an actual fitted forecast, use Python with NumPy and PyTorch. From the extracted directory or this repository folder:

```sh
python -m pip install numpy torch
python reach/predict.py reach/invented-handle.json --task movement --architecture diffusion
```

The four rows are invented handle coordinates and changes in centimetres. They contain no recordings. The program uses a model trained on the earlier macaque session. It returns the mean and marginal deciles of 16 sampled forecasts for displacement at 50 and 100 ms. Try `--architecture ar` and `--architecture hybrid` with the same input. A forecast on an invented example has no measured outcome. The report gives errors against measured outcomes.

## Reproduce a comparison

- [Reach comparison](reach/README.md). The source pack includes all 36 macaque fits, train-only scales, original reconstruction and full scoring programs. Either body sensor can be used. The original study, source hashes and required Python packages are identified.
- [Balance comparison](balance/README.md). Rebuild the source selection from OpenNeuro, fit the models on 18 people and score the same six comparison people. The recordings, individual event results and fitted human parameters stay on the machine that runs the experiment.
- [Geometry comparison](geometry/README.md). Run the weighted regression with and without modelled muscle–tendon lengths. The measured outcome is the later handle displacement.

Analysis code and text carry [CC0 1.0](LICENSE.txt) to the extent of the authors’ rights. The reaching data from Chowdhury, Glaser and Miller and the balance data from Peterson and Ferris have their own CC0 dedications. Third-party software, publications and linked services retain their own terms. [Reach data and terms](https://doi.org/10.5061/dryad.nk98sf7q7) · [Balance data and terms](https://doi.org/10.18112/openneuro.ds003739.v1.0.3)
