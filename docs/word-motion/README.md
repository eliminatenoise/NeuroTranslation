# Walk or run?

Open **index.html**, or use the Windows, macOS or Linux launcher in this folder. The page carries the fitted weights, browser inference code and two short motion-capture excerpts. It works directly from disk with the network disconnected. **Save offline copy** downloads the complete page.

Type **walk** or **run** and press Enter. The model also accepts **walking**, **running**, **jog**, **jogging** and **run/jog** as exact spelling variants. It generates one 0.60-second movement for each of the two action classes. No starting pose or previous movement enters the model.

Choose **Recorded example** to play a training recording from the Carnegie Mellon University Motion Capture Database. **Overlay both** draws its body points as blue rings beside the filled yellow-green points from the model. Each path starts at its own pelvis origin and uses the same direction of travel and camera. The lines connect surface landmarks. They show the movement of those landmarks, with no estimate of the internal joint centres.

Drag the view with a finger or mouse. With the view focused, the arrow keys rotate and Home resets the camera. Use Play or step through the time slider with the arrow keys. Open **Inspect a body point** to follow one landmark across the whole movement and read its X, Y and Z coordinates in millimetres.

## Rebuild

Use a checkout of the matching model from `models/word-motion` and run the following from this directory. Python’s standard library is sufficient to build the page.

```sh
python -B build.py --model ../../models/word-motion
```

The build verifies the model inputs against `src/inputs.sha256.json`. A new model or study result needs its own geometry, benchmark and browser checks. [Model, protocol and Python generator](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/word-motion)

## Credits

The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. CMU permits use of its data with acknowledgement and prohibits direct resale, including converted data. The recorded examples retain those terms. [Carnegie Mellon University Motion Capture Database](https://mocap.cs.cmu.edu/)

Original viewer code and text use the CC0 1.0 dedication. The camera and playback controls adapt the project's existing CC0 whole-body viewer. The model weights, generator and motion data retain their respective terms. [Viewer dedication](LICENSE) · [Earlier whole-body viewer](https://github.com/eliminatenoise/NeuroTranslation/tree/main/docs/whole-body) · [Model and data notices](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/word-motion)
