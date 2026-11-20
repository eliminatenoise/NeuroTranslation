# NeuroTranslate 0.0

**The current CPU package has three measurement paths.** One checkpoint forecasts a short movement distance for a human wrist or a rat. An additional path estimates two angles of a human right wrist from its recent motion, with optional electrical measurements from the forearm and scalp. It reuses the trained temporal layers and adds a separately fitted angle readout. The two original distance predictions are preserved. [Download the three-domain package](neurotranslate-0.0.zip) · [Source, examples and results](neurotranslate-0.0/)

### Wrist bend and sideways tilt

In six tests, each leaving one of six training participants out, reading past wrist angles alone produced **4.503°** of two-axis error. Adding forearm measurements lowered it to **4.291°**. With scalp measurements included as well, it was **4.491°**. An earlier movement-and-forearm correction model reached **3.549°** on the same observations. A matched control with randomly initialized frozen temporal layers also performed at least as well in all three input conditions. The comparison supports running the added angle path but did not establish a predictive benefit from the pretrained core on this task. The fitter and source-data recipe preserve separate angle and distance units. [Angular study and methods](neurotranslate-0.0/README.md)

## A shared model for two tracking tasks

A headset tracks a wrist in three dimensions. A camera tracks a rat in two dimensions. Both can measure how far the point moved between observations. Give this model five earlier positions in the same coordinate system, or the four intervals calculated from those positions. It predicts the straight-line distance to the next position about a quarter-second later, in centimetres.

**[Run the shared model in a browser](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/).** Compare an actual rat training trip with an invented wrist history or enter your own earlier tracking samples. The model runs on your device. You can save the self-contained page for offline use.

The two tasks use **one fitted Transformer checkpoint**. The same attention layers learn from both kinds of movement. A small final readout for each task turns the shared representation into a distance. The result gives a magnitude. The positions along a path and its direction require other predictions. [Download the model and source (ZIP)](shared-motion-distance.zip) · [Usage and reproduction](shared-motion/README.md)

The same fitted weights also run directly in a browser. The JavaScript API accepts the four motion intervals or derives them from time-stamped tracking points. It uses one model file for both tasks, and both distributed examples are invented. [Browser runtime and API](shared-motion-browser/) · [Download the standalone JavaScript package](shared-motion-browser.zip)

## Did learning together help?

| Quarter-second forecast | Human wrist | Rat position |
| --- | ---: | ---: |
| Shared Transformer | 1.725 cm | 1.310 cm |
| Single-task Transformer, equal exposure to its own recordings | 1.782 cm | 1.342 cm |
| Single-task Transformer, equal total training updates | 1.759 cm | 1.388 cm |
| Best of the two linear baselines | 1.922 cm | 1.119 cm |

Each entry is mean absolute error. Smaller is better. Each of six acquisition groups for the human wrist and each of nine held-out trips for the rat had equal weight within its task. The comparison used 583 wrist windows and 106 rat windows. Both evaluation collections had been examined in earlier work, and all the rat trips came from one animal. Windows from the same group or trip can contain related movements.

The shared model’s average errors were slightly lower than those of the separately trained attention models. On both tasks the uncertainty interval for the equal-exposure comparison included zero. The linear baseline also beat the shared model on the rat recordings. Neither task passed the full decision rule for a transfer benefit. The weights demonstrate joint learning on these two collections. Additional people, animals and movements remain to be tested. [Frozen protocol and complete results](shared-motion/shared-motion-model/README.md)

![Mean absolute error and uncertainty for the shared model compared with single-task models. The paired intervals for both tasks include zero.](figures/transfer-comparison.png)

[Download the figure as a PDF](figures/transfer-comparison.pdf) · [Figure source](figures/plot_transfer.py)
