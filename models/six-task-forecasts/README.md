# Try six forecasts from one shared model

This experimental release gives you two sizes of the same six-task NeuroTranslate model. Its input layouts come from human balance, macaque reaching and macaque grasp recordings. Each task keeps its own channels, timing and measurement units.

1. [Download and extract the whole ZIP](neurotranslate-six-task-preview.zip).
2. Open **Start here.html** in a browser or use the launcher for your computer. Choose a task and compare the two model sizes on two invented histories. The browser displays saved outputs from the trained models.
3. To recalculate an example or edit the readings, use Python 3 with NumPy and run the included **forecast.py**. Its README gives commands and explains the input fields.

The ZIP includes both checkpoints from the first training seed, the Python source, launchers, exact input layouts, example files and source credits. The results compared groups from previously used archives. Each input layout belongs to its named recording task. [Six-task comparison](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/shared-tasks/)
