# Portable interface: source only

This folder holds the source of a small local interface written earlier in the project for one recorded task: given 400 ms of spike counts from a macaque's motor and sensory cortex, estimate how fast the fingertip was just moving. It is published so that the design can be read.

It cannot run from here. The folder holds no model weights, no recordings and no installed dependencies, and the server and the page have never been started.

| File | What it is |
| --- | --- |
| [`preview_server.py`](preview_server.py) | A local server that would load a saved model and answer one request at a time. |
| [`preview.html`](preview.html) | The page that would send it a window of counts and draw the estimate. |
| [`README.txt`](README.txt) | What the interface expects, what it would return, and what that would not show. |

Nothing else in the repository depends on it. The [browser app and the study readers](https://eliminatenoise.github.io/NeuroTranslation/START.html) are separate, and they do run.

The source is dedicated to the public domain with the rest of the project's code ([CC0 1.0](../../../LICENSE)). The recording it was written for has its own terms, and the models are not published.
