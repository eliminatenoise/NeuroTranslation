"""Find the local base files and open the NeuroTranslate example."""

from pathlib import Path
import os
import sys

from demo import main


def launch():
    args = sys.argv[1:]
    if any(arg in ('-h', '--help', '--base-dir') or arg.startswith('--base-dir=') for arg in args):
        return main()
    base = os.environ.get('NEUROTRANSLATE_BASE_DIR')
    if not base:
        beside = Path(__file__).resolve().with_name('inkling2mini-base')
        if beside.is_dir():
            base = str(beside)
    if not base:
        print('Choose your local Inkling files with --base-dir PATH or set NEUROTRANSLATE_BASE_DIR. '
              'See README.md for the pinned download command.', file=sys.stderr)
        return 2
    sys.argv.extend(('--base-dir', base))
    return main()


if __name__ == '__main__':
    raise SystemExit(launch())
