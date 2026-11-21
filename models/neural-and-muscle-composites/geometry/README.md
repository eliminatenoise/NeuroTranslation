# Earlier simulated length, later measured position

Prepare the two verified original MATLAB members and the three reconstructed archives using the instructions in [the reach study](../reach/README.md). With NumPy and SciPy installed, run the following from this directory. The paths assume the data were prepared in the sibling reach directory.

```sh
python read_lengths.py train ../reach/raw/C_20170907_TRT_TD.mat ../reach/data/train.npz ../reach/data/train-lengths.npz
python read_lengths.py held ../reach/raw/C_20170914_TRT_TD.mat ../reach/data/block1.npz ../reach/data/block1-lengths.npz --labels names.json
python read_lengths.py held ../reach/raw/C_20170914_TRT_TD.mat ../reach/data/block2.npz ../reach/data/block2-lengths.npz --labels names.json
python compare.py ../reach/data ../reach/data repeated-results.json
```

Each study input must match the source file digests in [the released result](results.json). The reconstruction associates every length vector with its original block, workspace, trial and time. For the matched comparison, the model sees only the anchor lengths from the last input sample. Compare **repeated-results.json** with **results.json**. The primary outcome is error in the planar handle endpoint, in millimetres, reported separately by workspace. [Frozen comparison](design.md) · [Recording and muscle–tendon estimates](https://doi.org/10.5061/dryad.nk98sf7q7)
