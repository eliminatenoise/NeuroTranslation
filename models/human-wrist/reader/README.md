# Where will the wrists move?

Extract the whole ZIP. Open the launcher for Windows, macOS or Linux, or open `index.html` in a recent browser. The reader works from a local file with the network disconnected. Keep the files together. The Atlas, Study and dataset links lead to their online editions.

Four generated motions let you run a temporal Transformer for the right and left wrist. Each reference and every fitted parameter in the built-in example come from simulation. The model sees 15 earlier camera frames and eight earlier voltage traces. It predicts where each wrist will be eight and fifteen camera frames after the last known position. Move a wrist or change the signal gain to see the prediction update. The table lists both horizons in pixels.

A separate experiment uses AJILE12, one participant, and a second recording day. Related methods, source code and the procedure for making your own private model-and-case package are in the [study source](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/human-wrist). Read [the package instructions](reproduce/README.md) to reproduce the generated example or import real data locally.
