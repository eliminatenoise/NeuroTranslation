# Run two forecasts from a grasp

This NeuroTranslate preview takes 100 milliseconds of sensor readings and spike counts from one recorded task. It estimates how the six sensor readings will change and how many spikes each of 93 sorted cortical units will produce over the next 20 milliseconds.

1. [Download and extract the whole ZIP](paired-grasp-model.zip).
2. Use Python 3 with NumPy installed in the environment you will run.
3. Open **Run on Windows.cmd** or **Run on macOS.command**. On Linux, run **Run on Linux.sh** from a terminal. You can also run `python grasp.py` from the extracted folder.

The built-in example uses invented readings. The full schema inside the ZIP explains how to supply a history from the named Brochier L recording. The model uses that recording’s sensor and cortical unit labels. The sensor estimates are in raw recording counts, and conversion to newtons or millimetres remains unverified.

The ZIP includes both training seeds, three comparison choices, the Python source, weights, credits and checksums. The equal and balanced choices train the two forecasts together. The separate choice combines the outputs of two individually fitted forecasts. See how the fits compared with measurements. [Training study](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/grasp-sensor/joint/balance/)
