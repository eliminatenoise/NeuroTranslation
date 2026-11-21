# Next Neuron Prediction

A proposed NeuroTranslation task. From the activity recorded so far, predict which of the recorded neurons will fire the next spike. A spike is a brief electrical impulse.

To test the idea, stop a recording before a spike and make the prediction using only earlier activity. Play the recording forward to see which neuron fired. If two neurons fired too close together for the recorder to resolve the order, score that case as unresolved.

An electrode can pick up spikes from several neurons. In the one-week reach study, the model forecasts how many spikes each of 37 electrode contacts will pick up in the next 100 milliseconds. A count can be right even when the identity of the first neuron is unknown. [Read the one-week reach study](../models/reach-feedback-week/README.md).

Name each target at the level the data support, whether that is one neuron, one electrode channel or activity pooled across a population. A prediction tested on simulated spikes describes the simulation. Testing which recorded neuron fires next requires recordings kept out of training that distinguish the neurons and the order in which they fired.

Shared glossary revision 40 · SHA-256 `0a508c6a52f9e1dcf49f6bcfbbcf3a52136a24aee863eb28785f76fef0c5d03a`
