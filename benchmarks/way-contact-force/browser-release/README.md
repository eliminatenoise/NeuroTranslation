# Rebuild the contact-force comparison

The browser compares two fixed kinds of model on the same sensor history. The build checks the two published Python preview ZIPs and reads their fitted weights, channel order and aggregate results. The complete app then runs in the browser with local files. No training or original trial data are needed.

From the repository root on Linux or macOS, run this with Python 3.10 or later. The temporary build folder holds the output and leaves the checked-out files alone.

```sh
repo=$PWD
build_dir=$(mktemp -d)
mkdir "$build_dir/web"
cp "$repo/benchmarks/way-contact-force/browser-release/build.py" "$build_dir/"
for asset in index.html style.css forecast.js app.js README.md Run-Linux.sh Run-macOS.command Run-Windows.cmd; do
  cp "$repo/docs/contact-force/$asset" "$build_dir/web/"
done
python3 "$build_dir/build.py" \
  --ridge "$repo/benchmarks/way-contact-force/NeuroTranslation-Grip-After-Contact-Experimental-Preview.zip" \
  --cnn "$repo/benchmarks/way-contact-force/grip-contact-temporal-preview.zip"
```

The build prints the SHA-256 and writes the ZIP under `dist/` in the temporary folder. Its manifest records the model sources and hashes of the uncompressed files. Compare those hashes if a different compression library changes the ZIP bytes.

The European Commission supported the original WAY recordings under FP7-ICT-288551. [Original study acknowledgments](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/#ack1)
