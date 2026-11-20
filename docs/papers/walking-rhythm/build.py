"""Print the editable HTML note as a linked, searchable five-page PDF."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from pypdf import PdfReader, PdfWriter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="Path to Chrome or Chromium")
    parser.add_argument("--output", type=Path, help="Destination PDF")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    browser = args.browser or shutil.which("chromium") or shutil.which("google-chrome")
    if not browser:
        parser.error("Install Chromium or Chrome, then pass its path with --browser.")

    with tempfile.TemporaryDirectory() as temporary:
        scratch = Path(temporary)
        raw_pdf = scratch / "print.pdf"
        subprocess.run([
            browser, "--headless", "--disable-gpu", "--disable-background-networking",
            "--no-first-run", "--no-default-browser-check", "--no-pdf-header-footer",
            f"--user-data-dir={scratch / 'profile'}", f"--print-to-pdf={raw_pdf}",
            (folder / "index.html").as_uri(),
        ], check=True, capture_output=True, timeout=90)
        with raw_pdf.open("rb") as source:
            reader = PdfReader(source)
            if len(reader.pages) != 5:
                raise ValueError(f"Expected five pages, rendered {len(reader.pages)}")
            # Preserve tagged text, diagrams, external links and bookmarks while
            # dropping machine- and time-dependent print metadata.
            writer = PdfWriter(clone_from=reader)
            writer.metadata = {
                "/Title": "The next knee angle and the rhythm of a walk",
                "/Subject": "Treadmill knee angles, trial-level gait rhythms and estimated knee turning moments",
            }
            writer.write(args.output or folder / "gait-clocks.pdf")


if __name__ == "__main__":
    main()
