"""Study folders published after the numbered table: every folder under benchmarks/ that no ledger row names.

The front-page builder (build_front.py, beside this file) calls later_studies(), so a study folder published after the
ledger's last update is listed on the studies page, never fatal. Each entry gives the folder, the
first heading of its own README.md (or None when it has none) and the first commit that added the folder, with its date
(None while the folder is not committed). The list is sorted by the time of that commit, then by folder name, so it is the same on
every run over the same commits; a folder that is not committed yet sorts last.
"""
import subprocess
from pathlib import Path


def _heading(readme):
    if not readme.exists():
        return None
    for line in readme.read_text(encoding='utf-8').splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    return None


def _first_commit(repo, rel):
    out = subprocess.run(['git', '-C', str(repo), 'log', '--reverse', '--format=%h %ct %cs', '--', rel],
                         capture_output=True, text=True).stdout.split('\n')
    first = out[0].split() if out and out[0].strip() else None
    return (first[0], int(first[1]), first[2]) if first else (None, None, None)


def later_studies(repo, ledger_folders):
    """repo: path of the clone; ledger_folders: the top-level benchmarks/ folders that ledger rows name."""
    repo = Path(repo)
    rows = []
    for d in sorted(p for p in (repo / 'benchmarks').iterdir() if p.is_dir()):
        if d.name in ledger_folders:
            continue
        rel = f'benchmarks/{d.name}'
        commit, stamp, date = _first_commit(repo, rel)
        rows.append(dict(folder=d.name, path=rel + '/', heading=_heading(d / 'README.md'),
                         has_readme=(d / 'README.md').exists(), first_commit=commit, first_date=date, _stamp=stamp))
    rows.sort(key=lambda r: (r['_stamp'] is None, r['_stamp'] or 0, r['folder']))
    for r in rows:
        del r['_stamp']
    return rows
