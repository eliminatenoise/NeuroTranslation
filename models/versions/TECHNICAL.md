# NeuroTranslate versions and evaluation designs

[Simple guide](SIMPLE.md) · [Model downloads](../README.md#current-downloads)

## 0.0 · Released checkpoints

Shared motion runs in the browser. The separately trained joint model runs through the 0.0 ZIP’s local Demo launchers with Python and NumPy. The 0.2 protocol specifies one earlier 0.0 comparator, the 5,184-parameter shared encoder in `movement-weights.npz`. It learned from HoloAssist headset wrist tracking and W-track distance in one rat. In the five unseen-person comparisons cited for this encoder, simpler forecasts matched or beat it. The parameter count applies only to this encoder. [Shared-motion demo](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/) · [Joint-model setup](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/) · [0.0 download](../neurotranslate-0.0.zip) · [Comparator specification](../neurotranslate-0.2/PROTOCOL.json)

## 0.1 · Research Edition and Inkling walking fits

The expanded Research Edition walking checkpoint uses the TML-d24 Research Edition base. It takes 200 ms of muscle activity and vertical force and predicts new-load probability and signed vertical impulse over the next 100 ms. The companion walking adapter uses the Inkling 2 Mini base. In the expanded Research Edition, a pass repeats the middle layers at inference with fixed weights. At three passes, impulse and probability errors were lower than at two or four on nine previously scored validation walks from three people. [Expanded checkpoint and Linux setup](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24) · [Inkling adapter and demo](../neurotranslate-0.1/README.md) · [Pass-count study](../../benchmarks/expanded-walking-research/pass-count/near-three/TECHNICAL.md)

## 0.2 · Pooled training and transfer study

The protocol calls for one encoder trained across recording sources, then frozen while task-specific adapters and readouts are fitted. The two primary human tests use movement history alone to predict body-marker displacement in Gait120 and wrist displacement in AJILE12. Secondary comparisons add surface muscle activity (EMG) or cortical surface potentials (ECoG). The diversity comparisons vary the training sources at equal window counts. Separate comparisons vary the number of training windows. The protocol and training-mixture manifest are public. No trained 0.2 checkpoint or fresh-person score has been released. [Technical protocol](../neurotranslate-0.2/PROTOCOL.md) · [Training-mixture manifest](../neurotranslate-0.2/MIXTURE-MANIFEST.json)
