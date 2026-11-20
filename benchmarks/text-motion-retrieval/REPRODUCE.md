# Reproduce the recording search

The study pairs a description from a volunteer with the motion-capture recording shown to that volunteer. Karlsruhe published each description beside the corresponding movement file. This test asks which recording in a gallery a sentence describes. Replaying a stored trajectory and producing a new one are separate experiments. [KIT Motion–Language Dataset](https://motion-annotation.humanoids.kit.edu/dataset/) · [Plappert, Mandery and Asfour, 2016](https://doi.org/10.1089/big.2016.0028)

## Input

Obtain the 22 June 2017 ZIP from KIT. Keep it on your machine. Work from a directory containing the Python files, policy and frozen manifest. Use Python 3.11 or later with NumPy and PyTorch installed. The recorded study used Python 3.13 and a CPU build of PyTorch. The archive is about 4.16 GB. [Official download](https://motion-annotation.humanoids.kit.edu/dataset/)

```sh
python -m venv .venv
```

Activate the environment and run the commands below. In PowerShell the activation command is `.venv\Scripts\Activate.ps1`. On macOS and Linux use `source .venv/bin/activate`.

```sh
python -m pip install -r requirements.txt
python -m unittest test_retrieval.py
python kit_data.py train --zip 2017-06-22.zip --manifest manifest.json --local local
python study.py fit --manifest manifest.json --data local/data --work experiment --threads 2
python kit_data.py assessment --zip 2017-06-22.zip --manifest manifest.json --local local
python study.py assess --manifest manifest.json --data local/data --work experiment --threads 2
```

Use a fresh experiment directory. The fit command writes the final fitted parameters and their hashes before the assessment command opens the selected gallery. Results and the complete score matrices appear under `experiment/assessment`. The two commands that read the ZIP verify the archive and importer hashes first. The reserve has no preparation command. The manifest also supports a fresh catalogue audit with `kit_data.py manifest`, a different output manifest filename, and the same ZIP and local directory. That audit contacts KIT for the publisher’s current catalogue pages. Each page digest dates the evidence used to assign its subject and action.

## What the models receive

Each recording contributes 20 retargeted joint-angle channels for the shoulders, elbows, hips, knees and ankles on both sides. Two further channels describe the root’s horizontal distance from its starting point and its vertical offset. KIT supplied the fitted skeletal pose in its Master Motor Map format. The importer works in the source coordinate system and interpolates the channels at 24 points spanning the clip. This removes elapsed duration, starting position and compass heading from the inputs. The models see neither the source ID nor the tag or subject fields. The action-category comparison separately receives privileged catalogue labels. [KIT file format and example](https://motion-annotation.humanoids.kit.edu/dataset/)

A caption supplies up to 32 words and numbers. The first model predicts simple motion summaries from word counts, then ranks the recordings by their agreement with those predictions. The second model learns which words and phases of the motion are informative through self-attention. It brings genuine description–recording pairs closer together in a shared numerical representation. A third fit uses the same initialization and training procedure with the caption groups assigned to the wrong recordings.

For every caption we rank all the assessment recordings. Recall at one is the fraction of queries whose recording came first. Mean reciprocal rank gives 1 for first place, ½ for second, ⅓ for third and so on. We average captions within each source recording before averaging recordings. Equal scores share credit according to every possible ordering. Additional scores count any clip with identical normalized wording, or any genuine caption of a recording searched in reverse. Those rules count known relationships. Two people can still describe the same gesture in different words, and a caption can plausibly describe a second recording that nobody paired it with.

The action comparison uses the catalogue’s task tags, first matching a short list of broad movement names. When none matches, the source tag combination supplies its own class. A singleton contributes no same-category competitors. The oracle receives the correct category and divides credit among recordings sharing it. That answers how far a perfect category label alone can narrow this gallery.

## Exercise the software on invented inputs

```sh
python fixture.py toy
python study.py fit --manifest toy/manifest.json --data toy --work toy-run
python study.py assess --manifest toy/manifest.json --data toy --work toy-run
```

The fixture tests tied scores, repeated text, subject grouping and reserved files. Its curves and words were generated for this purpose. They supply no evidence about a person's movements.

## Search your local fitted gallery

Once fitting and scoring finish, enter a new description. The command prints the IDs of the closest recordings and their cosine similarity. That score measures proximity in the fitted representation. It is not a probability of success. The query does not change the weights.

```sh
python rank.py "walking forward" --manifest manifest.json --data local/data --fit experiment/fit --top 5
```
