# Describe an outcome in ordinary words

Text selects a forecast or a goal for the simulator. “Which recorded neuron fires next?” selects the spike-ranking task. “Raise the left hand above its shoulder” names a testable goal for the virtual avatar. A command does not supply a missing electrode signal, measure a muscle force, or operate a person's body. The supported task or goal appears for confirmation before switching examples. When a real local recording matches the selected task, retain its own labels, times and units.

The built-in text matcher runs locally. It handles common requests and asks for clarification when more than one outcome fits. A language model can propose the same small JSON message: `{"kind":"forecast","task":"rat_next_unit"}`, or `{"kind":"game_goal","effector":"left_hand","goal":"above_shoulder"}`. The validator accepts only known fields, tasks, effectors and goals. The actual forecast still comes from the single NeuroTranslate checkpoint. A game goal is checked using the avatar's resulting pose.

An optional local sentence encoder provides another way to match descriptions with measured outcomes. It uses a pinned copy of the Apache-2.0 **all-MiniLM-L6-v2** text encoder. The language weights are separate from the NeuroTranslate weights and remain an optional download. To use it, install PyTorch, Transformers and Safetensors in a Python environment and download the tokenizer, config and `model.safetensors` from the pinned model revision to your own folder. Then run:

```sh
python text_encoder.py --model-dir /path/to/local/encoder "Predict the calcium brightness in the next time step."
```

The command reads the model files and description locally. It returns a proposed task or an explicit unsupported result. In a development smoke check the encoder returned the expected result for ten of eleven authored descriptions. It abstained on an additional phrasing for a spike and made no incorrect affirmative selection in that small check. The result does not establish open-ended language comprehension. [Pinned encoder and license](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41)
