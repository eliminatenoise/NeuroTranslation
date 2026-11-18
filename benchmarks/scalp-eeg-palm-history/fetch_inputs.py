"""Fetch only the six frozen, version-addressed OpenNeuro derivative files."""

import argparse
from pathlib import Path
import shutil
import tempfile
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

import run


def fetch(destination):
    design = run.load_design()
    source, _, _ = run.load_source(design, destination, [])
    destination.mkdir(parents=True, exist_ok=True)
    for participant in [item for cohort in source["roles"].values() for item in cohort]:
        binding = source["runs"][participant]
        output = destination / binding["basename"]
        if output.exists():
            if output.stat().st_size != binding["asset_bytes"] or run.sha(output) != binding["asset_sha256"]:
                raise run.GateError(f"Existing {output.name} does not match the frozen source")
            print(f"Verified {output.name}")
            continue
        url = urlsplit(binding["versioned_url"])
        if (
            url.scheme != "https"
            or url.netloc != "s3.amazonaws.com"
            or url.path != f"/openneuro.org/ds006840/{binding['release_path']}"
            or parse_qs(url.query) != {"versionId": [binding["s3_version_id"]]}
        ):
            raise run.GateError(f"Unexpected pinned source URL for {participant}")
        with tempfile.TemporaryDirectory(prefix="iackd-", dir=destination) as staging:
            temporary = Path(staging) / output.name
            with urlopen(binding["versioned_url"], timeout=45) as response:
                if response.status != 200 or response.headers.get("x-amz-version-id") != binding["s3_version_id"]:
                    raise run.GateError(f"Response version mismatch for {participant}")
                with temporary.open("xb") as stream:
                    shutil.copyfileobj(response, stream)
            if temporary.stat().st_size != binding["asset_bytes"] or run.sha(temporary) != binding["asset_sha256"]:
                raise run.GateError(f"Downloaded bytes mismatch for {participant}")
            temporary.rename(output)
            print(f"Downloaded and verified {output.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Data directory, kept separately from the benchmark")
    args = parser.parse_args()
    try:
        fetch(args.output)
    except (OSError, run.GateError) as error:
        parser.exit(2, f"Download stopped: {error}\n")
