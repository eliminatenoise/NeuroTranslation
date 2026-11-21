# What can a fly or a worm teach a model about a vertebrate?

The programme’s main target is neural activity across vertebrate clades and classes. A different animal can still help us learn a particular rule. The rule that predicts which two neurons connect, the rule that predicts the next spike and the rule that converts muscle tension into movement make three different predictions. Each needs its own measurements.

## A shared cue for a growing nerve fiber

Researchers isolated proteins in embryonic chick brain that promote growing nerve fibers in an experiment. The proteins, called netrins, are relatives of UNC-6, a protein involved in guiding growing fibers in the worm. Here is a concrete reason to test whether information from an invertebrate helps us predict a vertebrate process. The observation concerns a particular molecular cue. It leaves open how other cues, cell types and developmental stages shape the resulting circuit. [Original chick–worm comparison](https://pubmed.ncbi.nlm.nih.gov/8062384/)

## Which data answer which question?

FlyWire maps roughly 50 million chemical synapses in one adult female fruit fly brain. It supplies detailed examples of which neurons connect. *C. elegans* offers a different advantage. Eight animals of the same genetic strain, examined at different ages, provide a series of wiring maps across development. Adult whole-animal reconstructions also map connections from motor neurons to muscle. The series reconstructs different individuals at different ages. To test a forecast of the next neural event, we need a recording that contains the events and their times. [FlyWire brain reconstruction](https://www.nature.com/articles/s41586-024-07558-y) · [Worm developmental series](https://www.nature.com/articles/s41586-021-03778-8) · [Worm whole-animal connectomes](https://www.nature.com/articles/s41586-019-1352-7)

## The same contractile machinery can move a different body

Flies and worms have muscles. In both, actin and myosin are part of the apparatus that generates force. Fly limb muscles transmit force through tendon cells to an external skeleton. In one specialized system, the muscles that power flight, the elastic thorax and stretch-sensitive muscle allow many wing strokes for each motor-neuron impulse. That timing is specific to those flight muscles. [Adult fly leg muscles and tendons](https://pubmed.ncbi.nlm.nih.gov/15537687/) · [Fly muscle–tendon junction](https://pubmed.ncbi.nlm.nih.gov/17314133/) · [Calcium and mechanical power in flying Drosophila](https://pmc.ncbi.nlm.nih.gov/articles/PMC1449689/)

The worm has another arrangement. Its body-wall muscles contain obliquely arranged contractile filaments. Their attachments transmit force to the body wall. Experiments that changed muscle contraction measured a corresponding change in whole-body stiffness. A model of movement therefore needs to know what receives the force: a flexible body wall, a jointed outer skeleton or a vertebrate skeleton connected by tendons. Shared contractile machinery alone does not give a common conversion from neural activity to displacement. [Worm muscle anatomy](https://pmc.ncbi.nlm.nih.gov/articles/PMC2113919/) · [Direct stiffness measurements](https://pmc.ncbi.nlm.nih.gov/articles/PMC3077690/)

## Give each proposed use a test

Choose a neural measurement and a forecast horizon that both sources support. Keep the architecture, training budget and controls fixed. Train one version on vertebrate recordings and a second with part of that training drawn from an invertebrate. Keep whole vertebrate animals and recordings out of both fits. Report error for each animal, including failures and any effect on rarely active units. A reliable improvement would support using the additional source for that task. Comparable forecasts can also arise from the same indicator chemistry, filtering or sampling rate. Establishing a shared developmental mechanism would require independent developmental measurements and a prediction that distinguishes that mechanism from those alternatives.

## A test using activity recorded over time

Can four recent brightness readings predict the next one in a fish’s forebrain? One experiment replaced a quarter of a fish’s training examples with calcium recordings from eight worms, then scored the same forecasts on seven unseen fish. This tests how well a particular signal carries across recordings. The development of a circuit and the forces it produces remain separate questions. [See the matched forecasts and every fish’s result](https://eliminatenoise.github.io/NeuroTranslation/worm-to-vertebrate/).
