# NeuroTranslate model versions

To try a movement forecast now, open a **0.0** browser example. **0.1** includes downloadable walking models. **0.2** is a study of whether learning from a wider range of recordings improves forecasts for new people. Its trained model and scores on new people have yet to be released. [Technical guide](TECHNICAL.md) · [Model downloads](../README.md#current-downloads)

## 0.0 · Run a forecast

Open shared motion and choose what to forecast. You can start with the invented readings or enter your own. The model uses those earlier readings to estimate what happens next. For the separately trained joint model, extract the 0.0 download and open the Demo launcher for your operating system. It runs locally with Python and NumPy. [Open shared motion](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/) · [Joint-model setup](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/) · [Download 0.0](../neurotranslate-0.0.zip)

One early 0.0 model learned from wrist movement recorded by a headset and from a rat moving along a track. Its shared calculation used **5,184 learned numbers**. That count belongs to the part reused by those tasks. The 0.2 study includes it as a comparison. In five earlier tests cited by the study, a simpler forecast matched it or did better on new people. Other 0.0 models have their own weights. [Description of this comparison model](../neurotranslate-0.2/PROTOCOL-SIMPLE.md#the-earlier-shared-encoder-neurotranslate-00)

## 0.1 · Compare walking models

The Research Edition reads the last 200 milliseconds of muscle activity and the push on a floor plate. It estimates whether the plate will start carrying weight and how much upward or downward force will accumulate over the next tenth of a second. You can run the saved walking fit with the TML-d24 Research Edition base, the larger set of weights named in the setup instructions. Another 0.1 walking fit uses a different base called Inkling 2 Mini. Each fit needs its own base. [Research Edition walking download and setup](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24) · [Inkling walking example](../neurotranslate-0.1/README.md)

A pass means sending the same example through the Research Edition’s middle layers again. On nine previously scored walks from three people, three passes gave smaller errors for both forecasts than two or four passes. This tests how many times to run the same fitted model. [Walking study comparing two, three and four passes](../../benchmarks/expanded-walking-research/pass-count/near-three/SIMPLE.md)

## 0.2 · Test learning across recordings

A wrist camera, a muscle electrode and a force plate each record something different about movement. The 0.2 plan pools training recordings so one model can learn patterns that might carry between tasks. The plan keeps the shared weights fixed for testing and fits small parts that turn the output into each required forecast. One human test predicts the movement of body markers in the Gait120 study. The other predicts the movement of the wrists in AJILE12. Both start with earlier movement alone. Separate comparisons add electrical readings from muscle or from the surface of the brain.

A longer recording supplies more short pieces of movement to train on. To test the effect of variety, the study gives models the same number of pieces while changing the mix of recording sources. A separate comparison varies the number of pieces. The published inventory lists the training material counted for these tests. Success will depend on the forecasts scored against later measurements. [Study plan](../neurotranslate-0.2/PROTOCOL-SIMPLE.md) · [Training inventory](../neurotranslate-0.2/MIXTURE-MANIFEST.json)
