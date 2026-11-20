# Back sensor rotation reader

Extract the whole ZIP first. Open **index.html** in a browser, or use **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh**. The reader runs from its folder, offline, using the included model. A current browser with JavaScript enabled is sufficient. Online source links need a connection.

Choose the known task and the model’s inputs. The three sliders change the size of the invented turns and the two invented electrode signals. A setting of 1× gives the original example. Expanding **Read the input values** shows the ten slices that reach the selected model. **Restore example** returns all controls to their starting positions.

The output is an unsigned change in the orientation of a back-mounted device over 100 milliseconds, in degrees. The example has no measured outcome. **Recorded results** reports separate errors from original recordings, including the comparison with electrode inputs from another time. Both planned four-person assessments are incomplete. In two trials from one person, a channel needed to calculate orientation is labelled “BufferChannel”. The three other people supply the separate descriptive comparison. There are no individual recording windows in this reader.

## Files

- `index.html`, `reader.css` and `reader.js` present the controls and results.
- `inference.js` evaluates the four trained specialist Transformers.
- `example.js` generates the invented motion and surface-electrode inputs.
- `weights.js` contains the training export in a browser-readable form.
- `results.json` contains the figures displayed in the recorded results.

Dataset attribution and reuse terms are in [NOTICE.md](NOTICE.md).
