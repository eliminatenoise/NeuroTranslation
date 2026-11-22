"""Open the Research Edition preview's checks from an extracted folder."""

import sys
from pathlib import Path

if __name__ == '__main__':
    if sys.version_info < (3, 10):
        print('Use Python 3.10 or later for the offline checks. See README.md for the full loader setup.', file=sys.stderr)
        raise SystemExit(2)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from demo import main

    raise SystemExit(main())
