"""Download exactly one pinned OpenNeuro role into a separate data directory."""

import argparse
from pathlib import Path
import shutil
import tempfile
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

import run


def verify_file(path, binding):
    if path.stat().st_size != binding["asset_bytes"] or run.cohort.sha(path) != binding["asset_sha256"]:
        raise run.cohort.GateError(f"File does not match the frozen source: {path.name}")


def fetch(destination, role):
    design, _, _ = run.study_files()
    source = run.load_json(run.SOURCE_PATH, run.SOURCE_SHA)
    bindings = run.input_bindings(source, design["dataset"])
    destination.mkdir(parents=True, exist_ok=True)
    for subject in design["dataset"]["participants"]:
        binding = bindings[subject, role]
        output = destination / binding["basename"]
        if output.exists():
            verify_file(output, binding)
            print(f"Verified {output.name}")
            continue

        release_path = f"derivatives/movement-execution/{subject}/ihc/{output.name}"
        asset = binding["derivative"]
        url = urlsplit(asset["versioned_url"])
        version = asset["s3_version_id"]
        if (
            url.scheme != "https"
            or url.netloc != "s3.amazonaws.com"
            or url.path != f"/openneuro.org/ds006840/{release_path}"
            or parse_qs(url.query) != {"versionId": [version]}
        ):
            raise run.cohort.GateError(f"Unexpected pinned source URL for {output.name}")

        with tempfile.TemporaryDirectory(prefix="iackd-", dir=destination) as temp:
            staging = Path(temp) / output.name
            with urlopen(asset["versioned_url"], timeout=45) as response:
                if response.status != 200 or response.headers.get("x-amz-version-id") != version:
                    raise run.cohort.GateError(f"Response version mismatch for {output.name}")
                with staging.open("xb") as stream:
                    shutil.copyfileobj(response, stream)
            verify_file(staging, binding)
            staging.rename(output)
        print(f"Downloaded and verified {output.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("CALIBRATION", "EVALUATION"), required=True)
    parser.add_argument("--output", type=Path, required=True, help="Data directory outside the benchmark")
    options = parser.parse_args()
    try:
        fetch(options.output, options.role)
    except (OSError, run.cohort.GateError) as error:
        parser.exit(2, f"Download stopped: {error}\n")
