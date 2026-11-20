# Which recording does the sentence describe?

A volunteer watches a person move and describes what happened. Given those words and 38 recordings, can a model find the one the volunteer saw? In this NeuroTranslation experiment the attention model placed the matching clip first in 5.6% of queries after averaging descriptions within each recording. Word counts paired with simple movement summaries reached 6.6%.

The source is the June 2017 KIT Motion–Language Dataset. We used 149 recordings from 16 KIT subject records to fit the models, then assessed 90 original descriptions of 38 recordings from 6 different catalogue subjects. An additional 31 recordings from 4 other subject records remained in reserve. Their motion and description files stayed unopened. KIT’s public catalogue supplies these identities; separation of catalogue IDs is the scope of the comparison. [Dataset and paper](https://motion-annotation.humanoids.kit.edu/dataset/)

| Ranking method | First place | Top five | Mean reciprocal rank |
| --- | ---: | ---: | ---: |
| Text and motion attention | 5.6% | 32.0% | 0.197 |
| Word counts and motion summaries | 6.6% | 32.9% | 0.200 |
| Caption to catalogue action | 7.7% | 23.4% | 0.180 |
| Attention trained on wrong recordings | 2.9% | 5.5% | 0.082 |
| Uniform random order | 2.6% | 13.2% | 0.111 |
| Given the correct catalogue action | 15.8% | 31.6% | 0.259 |

The attention model missed the comparison fixed before assessment. It had to beat chance, wrong pairings, the word-count baseline and the caption-to-action baseline on both first-place recall and mean reciprocal rank. Within the individual held-out subject records, its first-place difference from the word-count model ranged from -9.7 to +10.0 percentage points. These are outcomes for this gallery; repeated clips per subject limit claims about new people.

An exact recording is a demanding target. 34 of the 38 gallery recordings shared a catalogue action class with at least one other candidate. Walking accounts for 31 gallery clips. Even a random candidate matches the query’s action class 67.5% of the time. Among the 31 walks alone, exact first-place retrieval was 6.2% with attention, 7.0% with word counts and 3.2% by chance. Three catalogue subjects contributed only walks. All four singleton actions came from one subject record, making performer and task effects difficult to separate.

Of 90 assessment captions, 12 had wording that also appeared in training after lowercasing and tokenization. Six repeated a description attached to another assessment recording. The release supplies no annotator-disjoint split here. Different movements can warrant the same words, and volunteers can use different words for the same movement. The aggregate results give shared-wording matches and a reverse search for any genuine caption attached to a recording. [Aggregate results](results-summary.json)

The model ranks a stored recording. Its movement input consists of retargeted joint angles and root displacement measured relative to each clip’s start. The experiment contains no paired brain activity, muscle recordings or live camera control. An independently written description dates from viewing the recorded movement, so it cannot tell us what the performer intended before moving.

To rerun the experiment, download KIT’s original archive and build the embeddings locally. The instructions also show how to search the fitted gallery with your own words. [Reproduction and local search](REPRODUCE.md) · [Study policy](policy.json) · [Data credits and code licence](NOTICE.md)
