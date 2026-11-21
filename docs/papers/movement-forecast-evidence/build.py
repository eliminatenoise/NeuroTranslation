"""Render the standalone supplement to PDF with Chromium."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", default=shutil.which("chromium") or shutil.which("google-chrome"))
    parser.add_argument("--output", type=Path, default=ROOT / "movement-forecast-evidence.pdf")
    args = parser.parse_args()
    if not args.browser:
        parser.error("Supply the path to Chrome or Chromium with --browser.")
    output = args.output.resolve()
    with tempfile.TemporaryDirectory(prefix="render-", dir=output.parent) as temp:
        pdf = Path(temp) / "preview.pdf"
        subprocess.run(
            [
                args.browser,
                "--headless",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-sync",
                "--no-first-run",
                "--no-pdf-header-footer",
                f"--user-data-dir={temp}/profile",
                f"--print-to-pdf={pdf}",
                (ROOT / "index.html").as_uri(),
            ],
            check=True,
        )
        shutil.copyfile(pdf, output)


if __name__ == "__main__":
    main()
