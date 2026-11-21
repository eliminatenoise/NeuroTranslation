"""Check both stages on three recorded reaches with only NumPy installed."""
import json
from pathlib import Path
import numpy as np

from predict_reach import forecast

HERE = Path(__file__).resolve().parent


def main():
    refs = json.loads((HERE / "examples/forecast-reference.json").read_bytes())
    for split, cases in refs.items():
        record = json.loads((HERE / "examples" / f"{split}.json").read_bytes())
        inputs = [np.array(record[name])[None] for name in ("pose", "spikes", "cue")]
        guide = np.array(record["unit_guide"])
        for label, expected in cases.items():
            family, seed = ("regression", 17) if label == "regression" else ("transformer", int(label))
            predicted = forecast(*inputs, guide, family, seed)
            for actual, reference in zip(predicted, expected, strict=True):
                np.testing.assert_allclose(actual[0], reference, atol=2e-6, rtol=5e-5)
        print(f"{split}: three Transformer seeds and paired regressions reproduce both forecasts.")
    try:
        forecast(*inputs, guide[::-1])
    except ValueError as err:
        if "identities" not in str(err):
            raise
    else:
        raise AssertionError("Reversed sorted-unit identity order was accepted.")


if __name__ == "__main__":
    main()
