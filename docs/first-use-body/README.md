# Forecast an unfamiliar body

Open `index.html` in a browser. Choose a figure and move the time slider. Filled points are the current observations, rings are future estimates, and crosses reveal the next known positions when the exact selected time is present. The three visible examples are invented. They illustrate how model input changes with body shape and the number of tracked points.

The model uses the mixed-species fit recorded in the research package. It operates on tracked 2D coordinates, starting with a last-position forecast. It can use its fitted weights when five earlier observations have accumulated and the point's own history is sufficiently complete. It does not fit new weights or ask the user to perform a prescribed movement. The study compared different bodies, camera conditions and recording rates. Accuracy and timing apply to those measurements. [Results and source credits](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/first-use-body).

To open your own tracking data, expand **Open my own tracked movement**, then select a JSON file like `example.json`. Times increase in seconds, and points keep their local order within a recording. The page runs locally. The same input also runs through `python predict.py example.json` in the NeuroTranslate 0.0 download.

Original page and code use the repository’s CC0 dedication. The trained model comes with the source-specific notices included here.
