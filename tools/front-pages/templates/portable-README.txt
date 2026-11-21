NEUROTRANSLATOR: RECENT FINGERTIP VELOCITY

A fingertip has moved. Give a saved decoder the 400 ms of brain activity that
came before, and ask how fast the fingertip was moving along two axes. The
answer is a signed number in metres per second, which could one day be set
against an independent measurement of the movement.

THIS SOURCE HAS NEVER BEEN RUN

The folder holds the interface's source and nothing else: preview_server.py,
preview.html and this file. It holds no model weights, no recordings and no
installed dependencies. The server and the page have never been started, not
even with --help. Everything below describes what the source is written to
do, not what it has been seen to do.

WHAT IT WOULD NEED

Two saved models, each a weights file and an architecture file, under
artifacts/loco_multiregion/portable/first60seconds/ and
artifacts/loco_multiregion/portable/full_training_partition/. The server
carries the expected checksum of each and refuses any other file. It also
needs the unchanged decoder modules (neural/__init__.py,
neural/portable_loco.py, neural/portable_numpy.py), NumPy and SciPy (the
recorded versions are numpy 2.5.3 and scipy 1.18.1), and Python 3.11 or
later. None of these is in this repository.

With all of that in place, the command would be:

python -I -B preview_server.py run --port 8765

and the page would open at http://127.0.0.1:8765/ on the same computer. The
server listens on that computer only, answers one request at a time, makes
no network calls and serves no files.

WHAT YOU WOULD GIVE IT

The recording is loco_20170215_02, a reaching recording from a macaque
(Zenodo record 3854034). Its spikes were sorted into 344 features: 163 from
primary motor cortex (M1), then 181 from primary somatosensory cortex (S1),
in a fixed order.

One request is a window of twenty rows of 344 counts, oldest row first. Each
row is one 20 ms bin, so the window covers 400 ms. The counts are spikes per
bin: whole numbers, not rates in hertz and not voltages. With the window go
the checksum of the source recording and the names of all 344 features in
order. The server does not fill these in for you, and does not correct them.

You also say where the window came from: typed in, simulated or measured.
That is your declaration. The interface cannot check it, and a matching
checksum does not prove that a recording is genuine. No example window is
built in.

The two models differ in how much training data they saw. The short one
(first60seconds) needs both brain regions. The full one
(full_training_partition) also works with one region marked absent: it then
drops that region's part of the computation. It does not reconstruct the
missing cells.

WHAT IT WOULD RETURN

Two signed numbers, X and Y, in metres per second, and an arrow drawn from
them. The axes are those of the recording's own frame. They are not
"forward" or "left" of the body. There is no path, no animation and no body.

In the original study the comparison target was the fingertip's change of
position divided by the time that had passed. The last position counted ends
4 ms before the end of the last count bin. The delays in the recording
equipment and in the body are unknown.

WHAT THAT WOULD NOT SHOW

The estimate concerns recent movement in this one recording and task. It is
not a future motor command and not an intention. It comes with no measure of
its own uncertainty. The study behind the two models did not confirm that
training on other recordings first helped either of them. Nothing here says
anything about people, about other animals or other recordings, about the
spinal cord or the nerves of the arm, or about teaching a body a skill.
Nothing is stimulated and nothing is moved.

WHAT WAS CHECKED BEFORE

When the models were exported, the exported version was compared with the
original on 8,330 windows per model. The largest differences were
1.4901161193847656e-08 m/s and 3.725290298461914e-08 m/s, against a
tolerance of 2e-6 m/s. That showed the export computes the same numbers as
the original. It was not repeated for this folder, and it says nothing about
how accurate the models are.

NAMES AND RIGHTS

NeuroTranslation is the field and the project. NeuroTranslator is the
software. NeuroTranslate is the operation of mapping one recording to
another. The saved model files carry older spellings of these names inside
them. Those are part of the files and were not changed.

The recording is reported as CC BY 4.0 at its source. The source code in this
folder is dedicated to the public domain with the rest of the project's
code. The models are not published.
