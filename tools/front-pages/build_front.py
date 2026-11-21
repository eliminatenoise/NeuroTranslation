#!/usr/bin/env python3
"""Write the NeuroTranslation front pages from their templates, reading every number from the result files.

No number on a generated page is typed by hand. A template writes it as a call such as {{ S(1).ref(2) }}; this
script follows the pointer that the checked ledger (ledger.json, beside this file) holds for that number, a file and
a field, reads the value from that result file in this repository, compares it with the ledger's copy, rounds it and
writes it into the page. Sentences that depend on a result (which forecast won, whether a rule was met) are asserted
against the result files the same way, so a page cannot be built while it says something the files contradict.

Runs with Python 3 and its standard library, from any folder. It also calls git, and pdftotext and pdfinfo (from
Poppler, the poppler-utils package on most Linux systems) to read the papers' text and page numbers.

    python3 tools/front-pages/build_front.py               write the pages
    python3 tools/front-pages/build_front.py --check       build in memory; list every page, "same" or "DIFFERS"; exit 1 if any differs
    python3 tools/front-pages/build_front.py --out DIR     write the pages under DIR instead (a preview)
    python3 tools/front-pages/build_front.py --facts FILE  also write a table of every number: page, printed text, file,
                                                           field and unrounded value

Templates: templates/<name> beside this file; the TARGETS table below says which page each one becomes. Every page
but three starts with a comment that names its template (NO_NOTE says which three, and why).

A study folder under benchmarks/ that no ledger row names (published after the numbered table) never stops the
build: later_studies() finds it, the studies page lists it with its own page's heading and a link, and it is
counted apart from the numbered studies (n_later()). A new page under docs/ is counted the same way (n_pages()).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True                      # leave no compiled files in the repository
HERE = Path(__file__).resolve().parent              # tools/front-pages
REPO = HERE.parents[1]                              # the repository
TEMPLATES = HERE / 'templates'
CACHE = HERE / '.cache'                             # the papers' text, one file per PDF and hash (ignored by git)
sys.path.insert(0, str(HERE))
from later_studies import later_studies     # noqa: E402  (the folders no ledger row names)
LEDGER_FILE = 'tools/front-pages/ledger.json'
LEDGER = json.loads((REPO / LEDGER_FILE).read_text(encoding='utf-8'))
OLD_EDITION = 'papers/experimental/cemhsey-pinch-carry-2026-11-19/'   # where the ledger found the papers
NEW_EDITION = 'papers/current/'                                       # where they are now
LINK_RESULTS = NEW_EDITION + 'results/link-macaque.json'              # the macaque study's numbers, published with the 20 November edition
SOURCE_ZIP = 'papers/downloads/NeuroTranslation-Brain2Body-Papers-Source.zip'
SITE = 'https://eliminatenoise.github.io/NeuroTranslation/'
GH = 'https://github.com/eliminatenoise/NeuroTranslation/'

TARGETS = {
    'README.md': 'README.md',
    'benchmarks-README.md': 'benchmarks/README.md',
    'papers-README.md': 'papers/README.md',
    'papers-current-README.md': 'papers/current/README.md',
    'papers-current-index.html': 'papers/current/index.html',
    'docs-papers-current-index.html': 'docs/papers/current/index.html',
    # pages with no number taken from a result file (nothing to fill in)
    'LAUNCHERS.md': 'LAUNCHERS.md',
    'docs-README.md': 'docs/README.md',
    'docs-RIGHTS.md': 'docs/RIGHTS.md',
    'demo-README.md': 'demo/README.md',
    'demo-RIGHTS.md': 'demo/RIGHTS.md',
    'portable-NOTICE.md': 'interfaces/experimental/portable/NOTICE.md',
    'portable-README.txt': 'interfaces/experimental/portable/README.txt',
    # the site's front page and the old address that forwards to it
    'docs-START.html': 'docs/START.html',
    'docs-preview.html': 'docs/preview.html',
}

FACTS = []          # (page, printed, file, field, full value, note)
PAGE = ['?']
_json = {}
_pdf = {}


def here(path):
    return path.replace(OLD_EDITION, NEW_EDITION)


def load(rel):
    """A JSON file of the repository, or one inside a ZIP of the repository written as 'folder/file.zip!member.json'."""
    if rel not in _json:
        if '!' in rel:
            import zipfile
            archive, member = rel.split('!', 1)
            _json[rel] = json.loads(zipfile.ZipFile(REPO / archive).read(member).decode('utf-8'))
        else:
            _json[rel] = json.loads((REPO / rel).read_text(encoding='utf-8'))
    return _json[rel]


def walk(obj, field):
    for part in field.split('/'):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def pdf_text(rel):
    if rel not in _pdf:
        import hashlib     # the cache is keyed by the PDF's own hash, so a new edition is never read from an old text
        digest = hashlib.sha256((REPO / rel).read_bytes()).hexdigest()[:16]
        cache = CACHE / f'{Path(rel).stem}.{digest}.txt'
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            part = cache.with_name(cache.name + '.part')
            subprocess.run(['pdftotext', '-layout', str(REPO / rel), str(part)], check=True)
            part.replace(cache)
        _pdf[rel] = cache.read_text(encoding='utf-8').replace('−', '-')
    return _pdf[rel]


def value(ptr):
    """Value behind a ledger pointer, re-read from the working clone and compared with the ledger's copy."""
    rel = here(ptr['file'])
    if rel.endswith('.json'):
        raw = walk(load(rel), ptr['field'])
        assert isinstance(raw, (int, float)) and not isinstance(raw, bool), (rel, ptr['field'], raw)
        assert raw == ptr['raw'], ('clone differs from ledger', rel, ptr['field'], raw, ptr['raw'])
        v = raw * ptr.get('scale', 1.0)
        if ptr.get('note') == 'sign reversed':
            v = -v
        assert abs(v - ptr['value']) <= 1e-12 * max(1.0, abs(v)), (rel, ptr['field'], v, ptr['value'])
        return v
    assert rel.endswith('.pdf'), rel
    # The ledger read the macaque study's numbers (row 24) from the previous edition's text. This edition publishes them
    # in full in a result file beside the papers: the value must be there, equal to the ledger's to its ten decimals.
    assert rel == NEW_EDITION + 'neurotranslation-technical.pdf', rel
    hits = [e for e in load(LINK_RESULTS)['numbers'] if isinstance(e.get('value'), (int, float)) and round(e['value'], 10) == ptr['raw']]
    assert hits, ('not in the macaque result file', ptr['raw'])
    return ptr['value']


def log(printed, ptr=None, file=None, field=None, full=None, note=''):
    if ptr is not None:
        file, field, full = here(ptr['file']), ptr['field'], ptr['value']
        if file.endswith('.pdf'):          # row 24: logged at the result file that holds the number now (see value())
            hits = [e['macro'] for e in load(LINK_RESULTS)['numbers'] if isinstance(e.get('value'), (int, float)) and round(e['value'], 10) == ptr['raw']]
            file, field = LINK_RESULTS, 'numbers[macro=' + ' or '.join(hits) + ']/value'
        bits = []
        if ptr.get('scale', 1.0) != 1.0:
            bits.append('x%g' % ptr['scale'])
        if ptr.get('note'):
            bits.append(ptr['note'])
        note = '; '.join(bits + ([note] if note else []))
    FACTS.append((PAGE[0], printed, file, field, '' if full is None else repr(full), note))


def fmt(v, dp):
    s = f'{v:.{dp}f}'
    return s


def unit_join(txt, unit):
    if unit == '°':
        return txt + '°'
    if unit == '% of MVC':
        return txt + '%'
    if unit in ('mm', 'N', 'mV'):
        return txt + ' ' + unit
    return txt


RANGE_KIND = {
    'change when any one of the three people is left out': 'whichever one of the three people is left out',
    'middle 95% when the four people are resampled': 'the middle 95% when the four people are resampled',
    'middle 95% when the four people are resampled (sign reversed to error change)': 'the middle 95% when the four people are resampled',
    'middle 95% when the two donor pairs are resampled (sign reversed to error change)': 'the middle 95% when the two donor pairs are resampled, which is not a range across people',
    'change when any one test trial is left out': 'whichever one test trial is left out',
    "smallest and largest of the three people's changes": 'the smallest and largest change among the three people',
    "smallest and largest of the four people's changes": 'the smallest and largest change among the four people',
    'descriptive 95% interval across the three people (paired t)': 'a 95% interval across the three people',
    "rounded bounds that enclose the three people's changes (the exact extremes are withheld)": 'the range across the three people, which the study gives rounded outwards',
    'conditional 95% interval given in the paper': 'the 95% interval given in the paper',
    'change when any one of the six people is left out': 'whichever one of the six people is left out',
}


class Study:
    def __init__(self, s):
        self.s = s
        self.n = s['n']
        self.dp = s['dp']
        self.unit = s['unit']
        self.p = s.get('primary')

    # -- single numbers ------------------------------------------------------------------------------
    def _show(self, ptr, dp, unit=False, absolute=False):
        v = value(ptr)
        txt = fmt(abs(v) if absolute else v, self.dp if dp is None else dp)
        log(txt, ptr)
        return unit_join(txt, self.unit) if unit else txt

    def ref(self, dp=None, unit=True):
        return self._show(self.p['ref'], dp, unit)

    def cand(self, dp=None, unit=True):
        return self._show(self.p['cand'], dp, unit)

    def base(self, i, dp=None, unit=True):
        return self._show(self.s['baselines'][i][1], dp, unit)

    def model(self, i, dp=None, unit=True):
        return self._show(self.s['models'][i][1], dp, unit)

    def cmp(self, i, key, dp=None, unit=True):
        x = self.s['comparisons'][i][key]
        if isinstance(x, list):
            x = x[1]
        return self._show(x, dp, unit)

    def gap(self, dp=None, unit=True):
        """Size of the main difference, challenger minus reference, from the unrounded values."""
        r, c = value(self.p['ref']), value(self.p['cand'])
        d = c - r
        assert abs(d - self.p['diff']) <= 1e-9, (self.n, d, self.p['diff'])
        txt = fmt(abs(d), self.dp if dp is None else dp)
        log(txt, file=here(self.p['cand']['file']),
            field=self.p['cand']['field'] + '  minus  ' + self.p['ref']['field'], full=d,
            note='difference of the two unrounded scores')
        return unit_join(txt, self.unit) if unit else txt

    def cmpgap(self, i, a='with_', b='without', dp=None, unit=True):
        c = self.s['comparisons'][i]
        x, y = c[a], c[b]
        d = value(x) - value(y)
        txt = fmt(abs(d), self.dp if dp is None else dp)
        log(txt, file=here(x['file']), field=x['field'] + '  minus  ' + y['field'], full=d,
            note='difference of the two unrounded scores')
        return unit_join(txt, self.unit) if unit else txt

    def direction(self):
        return 'lower' if self.p['diff'] < 0 else 'higher'

    def better(self):
        b = self.p['better']
        if not b:
            return self.p['better_text'].replace('not published', 'not given')
        src = b[2]
        if ' → ' in src:
            file, field = src.split(' → ', 1)
        elif src.startswith('README only'):
            file, field = self.s['folder'] + 'README.md', src
        else:
            file, field = here(self.p['cand']['file']), src
        log(f'{b[0]} of {b[1]}', file=file, field=field, full=None, note='people whose own error went down')
        return f'{b[0]} of {b[1]}'

    def pair(self, a, b, dp=None, unit=True):
        """Size of the difference between two listed scores, e.g. pair(('base', 1), ('model', 2))."""
        def ptr(x):
            return self.s[{'base': 'baselines', 'model': 'models'}[x[0]]][x[1]][1]
        pa, pb = ptr(a), ptr(b)
        d = value(pb) - value(pa)
        txt = fmt(abs(d), self.dp if dp is None else dp)
        log(txt, file=here(pb['file']), field=pb['field'] + '  minus  ' + pa['field'], full=d,
            note='difference of the two unrounded scores')
        return unit_join(txt, self.unit) if unit else txt

    def range_kind(self):
        r = self.p.get('range') if self.p else None
        return RANGE_KIND[r['kind']] if r else ''

    def range_words(self, dp=None):
        r = self.p.get('range')
        if not r:
            return ''
        dp = self.dp if dp is None else dp
        lo, hi = value(r['lo']), value(r['hi'])
        tl, th = fmt(abs(lo), dp), fmt(abs(hi), dp)
        log(tl, r['lo'])
        log(th, r['hi'])
        zero = '0.' + '0' * dp
        if hi <= 0 and th == zero and lo < 0:
            body = f'from {tl} lower to no change'
        elif lo < 0 and hi < 0:
            body = f'{th} to {tl} lower'
        elif lo > 0 and hi > 0:
            body = f'{tl} to {th} higher'
        else:
            body = f'from {tl} lower to {th} higher'
        return body


STUDIES = {s['n']: Study(s) for s in LEDGER['studies']}
# Rows that are not tests: scored only on people already used for fitting (row 27, the general model's five-sensor walking fit, on its own fitting
# people; row 29, a correction scored on the six people the earlier wrist models were fitted on). They have a row and a page, and they
# enter no count of studies, tests or rules.
NOT_A_TEST = {s['n'] for s in LEDGER['studies'] if s.get('not_a_test')}
assert NOT_A_TEST == {27, 29}, NOT_A_TEST


def S(n):
    return STUDIES[n]


def C(*path):
    """A count from the ledger's "counts" block (each is the tally of the comparison rows printed on the studies page)."""
    o = LEDGER['counts']
    for part in path:
        o = o[part]
    log(str(o), file=LEDGER_FILE, field='counts/' + '/'.join(map(str, path)), full=o,
        note='tally over the comparison rows printed on the studies page')
    return str(o)


def N(rel, field, dp=0, scale=1.0, absolute=False):
    """A number read directly from a file in the clone."""
    raw = walk(load(rel), field)
    assert isinstance(raw, (int, float)) and not isinstance(raw, bool), (rel, field, raw)
    v = abs(raw * scale) if absolute else raw * scale
    txt = fmt(v, dp) if dp else str(int(round(v)))
    notes = [('x%g' % scale) if scale != 1.0 else '', 'sign dropped: the sentence says which way' if absolute else '']
    log(txt, file=rel, field=field, full=raw, note='; '.join(n for n in notes if n))
    return txt


def T(rel, field):
    """A text value read directly from a file in the clone."""
    txt = walk(load(rel), field)
    log(str(txt), file=rel, field=field, full=None)
    return str(txt)


# ---------------------------------------------------------------------------------------------------
# Names and links (one name per study, used on every page)
# ---------------------------------------------------------------------------------------------------
NAME = {
    1: 'Wrist pointing: brain signal on a learned forecast',
    2: 'Wrist pointing: muscle signal on a straight-line fit',
    3: 'Wrist pointing: muscle signal on the learned forecast',
    4: 'Everyday tasks: wrist angle from the muscle signal',
    5: "Hand to mouth: one person's muscle signal, another's elbow",
    6: 'Palm, first try: brain signal alone',
    7: 'Palm: brain signal on top of hand history',
    8: "Palm: adjusted on the person's first recording",
    9: 'Pinch and lift: grip force',
    10: 'Pinch and lift: grip force, timed from the squeeze',
    11: 'Paced grip: brain signal',
    12: 'Paced grip: muscle signal',
    13: 'Paced grip: a fit that changes with the cue',
    14: 'One finger: muscle signal',
    15: 'One finger: next-day adjustment',
    16: 'One finger: the other four fingers',
    17: 'One finger: new task',
    18: 'Pinch: muscle signal',
    19: 'Pinch: five electrode grids',
    20: 'Pinch: width of the band',
    21: 'Pinch at new targets',
    22: 'Pinch, next day',
    23: 'Pinch: a correction learned from other people',
    24: 'Macaque fingers from motor cortex (LINK)',
    25: 'One network shared by two signals: first run',
    26: 'Walking: a small transformer on an arm sensor',
    27: "Walking: the general model's five-sensor fit",
    28: 'Wrist pointing: the general model with muscle and brain signals',
    29: 'Wrist pointing: a muscle correction, scored on the people used for fitting',
}
FOLDER = {
    1: 'wrist-pointing-temporal/', 2: 'wrist-pointing-muscle/', 3: 'wrist-forearm-transfer/', 4: 'uji-wrist-emg/',
    5: 'surface-emg-elbow/', 6: 'scalp-eeg-hand/', 7: 'scalp-eeg-palm-history/', 8: 'scalp-eeg-personal-calibration/',
    9: 'way-grip-force/', 10: 'way-contact-force/', 11: 'hygrip-force/results-2026-11-19/',
    12: 'hygrip-force/forearm-results/', 13: 'hygrip-force/cue-phase/', 14: 'hyser-index/RESULTS.md',
    15: 'hyser-index/crossday/', 16: 'hyser-index/whole-hand/', 17: 'hyser-index/prescribed/',
    18: 'cemhsey-pinch/', 19: 'cemhsey-arrays/', 20: 'cemhsey-intervals/', 21: 'cemhsey-transfer/',
    22: 'cemhsey-carry/', 23: 'cemhsey-phase/', 26: 'daily-sports-arm/', 27: 'daily-sports-limbs/',
    28: 'paired-wrist-forecast/', 29: 'wrist-forearm-correction/',
}
STUDY_FOLDER = {k: v for k, v in FOLDER.items() if k not in NOT_A_TEST}     # the studies (rows 27 and 29 are not tests)
TABLE_FOLDERS = sorted({s['folder'][len('benchmarks/'):].split('/')[0] for s in LEDGER['studies'] if s['folder'].startswith('benchmarks/')})
assert {v.split('/')[0] for v in FOLDER.values()} == set(TABLE_FOLDERS), TABLE_FOLDERS
# Study folders published after the numbered table: every folder under benchmarks/ that no ledger row names, found afresh at
# each build. The four below have a paragraph of their own (LATER_TEXT) and come first, in this order of interest; any other
# keeps the order of its first commit and gets a plain line that sends the reader to its own page.
LATER_ORDER = ['wtrack-neural-motion', 'preceding-instructions', 'hand-language-retrieval', 'text-motion-retrieval']
LATER = sorted(later_studies(REPO, set(TABLE_FOLDERS)),
               key=lambda r: LATER_ORDER.index(r['folder']) if r['folder'] in LATER_ORDER else len(LATER_ORDER))
READER = {
    1: 'wrist-replay/', 2: 'wrist-pointing/', 3: 'wrist-forearm/', 4: 'daily-wrist/',
    7: 'index.html#palm-replay', 8: 'index.html#personal-calibration', 9: 'grip-force/', 10: 'contact-force/',
    11: 'hygrip-force/', 12: 'hygrip-force/', 13: 'hygrip-force/', 14: 'hyser-index/', 15: 'hyser-index/',
    16: 'hyser-index/', 17: 'hyser-index/', 18: 'cemhsey-pinch/', 19: 'cemhsey-arrays/', 20: 'cemhsey-intervals/',
    21: 'cemhsey-transfer/results/', 22: 'cemhsey-carry/', 23: 'cemhsey-phase/',
}
PAPER_ONLY = {      # the two rows with no folder: each links to its account in the technical paper (named destinations below)
    24: NEW_EDITION + 'neurotranslation-technical.pdf#nameddest=appendix.A',        # appendix A, the macaque study in full
    25: NEW_EDITION + 'neurotranslation-technical.pdf#nameddest=sec:self-forecast',  # its row in appendix B
}


def study_link(n, base):
    """Markdown link to the study's own page; base is the path from the page to the repository root."""
    if n in FOLDER:
        return f'[{NAME[n]}]({base}benchmarks/{FOLDER[n]})'
    _link_page_check(n)
    return f'[{NAME[n]}]({base}{PAPER_ONLY[n]})'


def _link_page_check(n):
    """Rows 24 and 25 link to a named destination in the technical paper: confirm it exists and is the right place."""
    rel, name = PAPER_ONLY[n].split('#nameddest=')
    page = pdf_dests(rel)[name]
    out = subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), '-layout', str(REPO / rel), '-'],
                         check=True, capture_output=True, text=True).stdout
    needles = {24: ('The Macaque Study In Full', 'Monkey N', 'Four more are reserved and have not been opened'),
               25: ('One long training run', 'A two-stream network against repeating the last value')}[n]
    for needle in needles:
        assert needle in re.sub(r'\s+', ' ', out), ('not on page %d of the technical paper' % page, needle)


def LN(n, base=''):
    """Numbered link, as the front page prints it: "3 · [name](link)"."""
    return f'{n} · {study_link(n, base)}'


def RL(nums, text=None):
    """Name of a reader in LAUNCHERS.md: the study's number and name, or a range of studies and a common name."""
    if isinstance(nums, int):
        return f'{nums} · {NAME[nums]}'
    lo, hi = nums
    stems = {NAME[k].split(':')[0] for k in range(lo, hi + 1)}
    assert stems == {text}, (stems, text)
    return f'{lo} to {hi} · {text}'


def L(n, base=''):
    return study_link(n, base)


def reader(n):
    return f'[open]({SITE}{READER[n]})' if n in READER else ''


# ---------------------------------------------------------------------------------------------------
# Tables for the studies page
# ---------------------------------------------------------------------------------------------------
TESTED = {
    1: '3 people (fitted on 6 others)', 2: 'the same 3 (fitted on 6 others)', 3: 'the same 3 (fitted on 6 others)',
    4: '4 people (fitted on 14 others)', 5: '1 person (fitted on 1 other)', 6: '1 person (fitted on 1 other)',
    7: '3 people (fitted on 3 others)', 8: '3 new people, on their second recording',
    9: '3 people (fitted on 6 others)', 10: 'the same 3 (fitted on 6 others)',
    11: '3 people (fitted on 7 others)', 12: 'the same 3', 13: 'the same 3',
    14: '4 people (fitted on 12 others)', 15: 'the same 4, on their second day', 16: 'the same 4',
    17: 'the same 4, on a task the models never saw',
    18: '4 people (fitted on 3 others)', 19: '4 new people (fitted on the same 3)',
    20: '2 people (band widths set on 4 others)', 21: '4 people, one day each', 22: 'the same 4, a day later',
    23: '3 people (corrections fitted on 3 others)',
    24: '1 macaque, 2 later days (fitted on 4 days)', 25: 'nobody: scored on its own training recording',
    26: '2 people (fitted on 4 others)', 27: 'nobody new: the 4 people it was fitted on',
    28: 'the same 3 as study 1 (fitted on 6 others)',
    29: 'nobody new: the 6 people studies 1 to 3 and 28 were fitted on, each scored by models fitted on the other five',
}
GROUPS = [
    ('Wrist angle', [1, 2, 3, 28, 29, 4]),
    ('Elbow angle', [5]),
    ('Palm position', [6, 7, 8]),
    ('Grip force during a lift', [9, 10]),
    ('Sensor voltage during a paced grip or a finger press', [11, 12, 13, 14, 15, 16, 17]),
    ('Pinch force between two fingers', [18, 19, 20, 21, 22, 23]),
    ('Arm acceleration while walking', [26]),
    ("The general model's five-sensor walking fit, scored on the people it was fitted on: not a test", [27]),
    ('Reported only in the papers', [24, 25]),
]
GROUP_NOTE = {
    'Wrist angle': 'Errors in degrees, both wrist axes together. Row 29 enters none of the counts below.',
    'Elbow angle': 'Errors in degrees.',
    'Palm position': 'Errors in millimetres, along the one sideways axis the tracker reports.',
    'Grip force during a lift': 'Errors in newtons.',
    'Sensor voltage during a paced grip or a finger press':
        'Errors in millivolts. Neither dataset says how many newtons a volt is, so these are errors in the sensor\'s '
        'voltage, not in force.',
    'Pinch force between two fingers':
        'Errors in % of the hardest squeeze the person could manage that day (their MVC, maximum voluntary contraction).',
    'Arm acceleration while walking':
        'Errors in the units the sensor stores: acceleration along its own three axes, gravity included, not converted to physical units.',
    "The general model's five-sensor walking fit, scored on the people it was fitted on: not a test":
        'Every score here is on the four people the model was fitted on. Nobody was held out, so nothing in this row is a test, and it enters '
        'none of the counts below. Errors in the units the sensors store.',
    'Reported only in the papers':
        'No folder under `benchmarks/`: each study is told in the NeuroTranslation paper, and its result file is published with '
        'the papers ([`link-macaque.json`]({base}papers/current/results/link-macaque.json), '
        '[`training-diagnostic-summary.json`]({base}papers/current/training-diagnostic-summary.json)). Both use units scaled to the '
        'data, so the numbers mean nothing outside their own row.',
}


FORECAST = {
    1: 'The two wrist angles a quarter of a second ahead (250 ms), at six moments after the cue',
    2: 'The same two wrist angles, 250 ms ahead',
    3: 'The same two wrist angles, 250 ms ahead',
    4: 'The two wrist angles at least 250 ms after the last EMG sample, during 26 everyday activities',
    5: 'The elbow angle 40 ms ahead, during five hand-to-mouth movements',
    6: 'Sideways palm position 10 ms after the last EEG sample, at nine moments after the cue',
    7: 'Sideways palm position 100 ms ahead, at nine moments in each trial',
    8: 'The same, on each person\'s second recording',
    9: 'Grip force 120 ms ahead, on a schedule tied to the go cue',
    10: 'Grip force 120 ms ahead, at five moments after the plates register a squeeze',
    11: 'The grip sensor\'s voltage 120 ms ahead, during ten paced squeezes per trial',
    12: 'The same as study 11',
    13: 'The same as study 11',
    14: 'The index-finger sensor\'s voltage 120 ms ahead, during freely chosen presses',
    15: 'The same, on the person\'s second recording day',
    16: 'The same as study 14',
    17: 'The same voltage, during 15 prescribed finger combinations',
    18: 'The gauge reading 120 ms ahead, during a pinch held at 30% of the hardest squeeze',
    19: 'The same as study 18',
    20: 'A band meant to hold 90% of the gauge readings 120 ms ahead',
    21: 'The gauge reading 120 ms ahead, at a 50% target (10% and 30% were scored too)',
    22: 'The same, on the next recording day',
    23: 'The gauge reading 120 ms ahead, at a 50% target',
    24: 'The position of the index finger, and of the other three fingers as a group, from the brain recording',
    25: 'Each signal\'s own next values from its own past. Nothing is predicted from one signal to the other',
    26: 'The right-arm sensor\'s three readings 120 ms ahead, from its last 16 readings, while walking',
    27: 'Each of five body sensors\' three readings 120 ms ahead, from that sensor\'s own last 16 readings, while walking',
    28: 'The same two wrist angles, 250 ms ahead, at six moments after the cue',
    29: 'The same two wrist angles, 250 ms ahead, at six moments from 0.75 to 2 seconds after the cue',
}
REFL = {
    1: 'Learned forecast from wrist history', 2: 'Straight-line fit on wrist history',
    3: 'Learned forecast, corrected from wrist motion', 4: 'Which activity it is and how long it has run',
    5: 'The average path, started when the movement starts', 6: 'The time within the task and nothing else',
    7: 'Time, and where the palm has been', 8: 'The model with EEG, as fitted on other people',
    9: 'Force and motion history', 10: 'Force and motion history', 11: 'Cue timing and recent voltage',
    12: 'Cue timing and recent voltage', 13: 'The plain fit on recent voltage', 14: 'The sensor\'s last 41 readings',
    15: 'The shared model, unchanged', 16: 'Index-finger history', 17: 'Index-finger history',
    18: 'Force history and the on-screen cue', 19: 'EMG as one overall amplitude',
    21: 'A one-line rule: the current reading plus the change the on-screen schedule calls for',
    22: 'The fitted five-grid model, corrected on one practice pinch from the new day', 23: 'The one-line rule',
    24: 'Straight-line fit on the latest brain sample', 25: 'Repeat the last value (glove signal)',
    26: 'Straight-line fit on the last 16 readings',
    28: 'The general model on wrist history', 29: 'Learned forecast, corrected from wrist motion',
}
CANDL = {
    1: 'The same with scalp EEG added', 2: 'The same with forearm EMG added', 3: 'The same correction with EMG added',
    4: 'The same with EMG added', 5: 'EMG alone, fitted on someone else', 6: 'Scalp EEG alone',
    7: 'The same with EEG added', 8: 'The same model, adjusted on the person\'s own first recording',
    9: 'The same with EEG added', 10: 'The same with EEG added', 11: 'The same with EEG added',
    12: 'The same with EMG added', 13: 'A fit allowed to differ between squeeze and rest',
    14: 'The same with EMG added', 15: 'Adjusted on the person\'s own first day',
    16: 'The other four fingers\' histories added', 17: 'Five fingers\' histories',
    18: 'The same with EMG added', 19: 'EMG as five separate grids',
    21: 'The fitted five-grid model after one practice pinch', 22: 'The same model, corrected on yesterday\'s practice pinch instead',
    23: 'The rule with separate corrections for the rise and the release, learned from 3 other people',
    24: 'The better of two networks that read recent brain history',
    25: 'One network shared by both signals, after 990 training steps (glove signal)',
    26: 'A small transformer on the same 16 readings',
    28: 'The same model fitted with forearm EMG added', 29: 'The same correction with forearm EMG added',
}
RANGE_OVERRIDE = {       # said in the cell
    5: 'one test person; the EMG fit lost in all five repetitions',
    25: 'one recording, no range',
}
NO_RANGE = {             # said under the table
    1: 'the results file gives no range across people',
    9: 'the results file gives no range',
}
PLAIN = [
    ('temporal network', 'learned forecast'), ('Temporal network', 'Learned forecast'),
    ('linear fit', 'straight-line fit'), ('Linear fit', 'Straight-line fit'),
    ('current force carried forward', 'last force repeated'), ('current voltage carried forward', 'last voltage repeated'),
    ('current reading carried forward', 'last reading repeated'),
    ('carried forward', 'repeated'), ('cue phase', 'the cue'),
    ("five-grid fit with yesterday's personal number", "five-grid fit, corrected on yesterday's practice pinch"),
    ("force history with yesterday's personal number", "force history, corrected on yesterday's practice pinch"),
    ('force history, no personal number', 'force history, no correction'),
    ("reuse yesterday's personal number instead of none", "reuse yesterday's practice correction instead of none"),
    ("Force-history fit with yesterday's number", "Force-history fit corrected on yesterday's practice pinch"),
    ("force-history fit with yesterday's number", "force-history fit corrected on yesterday's practice pinch"),
    ('general learner', 'general model'), ('(new panel)', '(new people)'), ('split corrections', 'separate rise and release corrections'),
    ('paired grid', 'five-grid'), ('development people', 'test people'), ('fitting people', 'people the model was fitted on'),
]


def plain(txt):
    for a, b in PLAIN:
        txt = txt.replace(a, b)
    return txt[0].upper() + txt[1:]


def _study_list(nums):
    """'study 4' / 'studies 2 and 3' / 'studies 11 to 13' / 'studies 14, 16 and 17'."""
    nums = sorted(nums)
    if len(nums) == 1:
        return f'study {nums[0]}'
    if len(nums) > 2 and nums == list(range(nums[0], nums[-1] + 1)):
        return f'studies {nums[0]} to {nums[-1]}'
    return 'studies ' + ', '.join(map(str, nums[:-1])) + ' and ' + str(nums[-1])


def table_all(base='../'):
    out = []
    for title, rows in GROUPS:
        out.append(f'### {title}')
        out.append('')
        out.append(GROUP_NOTE[title].replace('{base}', base))
        out.append('')
        out.append('| # | Study | What was forecast | Tested on | Reference forecast | Challenger | Difference | People better with the challenger |')
        out.append('| ---: | --- | --- | --- | --- | --- | --- | --- |')
        kinds = {}          # how each range was made -> the studies it applies to (said once, under the table)
        for n in rows:
            st = S(n)
            name = f'[{NAME[n]}]({FOLDER[n]})' if n in FOLDER else study_link(n, base)
            if n in READER:
                name += f' · [open in the browser]({SITE}{READER[n]})'
            pred = FORECAST[n]
            if st.p:
                ref = f"{REFL[n]}: **{st.ref()}**"
                cand = f"{CANDL[n]}: **{st.cand()}**"
                d = st.p['diff']
                zero = abs(d) < 0.5 * 10 ** (-st.dp)
                diff = 'none at this precision' if zero else f"{st.gap()} {'lower' if d < 0 else 'higher'}"
                rw = st.range_words()
                if n == 26:
                    assert not rw
                    diff += f' ({arm_people_range()})'
                elif n in RANGE_OVERRIDE:
                    assert not rw, n
                    diff += f' ({RANGE_OVERRIDE[n]})'
                elif n in NO_RANGE:
                    assert not rw, n
                    kinds.setdefault(NO_RANGE[n], []).append(n)
                elif rw:
                    diff += f' ({rw})'
                    kinds.setdefault(st.range_kind(), []).append(n)
                else:
                    raise AssertionError(('no range wording', n))
                bt = st.better()
            elif n == 27:
                ref = f"Straight-line fit made for the left-leg sensor alone: **{st.base(9)}**"
                cand = f"The general model, one fit for all five sensors: **{st.model(4)}** at the left leg"
                diff = 'not a test (scored on the people it was fitted on); the table below has all five sensors'
                others = [int(limbs_people(i).split()[0]) for i in range(4)]
                bt = f"{limbs_people(4)} at the left leg; at most {max(others)} of 4 at the other four sensors"
            else:
                assert n == 20
                ref = (f"One band width for the whole pinch, around the five-grid forecast: **{band('grids', 'one', 'width')}%** wide, "
                       f"{band('grids', 'one', 'covered')} of {band('grids', 'one', 'of')} later readings inside")
                cand = (f"A width for each part of the pinch: **{band('grids', 'phase', 'width')}%** wide, "
                        f"{band('grids', 'phase', 'covered')} inside")
                diff = 'narrower and holds more; the note below has all three forecasts'
                bt = 'not counted per person'
            out.append(f'| {n} | {name} | {pred} | {TESTED[n]} | {ref} | {cand} | {diff} | {bt} |')
        if kinds:
            parts = [f'{_study_list(v)}, {k}' for k, v in sorted(kinds.items(), key=lambda kv: min(kv[1]))]
            out.append('')
            out.append('Ranges: ' + '; '.join(parts) + '.')
        if title == 'Arm acceleration while walking':
            out.append('')
            out.append(arm_notes())
        if title == 'Wrist angle':
            out.append('')
            out.append(wrist_notes())
        if title.startswith("The general model's five-sensor walking fit"):
            out.append('')
            out.append(limbs_table())
        if title == 'Elbow angle':
            st = S(5)
            out.append('')
            out.append('The table gives the measure that punishes large misses (root mean squared error). On the plain average miss the EMG fit '
                       f'lost as well: {st.model(0)} against {st.base(2)} for the timed average path and {st.base(0)} for one fixed angle. '
                       'The person and the arm changed together, left arm to fit and right arm to test, so the study cannot say which of the two broke the fit.')
        out.append('')
    return '\n'.join(out).rstrip()


def _comps(kind, setting=None):
    for s in LEDGER['studies']:
        for i, c in enumerate(s['comparisons']):
            if c['kind'] == kind and (setting is None or c.get('setting') in setting) and not c.get('no_history'):
                yield S(s['n']), i, c


def short(n):
    return f'{n}'


def table_carry_home():
    out = ['| Study | "Repeat the last value" | Fitted to the target\'s own history |', '| ---: | --- | --- |']
    k = 0
    for st, i, c in _comps('carry', ('home',)):
        out.append(f"| {st.n} | {plain(c['rule_label'])}: {st.cmp(i, 'rule')} | "
                   f"{plain(c['fitted_label'])}: **{st.cmp(i, 'fitted')}** |")
        k += 1
    assert k == LEDGER['counts']['carry_home']['n'], k
    return '\n'.join(out)


TRANSFER = 'benchmarks/cemhsey-transfer/RESULTS.json'


def best_at_30():
    """Study 21 at 30%, the level the model was fitted at. The ledger's row holds the force-history fit after one
    practice pinch (0.4274%); the lowest fitted score there is the same fit without the practice pinch (0.4265%).
    The tables are headed "Best fitted model", so they print the lowest, read here from the results file."""
    arms = walk(load(TRANSFER), 'results/6/arms')
    assert walk(load(TRANSFER), 'results/6/target_percent_mvc') == 30 and walk(load(TRANSFER), 'results/6/phase') == 'overall'
    fitted = {k: v['mae'] for k, v in arms.items() if k.startswith('history_phase')}
    best = min(fitted.values())
    assert arms['history_phase_adjusted']['mae'] == best == arms['history_phase_frozen']['mae'], fitted
    assert best < arms['history_phase_adapted']['mae'] < arms['persistence_plus_cue_change']['mae'] < arms['persistence']['mae'], arms
    c = walk(load(TRANSFER), 'results/6/contrasts/2')
    assert (c['candidate'], c['comparator'], c['wins'], c['losses'], c['ties']) == \
        ('history_phase_adjusted', 'persistence_plus_cue_change', 4, 0, 0), c
    txt = N(TRANSFER, 'results/6/arms/history_phase_adjusted/mae', 4, 100.0) + '%'
    return txt, best * 100.0


def table_carry_shifted():
    out = ['| Study | What changed | "Repeat the last value" | Best fitted model |', '| ---: | --- | --- | --- |']
    for st, i, c in _comps('carry', ('shifted', 'fitted-level')):
        a, b = value(c['rule']), value(c['fitted'])
        if c.get('tag') == '21-30':
            fit30, b30 = best_at_30()
            assert a > b > b30, (a, b, b30)
            out.append(f"| {st.n} | The fitted level (30%), new people | {st.cmp(i, 'rule')} | **{fit30}** (force history, without the practice pinch) |")
            continue
        rule, fit = st.cmp(i, 'rule'), st.cmp(i, 'fitted')
        if a < b:
            rule = f'**{rule}**'
        else:
            fit = f'**{fit}**'
        m = re.match(r'best fitted model(?: after practice)? \((.*?)\)(?:, mean absolute error)?$', c['fitted_label'])
        label = m.group(1) if m else c['fitted_label']
        out.append(f"| {st.n} | {plain(c['shift'])} | {rule} | {fit} ({plain(label)[0].lower()}{plain(label)[1:]}) |")
    return '\n'.join(out)


def table_cue_rule():
    out = ['| Study | Target | Current reading plus the scheduled change | Best fitted model | People better with the fitted model |',
           '| ---: | --- | --- | --- | --- |']
    for st, i, c in _comps('cue-rule'):
        a, b = value(c['rule']), value(c['fitted'])
        if c.get('tag') == '21-30':
            fit30, b30 = best_at_30()
            assert a > b > b30 and c['better'] == [4, 4], (a, b, b30, c['better'])
            out.append(f"| {st.n} | {c['shift']} | {st.cmp(i, 'rule')} | **{fit30}** | 4 of 4 |")
            continue
        rule, fit = st.cmp(i, 'rule'), st.cmp(i, 'fitted')
        if a < b:
            rule = f'**{rule}**'
        else:
            fit = f'**{fit}**'
        shift = c['shift']
        if st.n == 23:
            # the ledger's row sets the fitted model against the rule WITH the correction learned from other people
            assert c['rule']['field'].endswith('persistence_plus_cue_change_split/mae'), c['rule']
            plain_rule = st.base(1)
            assert value(st.s['baselines'][1][1]) < b, 'the plain rule must beat the fitted model too'
            shift = '50%, new people'
            rule += f' (with the correction learned from three other people; the plain rule scored {plain_rule})'
        out.append(f"| {st.n} | {shift} | {rule} | {fit} | {c['better'][0]} of {c['better'][1]} |")
    return '\n'.join(out)


def _added(kind, word):
    out = [f'| Study | {word} added to | Without | With {word} | People better | The same model fed {word} from the wrong trial or moment | Main question? |',
           '| ---: | --- | --- | --- | --- | --- | --- |']
    k = low = 0
    for st, i, c in _comps(kind):
        a, b = value(c['without']), value(c['with_'])
        wo, wi = st.cmp(i, 'without'), st.cmp(i, 'with_')
        if b < a:
            wi = f'**{wi}**'
            low += 1
        else:
            wo = f'**{wo}**'
        bt = f"{c['better'][0]} of {c['better'][1]}" if c.get('better') else 'not given'
        ctl = f"{plain(c['control'][0])}: {st.cmp(i, 'control')}" if c.get('control') else 'not run'
        into = plain(c['into'])
        out.append(f"| {st.n} | {into} | {wo} | {wi} | {bt} | {ctl} | {'yes' if c['primary'] else 'no'} |")
        k += 1
    assert k == LEDGER['counts'][kind]['n'] and low == LEDGER['counts'][kind]['lower'], (kind, k, low)
    return '\n'.join(out)


def table_eeg():
    return _added('eeg', 'EEG')


def table_emg():
    return _added('emg', 'EMG')


def table_personal():
    out = ['| Study | Adjustment | Before | After | People better |', '| ---: | --- | --- | --- | --- |']
    k = low = 0
    for st, i, c in _comps('personal'):
        a, b = value(c['without']), value(c['with_'])
        wo, wi = st.cmp(i, 'without'), st.cmp(i, 'with_')
        if b < a:
            wi = f'**{wi}**'
            low += 1
        else:
            wo = f'**{wo}**'
        what = plain(c['what'])
        out.append(f"| {st.n} | {what} | {wo} | {wi} | {c['better'][0]} of {c['better'][1]} |")
        k += 1
    assert k == LEDGER['counts']['personal']['n'] and low == LEDGER['counts']['personal']['lower'], (k, low)
    return '\n'.join(out)


# ---------------------------------------------------------------------------------------------------
# The band study (20): coverage counts, read directly
# ---------------------------------------------------------------------------------------------------
BANDS = 'benchmarks/cemhsey-intervals/RESULTS.json'
BAND_FORECAST = {'carry': 'persistence', 'history': 'history_phase', 'grids': 'history_phase_paired_grid'}
BAND_HOW = {'one': 'pooled', 'phase': 'by_issue_phase'}


def band(forecast, how, what, dp=2):
    """what: covered | of | pct | width | score   (overall, all cue phases together)"""
    node = f'overall/{BAND_FORECAST[forecast]}/{BAND_HOW[how]}'
    if what == 'covered':
        return N(BANDS, node + '/covered')
    if what == 'of':
        return N(BANDS, node + '/issue_windows')
    if what == 'pct':
        a, b = walk(load(BANDS), node + '/covered'), walk(load(BANDS), node + '/issue_windows')
        txt = fmt(100.0 * a / b, 1)
        log(txt, file=BANDS, field=f'{node}/covered ÷ {node}/issue_windows', full=100.0 * a / b, note='x100')
        return txt
    if what == 'width':
        return N(BANDS, node + '/mean_width', dp, 100.0)
    if what == 'score':
        return N(BANDS, node + '/mean_interval_score', dp, 100.0)
    raise KeyError(what)


def band_extremes(scope):
    """Lowest and highest coverage, in %, over the six bands; scope: overall | release."""
    data = load(BANDS)
    vals = []
    for f_ in BAND_FORECAST.values():
        for h in BAND_HOW.values():
            node = data['overall'][f_][h] if scope == 'overall' else data['by_issue_phase']['release'][f_][h]
            vals.append(100.0 * node['covered'] / node['issue_windows'])
    want = S(20).s['extra_json']['coverage_' + scope]
    assert sorted(round(v, 9) for v in vals) == sorted(round(x['percent'], 9) for x in want), (vals, want)
    lo, hi = fmt(min(vals), 1), fmt(max(vals), 1)
    where = 'overall' if scope == 'overall' else 'by_issue_phase/release'
    log(lo, file=BANDS, field=f'{where}/<forecast>/<band>/covered ÷ issue_windows, lowest of the six bands', full=min(vals), note='x100')
    log(hi, file=BANDS, field=f'{where}/<forecast>/<band>/covered ÷ issue_windows, highest of the six bands', full=max(vals), note='x100')
    return lo, hi


def band_release(forecast, how):
    node = f'by_issue_phase/release/{BAND_FORECAST[forecast]}/{BAND_HOW[how]}'
    a, b = walk(load(BANDS), node + '/covered'), walk(load(BANDS), node + '/issue_windows')
    txt = fmt(100.0 * a / b, 1)
    log(txt, file=BANDS, field=f'{node}/covered ÷ {node}/issue_windows', full=100.0 * a / b, note='x100')
    return txt


# ---------------------------------------------------------------------------------------------------
# Paper pages: page counts, and where each study sits in the two NeuroTranslation editions (named destinations)
# ---------------------------------------------------------------------------------------------------
MANIFEST = NEW_EDITION + 'manifest.json'
EDITIONS = [  # index in manifest PDFs, file, label
    (0, 'neurotranslation-technical.pdf', 'NeuroTranslation, Technical'),
    (1, 'neurotranslation-explained.pdf', 'NeuroTranslation, Simple English'),
    (2, 'brain2body-article.pdf', 'Brain2Body, Technical'),
    (3, 'brain2body-simple-english.pdf', 'Brain2Body, Simple English'),
]
NT = EDITIONS[:2]       # only the NeuroTranslation editions have a row for each study (appendix B) and named destinations
# Every study has a row in appendix B of both NeuroTranslation editions, with a named destination there (study 2's of its own
# since the 21 November edition), except study 24, the macaque, whose account is appendix A. The anchors of the studies with a
# folder are read from the source ZIP's appendix (study_anchors()). SHARED_ANCHOR would map a study without a destination of
# its own to the study whose destination it shares; none does now.
SHARED_ANCHOR = {}
OWN_PLACE = {24: 'appendix.A', 25: 'sec:self-forecast'}
EARLIER_ANCHOR = ('sec:earlier-recorded-signals', 'Earlier studies of recorded brain signals, with no row on the studies page')
_anchors = {}


def pdf_dests(rel):
    """Named destinations of a PDF in the clone, {name: page}, read with pdfinfo -dests."""
    if rel not in _anchors:
        out = subprocess.run(['pdfinfo', '-dests', str(REPO / rel)], check=True, capture_output=True, text=True).stdout
        found = {}
        for line in out.splitlines()[1:]:
            parts = line.split()
            if parts and parts[0].isdigit() and line.rstrip().endswith('"'):
                found[line[line.index('"') + 1:line.rstrip().rindex('"')]] = int(parts[0])
        _anchors[rel] = found
    return _anchors[rel]


def study_anchors():
    """Study number -> named destination. The appendix of the source in the source ZIP pairs each destination with the folder
    of its study (\\StudyAnchor{...} ... \\StudyFolder{<ledger key>}); the ledger gives each key its study number."""
    if 'study' not in _anchors:
        import zipfile
        z = zipfile.ZipFile(REPO / SOURCE_ZIP)
        tex = {m: z.read(m).decode('utf-8') for m in z.namelist() if m.endswith(('/appendix-studies.tex', '/appendix-studies-simple.tex'))}
        assert len(tex) == 2, sorted(tex)
        pairs = [dict(re.findall(r'\\StudyAnchor\{([^}]+)\}[^\n]*?\\StudyFolder\{([^}]+)\}', t)) for t in tex.values()]
        assert pairs[0] == pairs[1], 'the two appendices pair destinations and folders differently'
        by_key = {key: anchor for anchor, key in pairs[0].items()}
        out = {}
        for s_ in LEDGER['studies']:
            n = s_['n']
            if s_['key'] in by_key:
                out[n] = by_key[s_['key']]
        for n, other in SHARED_ANCHOR.items():
            assert n not in out
            out[n] = out[other]
        for n, place in OWN_PLACE.items():
            assert n not in out
            out[n] = place
        assert sorted(out) == list(range(1, len(LEDGER['studies']) + 1)), sorted(out)
        long_run = [t for t in tex.values() if r'\StudyAnchor{sec:self-forecast}' in t]
        assert len(long_run) == 2 and all('two-stream network' in t.split(r'\StudyAnchor{sec:self-forecast}')[1].split('\n')[0] for t in long_run)
        _anchors['study'] = out
    return _anchors['study']


def dest(i, name):
    """Page of a named destination in edition i, checked three ways: the manifest records it, the PDF has it, on that page."""
    pdf = EDITIONS[i][1]
    page = walk(load(MANIFEST), f'PDFs/{i}/named_destinations/{name}')
    assert pdf_dests(NEW_EDITION + pdf).get(name) == page, (pdf, name, page)
    log(str(page), file=MANIFEST, field=f'PDFs/{i}/named_destinations/{name}', full=page,
        note='the same name and page read from the PDF with pdfinfo -dests')
    return page


def _page_rows():
    anchors = study_anchors()
    rows = [(f'{n} · {NAME[n]}', anchors[n]) for n in range(1, len(LEDGER['studies']) + 1)]
    rows.append((EARLIER_ANCHOR[1], EARLIER_ANCHOR[0]))
    return rows


def n_page_studies():
    """Studies with a place of their own in both NeuroTranslation editions (all of the numbered table)."""
    n = len(study_anchors())
    log(str(n), file=MANIFEST, field='PDFs/0..1/named_destinations: one for each row of the numbered table', full=n)
    return str(n)


def pages(i):
    return N(MANIFEST, f'PDFs/{i}/pages')


def pages_total():
    tot = sum(walk(load(MANIFEST), f'PDFs/{i}/pages') for i in range(4))
    log(str(tot), file=MANIFEST, field='PDFs/0..3/pages, summed', full=tot)
    return str(tot)


def page_table_md(prefix=''):
    out = ['| Study | ' + ' | '.join(lab for _, _, lab in NT) + ' |', '| --- | ' + ' | '.join(['---:'] * len(NT)) + ' |']
    for label, name in _page_rows():
        cells = [f'[p. {dest(i, name)}]({prefix}{pdf}#nameddest={name})' for i, pdf, _ in NT]
        out.append(f'| {label} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(out)


def page_table_html(query=''):
    out = ['<table>', '<thead><tr><th scope="col">Study</th>' + ''.join(f'<th scope="col">{lab}</th>' for _, _, lab in NT) + '</tr></thead>', '<tbody>']
    for label, name in _page_rows():
        cells = [f'<td><a href="{pdf}{query}#nameddest={name}">p.&nbsp;{dest(i, name)}</a></td>' for i, pdf, _ in NT]
        out.append(f'<tr><th scope="row">{label}</th>' + ''.join(cells) + '</tr>')
    out += ['</tbody>', '</table>']
    return '\n'.join(out)


def study_dest_link(n, prefix):
    """'[technical, p. 50](…#nameddest=…) · [Simple English, p. 59](…)' for one study."""
    name = study_anchors()[n]
    return ' · '.join(f'[{lab}, p. {dest(i, name)}]({prefix}{pdf}#nameddest={name})'
                      for (i, pdf, _), lab in zip(NT, ('Technical', 'Simple English')))


def appendix_pages(letter):
    """'p. 49 of the Technical edition and p. 59 of the Simple English' for appendix A or B."""
    a, b = (dest(i, 'appendix.' + letter) for i, _, _ in NT)
    return f'page {a} of the Technical edition and page {b} of the Simple English'


# ---------------------------------------------------------------------------------------------------
# Counts of things in the repository, and the test groups that were set aside and never opened
# ---------------------------------------------------------------------------------------------------
def n_rows():
    n = len(LEDGER['studies'])
    log(str(n), file=LEDGER_FILE, field='studies (rows)', full=n)
    return str(n)


def n_studies():
    """Studies with a folder under benchmarks/ (each has a result file there)."""
    n = sum(1 for s in LEDGER['studies'] if s['folder'].startswith('benchmarks/') and s['n'] not in NOT_A_TEST)
    for k in FOLDER.values():
        assert (REPO / 'benchmarks' / k).exists(), k
    assert n == len(STUDY_FOLDER), (n, len(STUDY_FOLDER))
    log(str(n), file='benchmarks/', field='result files of the studies (one row each in the ledger)', full=n)
    return str(n)


def n_folders():
    """Top-level folders under benchmarks/ that rows of the numbered table name. Every folder on disk is either one of them or
    a study published after the table (LATER); nothing else is possible, so a new folder can never make this fail."""
    on_disk = sorted(d.name for d in (REPO / 'benchmarks').iterdir() if d.is_dir())
    assert set(TABLE_FOLDERS) <= set(on_disk), sorted(set(TABLE_FOLDERS) - set(on_disk))     # a row's folder was removed
    assert sorted(TABLE_FOLDERS + [r['folder'] for r in LATER]) == on_disk
    log(str(len(TABLE_FOLDERS)), file='benchmarks/', field='folders named by rows of the numbered table: ' + ', '.join(TABLE_FOLDERS), full=len(TABLE_FOLDERS))
    return str(len(TABLE_FOLDERS))


def n_later():
    """Study folders published after the numbered table (no ledger row names them); counted apart from the numbered studies."""
    n_folders()
    log(str(len(LATER)), file='benchmarks/', field='folders that no ledger row names: ' + ', '.join(r['folder'] for r in LATER), full=len(LATER),
        note='published after the numbered table; listed by later_studies()')
    return str(len(LATER))


def _site_pages():
    return sorted(d.name for d in (REPO / 'docs').iterdir()
                  if d.is_dir() and (d / 'index.html').exists() and d.name not in ('papers', 'launchers'))


def n_readers():
    """Study readers of the numbered table on the site (the READER folders). Each must still be there."""
    readers = sorted(set(r.split('/')[0] for r in READER.values() if not r.startswith('index.html')))
    assert set(readers) <= set(_site_pages()), sorted(set(readers) - set(_site_pages()))
    log(str(len(readers)), file='docs/', field='study readers of the numbered table: ' + ', '.join(readers), full=len(readers))
    return str(len(readers))


def n_pages():
    """Every page on the site that runs a study or replays recordings: each folder under docs/ with an index.html, papers and
    launchers aside. The study readers must all be among them; a page published later is counted and named here, never fatal."""
    n_readers()
    names = _site_pages()
    readers = set(r.split('/')[0] for r in READER.values() if not r.startswith('index.html'))
    log(str(len(names)), file='docs/', field='folders with an index.html, papers and launchers aside: ' + ', '.join(names), full=len(names),
        note='not study readers of the numbered table: ' + ', '.join(n for n in names if n not in readers))
    return str(len(names))


def n_datasets(benchmarks_only=True):
    keys = []
    for s_ in LEDGER['studies']:
        if benchmarks_only and not s_['folder'].startswith('benchmarks/'):
            continue
        k = s_['dataset']['name'] if isinstance(s_['dataset'], dict) else s_['dataset']
        if k not in keys:
            keys.append(k)
    log(str(len(keys)), file=LEDGER_FILE, field='distinct datasets of the rows' + (' with a benchmarks folder' if benchmarks_only else ''), full=len(keys))
    return str(len(keys))


HELD = [  # label, studies, how many, what, file, field, what the field must hold
    ('Wrist pointing (EEG-EMG-WristMotion)', '1 to 3 and 28', 6, 'people', 'benchmarks/wrist-forearm-transfer/SOURCE.json', 'slices', 'six reserved test participants not examined'),
    ('Everyday tasks (KIN-MUS UJI)', '4', 4, 'people', 'benchmarks/uji-wrist-emg/DEVELOPMENT-AGGREGATE.json', 'cohort/reserved_test', 4),
    ('Hand to mouth (Lucchetti and colleagues)', '5', 1, 'person', 'benchmarks/surface-emg-elbow/RESULT.json', 'interpretation/confirmation_asset_HS03_opened', False),
    ('Palm (IACKD)', '6', 1, 'person', 'benchmarks/scalp-eeg-hand/DESIGN.json', 'reserve', 'sub-06, metadata only'),
    ('Pinch and lift (WAY-EEG-GAL)', '9 and 10', 3, 'people', 'benchmarks/way-contact-force/RESULTS.json', 'cohorts/final_test/people', 3),
    ('Paced grip (HYGRIP)', '11 to 13', 3, 'people', 'benchmarks/hygrip-force/results-2026-11-19/AGGREGATES.json', 'final_test/assigned_people', 3),
    ('One finger (Hyser)', '14 to 17', 4, 'people', 'benchmarks/hyser-index/crossday/RESULTS.json', 'train/limitations/5', 'Four FINAL participants remain unopened'),
    ('Walking (Daily and Sports Activities)', '26', 2, 'people', 'benchmarks/daily-sports-arm/protocol.json', 'reserve_do_not_read', ['p7', 'p8']),
]


def _held_check():
    # study 28 keeps the same six aside (its plan: six reserved for confirmation), and row 29 keeps them outside its study
    assert walk(load('benchmarks/paired-wrist-forecast/protocol.json'), 'roles/confirmation_reserved') == 6
    assert 'the six reserved participants and all remaining participants are outside this study' in (REPO / 'benchmarks/wrist-forearm-correction/protocol.md').read_text(encoding='utf-8')
    for label, rows, n, what, rel, field, want in HELD:
        got = walk(load(rel), field)
        if isinstance(want, str):
            assert want in got, (rel, field, got)
        else:
            assert got == want and type(got) is type(want), (rel, field, got)


def held_people():
    _held_check()
    n = sum(h[2] for h in HELD)
    log(str(n), file='; '.join(h[4] for h in HELD), field='; '.join(h[5] for h in HELD), full=n, note=f'sum of the {len(HELD)} set-aside groups')
    return str(n)


def held_datasets():
    return str(len(HELD))


def held_table():
    _held_check()
    out = ['| Recordings | Studies | Set aside, never opened |', '| --- | --- | --- |']
    for label, rows, n, what, rel, field, want in HELD:
        log(str(n), file=rel, field=field, full=None, note=f'field holds: {want!r}')
        out.append(f'| {label} | {rows} | {n} {what} |')
    txt = re.sub(r'\s+', ' ', pdf_text(NEW_EDITION + 'neurotranslation-technical.pdf'))
    said = 'Four more are reserved and have not been opened: 22 and 24 February 2020, and 21 and 22 June 2023'
    assert said in txt, said
    log('4', file=NEW_EDITION + 'neurotranslation-technical.pdf', field=f'appendix A, page {dest(0, "appendix.A")}: "{said}"', full=None)
    out.append('| Macaque fingers (LINK) | 24 | 4 recordings |')
    return '\n'.join(out)


def eeg_raised():
    """Comparisons in which adding EEG raised the error (the ledger counts the ones where it fell)."""
    up = sum(1 for st, i, c in _comps('eeg') if value(c['with_']) > value(c['without']))
    assert up == LEDGER['counts']['eeg']['n'] - LEDGER['counts']['eeg']['lower'], up
    log(str(up), file=LEDGER_FILE, field='counts/eeg/n minus counts/eeg/lower', full=up,
        note='recounted here from the result files: error with EEG above error without')
    return str(up)


EEG_RULES = [6, 9, 10, 11]      # the studies whose rule, set in advance, was about EEG (ledger, statement 3)


def eeg_rules():
    for n in EEG_RULES:
        assert S(n).s['rule']['met'].startswith('no') and not S(n).s['rule']['met'].startswith('no rule'), (n, S(n).s['rule'])
    log(str(len(EEG_RULES)), file=LEDGER_FILE, field='studies ' + ', '.join(map(str, EEG_RULES)) + ': rule/met', full=None,
        note='each of the four rules is recorded as not met')
    return str(len(EEG_RULES))


LATER_ABSENT = {   # work published after the papers were written -> words and digits of its results, in none of the four PDFs
    'wtrack-neural-motion': ('2.237', '2.010', 'Jadhav', 'W-Track'),
    'preceding-instructions': ('10.04', '9.79', 'HoloAssist'),
    'hand-language-retrieval': ('35.56', '23.89', 'HoloAssist'),
    'text-motion-retrieval': ('5.57', '6.58', 'Plappert', 'KIT Motion'),
    'models/shared-motion': ('1.725', '1.310', '1.782', '1.342'),
    'models/neurotranslate-0.0': ('4.503', '4.291', '4.491', '4.175', '4.054', '4.419'),
    'models/word-motion': ('89.82', '89.88', 'walk or run'),
    'models/stride-continuation': ('69.1 mm', '71.9 mm', '66.7 mm'),
    'models/knee-motion': ('40,201', '3.54°', '4.46°', 'Xsens'),
    'models/gait-rhythm': ('0.027 cycles', '3.055', 'cycles per minute'),
    'models/population-motion': ('2.898', '2.870', '2.887', 'KL8'),
    'models/neurotranslate-0.0/population': ('2.805', '2.778'),
    'models/knee-stride': ('2.679', '3.411', '3.535'),
    'models/neurotranslate-0.0/knee': ('3.465', '3.460', '3.422'),
    'models/cortical-glove': ('0.1774', '0.2849', '0.2502', '0.03470', 'electrocorticographic'),
    'models/finger-motion': ('0.288', '0.289', '0.354', 'finger-motion'),      # its 0.321 also occurs in the technical paper, as another number
    'models/knee-stride/external-optical': ('3.242', '3.398', 'Reznick'),
    'models/finger-transfer': ('0.4770', '0.4811', '0.5134', '0.5011', 'FingerFlex'),
    'models/neurotranslate-0.0/load': ('0.08874', '0.09761', '0.09373', '0.06785', 'N·m/kg'),
    'models/walking-force': ('65.19', '63.43', 'Moissenet'),     # its 70.20 also occurs in the technical paper, as another number
    'models/neurotranslate-0.0/right-plate': ('85.18', '93.93', '82.04', '76.45'),
    'models/walking-landmarks': ('18.02', '18.22', '17.90', 'Rehazenter'),      # its 17.78 also occurs in the technical paper, as another number
    'models/neurotranslate-0.0/point-motion': ('31.00', '28.73', '30.20', '30.64', '43.29'),
    'models/neurotranslate-0.0/cued-arm': ('0.751', '0.641', '0.525', '0.607', '0.632', '0.556'),
    'models/cue-elbow': ('0.07237', '0.07859', '0.07780', '0.07122', 'Ofner', 'Müller-Putz'),
    'models/arm-transfer': ('0.493', '0.489'),      # its 0.467 also occurs in the papers, as another number
    'models/neurotranslate-0.0/arm-transfer': ('0.484', '0.429', '0.521'),      # its 0.505, 0.793 and 0.435 also occur there, as other numbers
    'models/scalp-forecast': ('0.50853', '0.50856', '0.49278', '0.50965'),
    'models/neurotranslate-0.0/scalp-residual': ('0.49777', '0.49628', '0.49696'),
    'models/cervical-forecast': ('23.28', '24.67', '22.36', '8.09', 'axilla', 'armpit', 'ds004388'),     # 'Nierula' is cited in all four, as a reference
    'models/neurotranslate-0.0/cervical': ('7.77', '9.65', '10.05'),
    'models/back-rotation': ('0.361', '0.382', 'BufferChannel', '19065545'),      # its 0.381 and 0.445 also occur in the technical paper, as other numbers
    'models/neurotranslate-0.0/back_rotation': ('0.376', '0.380'),                # its 0.385 also occurs there, as another number
    'models/muscle-tracking': ('0.236', '0.233', '0.270', '0.223', '0.242', 'AnkleImage', 'S-BIAD1482', 'tibialis', 'ultrasound'),
    'models/neurotranslate-0.0/muscle_tracking': ('0.226', '0.219', '0.217', '0.215', '0.222', '0.249'),
    'models/pedal-load': ('0.05452', '0.06257', '0.12013', '0.16696', 'loadcell'),
    'models/neurotranslate-0.0/pedal_load': ('0.0434', '0.0476', '0.0563', '0.1023', '0.1199', '0.1793', '0.1533'),
    'models/heel-and-force': ('1.156', '92.36', '1.183', '93.73', '1.110', '80.74', '1.024', '103.28', 'calcaneus'),
    'models/neurotranslate-0.0/heel_force': ('1.850', '89.75', '1.232', '91.78', '1.107', '88.41'),
    'models/walking-instructions': ('5.022', '5.742', '5.116', '5.677', '5.491', '6.265', '5.762', '8.514', 'fast but not running'),
    'models/neurotranslate-0.0/walking_cues': ('5.629', '7.650', '7.983', '5.532', '7.504', '7.645', '9.453'),
    'models/visual-balance': ('7.798', '7.175', '7.668', '7.123', '7.840', '7.278', 'ds003739', 'Ferris'),
    'models/neurotranslate-0.0/visual_balance': ('7.368', '6.617', '8.579', '7.738', '8.108', '7.429'),
    'models/muscle-and-motion': ('9.499', '9.453', '1.965', '1.940', '6.248', 'peroneus', 'sacrum path'),
    'models/neurotranslate-0.0/muscle_motion': ('10.70', '10.27', '6.13', '6.06', '0.87 mm'),
    'models/cross-limb-movement': ('4.870', '5.100', '4.394', '2.169', '1.962', '1.981', '2.041', '8.391'),
    'models/neurotranslate-0.0/cross_limb': ('3.387', '2.521', '7.36', '7.70'),
    'models/cross-limb-movement/scalp': ('4.120', '3.905', '2.699', '2.667', '11.370', '11.385', '11.355'),
    'models/cross-limb-movement/path-maps': ('2.582', '2.645', '2.583', '3.878', '3.877', '3.686', '2.497', '2.481'),
    'models/muscle-spindle': ('0.499', '0.842', '0.325', '0.387', '0.435', '1.010', 'Blum', 'aff015'),
    'models/neurotranslate-0.0/cross_person_wrist': ('94.32', '44.18', 'cross-person-wrist'),
    'models/human-wrist': ('29.40', '47.32', '45.59', '51.79', '29.68', '48.83', 'AJILE12', '0.220127.0436'),
    'models/reach-feedback-week': ('0.201', '4.118', '4.783', '4.680', '3.852', '0.468', '0.882', '1.047', '1.539', '0.689', '0.540', '0.096', 'C_20170914'),
    'models/reach-feedback': ('1.1595', '1.1834', '1.1934', '1.1158', '8.398', '9.362', '8.421', '8.115', 'C_20170907'),
    'models/cylinder-rotation': ('0.1584', '0.1622', '0.1772', '0.1508', '0.2525', '2,653', 'gyroscope', 'MTw'),
    'models/target-reach': ('12.13', '12.24', '66.85', '35.43', 'Sziburis', 'J3QC8'),      # its 17.79 and 0.117 also occur in the NeuroTranslation papers, as other numbers
    'models/contact-forecast': ('1.987', '1.991', '1.990', '1.905', '1.015', '1.039', '2,436', 'C_20170913'),
    'models/cortical-reach': ('0.4974', '0.6044', '0.5941', '0.4880', '0.5342', '0.908', '0.761', '0.237', '0.190', 'nk98sf7q7', 'C_20170912'),      # its 0.446 and 0.503 also occur in the NeuroTranslation papers, as other numbers
}
IN_PAPERS = {      # study -> digits of its main scores as the NeuroTranslation paper prints them, which must be in both editions
    8: ('1.849', '1.700'), 10: ('0.6770', '0.6955'), 13: ('0.3741',), 23: ('0.69509',), 26: ('0.855', '1.182'),
    27: ('1.837', '1.929'), 28: ('5.432', '5.866'), 29: ('3.665', '3.549'),
}
SHARED_FIT_SAID = 'Later fits are outside this paper'     # both editions, end of section 7.4: the later fits are on the front page


def not_in_papers():
    """What the pages say about the contents of the papers, checked against the PDFs: the work published after them (the
    four later studies, the shared fit and its wrist-angle path, the walk/run generator) is in none of the four; the eight
    numbered rows that the previous edition lacked are in both NeuroTranslation editions; every numbered study has its place
    there (study_anchors(), each destination on its recorded page); and the papers say in one sentence that the shared fit
    came after them."""
    for _, pdf, _ in EDITIONS:
        t = pdf_text(NEW_EDITION + pdf)
        for k, needles in LATER_ABSENT.items():
            for needle in needles:
                assert needle not in t, (pdf, k, needle)
    for i, pdf, _ in NT:
        t = re.sub(r'\s+', ' ', pdf_text(NEW_EDITION + pdf))
        for n, needles in IN_PAPERS.items():
            for needle in needles:
                assert needle in t, (pdf, n, needle)
        for n, name in study_anchors().items():
            dest(i, name)
        assert SHARED_FIT_SAID in t, pdf
    log(', '.join(LATER_ABSENT), file=NEW_EDITION + '*.pdf', field='text of all four PDFs', full=None,
        note='published after the papers, none in them: ' + '; '.join(f'{k}: {", ".join(v)}' for k, v in LATER_ABSENT.items()))
    log(', '.join(map(str, sorted(IN_PAPERS))), file=NEW_EDITION + 'neurotranslation-technical.pdf and neurotranslation-explained.pdf', field='text', full=None,
        note='rows the previous edition lacked, now printed in both: ' + '; '.join(f'{k}: {", ".join(v)}' for k, v in IN_PAPERS.items()))
    return ''


def n_in_papers():
    """Rows of the numbered table that the NeuroTranslation paper holds: all of them."""
    n = len(study_anchors())
    assert n == len(LEDGER['studies'])
    log(str(n), file=NEW_EDITION + 'neurotranslation-technical.pdf and neurotranslation-explained.pdf', field='named destinations of the numbered rows (study_anchors())', full=n)
    return str(n)


WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
         'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'twenty-one',
         'twenty-two', 'twenty-three', 'twenty-four', 'twenty-five', 'twenty-six', 'twenty-seven', 'twenty-eight', 'twenty-nine',
         'thirty', 'thirty-one', 'thirty-two', 'thirty-three', 'thirty-four', 'thirty-five', 'thirty-six', 'thirty-seven',
         'thirty-eight', 'thirty-nine', 'forty']


def spell(n, cap=False):
    w = WORDS[int(n)]
    return w[0].upper() + w[1:] if cap else w


def max_tested():
    n = max(s_['n_tested'] for s_ in LEDGER['studies'])
    log(str(n), file=LEDGER_FILE, field='largest "n_tested" of any row', full=n)
    return str(n)


MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']


def built_date():
    iso = walk(load(MANIFEST), 'evidence_revision_date')
    y, m, d = iso.split('-')
    txt = f'{int(d)} {MONTHS[int(m) - 1]} {y}'
    log(txt, file=MANIFEST, field='evidence_revision_date', full=None, note=iso)
    return txt


def rules(kind):
    """Study numbers by the outcome of the pass rule each set in advance: failed | name | band | split | none."""
    got = {'failed': [], 'name': [], 'band': [], 'split': [], 'none': []}
    for s_ in LEDGER['studies']:
        if s_['n'] in NOT_A_TEST:
            continue
        m = s_['rule']['met']
        if m.startswith('no rule'):
            got['none'].append(s_['n'])
        elif m == 'no' or m.startswith('no ('):
            got['failed'].append(s_['n'])
        elif m.startswith('yes in name'):
            got['name'].append(s_['n'])
        elif m.startswith('yes'):
            got['band'].append(s_['n'])
        else:
            assert m.startswith('mixed') or m.startswith('grids:'), (s_['n'], m)
            got['split'].append(s_['n'])
    c = LEDGER['counts']['preset_rule']
    assert (len(got['failed']), len(got['split']), len(got['name']), len(got['band']), len(got['none'])) == \
        (c['not_met'], c['mixed'], c['met_in_name_only'], c['met_on_a_question_other_than_forecast_error'], c['none_stated']), got
    nums = sorted(got[kind])
    log(', '.join(map(str, nums)), file=LEDGER_FILE, field='studies[].rule.met', full=None,
        note=f'studies whose rule outcome is "{kind}"; each rule is quoted from its study\'s plan in studies[].rule.text')
    if len(nums) == 1:
        return str(nums[0])
    return ', '.join(map(str, nums[:-1])) + ' and ' + str(nums[-1])


ARM = 'benchmarks/daily-sports-arm/results.json'
ARM_LATER = 'benchmarks/daily-sports-arm/architecture/earlier-results.json'     # per-person scores and the general model's right-arm fit
ARM_HZ = 'benchmarks/daily-sports-arm/architecture/results.json'               # the comparison of horizons
LIMBS = 'benchmarks/daily-sports-limbs/results.json'
LIMBS_PLAN = 'benchmarks/daily-sports-limbs/protocol.json'
PAIRED = 'benchmarks/paired-wrist-forecast/results.json'          # study 28: the general model on the wrist, with EMG and EEG
PAIRED_PLAN = 'benchmarks/paired-wrist-forecast/protocol.json'
CORR = 'benchmarks/wrist-forearm-correction/results.json'         # row 29: a correction scored on the wrist data's fitting people


def swap_gap(kind):
    """Study 28: how much higher the same fitted model's error was when it was given the next trial's EMG or EEG instead of the
    trial's own (the sentences that print this say the own signal did better, so the sign must say so too)."""
    field = f'contrasts/aligned_{kind}_minus_wrong/equal_person_delta_deg'
    assert walk(load(PAIRED), field) < 0, (kind, walk(load(PAIRED), field))
    return N(PAIRED, field, 4, absolute=True)


def emg_worse_check():
    """For the README's EMG bullet: study 28's EMG raised the general model's error, and stayed higher with any one of its
    three people left out (the whole leave-one-out range above zero)."""
    c = walk(load(PAIRED), 'contrasts/add_emg')
    assert c['methods'] == ['transformer_emg', 'transformer_motion'] and c['equal_person_delta_deg'] > 0, c
    assert min(c['leave_one_out_range_deg']) > 0 and walk(load(PAIRED), 'participants') == 3, c
    log('stayed higher with any one of the three people left out', file=PAIRED, field='contrasts/add_emg/leave_one_out_range_deg',
        full=c['leave_one_out_range_deg'], note='both ends above zero; participants 3')
    return ''
def general_worse_check():
    """For the README's first screen: given forearm EMG, or EMG and scalp EEG, on top of the wrist's movement, the general model's
    error in study 28 was higher than with the movement alone (both brain-and-muscle fits above the movement-only fit)."""
    w = LEDGER['counts']['general_learner']['wrist']
    assert w['row'] == 28 and w['emg'] > w['motion'] and w['full'] > w['motion'] and w['emg_made_it_worse'], w
    log('did worse with them than without', file=LEDGER_FILE, field='counts/general_learner/wrist/{motion,emg,full}', full=None,
        note=f"motion {w['motion']!r}; with EMG {w['emg']!r}; with EMG and EEG {w['full']!r}")
    return ''


PARTS = [('torso', 'Torso'), ('right_arm', 'Right arm'), ('left_arm', 'Left arm'), ('right_leg', 'Right leg'), ('left_leg', 'Left leg')]


def first_fits():
    """For sentences about the general model's first fits: confirm, from the published files, that the five-sensor fit is
    scored only on its own fitting people, that its plan rules out any claim about new people, that the right-arm fit was
    scored on two people study 26 had already scored, and that neither saw a brain or muscle signal."""
    assert walk(load(LIMBS), 'scope') == 'TRAIN development only; p5-p8 excluded'
    assert walk(load(LIMBS), 'people') == ['p1', 'p2', 'p3', 'p4']
    assert 'No validation, generalization, new-subject accuracy' in walk(load(LIMBS_PLAN), 'report')
    assert set(walk(load(LIMBS_PLAN), 'channels_zero_based')) == {k for k, _ in PARTS}
    assert 'acceleration' in walk(load(LIMBS_PLAN), 'measure')
    assert walk(load(ARM_LATER), 'training_subjects') == ['p1', 'p2', 'p3', 'p4'] and 'Previously assessed p5 and p6' in walk(load(ARM_LATER), 'study')
    assert 'no neural/EMG/language observations' in walk(load(ARM_LATER), 'scope')
    assert S(27).s['not_a_test'] is True and LEDGER['counts']['general_learner_first_fit']['brain_or_muscle_signals_given'] == 0
    assert [k for k, _ in PARTS if walk(load(LIMBS), f'regions/{k}/strict_train_superiority')] == ['left_leg']
    # study 28: three fresh fits of the same learner, with forearm EMG and scalp EEG, scored on the three people studies 1 to 3 had scored
    assert 'HandArmLearner' in walk(load(LIMBS_PLAN), 'learner') and 'Only three fresh shared HandArmLearner fits' in walk(load(PAIRED_PLAN), 'fit')
    assert 'previously examined exploratory group' in walk(load(PAIRED_PLAN), 'question') and walk(load(PAIRED), 'participants') == 3
    assert 'Motion + EMG adds 4 RMS bipolar' in walk(load(PAIRED_PLAN), 'inputs') and 'Motion + EMG + EEG adds 8 measured scalp channel means' in walk(load(PAIRED_PLAN), 'inputs')
    gl = LEDGER['counts']['general_learner']
    assert gl['scored_on_people_not_looked_at_before'] == 0 and gl['fits'] == 5 and gl['wrist']['emg_made_it_worse'] and gl['wrist']['lowest_was_row_1_learned_forecast']
    log('first fits: motion only, scored on the fitted people or on two people already scored; wrist, with EMG and EEG, scored on three people already scored',
        file=LIMBS + '; ' + LIMBS_PLAN + '; ' + ARM_LATER + '; ' + PAIRED_PLAN, field='scope; report; channels_zero_based; training_subjects; study; scope; fit; question; inputs', full=None,
        note='"TRAIN development only; p5-p8 excluded"; the plan rules out new-subject claims; the right-arm fit was scored on "previously assessed p5 and p6"; '
             'study 28: "Only three fresh shared HandArmLearner fits", "On a previously examined exploratory group"')
    return ''


def arm_people_range():
    """Study 26: each test person's change, transformer minus straight-line fit (published after the study)."""
    d = []
    for q in ('p5', 'p6'):
        a, b = walk(load(ARM_LATER), f'ordered/{q}/mae/transformer'), walk(load(ARM_LATER), f'ordered/{q}/mae/ridge')
        d.append(a - b)
        log(fmt(a - b, 3), file=ARM_LATER, field=f'ordered/{q}/mae/transformer  minus  ordered/{q}/mae/ridge', full=a - b,
            note='difference of the two unrounded scores')
    assert all(x > 0 for x in d), d
    lo, hi = sorted(d)
    return f'higher by {fmt(lo, 3)} for one person and {fmt(hi, 3)} for the other'


def limbs_people(i, against='every'):
    """Row 27: how many of the four fitting people had a lower error with the general model than with every other
    forecast (or than with the straight-line fit) at placement i."""
    k = PARTS[i][0]
    sc = walk(load(LIMBS), f'regions/{k}/scores')
    comps = [m for m in sc['all']['mae'] if m != 'shared'] if against == 'every' else [against]
    n = sum(1 for q in ('p1', 'p2', 'p3', 'p4') if all(sc[q]['mae']['shared'] < sc[q]['mae'][m] for m in comps))
    log(f'{n} of 4', file=LIMBS, field=f'regions/{k}/scores/p1..p4/mae: shared below ' + ', '.join(comps), full=n,
        note='people of the four fitting people')
    return f'{n} of 4'


def limbs_table():
    st = S(27)
    out = ['| Sensor | Repeat the last value | Straight-line fit for that sensor | Study 26\'s transformer, fitted for the right arm alone | '
           'The general model, one fit for all five | People for whom the general model beat every other forecast |',
           '| --- | --- | --- | --- | --- | --- |']
    assert 'right arm' in st.s['baselines'][10][0]
    for i, (k, lab) in enumerate(PARTS):
        ptrs = [st.s['baselines'][i][1], st.s['baselines'][5 + i][1]] + ([st.s['baselines'][10][1]] if k == 'right_arm' else []) + [st.s['models'][i][1]]
        vals = [value(x) for x in ptrs]
        cells = [st.base(i), st.base(5 + i)] + ([st.base(10)] if k == 'right_arm' else []) + [st.model(i)]
        best = vals.index(min(vals))
        cells[best] = f'**{cells[best]}**'
        if k != 'right_arm':
            cells.insert(2, '')
        out.append(f'| {lab} | ' + ' | '.join(cells) + f' | {limbs_people(i)} |')
    out.append('')
    assert value(st.s['baselines'][10][1]) < value(st.s['models'][1][1])
    out.append('Study 26\'s transformer, fitted for the right-arm sensor alone on the same four people, was lower than the general model there for all '
               f'{spell(4 - int(limbs_people(1, "direct_right_arm").split()[0]))}. The rule set before fitting asked the general model '
               'to beat every other forecast for every person, sensor by sensor. That happened at the left leg only. Because the people are '
               'the ones it was fitted on, the rule says nothing about a new walker, and the plan itself rules out any such claim.' + first_fits())
    return '\n'.join(out)


def arm_notes():
    st = S(26)
    hz = load(ARM_HZ)
    assert walk(hz, 'uniform_direct_win') is True and walk(hz, 'reserve_members_opened') == 0
    rows = []
    names = [('direct', 'One straight-line fit for each horizon'), ('recursive', 'One straight-line fit fed its own guesses'),
             ('bolt_median', 'A downloaded pretrained model, used as it came'), ('persistence', 'Repeat the last value')]
    for i, ms in enumerate(walk(hz, 'horizons_nominal_ms')):
        cells = [N(ARM_HZ, f'metrics/pooled/{k}/mae/{i}', 3) for k, _ in names]
        vals = [walk(hz, f'metrics/pooled/{k}/mae/{i}') for k, _ in names]
        lo = min(vals)
        cells = [f'**{c}**' if v == lo else c for c, v in zip(cells, vals)]
        rows.append(f'| {ms} ms | ' + ' | '.join(cells) + ' |')
    table = '\n'.join(['| How far ahead | ' + ' | '.join(lab for _, lab in names) + ' |', '| --- | ---: | ---: | ---: | ---: |'] + rows)
    p5 = [N(ARM_LATER, f'ordered/p5/mae/{k}', 3) for k in ('ridge', 'transformer')]
    p6 = [N(ARM_LATER, f'ordered/p6/mae/{k}', 3) for k in ('ridge', 'transformer')]
    gen5, gen6 = N(ARM_LATER, 'ordered/p5/mae/general', 3), N(ARM_LATER, 'ordered/p6/mae/general', 3)
    return (f'Both forecasts in study 26 beat repeating the last value ({st.base(0)}). The straight-line fit was lower for both people '
            f'({p5[0]} against {p5[1]}, and {p6[0]} against {p6[1]}) and on both walks, so the transformer failed the pass rule set before scoring. '
            f'With the first 15 of the 16 readings shuffled, the straight-line fit rose to {st.model(2)} and the transformer to {st.model(3)}: '
            'both had been using the order of the readings.\n\n'
            'Two later comparisons used the same two people again, so they are not fresh tests. The general model, fitted to the right arm alone on the '
            f'same four people, scored {st.model(4)}: behind the straight-line fit for both people, behind the transformer for one ({gen5} against {p5[1]}) '
            f'and ahead of it for the other ({gen6} against {p6[1]}).{first_fits()} And a comparison of how far ahead to forecast found the straight-line fit with one equation per horizon '
            'lowest for both people at every horizon from 120 ms on:\n\n' + table + '\n\n'
            'The pretrained model is Chronos-Bolt tiny, a forecasting model trained by others on many kinds of time series and downloaded as it is. '
            '[The comparison](daily-sports-arm/architecture/README.md) also times each forecast; its closing advice on what to build next is a proposal, not a result.')


def wrist_notes():
    """Under the wrist table of the studies page: study 28 with its controls, and row 29."""
    st, sc = S(28), S(29)
    assert walk(load(PAIRED), 'trials') == 959 and walk(load('benchmarks/wrist-pointing-temporal/DEVELOPMENT-AGGREGATE.json'), 'support/development/eligible_trials') == 960
    assert 'All six windows of one previously published example trial were removed' in walk(load(PAIRED_PLAN), 'roles/selection')
    assert "Keep the prior ridge weights" in walk(load(PAIRED_PLAN), 'fit') and 'Never refit ridge, prior temporal CNN' in walk(load(PAIRED_PLAN), 'fit')
    pairs = [('Wrist history', 0, 3), ('Wrist history and forearm EMG', 1, 4), ('Wrist history, forearm EMG and scalp EEG', 3, 5),
             ('Wrist history and forearm EMG, the EMG taken from the next trial', 2, 6),
             ('Wrist history, EMG and EEG, the EEG taken from the next trial', 4, 7)]
    assert 'linear fit on wrist history' in st.s['baselines'][3][0] and 'learned forecast' in st.s['baselines'][8][0]
    rows = ['| What the forecast read | The general model | Study 2\'s straight-line fit, re-scored |', '| --- | ---: | ---: |']
    for lab, i, j in pairs:
        a, b = st.model(i), st.base(j)
        if value(st.s['models'][i][1]) < value(st.s['baselines'][j][1]):
            a = f'**{a}**'
        else:
            b = f'**{b}**'
        rows.append(f'| {lab} | {a} | {b} |')
    assert value(st.s['baselines'][8][1]) < min(value(m[1]) for m in st.s['models'])
    assert all(walk(load(PAIRED), f'contrasts/ridge_aligned_{k}_minus_wrong/equal_person_delta_deg') < 0 for k in ('emg', 'eeg'))   # "rose by"
    n3 = N(CORR, 'contrasts/corrected_emg_minus_base/people_favoring_first')
    slot = [N(CORR, f'scores/{k}/slot_rmse_deg/0', 3) for k in ('corrected_motion', 'corrected_emg')]
    sm, se = walk(load(CORR), 'scores/corrected_motion/slot_rmse_deg'), walk(load(CORR), 'scores/corrected_emg/slot_rmse_deg')
    assert [i for i in range(6) if se[i] < sm[i]] == [0, 1] and walk(load(CORR), 'target_seconds_after_cue')[:2] == [0.75, 1]
    return ('Study 28 holds the general model\'s first fits on a recording that also has muscle and brain signals: three fits, one for each set of inputs, on the six people studies 1 to 3 '
            f'were fitted on, scored on those studies\' three test people ({N(PAIRED, "trials")} of their 960 trials; one trial that had been published as an '
            'example elsewhere was removed). The straight-line fits beside them are study 2\'s own fits, re-scored on the same trials: they are not new, and they '
            'count nowhere.\n\n' + '\n'.join(rows) + '\n\n'
            f'Repeating the last angle scored {st.base(0)}. Study 1\'s learned forecast, which reads only the wrist\'s history, re-scored on the same trials, scored '
            f'{st.base(8)}: lower than every fit above. EMG made the general model worse whichever of the three people was left out ({st.range_words()}). '
            f'Given the next trial\'s EMG instead of its own, the general model\'s error rose by only {swap_gap("emg")}°, '
            f'and given the next trial\'s EEG, by {swap_gap("eeg")}°; the straight-line fits rose by '
            f'{N(PAIRED, "contrasts/ridge_aligned_emg_minus_wrong/equal_person_delta_deg", 3, absolute=True)}° and '
            f'{N(PAIRED, "contrasts/ridge_aligned_eeg_minus_wrong/equal_person_delta_deg", 3, absolute=True)}°. The straight-line fits depended on each '
            'trial\'s own electrical signals; the general model hardly did. The study set no pass rule.' + first_fits() + '\n\n'
            'In row 29, each of the six people was scored in turn by models fitted on the other five: a '
            f'learned forecast of study 1\'s design ({sc.base(2)}), then the same forecast with a correction learned from its mistakes on the other five, from wrist motion alone '
            f'({sc.ref()}) or with forearm EMG as well ({sc.cand()}), over {int(N(CORR, "eligible_trials")):,} trials. The EMG correction beat the motion-only one for {sc.better()} people, but against the uncorrected forecast only '
            f'{n3} of 6 did better. It helped early, 0.75 and 1 second after the cue (at 0.75 seconds, {slot[1]}° against {slot[0]}°), and made the forecast worse at '
            f'the four later moments. Given another person\'s EMG the correction scored {sc.model(3)}, and given its own EMG in reverse order, {sc.model(4)}. '
            'The folder notes that movement and the contact of the electrodes can both change the EMG reading, and that neither control tells the two apart.')


# ---------------------------------------------------------------------------------------------------
# Studies published after the numbered table (the folders published on the evening of 20 November). Their numbers are read
# here from their own result files; they enter no count of the numbered table.
# ---------------------------------------------------------------------------------------------------
WT = 'benchmarks/wtrack-neural-motion/fitted/scores.json'                       # rat on a W-shaped track: firing and position
WT_UNITS = 'benchmarks/wtrack-neural-motion/recording/evidence/units.json'
PI = 'benchmarks/preceding-instructions/preceding-words-model/results/aggregate.json'   # an instructor's words and the wrist
PI_MODEL = 'benchmarks/preceding-instructions/preceding-words-model/results/model.json'
HL = 'benchmarks/hand-language-retrieval/results/results.json'                   # a sentence and the tracked hand
HL_SPLIT = 'benchmarks/hand-language-retrieval/source/SPLIT.json'                # its recordings and their roles (train, review, reserve)
TM = 'benchmarks/text-motion-retrieval/results-summary.json'                     # a sentence and whole-body recordings
WB = 'docs/whole-body/data/manifest.json'                                        # three whole-body recordings in 3D
SM = 'models/shared-motion/shared-motion-model/summary.json'                     # the general model's shared fit: wrist and rat
SM_PLAN = 'models/shared-motion/shared-motion-model/protocol.json'
ANG = 'models/neurotranslate-0.0/results.json'                                   # the shared fit's added wrist-angle path
FA = 'models/neurotranslate-0.0/forearm/results.json'                            # a correction fitted on top of that path
GAIT = 'models/gait-rhythm/results.json'                                          # muscle and knee rhythms in the same treadmill walk


def gait_checks():
    """The rhythm comparison (models/, published after the papers): the same trial's muscle rhythm was far closer to the knee rhythm
    than another walker's or the training median; 11 test people at one speed."""
    g = load(GAIT)
    s = {k: v['mae'] for k, v in g['scores'].items()}
    assert g['included_people'] == 11 and len(g['people']) == 11 and s['matched_emg'] < s['affine_emg'] < s['training_median'] < s['wrong_person'] and g['criterion_met'] is True, s
    log('rhythm: same-trial muscle rhythm closest to the knee rhythm; another walker\'s furthest', file=GAIT, field='people; scores/*/mae; criterion_met', full=None)
    return ''


KNEE = 'models/knee-motion/phase-results.json'                                     # both knees 15 stored frames ahead, against replaying a stride


def knee_checks():
    """The knee forecast (models/, published after the papers): replaying an earlier stride beat the transformer on the same windows;
    51 recordings, 6 processed whole-file (HD) and 45 labelled Live; 12 held-out walkers."""
    k = load(KNEE)
    assert k['prior_stride_mean_mae_degrees'] < k['transformer_mean_mae_degrees'] and k['prior_stride_wins'] == 10 and k['transformer_wins'] == 2
    assert k['horizon_frames'] == 15 and k['long_history_frames'] == 240 and k['model_history_frames'] == 25 and k['test_people'] == 12
    t = load('models/knee-motion/technical-summary.json')
    assert t['files'] == 51 and sorted(c['files'] for c in t['counts']) == [6, 45], t['counts']
    log('knee: replaying a stride beat the transformer (10 of 12 walkers); 51 recordings, 6 whole-file HD and 45 Live', file=KNEE + '; models/knee-motion/technical-summary.json',
        field='prior_stride_mean_mae_degrees; transformer_mean_mae_degrees; *_wins; files; counts', full=None)
    return ''


def knee_n():
    n = walk(load(KNEE), 'eligible_cutoffs')
    log(f'{n:,}', file=KNEE, field='eligible_cutoffs', full=n)
    return f'{n:,}'


FG = 'models/cortical-glove/study-results.json'             # one person's glove and a recording from the surface of the brain


def finger_checks():
    """The five-finger study (models/, published after the papers): keeping the last reading had the lowest error of all; adding the
    brain recording raised the straight-line model's error on every finger (each finger's range below zero) and in all 23 trials, with
    a range below zero overall; the right trial's recording did not clearly beat an earlier trial's (range through zero); the
    transformer got worse with it too; one person; 52 fitting and 23 scored trials."""
    f = load(FG)
    s = {k: v['macro_normalized_mae'] for k, v in f['scores'].items()}
    assert s['persistence'] == min(s.values()) and s['motion_cue'] < s['aligned'] and s['encoder_motion_cue'] < s['encoder_aligned'], s
    c = {(x['baseline'], x['candidate']): x for x in f['contrasts']}
    a = c[('motion_cue', 'aligned')]
    assert a['macro_normalized_gain'] < 0 and a['macro_interval'][1] < 0 and a['evaluated_trials_positive_macro_gain'] == 0
    assert all(g < 0 for g in a['per_digit_gain_glove_units']) and all(hi < 0 for lo, hi in a['per_digit_interval'])
    w = c[('earlier_substitute', 'aligned')]
    assert w['macro_interval'][0] < 0 < w['macro_interval'][1]
    assert f['count_people'] == 1 and f['train']['scored_trials'] == 52 and f['development_evaluation']['scored_trials'] == 23 and f['provisional_ridge_advantage'] is False
    log('five fingers: keeping the last reading lowest; brain recording worse for the straight-line model on every finger and every trial, range below zero; '
        'right trial not clearly better than an earlier trial; transformer worse too; one person, 52 and 23 trials', file=FG,
        field='scores/*/macro_normalized_mae; contrasts; count_people; train/scored_trials; development_evaluation/scored_trials; provisional_ridge_advantage', full=None)
    return ''


FM = 'models/finger-motion/results.json'                     # the same person and recording: how much each finger moves, with no recent glove reading
KX = 'models/knee-stride/external-optical/results.json'      # the four-second knee model, unchanged, on ten walkers of a second laboratory


def finger_motion_checks():
    """How much each finger moves (models/, published after the papers): the screen alone gave the lowest error, for both model kinds;
    adding the brain recording raised both, with ranges clear of zero; the brain recording alone was about the training average for the
    straight-line model; neither met the within-cue rule; one person, the cortical-glove recording, 52 and 23 trials."""
    f = load(FM)
    s = {k: v['macro_normalized_mae'] for k, v in f['scores'].items()}
    assert s['ridge_cue'] == min(s.values()) and s['transformer_cue'] < s['transformer_aligned'] and s['ridge_cue'] < s['ridge_aligned'], s
    assert abs(s['ridge_cortex'] - s['training_mean']) < 0.002 and s['ridge_cortex'] < s['training_mean']
    c = {(x['baseline'], x['candidate']): x for x in f['primary_contrasts']}
    for b, a in (('ridge_cue', 'ridge_aligned'), ('transformer_cue', 'transformer_aligned')):
        assert c[(b, a)]['macro_normalized_gain'] < 0 and c[(b, a)]['macro_interval'][1] < 0, (b, a)
    assert f['gated_within_cue_advantage'] == {'ridge': False, 'transformer': False} and f['person_count'] == 1
    assert f['train']['trials'] == 52 and f['evaluation']['trials'] == 23 and f['development_prefix_sha256'] == load(FG)['source_sha256']
    log('finger movement: screen alone lowest for both models; brain recording raised both, ranges below zero; brain alone about the training mean; '
        'within-cue rule not met; one person, same recording as the glove study', file=FM + '; ' + FG,
        field='scores/*/macro_normalized_mae; primary_contrasts; gated_within_cue_advantage; person_count; train/trials; evaluation/trials; development_prefix_sha256', full=None)
    return ''


def knee_external_checks():
    """The four-second knee model in a second laboratory (models/knee-stride/external-optical/): ten walkers, unchanged model; the
    transformer was lower than the copied stride on average with a range through zero, closer for 6 of 10, rule failed; it beat the
    straight-line correction (9 of 10, rule passed); the walking was faster than the original 0.5 m/s."""
    x = load(KX)
    m = {k: v['bilateral'] for k, v in x['mean_person_mae_deg'].items()}
    c = x['comparisons']
    s, r = c['transformer_residual_minus_prior_stride'], c['transformer_residual_minus_ridge_residual']
    assert x['participants_scored'] == 10 and m['transformer_residual'] < m['prior_stride'] < m['ridge_residual'], m
    assert s['mean'] < 0 and s['CI95'][0] < 0 < s['CI95'][1] and s['wins'] == 6 and s['passed'] is False
    assert r['wins'] == 9 and r['passed'] is True and r['CI95'][1] < 0
    assert x['model_hashes']['weights.json'] == load(KS)['weights_sha256'], 'the same weights as the original study'
    assert 's0x8' in x['domain'] and 'optical' in x['domain']
    log('external knee test: transformer < copied stride < straight-line; vs stride range through zero, 6 of 10, rule failed; vs straight-line 9 of 10, passed; same weights; 0.8 m/s optical',
        file=KX + '; ' + KS, field='participants_scored; mean_person_mae_deg; comparisons; model_hashes/weights.json; domain; weights_sha256', full=None)
    return ''


FT = 'models/finger-transfer/results.json'                  # five people's finger movement, each person held out in turn, after a short calibration
KM = 'models/neurotranslate-0.0/load/results.json'           # the general model's knee turning-moment task (a second laboratory's treadmill walking)


def finger_transfer_checks():
    """The cross-person finger study (models/, published after the papers): five people, each held out in turn and scored after the
    first 80 seconds of their own recording; the cue table lowest; cue and time beat both models given the brain recording too, for both
    kinds of model; the brain recording alone worst; the right trial's recording a little better than an earlier trial's (interval
    above zero); neither model met the transfer rule; the brain recording helped against the cue table for two of the five (the
    transformer for one, the straight-line model for another)."""
    d = load(FT)
    m = d['cohort_mean_scaled_mae']
    assert d['person_order'] == ['bp', 'cc', 'ht', 'jc', 'jp'] and m['cue_table'] == min(m.values()), m
    for k in ('ridge', 'transformer'):
        assert m[f'{k}_cue'] < m[f'{k}_aligned'] < m[f'{k}_earlier'] < m[f'{k}_cortex'], (k, m)
        e = d['contrasts'][f'{k}.primary.earlier']
        assert e['mean'] > 0 and e['interval'][0] > 0 and d['gate'][k]['five_person_pass'] is False, (k, e)
    helped = sorted(p for p in d['person_order'] if min(d['people'][p]['models'][f'{k}_aligned']['scaled_mae'] for k in ('ridge', 'transformer')) < d['people'][p]['models']['cue_table']['scaled_mae'])
    assert helped == ['bp', 'jc'], helped
    assert all(d['people'][p]['support']['calibration_trials'] == 18 for p in d['person_order'])
    log('cross-person fingers: cue table lowest; cue beat cue+brain for both models; brain alone worst; right trial a little better than an earlier one; '
        'transfer rule not met; brain helped against the cue table for bp and jc', file=FT,
        field='person_order; cohort_mean_scaled_mae; contrasts/*.primary.earlier; gate/*/five_person_pass; people/*/models; people/*/support/calibration_trials', full=None)
    return ''


def knee_moment_checks():
    """The general model's knee turning-moment task (models/neurotranslate-0.0/load/, published after the papers): seven training and
    three test walkers; the task-trained correction lowest of the angle-only methods but without its consistent advantage; the frozen
    shared encoder behind the straight-line fit and the training-walker match, and a scrambled copy behind it; replaying an earlier
    measured moment lower than everything on the cutoffs where it was possible."""
    d = load(KM)
    m = d['mean_person_mae_Nm_per_kg']
    assert len(d['training']['people']) == 7 and len(d['evaluation']['people']) == 3, d['evaluation']['people']
    assert m['trained'] == min(m.values()) and m['train_walker_match'] < m['ridge'] < m['shared'] < m['scrambled'] < m['mean'], m
    assert d['trained_advantage'] is False and d['shared_encoder_advantage'] is False
    s = d['mean_person_mae_past_moment_subset']
    assert s['replay_past_moment'] == min(s.values()) and s['hold_past_moment'] == max(s.values()), s
    assert d['paired_differences_Nm_per_kg']['trained_minus_ridge']['wins'] == 2 and d['paired_differences_Nm_per_kg']['trained_minus_train_walker_match']['wins'] == 1
    log('knee moments: task-trained lowest of angle-only, no consistent advantage; frozen shared encoder behind the linear fit and the walker match; '
        'replaying an earlier moment lowest where possible', file=KM,
        field='training/people; evaluation/people; mean_person_mae_Nm_per_kg; mean_person_mae_past_moment_subset; *_advantage; paired_differences_Nm_per_kg', full=None)
    return ''


KS = 'models/knee-stride/results.json'                      # four seconds of both knees: the stride replay and two corrections trained for the knees
KS_PLAN = 'models/knee-stride/protocol.json'
KSH = 'models/neurotranslate-0.0/knee/results.json'          # the general model's knee task on the same cutoffs
KSH_PLAN = 'models/neurotranslate-0.0/knee/protocol.json'


def knee_stride_checks():
    """The four-second knee comparison and the general model's knee task (models/, published after the papers): every direction
    the pages state, asserted against the result files. The 12 walkers and 40,201 cutoffs are those of the 15-frame knee forecast
    (KNEE), already known when this was designed; the transformer beat the replay and the straight-line correction for all 12; the
    general model's task was a little below the replay with a range through zero, above the same step without its shared part, and
    a scrambled copy did better; it met not its own rule."""
    k = load(KS)
    m = {x: k['mean_person_mae_deg'][x]['bilateral'] for x in ('prior_stride', 'ridge_residual', 'transformer_residual')}
    assert m['transformer_residual'] < m['ridge_residual'] < m['prior_stride'], m
    d = k['paired_person_differences_deg']
    assert d['transformer_residual_minus_prior_stride']['wins'] == 12 and d['transformer_residual_minus_ridge_residual']['wins'] == 12
    assert k['people'] == 12 and k['train_people'] == 39 and k['cutoffs'] == walk(load(KNEE), 'eligible_cutoffs') == 40201
    assert sorted(p['participant'] for p in k['participants']) == list(range(41, 53)) and walk(load(KNEE), 'test_people') == 12
    assert m['prior_stride'] == walk(load(KNEE), 'prior_stride_mean_mae_degrees'), 'the same replay on the same cutoffs'
    plan = walk(load(KS_PLAN), 'eligibility') + ' ' + walk(load(KS_PLAN), 'design')
    assert '240 finite bilateral knee pairs' in plan and 'Fifteen frames span 0.25 s' in plan and 'Descriptive reuse of the original 12 test participants' in plan
    s = load(KSH)
    e = s['mae_degrees']
    assert e['stride'] == m['prior_stride'] and s['cutoffs'] == k['cutoffs'] and sorted(p['person'] for p in s['per_person']) == list(range(41, 53))
    assert e['scrambled'] < e['raw'] < e['shared'] < e['stride'] and s['shared_advantage_criterion_met'] is False, e
    c = s['comparisons']['stride']
    assert c['shared_minus_comparator_deg'] < 0 and c['paired_ci95'][0] < 0 < c['paired_ci95'][1] and m['transformer_residual'] < e['shared']
    assert 'without changing its weights' in walk(load(KSH_PLAN), 'tokens') and 'Train S1–40 except S24' in walk(load(KSH_PLAN), 'split')
    log('four-second knees: transformer < straight-line < replay, transformer closer for all 12 against both; same 12 walkers and cutoffs as the '
        '15-frame forecast; general model: scrambled < without shared part < with it < replay, range through zero, its rule not met',
        file=KS + '; ' + KSH + '; ' + KS_PLAN + '; ' + KSH_PLAN,
        field='mean_person_mae_deg; paired_person_differences_deg; participants; mae_degrees; comparisons/stride; shared_advantage_criterion_met', full=None)
    return ''


STRIDE = 'models/stride-continuation/fresh-results.json'                         # half a second of a stride, and the next 0.60 s
STRIDE_SCHEMA = 'models/stride-continuation/schema.json'
POP = 'models/population-motion/scores.json'                                     # three held-out rats: firing from two brain regions
POPSHARED = 'models/neurotranslate-0.0/population/results.json'                  # the shared model given the same firing


def stride_pop_checks():
    """The stride forecast and the three-rat forecast (models/, published after the papers), and the shared model given the rats'
    firing: every direction the pages state, asserted against the result files (nothing is printed)."""
    s = load(STRIDE)
    m = {k: s['models'][k]['overall'] for k in ('conditional', 'history-only', 'ridge')}
    assert m['conditional']['bodyMeanMm'] < m['history-only']['bodyMeanMm'], 'the walk or run label lowered the body error'
    assert m['ridge']['pelvisMeanMm'] < m['conditional']['pelvisMeanMm'], 'a linear forecast tracked the pelvis more closely'
    assert len(s['eligibleGroups']) == 6 and len(s['models']['conditional']['byTrial']) == 12 and s['eligibleWindows'] == 351
    acts = {}
    for r in load('models/stride-continuation/cohort.json')['rows']:
        if r['split'] == 'fresh':
            acts.setdefault(r['subject'], set()).add(r['action'])
    assert sorted(acts) == sorted(s['eligibleGroups']) and sum(1 for v in acts.values() if v == {'run'}) == 1 and sum(1 for v in acts.values() if v == {'walk'}) == 5, acts
    sch = load(STRIDE_SCHEMA)
    assert sch['sampleRateHz'] == 20 and len(sch['horizonTimesS']) == 12 and len(sch['historyTimesS']) == 11 and len(sch['sites']) == 18
    p = walk(load(POP), 'equal_rat')
    assert p['combined'] < p['earlier_trip'] < p['motion'] and load(POP)['consistent_gain'] is False
    assert sum(r['anchors'] for r in load(POP)['by_rat']) == 549 and all(r['trips'] == 15 for r in load(POP)['by_rat']) and len(load(POP)['by_rat']) == 3
    better_both = [r['rat'] for r in load(POP)['by_rat'] if r['motion_minus_combined'] > 0 and r['earlier_minus_combined'] > 0]
    assert better_both == ['KL8'], better_both
    kl8 = next(r for r in load(POP)['by_rat'] if r['rat'] == 'KL8')
    assert kl8['constant_speed'] < min(kl8['motion'], kl8['combined'], kl8['earlier_trip']), 'for KL8 the last speed did better still'
    q = walk(load(POPSHARED), 'equal_rat')
    assert q['shared_combined'] < q['shared_motion'] and q['shared_combined'] < q['shared_donor'] and load(POPSHARED)['retrospective'] is True
    both = [c['rat'] for c in load(POPSHARED)['checks_by_rat'] if c['shared_motion'] and c['shared_donor']]
    assert both == ['KL8'], both
    log('stride: label lowered body error, ridge closer on the pelvis; three rats: firing lower on average, both checks met only for KL8, last speed lower for KL8; shared model with firing: lower on average, both checks only for KL8, retrospective',
        file=STRIDE + '; ' + POP + '; ' + POPSHARED, field='models/*/overall; equal_rat; by_rat; checks_by_rat; retrospective', full=None)
    return ''


def stride_horizon():
    """Seconds the stride forecast covers: the last of its future times (twelve at 20 Hz, the last at 0.60 s)."""
    times = walk(load(STRIDE_SCHEMA), 'horizonTimesS')
    assert abs(times[-1] - len(times) / walk(load(STRIDE_SCHEMA), 'sampleRateHz')) < 1e-9, times
    txt = f'{times[-1]:.2f}'
    log(txt, file=STRIDE_SCHEMA, field='horizonTimesS (last)', full=times[-1])
    return txt


WM = 'models/word-motion/results.json'                                           # a stride generated from the word walk or run
WM_SCHEMA = 'models/word-motion/schema.json'


def word_motion_checks():
    """The walk/run generator (models/word-motion/, published after the papers): scored on three held-out recordings of two
    catalogue subject IDs; the word-conditioned decoder came out a little below the average recorded action of its training clips,
    by less than 0.1 mm, and below the decoder without the word and the one with shuffled words."""
    d = load(WM)
    m = {k: walk(d, f'byMethod/{k}/equalSubject/bodyMm') for k in ('conditional', 'classMean', 'constant', 'shuffled', 'globalMean')}
    assert d['dataCounts'] == {'trials': 3, 'groups': 2}, d['dataCounts']
    assert m['conditional'] < m['classMean'] < m['constant'] < m['shuffled'] and m['classMean'] - m['conditional'] < 0.1, m
    assert walk(load(WM_SCHEMA), 'durationSeconds') == 0.6 and len(walk(load(WM_SCHEMA), 'joints')) == 18
    log('walk/run generator: almost the same as the average action from training (difference below 0.1 mm)', file=WM,
        field='dataCounts; byMethod/{conditional,classMean,constant,shuffled}/equalSubject/bodyMm', full=None,
        note=f'conditional {m["conditional"]!r}, class mean {m["classMean"]!r}')
    return ''


def angle_checks():
    """The wrist-angle path: scored on the six fitting people of the wrist data, each by a version fitted on the other five, on the
    same 1,879 trials as row 29; EMG lowered the error, EEG on top raised it again; row 29's EMG correction (3.549) was lower; the
    version with random frozen layers was lower in all three input sets."""
    d = load(ANG)
    s = {k: v['rmse_deg'] for k, v in d['scores'].items()}
    assert d['people'] == 6 and d['trials'] == walk(load(CORR), 'eligible_trials') and d['rows'] == walk(load(CORR), 'time_points')
    assert s['pretrained.emg'] < s['pretrained.full'] < s['pretrained.motion'] and s['prior_emg_corrected_cnn'] < min(s[k] for k in s if k.startswith(('pretrained', 'random')))
    assert s['prior_emg_corrected_cnn'] == walk(load(CORR), 'scores/corrected_emg/equal_person_rmse_deg')
    assert all(s['random.' + k] <= s['pretrained.' + k] for k in ('motion', 'emg', 'full'))
    log('wrist-angle path: EMG lowered, EEG on top raised again; row 29 lower; random frozen layers lower in all three', file=ANG + '; ' + CORR,
        field='people; trials; rows; scores/*/rmse_deg; scores/corrected_emg/equal_person_rmse_deg', full=None,
        note='6 people, the same trials and forecasts as row 29; prior_emg_corrected_cnn equals row 29\'s EMG correction')
    return ''


def forearm_checks():
    """The forearm correction on top of the wrist-angle path: the same six people and trials as row 29; the movement-only correction
    beat the uncorrected forecast, forearm EMG lowered it further, another trial's EMG raised it above the movement-only correction (still
    below the uncorrected forecast), and row 29's model (the same score as
    in row 29) stayed lower."""
    d = load(FA)
    s = {k: v['equal_person_rmse_deg'] for k, v in d['scores'].items()}
    assert d['people'] == 6 and d['trials'] == walk(load(CORR), 'eligible_trials') and d['overlapping_windows'] == walk(load(CORR), 'time_points')
    assert s['prior_emg_corrected_cnn'] < s['emg'] < s['motion'] < s['wrong_trial'] < s['zero'], s
    assert s['zero'] == walk(load(ANG), 'scores/pretrained.motion/rmse_deg') and s['prior_emg_corrected_cnn'] == walk(load(CORR), 'scores/corrected_emg/equal_person_rmse_deg')
    assert d['beats_prior_corrected_cnn_on_these_rows'] is False
    log('forearm correction: below the movement-only correction, above row 29; another trial\'s EMG above the movement-only correction', file=FA + '; ' + CORR,
        field='people; trials; overlapping_windows; scores/*/equal_person_rmse_deg; beats_prior_corrected_cnn_on_these_rows', full=None,
        note='zero equals the wrist-angle path\'s motion score; prior_emg_corrected_cnn equals row 29\'s EMG correction')
    return ''


def fa_row29_better():
    """People for whom row 29's model beat the forearm correction (6 minus those for whom the correction was lower)."""
    n = load(FA)['people'] - walk(load(FA), 'contrasts/emg_minus_prior_emg_corrected_cnn/people_lower_error')
    log(spell(n), file=FA, field='people minus contrasts/emg_minus_prior_emg_corrected_cnn/people_lower_error', full=n)
    return spell(n)


def shared_checks():
    """The shared fit (models/, published after the numbered table): what the pages say about it, asserted against its files.
    It is named NeuroTranslate 0.0 in its own plan; the released weights are seed 27181 (the scores printed); the fits on one
    dataset alone came out a little higher; neither task passed the transfer rule; a straight-line fit beat it on the rat."""
    assert walk(load(SM_PLAN), 'name').startswith('NeuroTranslate 0.0 shared movement-distance experiment')
    d = walk(load(SM), 'domains')
    for k in ('wrist', 'rat'):
        m = d[k]['macro_mae_cm']
        assert m['joint_27181'] < m['solo32_27181'] and m['joint_27181'] < m['solo64_27181'] and d[k]['transfer_gate'] is False, (k, m)
        assert m['ridge_log'] <= m['ridge_cm'], (k, m)       # the better of the two straight-line fits is ridge_log
    assert d['rat']['macro_mae_cm']['ridge_log'] < d['rat']['macro_mae_cm']['joint_27181'] and d['rat']['beats_all_physical_and_ridge_controls'] is False
    assert d['wrist']['macro_mae_cm']['joint_27181'] < d['wrist']['macro_mae_cm']['ridge_log'] and walk(load(SM), 'bidirectional_transfer_gate') is False
    log('the shared fit: lower than each one-dataset fit, transfer rule not passed on either task, straight-line fit lower on the rat', file=SM + '; ' + SM_PLAN,
        field='domains/{wrist,rat}/macro_mae_cm; transfer_gate; beats_all_physical_and_ridge_controls; bidirectional_transfer_gate; name', full=None,
        note='released checkpoint = seed 27181')
    return ''


def arm_more_data_check():
    """README, presumption paragraph: the arm task is a test on unseen people (GENERAL_FITS), fitted on seven people instead of
    one; the seven-person fit was closer on the five new people than the one-person fit, and the fitting group's median change
    for each cue closer still."""
    assert GENERAL_FITS['arm-transfer'] == 'unseen' and 'arm-transfer' in UNSEEN
    assert walk(load(GA), 'training/eligible_people') == 7 and walk(load(GA), 'assessment/eligible_people') == 5
    seven, one, cue = (walk(load(GA), f'unseen_person/models/{k}/standardized_mae') for k in ('shared_cue_motion', 's1_shared_cue_motion', 'cue_median'))
    assert cue < seven < one, (cue, seven, one)
    log('seven people better than one; the cue median better still', file=GA, field='unseen_person/models/{cue_median, shared_cue_motion, s1_shared_cue_motion}/standardized_mae',
        full=None, note=f'{cue:.4f} < {seven:.4f} < {one:.4f}')
    return ''


def sharing_checks():
    """The shared fit against the same model fitted on one dataset (the matched-examples fit, solo32): lower on both, by amounts
    whose 95% resampling range reaches past zero on both; neither passed the transfer rule. Its wrist groups were kept out of
    fitting but are not established as new people, and the rat's assessment trips come from the session it was fitted on."""
    d = walk(load(SM), 'domains')
    for k in ('wrist', 'rat'):
        c = d[k]['paired_joint_minus_comparator_cm']['solo32_27181']
        assert c['mean'] < 0 and c['percentile_95'][0] < 0 < c['percentile_95'][1] and d[k]['transfer_gate'] is False, (k, c)
    m = {k: walk(load(SM), f'domains/{k}/macro_mae_cm') for k in ('wrist', 'rat')}
    for k in ('wrist', 'rat'):          # against the fit given as many examples in total (solo64): lower on both, range below zero for the released seed
        c = d[k]['paired_joint_minus_comparator_cm']['solo64_27181']
        assert c['mean'] < 0 and c['percentile_95'][1] < 0, (k, c)
    assert m['wrist']['joint_27183'] > m['wrist']['solo64_27183'] and all(m['rat'][f'joint_{s}'] < m['rat'][f'solo64_{s}'] for s in (27181, 27182, 27183)), 'another seed reversed it for the wrist only'
    assert 'both contrasts strictly favorable for each of the other two seeds' in walk(load(SM_PLAN), 'transfer_decision')
    plan = walk(load(SM_PLAN), 'admission') + ' ' + walk(load(SM_PLAN), 'assessment')
    assert 'R035,R037,R042,R045,R072,R074 for assessment' in plan and 'trips 55–78 train and 81–89 reused assessment' in plan, plan
    assert 'one rat session and acquisition groups not established independent people' in plan
    log('sharing: lower on both datasets than the same-examples fit, 95% range past zero on both; lower than the as-many-examples fit with range below zero on both, '
        'reversed for the wrist by seed 27183; transfer rule not passed; wrist groups held out of fitting but not new people; rat trips from the fitted session',
        file=SM + '; ' + SM_PLAN, field='domains/{wrist,rat}/paired_joint_minus_comparator_cm/{solo32_27181,solo64_27181}/{mean,percentile_95}; macro_mae_cm/{joint,solo64}_2718{1,2,3}; '
        'transfer_gate; transfer_decision; admission; assessment', full=None)
    return ''


def L_len(rel, field, what):
    """How many items a list in a result file holds."""
    n = len(walk(load(rel), field) if field else load(rel))
    log(str(n), file=rel, field=(field or '(the whole file)') + ' (length)', full=n, note=what)
    return str(n)


def pct(rel, field, dp=1):
    return N(rel, field, dp, 100.0) + '%'


def later_checks():
    """Every direction the pages state about the later studies, asserted against their files (nothing is printed)."""
    m = walk(load(WT), 'metrics')
    assert m['ridge_motion']['mean_trip_error_cm'] < m['ridge_combined']['mean_trip_error_cm'] < m['ridge_wrong']['mean_trip_error_cm'], 'rat: firing did not help; earlier-trip firing worse still'
    assert m['ridge_motion']['mean_trip_error_cm'] == min(v['mean_trip_error_cm'] for v in m.values()) and walk(load(WT), 'primary_pass') is False
    assert walk(load(WT), 'n_paired_trials') == len(walk(load(WT), 'paired_trials')) == 9
    g = walk(load(PI), 'all_scorable/group_balanced_mae_cm')
    assert g['motion_context'] < g['motion_context_words'] and g['prior_net'] == min(g.values()) and walk(load(PI), 'conclusion') == 'language_increment_not_demonstrated'
    assert walk(load(PI_MODEL), 'attention_admitted') is False
    h = {k: walk(load(HL), f'metrics/exact/models/{k}/family_macro/recall1') for k in ('ridge', 'attention', 'chance', 'joint_nuisance')}
    assert h['joint_nuisance'] > h['ridge'] > h['attention'] > h['chance'], h
    k = {x: walk(load(TM), f'metrics/{x}/motion_macro/recall1') for x in ('attention', 'ridge', 'chance')}
    k['caption_to_action'] = walk(load(TM), 'metrics/caption_to_action/motion_macro/recall1')
    assert k['caption_to_action'] > k['ridge'] > k['attention'] > k['chance'] and walk(load(TM), 'prespecified_descriptive_comparison_passed') is False, k
    assert all(c['markers'] == 41 for c in walk(load(WB), 'clips')) and len(walk(load(WB), 'clips')) == 3
    log('directions of the later studies', file='; '.join((WT, PI, HL, TM, WB)), field='metrics; group_balanced_mae_cm; family_macro/recall1; motion_macro/recall1; clips',
        full=None, note='rat: positions alone lowest, firing worse, earlier-trip firing worse still, primary_pass false; wrist: words raised the error, '
                        'repeating the last second lowest; hand: timing > ridge > attention > chance; whole body: catalogue-name ranking > ridge > attention > chance, '
                        'comparison set in advance not passed; three clips of 41 markers')
    return ''


def wt_motion_better():
    """Rat study: trips on which the positions-only forecast was closer than the one with firing."""
    m = walk(load(WT), 'metrics')
    trips = walk(load(WT), 'paired_trials')
    n = sum(1 for q in trips if m['ridge_motion']['by_trial_cm'][str(q)] < m['ridge_combined']['by_trial_cm'][str(q)])
    assert n == len(trips) - walk(load(WT), 'comparisons/ridge_motion_minus_ridge_combined/positive_trips')
    log(f'{n} of {len(trips)}', file=WT, field='metrics/{ridge_motion,ridge_combined}/by_trial_cm', full=n, note='trips with the lower positions-only error')
    return f'{n} of {len(trips)}'


def _later_wtrack():
    return (f'No. A camera tracked a rat running round a W-shaped track while electrodes in its brain picked up electrical spikes, which the '
            f'recording sorts into {L_len(WT_UNITS, "", "sorted units")} sources, each probably one brain cell. '
            f'A forecast of where the rat would be a quarter of a second later, from its recent positions alone, missed by '
            f'{N(WT, "metrics/ridge_motion/mean_trip_error_cm", 3)} cm on average. With one second of firing added it missed by '
            f'{N(WT, "metrics/ridge_combined/mean_trip_error_cm", 3)} cm, and the positions alone were closer on {wt_motion_better().replace(" of ", " of the ")} later trips that were scored. '
            f'Given firing from an earlier trip instead, the same fitted model did worse again ({N(WT, "metrics/ridge_wrong/mean_trip_error_cm", 3)} cm): '
            'it used the timing of the firing, and still did not beat the positions. This is one rat in one recording, and '
            f'{spell(L_len(WT, "reserve", "trips set aside"))} later trips were set aside and never opened.' + later_checks())


def _later_instructions():
    words = walk(load(PI_MODEL), 'vocabulary')
    assert {'turn', 'on', 'off'} <= set(words), words
    log('"turn", "on", "off"', file=PI_MODEL, field='vocabulary', full=None, note='the whole list: ' + ', '.join(words))
    return ('Not here. A headset tracked a person\'s right wrist while an instructor talked them through a task. A quarter of a second after '
            'each instruction ended, a model forecast how far the wrist would move in the next second, from its recent movement, the task and '
            f'facts about the finished instruction such as its length. It missed by {N(PI, "all_scorable/group_balanced_mae_cm/motion_context", 2)} cm on average. '
            f'Told also which of {spell(L_len(PI_MODEL, "vocabulary", "recurring words the model could use"))} recurring words the instruction held '
            f'("turn", "on", "off" and the like), it missed by {N(PI, "all_scorable/group_balanced_mae_cm/motion_context_words", 2)} cm. '
            f'Repeating the wrist\'s movement over the previous second did best, at {N(PI, "all_scorable/group_balanced_mae_cm/prior_net", 2)} cm. '
            f'Only {N(PI, "all_scorable/scored_examples")} forecasts were scored, from {spell(N(PI, "all_scorable/recordings"))} recordings in '
            f'{spell(N(PI, "all_scorable/groups"))} groups (the dataset groups recordings by a code, not by person), and the model was fitted on '
            f'{N(PI, "training_coverage/flow/scorable")} examples. These recordings had been open earlier, while a different task was built on them, so this is not a fresh test.' + later_checks())


def _later_hand():
    return ('Timing beat the hand. A headset tracked the right hand of people doing tasks such as setting up a printer, and observers later wrote a sentence '
            'about each step. Given one of those sentences, a model ranked the steps of the same recording, and the score is how often the right step came first: '
            f'here higher is better. On {N(HL, "assessment_segments")} sentences from {spell(L_len(HL, "gallery_sizes", "assessment recordings"))} recordings in '
            f'{spell(L_len(HL, "metrics/exact/models/ridge/by_family", "groups of recordings"))} groups kept out of fitting, a model that read the shape and movement '
            f'of the hand put the right step first {pct(HL, "metrics/exact/models/ridge/family_macro/recall1", 2)} of the time (a second model, built on attention, '
            'the mechanism a transformer uses to weigh one part of its input against another: '
            f'{pct(HL, "metrics/exact/models/attention/family_macro/recall1", 2)}), against {pct(HL, "metrics/exact/models/chance/family_macro/recall1", 2)} for a random order. '
            'Ranking by each step\'s length, its place in the recording and how often the hand was tracked, with no hand shape at all, reached '
            f'{pct(HL, "metrics/exact/models/joint_nuisance/family_macro/recall1", 2)}. The groups are the dataset\'s recording codes, not verified people, and the same '
            f'person may appear under different codes. {hand_reserve()} [Inspect five recorded movements in your browser](' + SITE + 'hand-search/).' + later_checks())


def _later_text():
    return ('The simpler model did better. Volunteers watched recorded whole-body movements, most of them walks, and described each one. Given a description, '
            f'a model ranked {N(TM, "split/assessment/recordings")} recordings of {spell(N(TM, "split/assessment/subject_ids"))} performers, as the dataset\'s catalogue names them, '
            'all kept out of fitting, and the score is '
            f'how often the right recording came first, averaged so that each of the {N(TM, "split/assessment/recordings")} recordings counts equally: higher is better. '
            f'A model built on attention put it first {pct(TM, "metrics/attention/motion_macro/recall1")} of the time; a simpler one, built on word counts and plain summaries of the '
            f'movement, {pct(TM, "metrics/ridge/motion_macro/recall1")}; a random order, {pct(TM, "metrics/chance/motion_macro/recall1")}. Ranking the recordings by the action name '
            f'the dataset\'s catalogue gives each one, matched to the sentence\'s words, with no movement at all, did better than both: '
            f'{pct(TM, "metrics/caption_to_action/motion_macro/recall1")}. The attention model failed the pass rule set for it in advance, which asked it to beat that ranking too. '
            f'{N(TM, "assessment_cue_recording_counts/walk")} of the {N(TM, "split/assessment/recordings")} recordings are walks, so many descriptions '
            'fit several of them, and the folder says that repeated clips of the same people limit any claim about new people. '
            f'Another {N(TM, "split/reserve/recordings")} recordings, of {spell(N(TM, "split/reserve/subject_ids"))} other performers, were set aside and never opened.' + later_checks())


def hand_reserve():
    """Hand search: the recordings its split set aside (role "reserve"), and how many recording groups they come from."""
    recs = [r for r in walk(load(HL_SPLIT), 'recordings') if r['role'] == 'reserve']
    groups = sorted({r['group'] for r in recs})
    log(f'{len(recs)} recordings, {len(groups)} groups', file=HL_SPLIT, field='recordings[role == "reserve"] and their "group"', full=len(recs),
        note='groups: ' + ', '.join(groups) + '; the folder README: "Ten further recordings in three reserved groups stayed unopened."')
    return f'{spell(len(recs), True)} more recordings, in {spell(len(groups))} groups, were set aside and never opened.'


def later_how():
    """How the README's "Where to click" describes the list of later studies: a result in plain words for each written-up folder,
    a link to its own page for a folder published after this builder was last changed."""
    if all(r['folder'] in LATER_TEXT for r in LATER):
        return 'each with its result in plain words'
    return 'each with its result in plain words or a link to its own page'


def later_heading():
    """Heading of the studies page's section on the later studies. It states what the four written-up studies found; while a
    folder that has no paragraph yet is among them, it falls back to a plain heading that stays true."""
    later_order_check()
    if [r['folder'] for r in LATER] == LATER_ORDER:
        return f"{spell(n_later(), True)} newer studies: neither a rat's brain cells nor an instructor's words helped, and a sentence rarely found its movement"
    return f'{spell(n_later(), True)} newer studies, outside the numbered table'


PAGE_ROWS = ('hand-search', 'shared-motion', 'whole-body', 'word-motion', 'stride', 'population-motion', 'knee-motion', 'gait-rhythm', 'knee-stride', 'finger-signals', 'finger-motion', 'finger-transfer', 'knee-moment', 'walking-force', 'walking-landmarks', 'elbow-cue', 'arm-transfer', 'scalp-forecast', 'cervical-forecast', 'neck-voltage', 'back-rotation', 'shared-back-rotation', 'muscle-tracking', 'shared-muscle-tracking', 'pedal-load', 'shared-pedal-load', 'heel-and-force', 'shared-heel-and-force', 'walking-instructions', 'walking-instruction-controls', 'cross-limb-movement', 'cross-limb-controls', 'muscle-and-motion', 'muscle-motion-controls', 'visual-balance', 'visual-balance-controls', 'muscle-spindle', 'cortical-reach', 'contact-forecast', 'target-reach', 'cylinder-rotation', 'reach-feedback', 'human-wrist', 'cross-person-wrist', 'first-use-body', 'next-neuron-prediction', 'vertebrate-neural-data', 'worm-to-vertebrate')      # the site pages that are not study readers and have a row of their own


def other_pages():
    """The site pages that are not study readers of the numbered table, as the site's file list names them."""
    readers = set(r.split('/')[0] for r in READER.values() if not r.startswith('index.html'))
    names = [f'`{n}/`' for n in _site_pages() if n not in readers]
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def later_page_rows():
    """A row in the site's file list for each page under docs/ that is neither a study reader nor one of PAGE_ROWS: published after
    the list was written, so it is listed with a link and no description, never dropped and never fatal."""
    readers = set(r.split('/')[0] for r in READER.values() if not r.startswith('index.html'))
    new = [n for n in _site_pages() if n not in readers and n not in PAGE_ROWS]
    assert all((REPO / 'docs' / n / 'index.html').exists() for n in PAGE_ROWS), PAGE_ROWS
    return ''.join(f'\n| [`{n}/`]({SITE}{n}/) | Published after this list was last written: its own folder says what it is. |' for n in new)


LATER_TEXT = {'wtrack-neural-motion': _later_wtrack, 'preceding-instructions': _later_instructions,
              'hand-language-retrieval': _later_hand, 'text-motion-retrieval': _later_text}
assert list(LATER_TEXT) == LATER_ORDER


def later_order_check():
    """The studies page says the first two later studies are forecasts and the next two searches with words. That holds while the
    four written-up folders are still later studies, in LATER_ORDER; a new folder sorts after them and cannot break it. (If one of
    the four is given a ledger row, this fails, and the sentence has to be rewritten with it.)"""
    assert [r['folder'] for r in LATER][:len(LATER_ORDER)] == LATER_ORDER, [r['folder'] for r in LATER]
    return ''


def later_list():
    """The studies page's list of the studies published after the numbered table: each folder with its own page's heading and a
    link, then the paragraph written for it, or, for a folder published after this builder was last changed, a line that sends the
    reader to its own page. Generated from the folders on disk, so a new folder is listed at the next build."""
    out = []
    for r in LATER:
        name = r['heading'] or r['folder']
        head = f"- **[{name}]({r['folder']}/)** (`{r['folder']}/`)."
        body = LATER_TEXT[r['folder']]() if r['folder'] in LATER_TEXT else \
            'Published after this page was last written: its own page has the result, and it is in none of the counts above.'
        out += [head + ' ' + body, '']
    log(str(len(LATER)), file='benchmarks/', field='later_studies(): ' + '; '.join(f"{r['folder']} = {r['heading']!r}" for r in LATER), full=len(LATER),
        note='folder and the first heading of its README.md')
    return '\n'.join(out).rstrip()


def _later_entry(r):
    name = r['heading'] or r['folder']
    head = f"- **[{name}]({r['folder']}/)** (`{r['folder']}/`)."
    body = LATER_TEXT[r['folder']]() if r['folder'] in LATER_TEXT else \
        'Published after this page was last written: its own page has the result, and it is in none of the counts above.'
    return head + ' ' + body


def later_item(folder):
    """One written-up later study, as an entry of the studies page's grouped list (the page places each of the four in the group
    its question belongs to). The folder must still be a later study: if it is given a ledger row, this fails, and the page's
    grouping has to change with it."""
    later_order_check()
    hits = [r for r in LATER if r['folder'] == folder]
    assert len(hits) == 1 and folder in LATER_TEXT, folder
    log('1', file='benchmarks/', field=f"later_studies(): {folder} = {hits[0]['heading']!r}", full=None, note='folder and the first heading of its README.md')
    return _later_entry(hits[0])


def later_rest():
    """Every folder under benchmarks/ that no ledger row names and that has no paragraph written for it (published after this
    builder was last changed): a section of its own at the end of the studies page's newer studies, each folder with its own
    page's heading and a link. Empty while there is none, so a new folder is listed at the next build, never dropped and never fatal."""
    rest = [r for r in LATER if r['folder'] not in LATER_TEXT]
    log(str(len(rest)), file='benchmarks/', field='later_studies() without a written paragraph: ' + (', '.join(r['folder'] for r in rest) or 'none'), full=len(rest))
    if not rest:
        return ''
    return '\n\n### Published after this page was last written\n\n' + '\n\n'.join(_later_entry(r) for r in rest)


def lead_ms(rel='benchmarks/daily-sports-limbs/protocol.json'):
    """How far ahead the walking forecasts look: samples ahead divided by samples per second."""
    d = load(rel)
    rows, hz = (d['lead_rows'], d['sample_hz']) if 'lead_rows' in d else (d['lead_samples'], d['sample_hz'])
    ms = 1000 * rows / hz
    assert ms == int(ms)
    log(str(int(ms)), file=rel, field='lead_rows (or lead_samples) ÷ sample_hz', full=ms, note=f'{rows} samples at {hz} Hz')
    return str(int(ms))


def n_study_dirs():
    """Top-level folders under benchmarks/ that hold at least one study (the fit of row 27 has a folder of its own)."""
    dirs = sorted({v.split('/')[0] for v in STUDY_FOLDER.values()})
    log(str(len(dirs)), file='benchmarks/', field='top-level folders of the studies: ' + ', '.join(dirs), full=len(dirs))
    return str(len(dirs))


def n_paper_only():
    n = sum(1 for s_ in LEDGER['studies'] if not s_['folder'].startswith('benchmarks/'))
    log(str(n), file=LEDGER_FILE, field='rows with no folder under benchmarks/', full=n)
    return str(n)


def rmse_17():
    """Study 17 on its second measure (root mean squared error): "repeat the last value" lost to both fitted models."""
    rel = 'benchmarks/hyser-index/prescribed/RESULTS.json'
    base = 'cohorts/previous_random_development_participants/groups/all/time/both_days/models/'
    last, one, five = (walk(load(rel), base + k + '/rmse_v') for k in ('persistence', 'index_only', 'aligned_five'))
    assert last > one > five, (last, one, five)
    mae = [walk(load(rel), base + k + '/mae_v') for k in ('persistence', 'index_only', 'aligned_five')]
    assert mae[0] < mae[2] < mae[1], mae
    log('it lost to both', file=rel, field=base + '{persistence, index_only, aligned_five}/rmse_v', full=None,
        note=f'x1000: {last * 1000:.3f}, {one * 1000:.3f} and {five * 1000:.3f} mV')
    return ''


def both_networks_24():
    """Study 24: both networks scored below the straight-line fit on average, both were worse than it for the index finger on
    the second test day, and all five further claims failed (the macaque result file and the technical paper's text)."""
    t = re.sub(r'\s+', ' ', re.sub(r'-\n\s*', '', pdf_text(NEW_EDITION + 'neurotranslation-technical.pdf')))
    ref, a, b = (value(x[1]) for x in (S(24).s['baselines'][1], S(24).s['models'][0], S(24).s['models'][1]))
    assert a < ref and b < ref and b < a, (ref, a, b)
    for needle in ('error was above the ridge', 'by 0.0052472 for the index finger', 'was above it by 0.0043575 for the index finger',
                   'All five failed', 'Across 18 runs and 720 saved passes through the fitting data, no model passed'):
        assert needle in t, needle
    log('both networks; 18 runs and 720 saved passes', file=NEW_EDITION + 'neurotranslation-technical.pdf',
        field=f'section 4.6 and appendix A (from page {dest(0, "appendix.A")})', full=None,
        note='both networks below the last-sample fit on average; both above it for the index finger on 11 February; all five further claims failed')
    return ''


def measures_check():
    """The pages say: studies 1 to 13 use root mean squared error, 14 to 23 mean absolute error (20 compares
    bands), 24 and 25 a squared error in scaled units. Confirm against the ledger's measure of each study and
    against the field each main score is read from."""
    for s_ in LEDGER['studies']:
        n, m = s_['n'], s_['measure']
        field = (s_.get('primary') or {}).get('ref', {}).get('field', '')
        if n <= 13 or n in (28, 29):
            assert 'root mean squared error' in m and 'rmse' in field.lower(), (n, m, field)
        elif n == 20:
            assert m.startswith('share of later readings inside the band'), (n, m)
        elif n <= 23:
            assert m.startswith('mean absolute error') and 'mae' in field.lower(), (n, m, field)
        elif n in (26, 27):
            assert m.startswith('mean absolute error') and (n == 27 or 'mae' in field.lower()), (n, m, field)
        elif n == 24:
            assert m.startswith('mean squared error'), (n, m)
        else:
            assert n == 25 and m.startswith('normalised mean squared error'), (n, m)
    log('1 to 13, 28 and 29; 14 to 23, 26 and 27; 24 and 25', file=LEDGER_FILE, field='studies[].measure, and the field of each main score', full=None,
        note='root mean squared error; mean absolute error (20: band coverage and width); mean squared error in scaled units')
    return ''


def gh_anchor(heading):
    """GitHub's anchor for a Markdown heading: lower case, punctuation other than hyphens and spaces dropped, spaces to hyphens."""
    slug = re.sub(r'[^\w\- ]', '', heading.strip().lower()).replace(' ', '-')
    return '#' + slug


def zero_check(txt):
    """For a sentence that says "none": the count it stands for must be 0."""
    assert txt == '0', txt
    return ''


def edition_query():
    """The site copy adds ?edition=<version> to each PDF link so that a browser fetches a new edition afresh."""
    return '?edition=' + walk(load(MANIFEST), 'version')


def source_files():
    """Files of the source tree in the source ZIP (its source/ folder), which must be the files EDITION.json lists, byte for byte."""
    import zipfile
    import hashlib
    z = zipfile.ZipFile(REPO / SOURCE_ZIP)
    top = 'NeuroTranslation-Brain2Body-Papers-Source/'
    assert all(m.startswith(top) for m in z.namelist())
    tree = {m[len(top) + len('source/'):]: hashlib.sha256(z.read(m)).hexdigest() for m in z.namelist() if m.startswith(top + 'source/')}
    edition = json.loads(z.read(top + 'EDITION.json'))
    listed = {r['path']: r['sha256'] for r in edition['to_rebuild']['source_tree_files']}
    assert tree == listed, sorted(set(tree) ^ set(listed))
    for name in ('build.sh', 'README.md', 'ledger.json', 'toolchain-files.json', 'NOTICE.md', 'LICENSE.txt'):
        assert top + name in z.namelist(), name
    assert walk(load('papers/current.json'), 'matching_public_source_bundle_provided') is True
    log(str(len(tree)), file=SOURCE_ZIP, field='members under source/, against EDITION.json to_rebuild/source_tree_files (path and SHA-256)', full=len(tree))
    return str(len(tree))


def day_flip():
    """Confirms that the five-grid difference of study 19 has opposite signs on its two recording days."""
    rel = 'benchmarks/cemhsey-arrays/RESULTS.json'
    node = 'refit_mae_differences/history_phase_paired_grid/history_phase_paired_emg/indexed_day_differences'
    d = walk(load(rel), node)
    vals = list(d.values()) if isinstance(d, dict) else list(d)
    assert len(vals) == 2 and vals[0] * vals[1] < 0, d
    log('the sign flipped between the two days', file=rel, field=node, full=None, note=f'the two values: {vals[0]!r} and {vals[1]!r}')
    return ''


# ---- counts the README's words depend on, read from the files rather than typed ---------------------------------------
SUPPLEMENTS = {     # the short PDFs published beside the papers; their page counts are printed as "four-page" and so on
    'language': 'docs/papers/language-and-observed-movement/language-and-movement.pdf',
    'finger': 'docs/papers/finger-cues/finger-cues.pdf',
    'walking': 'docs/papers/walking-rhythm/gait-clocks.pdf',
    'forecast': 'docs/papers/forecasting-movement/movement-forecast.pdf',
    'force': 'docs/papers/muscle-and-floor/muscle-and-floor.pdf',
    'landmarks': 'docs/papers/walking-landmarks/walking-landmarks.pdf',
    'cued': 'docs/papers/cued-arm/cued-arm.pdf',
    'arm': 'docs/papers/arm-transfer/arm-transfer.pdf',
    'scalp': 'docs/papers/scalp-forecast/scalp-forecast.pdf',
    'neck': 'docs/papers/cervical-forecast/cervical-forecast.pdf',
    'back': 'docs/papers/back-rotation/back-rotation.pdf',
    'muscle': 'docs/papers/muscle-tracking/muscle-tracking.pdf',
    'pedal': 'docs/papers/pedal-load/pedal-load.pdf',
    'heel': 'docs/papers/heel-and-force/heel-and-force.pdf',
    'walking-instructions': 'docs/papers/walking-instructions/walking-instructions.pdf',
    'balance': 'docs/papers/visual-balance/visual-balance.pdf',
    'muscle-motion': 'docs/papers/muscle-and-motion/muscle-and-motion.pdf',
    'cross-limb': 'docs/papers/cross-limb-movement/cross-limb-movement.pdf',
    'cross-limb-maps': 'docs/papers/cross-limb-movement/decoder-study/decoder-study.pdf',
    'cross-limb-scalp': 'docs/papers/cross-limb-movement/scalp-study/scalp-study.pdf',
    'spindle': 'docs/papers/muscle-spindle/muscle-spindle.pdf',
    'cortical': 'docs/papers/cortical-reach/cortical-reach.pdf',
    'contact': 'docs/papers/contact-forecast/contact-forecast.pdf',
    'target': 'docs/papers/target-reach/target-reach.pdf',
    'cylinder': 'docs/papers/cylinder-rotation/cylinder-rotation.pdf',
    'reach': 'docs/papers/reach-feedback/reach-feedback.pdf',
    'week': 'docs/papers/reach-feedback/one-week/one-week.pdf',
    'wrist2': 'docs/papers/human-wrist/human-wrist.pdf',
    'first_use': 'docs/papers/first-use-body/first-use-body.pdf',
    'next_spike': 'docs/papers/next-neuron-prediction/next-neuron-prediction.pdf',

    'wrist_transfer': 'docs/papers/cross-person-wrist/cross-person-wrist.pdf',
}
_pdf_pages = {}


def pdf_pages(key, cap=False):
    """A supplement's page count, spelled out ("five"), read from the PDF itself with pdfinfo, so a new edition with another page
    count changes every label at the next build instead of leaving one stale."""
    rel = SUPPLEMENTS[key]
    if rel not in _pdf_pages:
        out = subprocess.run(['pdfinfo', str(REPO / rel)], check=True, capture_output=True, text=True).stdout
        _pdf_pages[rel] = int(re.search(r'^Pages:\s+(\d+)', out, flags=re.M).group(1))
    n = _pdf_pages[rel]
    word = spell(n, cap)
    log(word, file=rel, field='Pages (pdfinfo)', full=n)
    return word


SP = 'models/muscle-spindle/score/strict-afferent/summary.json'     # rat muscle spindles: one sensory fibre's spikes in the next 20 ms
SP_MECH = 'models/muscle-spindle/mechanics/strict-afferent/results.json'
SP_README = 'models/muscle-spindle/README.md'
SP_SOURCE = 'models/muscle-spindle/source/README.md'
SP_PAPER = 'docs/papers/muscle-spindle/muscle-spindle.pdf'


def SPN(model, metric, group='full', dp=3):      # noqa: N802
    """A score of the muscle-spindle study: the mean of the three seeds' scores where there are seeds, else the one fit's."""
    key = 'mean' if 'mean' in load(SP)['models'][group][model] else 'fixed'
    return N(SP, f'models/{group}/{model}/{key}/macro/all/{metric}', dp)


def sp_checks():
    """The muscle-spindle study (published after the papers). Rat group Ia fibres recorded while a motor stretched the calf muscle;
    from five 20 ms steps of tendon force, motor position and the fibre's spike counts, forecasts of the count in the next 20 ms.
    The planned three-group test could not be run; three fibres, all of one filename group, each scored by fits on the other two
    (94 trials, 16,262 windows). Primary score Poisson deviance: the history-only transformer best of all sixteen models, worse
    with the mechanics, both conditional tests failed; better than the count model on the same inputs; the right moment's mechanics
    better than the previous 100 ms window's for all three fibres; repeating the last count lowest in absolute error. The reverse
    forecast (past spikes added to the mechanics) did not help everywhere. Not the general model: no folder of
    models/neurotranslate-0.0/ is about it."""
    s = load(SP)
    assert s['primary_metric'] == 'Poisson deviance' and s['original_three_prefix_gates_evaluable'] is False
    assert s['groups_are_not_confirmed_animals'] is True and s['held_unit'] == 'member'
    g = s['group_sizes_windows']
    assert sorted(g['full']['member']) == ['0/aff004', '0/aff015', '0/aff017'] and len(g['full']['trial']) == 94
    assert g['full']['macro']['all'] == 16262 and g['common_lag']['macro']['all'] == 15792
    full = s['models']['full']

    def score(m, k, group=full):
        return group[m]['mean' if 'mean' in group[m] else 'fixed']['macro']['all'][k]
    dev = {m: score(m, 'deviance') for m in full}
    mae = {m: score(m, 'mae') for m in full}
    assert len(dev) == 16 and min(dev, key=dev.get) == 'transformer_history', dev       # best on the chosen score
    assert min(mae, key=mae.get) == 'recent_one', mae                                    # repeating the last count missed by least
    assert dev['transformer_all'] > dev['transformer_history'] and mae['transformer_all'] > mae['transformer_history']
    assert dev['transformer_all'] < dev['glm_all'] and mae['transformer_all'] < mae['glm_all']
    gates = s['gates']
    assert gates['transformer_conditional']['pass_all'] is False and gates['glm_conditional']['pass_all'] is False
    assert gates['transformer_timing']['pass_all'] is True and gates['transformer_over_primary_glm']['pass_all'] is True
    paired = gates['transformer_timing']['paired']['mean']
    assert all(paired[m]['deviance'] < 0 for m in g['full']['member']), paired           # the right moment's pull and position, for all three
    lag = s['models']['common_lag']
    assert score('transformer_stale', 'deviance', lag) > score('transformer_all', 'deviance', lag)
    assert load(SP_MECH)['primary']['combined_beats_mechanics_everywhere'] == {'force': False, 'position': False}
    readme = (REPO / SP_README).read_text(encoding='utf-8')
    assert 'The original three-group test could not be run.' in readme
    assert 'Repeating the last count gave lower mean absolute error than either network.' in readme
    src = (REPO / SP_SOURCE).read_text(encoding='utf-8')
    assert 'The two prefix-5 files remain unopened.' in src
    assert 'while an actuator moved the muscle and a sensor measured force at the tendon' in src
    paper = re.sub(r'\s+', ' ', pdf_text(SP_PAPER))
    assert 'A motor pulls on a rat’s calf muscle.' in paper
    assert 'The three fibres admitted under the original clock rule all belong to the same filename group.' in paper
    assert 'The movements were imposed.' in paper
    assert not [p.name for p in (REPO / 'models/neurotranslate-0.0').iterdir() if 'spindle' in p.name.lower()]
    log('muscle spindle: spike history alone best by deviance, worse with the mechanics (test failed), the right moment\'s mechanics '
        'better than the previous window\'s for all three fibres, repeating the last count lowest in absolute error', file=SP,
        field='models/{full,common_lag}/*/{mean,fixed}/macro/all/{deviance,mae}; gates; group_sizes_windows', full=None,
        note='deviance 0.446 / 0.499, stale 0.842 / 0.503, MAE last count 0.325 / transformer 0.387; 3 fibres, 94 trials, 16,262 windows')
    return ''


CXR = 'models/cortical-reach/score/test/scores.json'      # one macaque: the handle's next 100 ms, with and without area 2 spikes
CXR_IDS = 'models/cortical-reach/score/original-ids.json'
CXR_LM = 'models/cortical-reach/landmarks/test/results.json'
CXR_README = 'models/cortical-reach/score/README.md'
CXR_PAPER = 'docs/papers/cortical-reach/cortical-reach.pdf'


def CXRN(model, subset='matched', dp=4):      # noqa: N802
    """A score of the cortical-reach study on its test trials: mean distance missed in cm (three seeds' mean for a transformer)."""
    return N(CXR, f'subsets/{subset}/models/{model}/mean/euclidean', dp)


def cr_checks():
    """The cortical-reach study (published after the papers). Chowdhury, Glaser and Miller's recording of macaque C on 12 September
    2017: a robot pushed the hand, later a target cued a reach; from five 40 ms steps of the handle, the task events already past and
    30 sorted area 2 units' counts, forecasts of the handle's change over the next 100 ms. Rewarded trials split 324/108/108 in time
    order; test 778 windows from 105 trials with an earlier donor. Adding the spikes made the transformer worse (decision 'worsening',
    interval below zero), in the push and in the reach; another trial's spikes did not settle the timing test ('unresolved'); the
    straight-line fit on handle and events lowest of all 20 methods, and worse with the spikes too. The secondary straight-line
    comparison: two camera-tracked points helped in the push and not in the reach, spikes after them made it worse, neither passed its
    rule. Not the general model: no folder of models/neurotranslate-0.0/ is about it."""
    s = load(CXR)
    assert s['stage'] == 'test' and s['decision'] == {'incremental': 'worsening', 'wrong_trial_control': 'unresolved'}, s['decision']
    ids = load(CXR_IDS)
    assert [len(ids[k]) for k in ('train', 'validation', 'test')] == [324, 108, 108] and s['n_originals_in_block'] == 108
    m = s['subsets']['matched']
    assert m['n_trials'] == 105 and m['n_windows'] == 778
    e = {k: v['mean']['euclidean'] for k, v in m['models'].items()}
    assert len(e) == 20 and min(e, key=e.get) == 'ridge_movement_cue', e
    assert e['transformer_all'] > e['transformer_movement_cue'] and e['ridge_all'] > e['ridge_movement_cue']
    c = m['contrasts_cm']
    assert c['transformer_movement_cue_minus_joint']['ci95'][1] < 0                           # worse with the spikes, range clear of zero
    lo, hi = c['transformer_wrong_neural_minus_joint']['ci95']
    assert lo < 0 < hi                                                                        # the timing test: not settled
    for sub in ('matched_bump', 'matched_reach'):
        ss = s['subsets'][sub]
        assert ss['models']['transformer_all']['mean']['euclidean'] > ss['models']['transformer_movement_cue']['mean']['euclidean']
        assert ss['contrasts_cm']['transformer_movement_cue_minus_joint']['ci95'][1] < 0
    lm = load(CXR_LM)['primary']['contrasts']
    marks = lm['body_markers_minus_body_control']
    assert marks['epoch_means']['perturbation'] < 0 < marks['epoch_means']['reach'] and marks['gate'] is False
    after = lm['full_minus_body_markers']
    assert after['mean'] > 0 and after['interval95'][0] > 0 and after['gate'] is False
    readme = (REPO / CXR_README).read_text(encoding='utf-8')
    assert 'Giving the same Transformer the preceding area 2 spike counts increased error to **0.6044 cm**.' in readme
    paper = re.sub(r'\s+', ' ', pdf_text(CXR_PAPER))
    assert 'the final 108 were sealed until the analysis was fixed' in paper
    assert 'the documented encoder processing uses forward and backward filtering' in paper
    assert 'The landmark comparison did not meet the preset criterion, and the added-spike comparison did not meet it.' in paper
    assert not [p.name for p in (REPO / 'models/neurotranslate-0.0').iterdir() if 'cortical' in p.name.lower() or 'reach' in p.name.lower()]
    log('cortical reach: spikes made the transformer worse (push and reach), the timing test unresolved, the straight-line fit on handle '
        'and events lowest of 20, landmarks helped in the push only', file=CXR,
        field='decision; subsets/{matched,matched_bump,matched_reach}/models/*/mean/euclidean; contrasts_cm/*/ci95', full=None,
        note='0.4974 / 0.6044, wrong trial 0.5941, ridge 0.4880 / 0.5342; 778 windows, 105 trials; split 324/108/108; '
             'landmarks results.json primary/contrasts')
    return ''


NDC = 'models/contact-forecast/scoring/test/summary.json'      # the same macaque a day later: event counts at 26 area 2 contacts
NDC_RESULTS = 'models/contact-forecast/scoring/test/RESULTS.md'
NDC_PAPER = 'docs/papers/contact-forecast/contact-forecast.pdf'


def NDCN(model, metric='deviance', dp=3):      # noqa: N802
    """A score of the contact-forecast study on the second day's pushes (donor-matched windows): Poisson deviance or mean absolute
    error per contact and 100 ms (the three seeds' errors averaged for a transformer)."""
    return N(NDC, f'phases/pre_target_bump/matched/scores/{model}/{metric}/estimate', dp)


def ndc_checks():
    """The contact-forecast study (published after the papers). Chowdhury, Glaser and Miller's macaque C on 12 and 13 September 2017:
    from five 40 ms steps of the handle, the earlier counts at 26 shared contacts and the task events already past, models fitted on
    the first day's pushes forecast each contact's event count over the next 100 ms of the second day. 2,436 donor-matched windows
    from 609 originals. The full transformer: better with the right movement than with an earlier trial's (interval clear of zero),
    not clearly better than counts and cues alone (interval across zero), so the primary test failed; the cue-only count regression
    lowest in deviance of all sixteen methods; copying the last count lowest in absolute error. Not the general model."""
    s = load(NDC)
    assert s['stage'] == 'test' and s['primary']['passed'] is False, s['primary']
    assert s['primary']['checks'] == {'count_cue': 'unresolved', 'wrong_movement': 'lower_error'}, s['primary']['checks']
    m = s['phases']['pre_target_bump']['matched']
    assert m['windows'] == 2436 and m['originals'] == 609 and m['contacts'] == 26
    dev = {k: v['deviance']['estimate'] for k, v in m['scores'].items()}
    mae = {k: v['mae']['estimate'] for k, v in m['scores'].items()}
    assert len(dev) == 16 and min(dev, key=dev.get) == 'poisson_cue' and min(mae, key=mae.get) == 'persistence', (dev, mae)
    assert dev['transformer_all'] < dev['transformer_wrong_movement'] and dev['transformer_all'] < dev['transformer_count_cue']
    c = m['contrasts']
    assert c['transformer_all-minus-transformer_wrong_movement']['deviance']['interval'][1] < 0
    lo, hi = c['transformer_all-minus-transformer_count_cue']['deviance']['interval']
    assert lo < 0 < hi
    res = (REPO / NDC_RESULTS).read_text(encoding='utf-8')
    assert 'For movement to pass this test, both intervals must fall entirely below zero.' in res
    assert 'The instrument records unsorted events at each named contact.' in res
    assert 'A contact can pick up different cells from one day to the next.' in res
    paper = re.sub(r'\s+', ' ', pdf_text(NDC_PAPER))
    assert 'We trained on one day and tested on the next. The two recordings come from the same animal.' in paper
    assert not [p.name for p in (REPO / 'models/neurotranslate-0.0').iterdir() if 'contact' in p.name.lower()]
    log('contact forecast: right movement beat borrowed movement, not counts and cues alone (test failed); cue-only count regression '
        'lowest deviance, copying the last count lowest absolute error', file=NDC,
        field='primary; phases/pre_target_bump/matched/{scores,contrasts}', full=None,
        note='deviance 1.987 / 1.991 / 1.990, cue-only regression 1.905; MAE 1.039 / persistence 1.015; 2,436 windows, 609 trials, 26 contacts')
    return ''


TR = 'models/target-reach/results/crossing/summary.json'       # a cylinder carried to one of nine targets: clock started once it had moved 15 mm
TRA = 'models/target-reach/results/acquisition/summary.json'   # the same trials, clock started at the first camera sample (the planned test)
TR_PAPER = 'docs/papers/target-reach/target-reach.pdf'
TR_METHODS = 'models/target-reach/METHODS.md'


def TRV(rel, field, dp, scale=1000):      # noqa: N802
    """A number of the target-reach summaries under groups["600/both"] (a key with a slash in it, which N() cannot walk), in
    millimetres; logged like N()."""
    raw = walk(load(rel)['groups']['600/both'], field)
    assert isinstance(raw, (int, float)) and not isinstance(raw, bool), (rel, field, raw)
    txt = fmt(raw * scale, dp)
    log(txt, file=rel, field='groups["600/both"]/' + field, full=raw, note='x%g' % scale)
    return txt


def TRN(model, rel=TR, dp=2):      # noqa: N802
    """A score of the target-reach study 0.6 s after the named clock started, both hands: the mean distance in millimetres from the
    forecast to the measured position (trials averaged within each person, then people; a transformer's three fits averaged)."""
    return TRV(rel, f'scores/{model}/mean_m', dp)


def TRA_MOVED():      # noqa: N802
    """How far the cylinder moved, on average, between the last input (0.2 s) and 0.6 s on the planned clock: the error of holding it
    still, in millimetres (the summary's true_amplitude_m, equal to the stationary forecast's score; tr_checks() asserts both)."""
    return TRV(TRA, 'true_amplitude_m', 3)


def tr_checks():
    """The target-reach study (published after the papers). Sziburis and colleagues' Ruhr Hand Motion Catalog: from five positions of a
    carried cylinder over 200 ms, the hand and the assigned target, models fitted on 24 people forecast its displacement 0.4, 0.6 and
    0.8 s after the clock started, for seven others. Planned clock (first camera sample): the cylinder hardly moved; the two models
    without the target were the two closest; the full transformer was clearly worse than its motion-only twin; the rule failed. Second
    clock (15 mm travelled): the full transformer closest of all eleven forecasts, clearly better than with a wrong target, not clearly
    better than motion alone; the rule failed there too. Not the general model."""
    c, a = load(TR), load(TRA)
    for s, n600 in ((c, 237), (a, 239)):
        assert s['people'] == 7 and s['horizons_s'] == [0.4, 0.6, 0.8] and s['incremental_gate'] is False, s['people']
        assert s['eligible']['600']['both'] == {'n': n600, 'people': 7}, s['eligible']['600']
    cs = {k: v['mean_m'] for k, v in c['groups']['600/both']['scores'].items()}
    assert len(cs) == 11 and min(cs, key=cs.get) == 'transformer_full', cs
    assert cs['transformer_full'] < cs['transformer_pose_only'] < cs['transformer_wrong_target'] < cs['goal_hand_mean'] < cs['stationary'], cs
    cc = c['groups']['600/both']['comparisons']
    lo, hi = cc['transformer_pose_only']['ci']
    assert lo < 0 < hi, (lo, hi)
    assert cc['transformer_wrong_target']['ci'][1] < 0, cc['transformer_wrong_target']['ci']
    ag = a['groups']['600/both']
    asc = {k: v['mean_m'] for k, v in ag['scores'].items()}
    assert sorted(asc, key=asc.get)[:2] == ['ridge_pose_only', 'transformer_pose_only'], sorted(asc, key=asc.get)
    assert ag['true_amplitude_m'] == asc['stationary'], (ag['true_amplitude_m'], asc['stationary'])
    assert ag['comparisons']['transformer_pose_only']['ci'][0] > 0, ag['comparisons']['transformer_pose_only']
    paper = re.sub(r'\s+', ' ', pdf_text(TR_PAPER))
    for said in ('Between 200 and 600 ms on the acquisition clock the object shifted just 0.117 mm on average.',
                 'The primary criterion failed.', 'Neither gesture comparison established a benefit from supplying the object label.',
                 'Staying still did better at 41.35 mm.'):
        assert said in paper, said
    methods = (REPO / TR_METHODS).read_text(encoding='utf-8')
    assert 'A destination benefit at 600 ms requires both the full-minus-pose-only and full-minus-wrong-destination intervals to fall wholly below zero.' in methods
    assert 'Neither clock passed both tests.' in methods
    assert not [p.name for p in (REPO / 'models/neurotranslate-0.0').iterdir() if re.search(r'target|reach|cylinder|ruhr', p.name.lower())]
    log('target reach: on the planned clock the cylinder hardly moved and the forecasts without the target came closest (rule failed); '
        'after 15 mm the full transformer beat a wrong target clearly and the motion-only transformer not clearly (rule failed)', file=TR,
        field='people; incremental_gate; eligible/600/both; groups/600/both/{scores,comparisons} (and the same in ' + TRA + ')', full=None,
        note='crossing 12.13 / motion only 12.24 / wrong target 17.79 / hand-and-target mean 35.43 / still 66.85 mm; planned clock: moved 0.117 mm')
    return ''


CY = 'models/cylinder-rotation/results/test/summary.json'            # a sensor on a carried cylinder: its next 100 ms of turning, on the ninth and tenth trips
CY_DEV = 'models/cylinder-rotation/results/validation/summary.json'   # the same models on the seventh and eighth trips (the development check)
CY_ORIENT = 'models/cylinder-rotation/orientation/test.json'           # the forecast turned into a change of orientation, against the sensor's own estimate
CY_PAPER = 'docs/papers/cylinder-rotation/cylinder-rotation.pdf'
CY_METHODS = 'models/cylinder-rotation/model/METHODS.md'
CY_SOURCE = 'models/cylinder-rotation/source/README.md'
CY_MATCHED = 'matched/overall/gyro'      # the moments with an earlier trip to lend its acceleration: the planned test's common support


def CYV(field, dp=4, rel=CY, group=CY_MATCHED, comma=False):      # noqa: N802
    """A number of the cylinder-rotation summaries under groups[group] (a key with slashes in it, which N() cannot walk); logged
    like N(). comma=True prints a whole count with a thousands separator."""
    raw = walk(load(rel)['groups'][group], field)
    assert isinstance(raw, (int, float)) and not isinstance(raw, bool), (rel, group, field, raw)
    txt = f'{int(raw):,}' if comma else fmt(raw, dp)
    log(txt, file=rel, field=f'groups["{group}"]/{field}', full=raw)
    return txt


def CYN(model, rel=CY):      # noqa: N802
    """A score of the cylinder-rotation study on the matched moments: the mean miss, in radians per second, of the forecast of the
    cylinder's average turning rate over the next ten readings (windows averaged within each trip, trips within each person, then
    people; a transformer's three fits scored separately, then averaged)."""
    return CYV(f'scores/{model}/error', 4, rel)


def CYC(what, rel=CY):      # noqa: N802
    """A count of the matched moments of the cylinder-rotation study: 'windows', 'recordings' or 'participants'."""
    return CYV(what, rel=rel, comma=True)


def CYP(model):      # noqa: N802
    """How many of the 24 people the full transformer beat the named model for, on the matched moments."""
    return CYV(f'full_minus/{model}/better_people', comma=True)


def CYO(method):      # noqa: N802
    """The angle in degrees between the orientation the sensor estimated a tenth of a second on and the one reached by turning the last
    orientation at the forecast rate (or, for hold_orientation, by not turning it), on the matched moments."""
    raw = load(CY_ORIENT)['results']['matched/overall']['methods'][method]['mean_degrees']
    txt = fmt(raw, 3)
    log(txt, file=CY_ORIENT, field=f'results["matched/overall"]/methods/{method}/mean_degrees', full=raw)
    return txt


def cy_checks():
    """The cylinder-rotation study (published after the papers). Sziburis and colleagues' Ruhr Hand Motion Catalog, the sensor on the
    cylinder: from its last 20 readings, the hand, the target and the elapsed time, models forecast the average turning rate over the
    next ten readings. Fitted on the third to sixth trips per person, hand and target, checked on the seventh and eighth, tested on the
    ninth and tenth, all by the same 24 people. On the test's matched moments the full transformer was not clearly better than without
    the accelerometer and clearly better than with another trip's acceleration, so the planned test failed (it had passed on the
    development check); without the target the transformer did best of all, for every person; turned into an orientation, the full
    forecast beat holding the last orientation and repeating the last rate. Not the general model."""
    s, d = load(CY), load(CY_DEV)
    assert s['primary_passed'] is False and d['primary_passed'] is True, (s['primary_passed'], d['primary_passed'])
    g = s['groups'][CY_MATCHED]
    assert (g['windows'], g['recordings'], g['participants']) == (2653, 379, 24), (g['windows'], g['recordings'], g['participants'])
    a = s['groups']['all/overall/gyro']
    assert (a['windows'], a['recordings'], a['participants']) == (5628, 804, 24)
    sc = {k: v['error'] for k, v in g['scores'].items()}
    assert len(sc) == 16 and min(sc, key=sc.get) == 'transformer_sensors', sc
    assert sc['transformer_sensors'] < sc['transformer_full'] < sc['transformer_gyro_task'] < sc['transformer_wrong_accel'] < sc['hand_target_time_mean'] < sc['persistence'], sc
    fm = g['full_minus']
    lo, hi = fm['transformer_gyro_task']['interval']
    assert lo < 0 < hi and fm['transformer_gyro_task']['better_people'] == 13, fm['transformer_gyro_task']
    assert fm['transformer_wrong_accel']['interval'][1] < 0, fm['transformer_wrong_accel']
    assert fm['transformer_sensors']['interval'][0] > 0 and fm['transformer_sensors']['better_people'] == 0, fm['transformer_sensors']
    full, without = g['scores']['transformer_full']['by_person'], g['scores']['transformer_sensors']['by_person']
    assert len(full) == 24 and all(without[p] < full[p] for p in full)
    dg = d['groups'][CY_MATCHED]['full_minus']
    assert dg['transformer_gyro_task']['interval'][1] < 0 and dg['transformer_wrong_accel']['interval'][1] < 0, dg
    o = load(CY_ORIENT)['results']['matched/overall']
    om = {k: v['mean_degrees'] for k, v in o['methods'].items()}
    assert o['rows'] == 2653 and om['transformer_full'] < om['hold_orientation'] < om['persistence'], om
    assert o['full_minus']['hold_orientation']['interval'][1] < 0 and o['full_minus']['persistence']['interval'][1] < 0, o['full_minus']
    paper = re.sub(r'\s+', ' ', pdf_text(CY_PAPER))
    for said in ('The two prespecified comparisons did not establish an incremental acceleration benefit on the donor-matched repetitions.',
                 'Each held repetition belongs to a familiar person performing a familiar task.',
                 'On these repetitions, the sensor pair also worked best when the hand and clock were supplied without the target number.',
                 'The required joint benefit failed.'):
        assert said in paper, said
    methods = (REPO / CY_METHODS).read_text(encoding='utf-8')
    assert 'Both differences must have upper paired 95% limits below zero on common held windows.' in methods
    source = (REPO / CY_SOURCE).read_text(encoding='utf-8')
    for said in ('The third through sixth assignments enter training, the seventh and eighth enter validation, and the ninth and tenth form the reserved test.',
                 'The roster covers 24 people already observed in an earlier development study.'):
        assert said in source, said
    assert not [p.name for p in (REPO / 'models/neurotranslate-0.0').iterdir() if re.search(r'cylinder|ruhr|inertial|gyro', p.name.lower())]
    log('cylinder rotation: on the matched test moments the acceleration did not clearly help (rule failed; it had passed on the '
        'development check), another trip\'s acceleration clearly hurt, the transformer without the target did best for all 24 people, and '
        'the forecast turned into an orientation beat holding the last one', file=CY,
        field='primary_passed; groups["matched/overall/gyro"]/{windows,recordings,participants,scores,full_minus} (and ' + CY_DEV + ', ' + CY_ORIENT + ')',
        full=None, note='full 0.1584 / without accelerometer 0.1622 / another trip\'s acceleration 0.1772 / without target 0.1508 rad/s; orientation 0.909 against 1.185 degrees')
    return ''


RF = 'models/reach-feedback/results/transfer.json'         # one macaque's reaches in the second region of the apparatus (the transfer test)
RF_W = 'models/reach-feedback/results/within.json'         # later reaches in the region the models were fitted in
RF_TR = 'models/reach-feedback/results/train.json'         # the fitting reaches
RF_J = 'models/reach-feedback/results/joint-transfer.json'  # the separate model that feeds its own last forecast back in, second region
RF_PAPER = 'docs/papers/reach-feedback/reach-feedback.pdf'
RF_SOURCE = 'models/reach-feedback/source/RECONSTRUCT.md'


def RFC(model, rel=RF):      # noqa: N802
    """A count forecast's error in the reach-feedback study, on the reaches with an earlier reach to lend its forecast: Poisson deviance of
    each unit's total over the ten later bins, averaged over the 23 units, reaches within a sequence, sequences, then the three fits."""
    return N(rel, f'counts/matched/{model}/mean/total_deviance', 4)


def RFM(model, part, rel=RF):      # noqa: N802
    """A movement forecast's miss, in mm, at the end of the forecast (100 ms after the last known position), all eligible reaches."""
    return N(rel, f'motor/all/{model}/mean/{part}/endpoint', 3)


def RFD(contrast, rel=RF):      # noqa: N802
    """A planned count comparison: the count model given the movement forecast minus the history alone ('full_minus_direct') or minus the
    same model given an earlier reach's forecast ('full_minus_wrong'); printed without its sign (the sentence says which way)."""
    return N(rel, f'primary/count/{contrast}/mean/difference', 4, absolute=True)


def RFS(part, rel=RF):      # noqa: N802
    """The planned movement comparison: the movement transformer given earlier spikes minus the one given positions and cues alone, endpoint
    miss in mm; printed without its sign."""
    return N(rel, f'primary/motor/{part}/mean/difference', 3, absolute=True)


def RFN(field, rel=RF):      # noqa: N802
    """A count of reaches ('windows') or sequences ('originals') in the reach-feedback study."""
    return N(rel, field)


def rf_checks():
    """The reach-feedback study (published after the papers). Chowdhury, Glaser and Miller's recording of macaque C on 7 September 2017,
    reaching to one target after another in two regions of the apparatus. Fifty milliseconds after a go cue, a movement model forecast the
    next ten positions from 200 ms of positions, spikes and cues; a count model given the same history and that forecast predicted each of 23
    units' spikes 100 to 200 ms after the cutoff. Neither planned count test passed (later reaches in the first region: no clear change
    against the history alone, clearly better than an earlier reach's forecast; second region: clearly worse than the history alone, no
    clear change against an earlier reach's), and the training average beat both transformers in the second region, where a Poisson
    regression on the predicted movement alone came closest. The planned movement test failed: earlier spikes brought the hand closer and
    the elbow further in the second region, and made both worse in the first. The separate feedback model lowered the hand's and the
    counts' errors against the parallel one and raised the elbow's, so its own test failed. Not the general model."""
    t, w, tr, j = load(RF), load(RF_W), load(RF_TR), load(RF_J)
    assert t['primary']['count_gate'] == {'status': 'evaluated', 'pass': False}, t['primary']['count_gate']
    assert w['primary']['count_gate'] == {'status': 'evaluated', 'pass': False}, w['primary']['count_gate']
    assert t['primary']['motor_gate'] == {'status': 'evaluated', 'pass': False}, t['primary']['motor_gate']
    assert t['primary']['both_test_count_gates_pass'] is False and w['primary']['both_test_count_gates_pass'] is False
    c = tr['coverage']
    assert (c['source']['roster'], c['source']['eligible'], c['count_supported_windows'], c['count_supported_originals'], c['count_warmup_windows_excluded']) == (198, 519, 408, 158, 111), c
    assert (w['coverage']['count_supported_windows'], w['coverage']['count_supported_originals'], w['coverage']['count_matched_windows'], w['coverage']['count_matched_originals']) == (116, 43, 113, 42)
    assert (t['coverage']['count_supported_windows'], t['coverage']['count_supported_originals'], t['coverage']['count_roster_originals'], t['coverage']['count_matched_windows'], t['coverage']['count_matched_originals']) == (825, 316, 321, 822, 315)
    assert len(t['coverage']['unit_guide']) == 23 and len(w['coverage']['unit_guide']) == 23

    def iv(d, grp, name):
        m = d['primary'][grp][name]['mean']
        return m['difference'], m['moving_block_95']
    d, (lo, hi) = iv(w, 'count', 'full_minus_direct'); assert d > 0 and lo < 0 < hi, (d, lo, hi)
    d, (lo, hi) = iv(w, 'count', 'full_minus_wrong'); assert d < 0 and hi < 0, (d, lo, hi)
    d, (lo, hi) = iv(t, 'count', 'full_minus_direct'); assert d > 0 and lo > 0, (d, lo, hi)
    d, (lo, hi) = iv(t, 'count', 'full_minus_wrong'); assert d < 0 and lo < 0 < hi, (d, lo, hi)
    d, (lo, hi) = iv(t, 'motor', 'hand'); assert d < 0 and hi < 0, (d, lo, hi)
    d, (lo, hi) = iv(t, 'motor', 'elbow'); assert d > 0 and lo > 0, (d, lo, hi)
    for part in ('hand', 'elbow'):
        d, (lo, hi) = iv(w, 'motor', part); assert d > 0 and lo > 0, (part, d, lo, hi)
    for d_ in (t, w):
        for name in ('full_minus_direct', 'full_minus_wrong'):
            assert d_['primary']['count'][name]['windows'] == d_['coverage']['count_matched_windows']
    m = {k: v['mean']['total_deviance'] for k, v in t['counts']['matched'].items()}
    assert m['train_mean'] < m['direct'] < m['full'] < m['wrong'], m
    fair = {k: v for k, v in m.items() if 'privileged' not in k}       # the privileged arms read the movement that actually followed
    assert min(fair, key=fair.get) == 'glm_predicted_only', sorted(fair.items(), key=lambda kv: kv[1])[:3]
    mo = t['motor']['all']
    assert mo['full']['mean']['hand']['endpoint'] < mo['pose_cue']['mean']['hand']['endpoint']
    assert mo['full']['mean']['elbow']['endpoint'] > mo['pose_cue']['mean']['elbow']['endpoint']
    p = j['paired']['rollout_minus_parallel']
    assert j['all_three_rollout_better'] is False and j['rows'] == 825
    assert p['hand_mm_endpoint']['interval'][1] < 0 and p['count_deviance']['interval'][1] < 0 and p['elbow_mm_endpoint']['interval'][0] > 0, p
    paper = re.sub(r'\s+', ' ', pdf_text(RF_PAPER))
    for said in ('Neither held test established an advantage from supplying the predicted path.',
                 'Both workspace-specific criteria failed.',
                 'The two workspaces were interleaved.',
                 'We stopped five 10 ms bins after the controller registered the second, third or fourth go cue in a sequence.',
                 'The elbow worsened, so the two-marker criterion failed.',
                 'The declared requirement for all three outcomes therefore failed.'):
        assert said.replace('−', '-') in paper, said
    source = (REPO / RF_SOURCE).read_text(encoding='utf-8')
    for said in ('Among rewarded workspace-1 originals, chronological order gives 198 for training, 42 for validation and 43 for the later test.',
                 'Its trials were interleaved in recording time with those in workspace 1.',
                 'This reconstruction uses one macaque, C, on 7 September 2017.'):
        assert said in source, said
    assert not [q.name for q in (REPO / 'models/neurotranslate-0.0').iterdir() if re.search(r'reach|feedback|area2|somato', q.name.lower())]
    log('reach feedback: neither planned count test passed in either region, the training average beat both transformers in the second '
        'region, the planned movement test failed (hand closer, elbow further), and the feedback model failed its own test', file=RF,
        field='primary/{count_gate,motor_gate}; coverage; counts/matched; motor/all (and ' + RF_W + ', ' + RF_TR + ', ' + RF_J + ')',
        full=None, note='second region: with forecast 1.1934 / history alone 1.1834 / training average 1.1595 / regression on the forecast 1.1158; hand 8.398 against 9.362 mm, elbow 8.421 against 8.115 mm')
    return ''


RW_C = 'models/reach-feedback-week/counts/results.json'        # the reach-feedback macaque a week later: spikes after the measured movement
RW_L = 'models/reach-feedback-week/late_counts/results.json'   # the same, for a model that also knew the spikes in between (17 contacts)
RW_M = 'models/reach-feedback-week/motor/scores.json'          # the forecast of the arm, with and without the spike counts
RW_P = 'models/reach-feedback-week/muscles/results.json'       # 39 muscle-tendon path lengths the source's OpenSim model calculated
RW_PAPER = 'docs/papers/reach-feedback/one-week/one-week.pdf'


def _rw_block(ws, block, pop='primary'):
    return load(RW_C)['workspaces'][ws]['populations'][pop][block]


def RWC(ws, name, pop='primary'):      # noqa: N802
    """A count forecast's error a week later, on the reaches with an earlier reach to lend its movement: mean Poisson deviance per
    contact per 100 ms, contacts within a reach, reaches within a sequence, sequences within the region."""
    i = _rw_block(ws, 'with_count_references', pop)['metric_order'].index(name)
    return N(RW_C, f'workspaces/{ws}/populations/{pop}/with_count_references/matched/mean/{i}', 3)


def RWD(ws, name='update_minus_base', pop='primary'):      # noqa: N802
    """A planned count comparison a week later (the forecast given the measured movement minus the one without it); printed without
    its sign (the sentence says which way)."""
    i = _rw_block(ws, 'prespecified', pop)['metric_order'].index(name)
    return N(RW_C, f'workspaces/{ws}/populations/{pop}/prespecified/matched/mean/{i}', 3, absolute=True)


def RWN(field, rel=RW_C):      # noqa: N802
    """A count of sequences or reaches ('windows') of the later day."""
    return N(rel, field)


def RWL(ws, name='measured_minus_stale'):      # noqa: N802
    """The model that also knew the spikes in between: with the measured movement minus with the position held at its last value;
    printed without its sign."""
    d = load(RW_L)
    i = len(d['method_order']) + d['contrast_order'].index(name)
    return N(RW_L, f'workspaces/{ws}/populations/common/matched/mean/{i}', 3, absolute=True)


def RWM(ws, region, contrast='full_minus_pose'):      # noqa: N802
    """The forecast of the arm given the spike counts minus the one given positions and cues alone, averaged over the ten forecast
    times (hand and elbow in mm); printed without its sign."""
    assert load(RW_M)['dimensions'][0] == 'trajectory_mean'
    return N(RW_M, f'workspaces/{ws}/regions/{region}/contrasts/{contrast}/mean/0', 3, absolute=True)


def RWP(ws, arm):      # noqa: N802
    """The miss, in mm, at the end of the 100 ms, of a forecast of the change in length of the 39 muscle-tendon paths, averaged over
    the paths, on the reaches with an earlier reach to lend its movement."""
    return N(RW_P, f'scores/{ws}/arms/{arm}/matched/endpoint_mae/0', 3)


def rw_checks():
    """The reach-feedback models a week later (published after the papers). The macaque of the reach-feedback study on 14 September
    2017, models fixed on 7 September. Given the measured movement, the forecast of the spikes on 37 contacts improved in the first
    region and worsened in the second, each clear of zero, so the planned test failed; another reach's movement was worse than both in
    both; each contact's training average beat both forecasts in the second region and lay between them in the first. The model that
    also knew the spikes in between gained nothing from the movement (no clear change in the first region, worse in the second). The
    spike counts made the forecast hand worse in both regions, the elbow worse in the first and better in the second. For the 39
    muscle-tendon paths, forecasting no change came closest in both regions. Not the general model."""
    c, late, m, p = load(RW_C), load(RW_L), load(RW_M), load(RW_P)
    assert c['primary_incremental_success'] is False
    assert (c['total_originals'], c['unassigned_originals'], c['total_windows']) == (512, 3, 493)
    assert [len(c['contacts_by_population'][k]) for k in ('primary', 'zero', 'positive')] == [37, 37, 17]

    def pre(ws, name):
        b = _rw_block(ws, 'prespecified')
        i = b['metric_order'].index(name)
        return b['matched']['mean'][i], b['matched']['moving8']['interval'][i]
    for ws, (n_w, n_o, n_a) in {'1': (197, 109, 241), '2': (288, 161, 268)}.items():
        b = _rw_block(ws, 'prespecified')['matched']
        assert (b['windows'], b['originals'], c['workspaces'][ws]['assigned_originals']) == (n_w, n_o, n_a), (ws, b['windows'], b['originals'])
        d, (lo, hi) = pre(ws, 'update_minus_wrong_motion')
        assert d < 0 and hi < 0, (ws, d, lo, hi)
        r = _rw_block(ws, 'with_count_references')
        assert (r['matched']['windows'], r['matched']['originals']) == (n_w, n_o)
        mean = dict(zip(r['metric_order'], r['matched']['mean']))
        for k in ('update', 'base', 'wrong_motion', 'update_minus_base'):
            assert mean[k] == pre(ws, k)[0], (ws, k)
        assert mean['wrong_motion'] > max(mean['update'], mean['base']), mean
        methods = {k: v for k, v in mean.items() if '_minus_' not in k}
        if ws == '1':
            assert mean['update'] < mean['train_mean'] < mean['base'], mean
        else:
            assert min(methods, key=methods.get) == 'train_mean', methods
    d, (lo, hi) = pre('1', 'update_minus_base')
    assert d < 0 and hi < 0, (d, lo, hi)
    d, (lo, hi) = pre('2', 'update_minus_base')
    assert d > 0 and lo > 0, (d, lo, hi)

    assert late['consistent_improvement_both_workspaces'] is False and len(late['contacts']['common']) == 17

    def lc(ws, name='measured_minus_stale'):
        b = late['workspaces'][ws]['populations']['common']['matched']
        i = len(late['method_order']) + late['contrast_order'].index(name)
        return b['mean'][i], b['moving8']['interval'][i]
    d, (lo, hi) = lc('1')
    assert d > 0 and lo < 0 < hi, (d, lo, hi)
    d, (lo, hi) = lc('2')
    assert d > 0 and lo > 0, (d, lo, hi)

    assert m['all_required_primary_intervals_below_zero'] is False and m['dimensions'][0] == 'trajectory_mean'

    def mc(ws, region):
        x = m['workspaces'][ws]['regions'][region]['contrasts']['full_minus_pose']
        return x['mean'][0], x['moving']['interval'][0]
    for ws in '12':
        d, (lo, hi) = mc(ws, 'hand_mm')
        assert d > 0 and lo > 0, (ws, d, lo, hi)
    d, (lo, hi) = mc('1', 'elbow_mm')
    assert d > 0 and lo > 0, (d, lo, hi)
    d, (lo, hi) = mc('2', 'elbow_mm')
    assert d < 0 and hi < 0, (d, lo, hi)

    assert p['positive_claim'] is False and len(p['paths']) == 39
    for ws, n in (('1', 197), ('2', 288)):
        arms = {k: v['matched'] for k, v in p['scores'][ws]['arms'].items()}
        assert all(v['windows'] == n for v in arms.values()), ws
        e = {k: v['endpoint_mae'][0] for k, v in arms.items()}
        assert min(e, key=e.get) == 'stationary', sorted(e.items(), key=lambda kv: kv[1])[:3]
        assert e['full'] > e['stationary']

    paper = re.sub(r'\s+', ' ', pdf_text(RW_PAPER))
    for said in ('We fitted the models on the first day and tested them on the second.',
                 'All fitted weights, scaling and comparison rules were fixed before access to its numerical signals.',
                 'In workspace 2 it increased the error.',
                 'Substituting movement from a different reach made the forecast worse in both workspaces.',
                 'They did not reliably improve the hand and elbow together.',
                 'For 39 muscle–tendon paths calculated from the tracked arm, predicting that each length would stay put gave the smallest '
                 'average error in both workspaces.',
                 'These comparisons concern one animal on one held-out day.'):
        assert said in paper, said
    assert not [q.name for q in (REPO / 'models/neurotranslate-0.0').iterdir() if re.search(r'reach|feedback|week|area2|somato', q.name.lower())]
    log('reach feedback a week later: the measured movement helped the spike forecast in the first region and hurt it in the second '
        '(planned test failed), the training average beat both forecasts in the second region, the spikes made the forecast hand worse in '
        'both regions, and forecasting no change came closest for the 39 muscle-tendon paths', file=RW_C,
        field='primary_incremental_success; workspaces/*/populations/primary (and ' + RW_L + ', ' + RW_M + ', ' + RW_P + ')', full=None,
        note='second region: with the movement 4.783 / without 4.680 / training average 4.118; hand +0.468 and +0.882 mm; paths 1.047 and '
             '1.539 against no change 0.689 and 0.540 mm')
    return ''


BODY_COMPARISON = 'models/first-use-body/matched-comparison.json'
SECOND_RAT = 'models/next-neuron-prediction/er1-results.json'


def first_use_checks():
    rows = load(BODY_COMPARISON)
    mammal, mixed, mammal_locust, mixed_locust = (rows[i] for i in (0, 12, 6, 18))
    for earlier, later in ((mammal, mixed), (mammal_locust, mixed_locust)):
        assert (earlier['fit'], later['fit']) == ('mammal', 'mixed')
        assert all(row['condition'] == 'observed' and row['phase'] == 'all' for row in (earlier, later))
        assert earlier['matched_points'] == later['matched_points']
        assert earlier['recordings'] == later['recordings']
        assert earlier['methods'] == later['methods'] and earlier['methods'][:2] == ['shape', 'no_shape']
    assert mammal['horizon_s'] == mixed['horizon_s'] == 0.12
    assert mammal_locust['horizon_s'] == mixed_locust['horizon_s'] == 0.2
    assert mammal['recording_mean'][0] < mixed['recording_mean'][0]
    assert mixed_locust['recording_mean'][0] < mammal_locust['recording_mean'][0]
    log('mixed training improved the slower locust forecast and worsened the common short-horizon mean',
        file=BODY_COMPARISON, field='matched observed sets; recording_mean/shape', full=None)
    return ''


def next_neuron_checks():
    methods = load(SECOND_RAT)['methods']
    fitted, running, recent = [methods[name]['pooled'] for name in ('shared_model', 'online_rate', 'recency')]
    assert fitted['rows'] == running['rows'] == recent['rows']
    assert fitted['log_loss'] < min(running['log_loss'], recent['log_loss'])
    assert running['top1'] < fitted['top1'] < recent['top1']
    log('second rat: fitted history improves log loss while recency has slightly higher first-choice accuracy',
        file=SECOND_RAT, field='methods/{shared_model,online_rate,recency}/pooled', full=None)
    return ''

CROSS_WRIST = 'docs/papers/cross-person-wrist/cross-person-wrist-source.zip!aggregate.json'


def cross_wrist_checks():
    """Check the support and direction of the primary wrist comparison at both horizons."""
    results = load(CROSS_WRIST)
    for horizon in (8, 15):
        row = results['primary'][f'contralateral_{horizon}']
        assert row['n'] == results['selected'] == results['width']['test']['count']
        assert row['means']['pixels']['ridge'] > row['means']['pixels']['damped_velocity']
        assert row['ridge_minus_damped']['shoulder_widths'] > 0
    assert GENERAL_FITS['cross_person_wrist'] == 'not the general model'
    log('the regression missed farther than continuing a fraction of earlier velocity at both horizons',
        file=CROSS_WRIST, field='primary/{contralateral_8,contralateral_15}; selected; width/test/count', full=None)
    return ''


HW_SRC = 'docs/papers/human-wrist/human-wrist-source.zip'
HW = HW_SRC + '!results.json'                         # one person's two wrists on a second recording day: the supplement's results file
HW_README = 'models/human-wrist/README.md'
HW_TASK = 'models/neurotranslate-0.0/bilateral_wrist/README.md'
HW_PAGE = 'docs/human-wrist/README.md'
HW_SEEDS = (17, 37, 73)


def _hw_n58(side, h):
    """Every forecast scored on all 58 held reaches for that wrist and horizon: {method: mean error in camera pixels}."""
    a = load(HW)['absolute']
    return {k: v[side][h]['mean_px'] for k, v in a.items()
            if side in v and h in v[side] and v[side][h].get('n') == 58 and v[side][h].get('mean_px') is not None}


def HWA(method, side, h, dp=2):      # noqa: N802
    """Mean endpoint error, in camera pixels, of one forecast of one wrist at 8 or 15 camera frames, over the 58 held reaches."""
    return N(HW, f'absolute/{method}/{side}/{h}/mean_px', dp)


def HWN(field):      # noqa: N802
    """A count from the results file."""
    return N(HW, field)


def HWMAX():      # noqa: N802
    """The largest gain on the right wrist from the voltages, against the same transformer on the pose alone (57 common reaches)."""
    pc = load(HW)['primary_common']
    cells = [(pc[f'transformer_anchored_full_s{s}__minus__transformer_anchored_pose_s{s}']['right'][h]['mean_delta_px'], s, h)
             for s in HW_SEEDS for h in ('8', '15')]
    v, s, h = min(cells)
    return N(HW, f'primary_common/transformer_anchored_full_s{s}__minus__transformer_anchored_pose_s{s}/right/{h}/mean_delta_px', 2, absolute=True)


def hw_checks():
    """Every direction and count the pages state about the two-wrist study, asserted against its results file and its own pages:
    the training reaches' average movement is the closest forecast of the right wrist at both horizons, and no movement the closest
    of the left (of every forecast scored on all 58 reaches); on the 57 reaches with an earlier reach to lend its voltages, the voltages
    lower each of the three transformers' right-wrist error against the same transformer on the pose alone, while another reach's voltages
    do as well or better in three of those six comparisons; the test set in advance failed for both wrists; the transformers of the
    general model's folder carry weights of their own."""
    d = load(HW)
    for h in ('8', '15'):
        right, left = _hw_n58('right', h), _hw_n58('left', h)
        assert min(right, key=right.get) == 'mean', (h, min(right, key=right.get))
        assert left['zero'] == min(left.values()), h
        assert right['transformer_anchored_full_s17'] > right['mean'] and len(right) == 86 and len(left) == 34, (h, len(right), len(left))
    pc = d['primary_common']
    for s in HW_SEEDS:
        for h in ('8', '15'):
            c = pc[f'transformer_anchored_full_s{s}__minus__transformer_anchored_pose_s{s}']['right'][h]
            assert c['n'] == 57 and c['mean_delta_px'] < 0, (s, h, c['n'], c['mean_delta_px'])
    wrong = [pc[f'transformer_anchored_full_s{s}__minus__transformer_anchored_full_s{s}_wrong']['right'][h]['mean_delta_px'] >= 0
             for s in HW_SEEDS for h in ('8', '15')]
    assert sum(wrong) == 3 and len(wrong) == 6, wrong
    assert d['primary'] == {'right': {'defined': True, 'lower_against_both_controls_all_seeds_and_horizons': False},
                            'left': {'defined': True, 'lower_against_both_controls_all_seeds_and_horizons': False}}, d['primary']
    st = d['study']
    assert (st['species'], st['training_session'], st['test_session'], st['training_hours'], st['training_blocks'], st['horizons_frames'],
            st['video_hz'], st['electrical_hz'], st['seeds']) == ('human', 3, 4, [0, 16], 60, [8, 15], 30, 500, [17, 37, 73]), st
    assert st['population'] == 'one AJILE12 participant, release 0.220127.0436', st['population']
    assert d['rows'] == 58 and d['stratum_window_counts'] == [3, 7, 12, 12, 12, 12] and d['eligible_prior_voltage_donor'] == 57
    readme = re.sub(r'\s+', ' ', (REPO / HW_README).read_text(encoding='utf-8'))
    for s in ('A camera tracks two wrists, two elbows and two shoulders.', 'Eight electrodes measure electrical activity at the surface of the brain.',
              'The experiment fits one recording from AJILE12 and tests the next recording of the same person.',
              'The public example uses invented movement and voltage.', 'Eight frames take about 267 milliseconds at 30 frames per second. Fifteen take half a second.',
              'The authors detected right-wrist reaches retrospectively from tracked video.', 'No instructions were given at these onsets.',
              'The first 16 hours of session 3 supplied 60 eligible right-wrist events.',
              'Session 4 contributed the first twelve eligible events in each four-hour interval where available.',
              'Each example contains 250 earlier samples at 500 Hz from eight grid channels, and fifteen earlier camera frames at 30 Hz for each of six landmarks.',
              'without a depth or physical-distance calibration', 'Each set has five simple forecasts and 36 combinations of linear regression, small causal Transformers, pose alone, pose plus voltage and earlier-event voltage controls.',
              'three fixed initializations (17, 37, 73)', 'Neither wrist met the prespecified requirement to beat both controls at both horizons in every fit.',
              'The left-wrist estimates describe what happened during selected **right**-wrist movements.',
              'The frozen fitted weights and individual event values stay out of this distribution.'):
        assert s in readme, s
    task = re.sub(r'\s+', ' ', (REPO / HW_TASK).read_text(encoding='utf-8'))
    assert 'Each wrist has its own fitted Transformer.' in task and 'The older movement checkpoint has no role in its predictions.' in task
    page = re.sub(r'\s+', ' ', (REPO / HW_PAGE).read_text(encoding='utf-8'))
    assert 'Each reference and every fitted parameter in the built-in example come from simulation.' in page
    assert 'Move a wrist or change the signal gain to see the prediction update.' in page
    assert GENERAL_FITS['bilateral_wrist'] == 'not the general model'
    log('the closest forecasts; the voltages against the pose alone and against another reach\'s voltages; the test set in advance',
        file=HW, field='absolute/*/{right,left}/{8,15}/mean_px (n 58); primary_common; primary; study; rows; stratum_window_counts; '
        'eligible_prior_voltage_donor', full=None,
        note='right: training mean lowest at both horizons; left: zero lowest; voltages lower for all three seeds at both horizons on the '
             'right; another reach\'s voltages as good or better in 3 of 6; prespecified test failed for both wrists')
    return ''


GENERAL_HEADING = 'The general model has had its first runs, and in six tests on unseen people it beat simpler forecasts once'


def try_rows(kind):
    """Rows of the README's table of things to try: 'browser' (a page on the site opens from the row; they come first) or
    'programmers' (no page to open; they come last). Counted from the README template itself, so a row added or moved changes the
    numbers the page prints, or stops the build if the browser rows stop coming first."""
    t = (TEMPLATES / 'README.md').read_text(encoding='utf-8')
    start = t.index('| What it asks | What you do, and what was found |')
    rows = [ln for ln in t[start:].split('\n\n', 1)[0].splitlines()[2:] if ln.startswith('| ')]
    web = ['eliminatenoise.github.io' in ln for ln in rows]
    n_web = sum(web)
    assert web == [True] * n_web + [False] * (len(rows) - n_web), web
    n = n_web if kind == 'browser' else len(rows) - n_web
    log(str(n), file='tools/front-pages/templates/README.md',
        field='rows of the table of things to try ' + ('with a link to a page on the site (all before the others)' if kind == 'browser' else 'without one (all after the others)'), full=n)
    return str(n)


def TRY_HEADING():      # noqa: N802  (a heading that other links point to; one definition, so the anchors cannot drift)
    return spell(try_rows('browser'), True) + ' pages run in your browser, with nothing to install'


WF = 'models/walking-force/results.json'                      # overground walking: the load two floor plates record, from markers and leg muscles
RP = 'models/neurotranslate-0.0/right-plate/results.json'      # the general model's sixth task: the plate under the right foot, after heel strike
RP_METHOD = 'models/neurotranslate-0.0/right-plate/METHOD.md'


def force_checks():
    """The walking-force study and the general model's right-foot plate task (published after the papers): eight assessment walkers
    of a 30/10/10 split, the last ten unopened; on the two plates, the marker transformer below the marker-and-muscle one, better
    with the muscle signals for only two of eight, carrying the current load forward lower still, the muscle rule not met; on the
    right plate, the general model lower with the muscle signals than without (five of eight walkers), the straight-line fit with
    them lower still, carrying the current plate reading forward lowest, both rules not met, and the design fixed before the
    assessment walkers' force or muscle values were inspected."""
    w = load(WF)
    m = {k: v['MAE_N'] for k, v in w['metrics'].items()}
    assert w['held_people'] == 8 and w['held_trials'] == 17
    assert m['current-plate-persistence'] < m['transformer-markers'] < m['transformer-combined'] == min(v for k, v in m.items() if k not in ('current-plate-persistence', 'transformer-markers')), m
    inc = w['incremental_EMG_comparisons']['transformer-markers']
    assert inc['people_better'] == 2 and inc['pass'] is False and w['incremental_EMG_gate_passed'] is False, inc
    proto = json.dumps(load('models/walking-force/protocol.json'), ensure_ascii=False)
    assert 'First 30 train, next 10 assess after the entire fit seal, last 10 remain unopened.' in proto
    r = load(RP)
    f = r['full']['mean_absolute_error_N']
    assert r['full']['people'] == 8 and r['full']['trials'] == 16
    assert f['combined_ridge'] < f['combined_shared'] < f['marker_shared'], f
    pf = r['privileged_past_force']['mean_absolute_error_N']
    assert pf['current_plate'] == min(pf.values()), pf
    c = {x['other']: x for x in r['paired_contrasts_N']}
    assert c['marker_shared']['wins'] == 5 and c['marker_shared']['people'] == 8
    assert r['incremental_emg_gate'] is False and r['frozen_representation_gate'] is False
    assert "Both this design and its comparisons are fixed before inspecting the ten assessment people's force or EMG values." in (REPO / RP_METHOD).read_text(encoding='utf-8')
    log('walking force: muscle signals raised the marker transformer\'s error, helped two of eight, rule not met; right plate: general model lower with muscle '
        'signals (five of eight), straight-line fit lower still, current plate reading lowest, both rules not met, design fixed before inspection',
        file=WF + '; ' + RP + '; ' + RP_METHOD, field='metrics/*/MAE_N; incremental_EMG_comparisons; full; privileged_past_force; paired_contrasts_N; *_gate', full=None)
    return ''


WL = 'models/walking-landmarks/results.json'                  # six skin markers of a walker 200 ms ahead, with and without the right leg's muscles
WL_PLAN = 'models/walking-landmarks/protocol.json'
PM = 'models/neurotranslate-0.0/point-motion/results.json'     # the general model's seventh task: one skin marker, tried at 46 places it was not fitted on
PM_PLAN = 'models/neurotranslate-0.0/point-motion/PROTOCOL.md'
CA = 'models/neurotranslate-0.0/cued-arm/results.json'         # the general model's eighth task: three sensors of an arm after a picture cue
CA_PLAN = 'models/neurotranslate-0.0/cued-arm/PROTOCOL.md'
CE = 'models/cue-elbow/scores.json'                            # the elbow after the cue, with and without scalp electrode C3
CE_PLAN = 'models/cue-elbow/protocol.json'


def landmark_checks():
    """The six-marker walking study (models/walking-landmarks/, published after the papers): ten walkers, the assessment group of the
    walking dataset's 30/10/10 split, already studied for other outcomes, the last ten unopened; 200 ms ahead from 40 frames; the
    straight-line fit on the markers lowest of the fitted models; the muscle signals a little better for the transformer (within the
    noise, six of ten walkers) and a little worse for the straight-line fit; another walk's muscle signals worse than the right ones;
    neither rule set in advance passed."""
    d = load(WL)
    a = {k: v['mean_mm'] for k, v in d['all_anchors'].items()}
    cov = d['coverage']
    assert cov['planned_people'] == 10 and cov['planned_trials'] == 30 and cov['scored_cutoffs'] == cov['possible_cutoffs'] == 1220
    assert a['ridge_markers'] == min(a.values()), a
    assert a['ridge_markers'] < a['ridge_combined'] < a['transformer_combined'] < a['transformer_markers'] < a['velocity'] < a['phase'] < a['persistence'], a
    c = d['combined_transformer_minus_comparator']
    t = c['transformer_markers']
    assert t['mean_mm'] < 0 and t['ci95_mm'][0] < 0 < t['ci95_mm'][1] and t['walkers_improved'] == 6 and t['walkers_compared'] == 10 and t['passes'] is False, t
    assert c['wrong_emg']['mean_mm'] < 0 and c['wrong_emg']['ci95_mm'][1] < 0 and c['wrong_emg']['coverage']['cutoffs'] == 815
    assert d['gates'] == {'incremental_emg': False, 'transformer_advantage': False}, d['gates']
    plan = load(WL_PLAN)
    assert 'Ordinals 1-30 fit, 31-40 assess (previously studied for other outcomes), 41-50 unopened.' in plan['source']
    assert d['clock'].startswith('20 stored 100 Hz frames; 200 ms') and 'shape (40,8,3)' in plan['input'] and 'eight right-leg channels' in plan['input']
    assert d['landmarks'] == ['L_FAL', 'R_FAL', 'L_FLE', 'R_FLE', 'L_RSP', 'R_RSP'], d['landmarks']     # both outer ankles, outer knees, thumb sides of the wrists
    log('six markers: straight-line fit on markers lowest; muscle signals a little better for the transformer (range through zero, 6 of 10), a little worse '
        'for the straight-line fit; wrong walk\'s muscle signals worse; both rules failed; walkers 31-40, studied before, 41-50 unopened', file=WL + '; ' + WL_PLAN,
        field='coverage; all_anchors/*/mean_mm; combined_transformer_minus_comparator/{transformer_markers,wrong_emg}; gates; source; input; clock', full=None)
    return ''


def point_motion_checks():
    """The general model's seventh task (models/neurotranslate-0.0/point-motion/): one marker's nine positions, 50 ms apart, and its
    movement 200 ms later; a new final step on the fixed shared part, fitted at six places on 30 walkers; on 46 other places of ten
    walkers who had appeared in earlier walking studies, the look-up of similar training paths lowest, then the shuffled shared part,
    the straight-line fit and the trained shared part, all far below the latest speed; the rule set for a gain from the shared part failed."""
    d = load(PM)
    g = d['groups']['other_46']
    m = {k: v['endpoint_error_mm'] for k, v in g['modes'].items()}
    assert g['coverage']['people'] == 10 and g['coverage']['trials'] == 30 and g['coverage']['sites'] == 46, g['coverage']
    assert m['radial'] < m['shuffled'] < m['linear'] < m['shared'] < m['velocity'] < m['previous'] < m['stationary'], m
    assert g['advantage_gate'] is False and d['groups']['fit_6']['advantage_gate'] is False and d['overall_advantage_gate'] is False
    tr = d['training']
    assert tr['training_people'] == 30 and tr['training_walks'] == 90 and sorted(tr['sites_fitted']) == sorted(d['training_sites']) and len(d['training_sites']) == 6
    assert len(set(d['assessment_sites']) - set(d['training_sites'])) == 46 and d['horizon_ms'] == 200
    plan = (REPO / PM_PLAN).read_text(encoding='utf-8')
    for s in ('Take nine positions of a single reflective skin marker, one every 50 milliseconds.', 'The model receives no marker name',
              'Assessment participants also appeared in earlier, distinct walking experiments.', 'fixed 24-wide, four-head, one-block NeuroTranslate temporal encoder'):
        assert s in plan, s
    log('one marker: look-up of training paths < shuffled shared part < straight-line fit < trained shared part < latest speed, on 46 untried places of 10 walkers '
        'seen in earlier walking studies; rule for the shared part failed', file=PM + '; ' + PM_PLAN,
        field='groups/other_46/{coverage,modes,advantage_gate}; training; training_sites; assessment_sites; horizon_ms', full=None)
    return ''


def cued_arm_checks():
    """The general model's eighth task (models/neurotranslate-0.0/cued-arm/): one person, 126 trials in three runs, each run scored by
    a version fitted on the other two; no EEG; the cue lowered the shared model's error in all three runs and passed its rule, but a
    model given only the cue did best, keeping the last reading, the straight-line fit with the cue and the shuffled shared part were
    all closer than the shared model with the cue, and the rule for a gain from the shared part failed."""
    d = load(CA)
    m = d['balanced_standardized_mae']
    assert d['people'] == 1 and d['eligible_trials'] == 126 and len(d['held_runs']) == 3 and all(r['test_trials'] == 42 for r in d['held_runs'])
    assert m['cue'] == min(m.values()) and m['cue'] < m['still'] < m['cue_motion'] < m['shuffled_cue_motion'] < m['shared_cue_motion'] < m['motion'] < m['shared_motion'] < m['wrong_cue'], m
    c = d['contrasts']
    assert c['shared_motion']['runs_with_lower_error'] == 3 and c['shared_motion']['pass'] is True and c['wrong_cue']['pass'] is True
    assert d['consistent_cue_advantage'] is True and d['pretrained_encoder_advantage'] is False
    assert d['horizon_after_cutoff_s'] == [0.5, 1.0, 1.5] and d['channels'] == ['elbow', 'forearm rotation', 'index near'] and len(d['cues']) == 7
    plan = (REPO / CA_PLAN).read_text(encoding='utf-8')
    assert 'This experiment uses no EEG.' in plan and 'existing frozen 24-wide one-block NeuroTranslate encoder' in plan
    assert 'Divide the 32 most recent samples, up to and including that index, into four successive eight-sample bins.' in plan and 'Each mechanical channel is sampled at 64 Hz.' in plan
    log('cued arm: cue alone < no change < straight-line fit with cue < shuffled shared part < shared part with cue < without cue; cue rule passed in all three runs, '
        'shared-part rule failed; one person, 126 trials, no EEG', file=CA + '; ' + CA_PLAN,
        field='people; eligible_trials; held_runs; balanced_standardized_mae; contrasts; consistent_cue_advantage; pretrained_encoder_advantage', full=None)
    return ''


def elbow_checks():
    """The elbow study (models/cue-elbow/): 36 trials of one person, each run scored by a fit on the other two; scalp electrode C3 added
    to the cue and the elbow's recent readings raised the error, another trial's C3 did slightly better than the right one, the eye
    channels worse still; the rule failed (better in one run of three, in neither cue group); the attention extra, secondary in the plan,
    was lowest overall and higher than the cue and elbow alone on the bending trials."""
    d = load(CE)
    m = d['balanced_mae']
    assert d['pooled']['n'] == 36 and all(f['held_n'] == 12 and f['fit_n'] == 24 for f in d['folds']) and len(d['folds']) == 3
    assert m['temporal_attention'] < m['cue_mechanics'] < m['cue_median'] < m['persistence'] < m['shifted_c3'] < m['cue_mechanics_c3'] < m['cue_mechanics_eog'], m
    dec = d['decision']
    assert dec['incremental_c3_gate_passed'] is False and dec['runs_c3_beats_mechanics'] == 1 and dec['cue_groups_c3_beats_mechanics'] == 0, dec
    f = d['by_cue']['flexion']['mae']
    assert f['temporal_attention'] > f['cue_mechanics']
    plan = load(CE_PLAN)
    assert 'Only S1 right-arm motor execution runs 1,2,3.' in plan['source'] and plan['signal'].startswith('One-based channel 28 C3')
    assert 'Attention is a secondary architecture comparison and cannot rescue the primary decision.' in plan['decision']
    log('elbow: C3 raised the error; another trial\'s C3 slightly lower; eye channels worst; rule failed (1 run of 3, 0 cue groups); attention lowest overall, '
        'higher on flexion, secondary in the plan; one person, 36 trials', file=CE + '; ' + CE_PLAN,
        field='pooled/n; folds; balanced_mae; decision; by_cue/flexion/mae; source; signal; decision (plan)', full=None)
    return ''


def signal_heading():
    """Heading of the studies page's first group of newer studies, which asks whether a brain or muscle signal helps a forecast that
    already knows the recent movement. Each entry's main comparison, with the signal against without: worse on average for nine of
    eleven (the cortical-reach study, carried 21 November, is the eleventh); the two that came out lower on average failed the rule
    set for them in advance."""
    m = {k: v['mean_mm'] for k, v in load(WL)['all_anchors'].items()}
    up = {
        'wtrack-neural-motion': walk(load(WT), 'metrics/ridge_combined/mean_trip_error_cm') > walk(load(WT), 'metrics/ridge_motion/mean_trip_error_cm'),
        'cortical-glove': walk(load(FG), 'scores/aligned/macro_normalized_mae') > walk(load(FG), 'scores/motion_cue/macro_normalized_mae'),
        'finger-motion': walk(load(FM), 'scores/ridge_aligned/macro_normalized_mae') > walk(load(FM), 'scores/ridge_cue/macro_normalized_mae'),
        'finger-transfer': walk(load(FT), 'cohort_mean_scaled_mae/ridge_aligned') > walk(load(FT), 'cohort_mean_scaled_mae/ridge_cue'),
        'walking-force': walk(load(WF), 'metrics/transformer-combined/MAE_N') > walk(load(WF), 'metrics/transformer-markers/MAE_N'),
        'cue-elbow': walk(load(CE), 'balanced_mae/cue_mechanics_c3') > walk(load(CE), 'balanced_mae/cue_mechanics'),
        'population-motion': walk(load(POP), 'equal_rat/combined') > walk(load(POP), 'equal_rat/motion'),
        'walking-landmarks': m['transformer_combined'] > m['transformer_markers'],
        'scalp-forecast': walk(load(SF), 'methods/scalp/normalized_mae') > walk(load(SF), 'methods/history/normalized_mae'),
        'visual-balance': all(load(VB)['primary']['methods']['full']['marker_error_mm'][i] > load(VB)['primary']['methods']['no_scalp']['marker_error_mm'][i] for i in (0, 1)),
        'cortical-reach': walk(load(CXR), 'subsets/matched/models/transformer_all/mean/euclidean') > walk(load(CXR), 'subsets/matched/models/transformer_movement_cue/mean/euclidean'),
    }
    down = sorted(k for k, v in up.items() if not v)
    assert down == ['population-motion', 'walking-landmarks'], down
    assert load(POP)['consistent_gain'] is False and load(WL)['gates']['incremental_emg'] is False
    n_up = sum(up.values())
    log(f'{n_up} of {len(up)}', file='; '.join((WT, FG, FM, FT, WF, CE, POP, WL, SF, VB, CXR)), field='each entry\'s main comparison, with the signal against without', full=None,
        note='lower with the signal: ' + ', '.join(down) + ' (population-motion consistent_gain false; walking-landmarks gates/incremental_emg false)')
    return (f'Brain and muscle signals made {spell(n_up)} of these {spell(len(up))} forecasts worse on average, and the {spell(len(down))} small gains '
            'failed the tests set for them in advance')


GA = 'models/neurotranslate-0.0/arm-transfer/results.json'      # the general model's arm task refitted on seven people, scored on five new ones
GA_PLAN = 'models/neurotranslate-0.0/arm-transfer/PROTOCOL.md'
AT = 'models/arm-transfer/assessment-summary.json'               # a small transformer trained for the same task, frozen and scored on the same five
AT_PLAN = 'models/arm-transfer/PROTOCOL.md'


def arm_transfer_checks():
    """The arm task across people (published after the papers): the general model's readouts refitted on S1-S7 (882 trials) and
    scored on S8-S12 (630 trials, 15 runs), whose files were opened only after the protocol, code and fitted model were sealed; it
    beat the one-person fit for all five and the cue helped (both rules passed), but the fitting group's median change for each cue
    was lowest and beat it for all five, no change and the shuffled copy were lower too, and the rule for the shared part failed; after
    one earlier run, the correction lowered the later-run error for all five but the person's own median change did better and that
    rule failed; the task-trained transformer, frozen the same way, was behind the mean change for each cue and no change."""
    d = load(GA)
    assert d['training']['eligible_people'] == 7 and d['training']['eligible_trials'] == 882
    assert d['assessment']['eligible_people'] == 5 and d['assessment']['eligible_trials'] == 630 and d['assessment']['eligible_runs'] == 15
    u = d['unseen_person']
    m = {k: v['standardized_mae'] for k, v in u['models'].items()}
    assert m['cue_median'] == min(m.values()), m
    assert m['still'] < m['shared_cue_motion'] < m['s1_shared_cue_motion'] and m['shuffled_cue_motion'] < m['shared_cue_motion'] < m['shared_motion'] < m['wrong_cue'], m
    c = u['comparisons']
    assert c['s1_shared_cue_motion']['people_improved'] == 5 and c['s1_shared_cue_motion']['pass'] is True
    assert c['shared_motion']['pass'] is True and c['wrong_cue']['pass'] is True and c['cue_median']['people_improved'] == 0
    assert u['passes'] == {'pooled_vs_s1': True, 'cue': True, 'encoder': False}, u['passes']
    a = d['after_first_run']
    am = {k: v['standardized_mae'] for k, v in a['models'].items()}
    assert a['coverage']['trials'] == 420 and am['personal_median'] < am['cue_median'] < am['calibrated_shared'] < am['shared_cue_motion'], am
    assert a['comparisons']['shared_cue_motion']['people_improved'] == 5 and a['passes'] is False
    plan = (REPO / GA_PLAN).read_text(encoding='utf-8')
    assert 'Before accessing even the headers of S8–S12, seal this protocol, executable fit and evaluation logic, parent and fitted checkpoints' in plan
    assert 'allocates S1–S7 to fitting, S8–S12 to assessment and S13–S15 to reserve' in plan
    t = load(AT)
    s = {k: v['score'] for k, v in t['summary']['methods'].items()}
    assert t['n'] == 630 and t['n_people'] == 5 and s['cue'] < s['still'] < s['transformer'] < m['shared_cue_motion'], (s, m['shared_cue_motion'])
    assert t['summary']['criteria'] == {'cue_contribution': True, 'attention_architecture': False, 'net_benefit': False} and t['summary']['overall_advantage'] is False
    assert 'Freeze weights, scoring code and evaluation rules before opening S8–S12' in (REPO / AT_PLAN).read_text(encoding='utf-8')
    log('arm across people: general model beat its one-person fit for all 5 and the cue helped; group median per cue lowest, beat it for all 5; no change and the '
        'shuffled copy lower too; shared-part rule failed; first-run correction helped all 5, own median better, rule failed; task-trained transformer behind '
        'the mean per cue and no change; S8-S12 opened after sealing', file=GA + '; ' + GA_PLAN + '; ' + AT + '; ' + AT_PLAN,
        field='training; assessment; unseen_person/{models,comparisons,passes}; after_first_run; summary/methods/*/score; summary/criteria', full=None)
    return ''


SF = 'models/scalp-forecast/assessment-summary.json'               # a small transformer on the fourth runs of the five new arm people, with and without six scalp electrodes
SF_RESULTS = 'models/scalp-forecast/RESULTS.md'
SR = 'models/neurotranslate-0.0/scalp-residual/results.json'      # the general model's correction to the usual change for each cue, with the same scalp electrodes
SR_README = 'models/neurotranslate-0.0/scalp-residual/README.md'


def scalp_checks():
    """The scalp study (published after the papers): the fourth runs of the five assessment people of the arm study (210 trials),
    unopened until both models were frozen, their first three runs scored before; the transformer's error almost the same with the
    six scalp electrodes (lower for three of five), the eye channels worse, the usual change for each cue lowest (closer for four of
    five) and both its rules failed; the general model's correction a little lower with the scalp electrodes (two of five), the usual
    change for each cue between the two, the eye and joint models higher, both its rules failed."""
    s = load(SF)
    m = {k: v['normalized_mae'] for k, v in s['methods'].items()}
    assert s['n_people'] == 5 and s['n_trials'] == 210 and s['stage'] == 'fourth_run'
    assert m['cue_median'] == min(m.values()) and m['history'] < m['scalp'] < m['eye'] < m['still'], m
    c = s['contrasts']
    assert c['scalp_over_history']['people_lower'] == 3 and c['scalp_over_history']['gate'] is False and c['scalp_over_cue_median']['people_lower'] == 1
    assert s['gates'] == {'engineering_advantage': False, 'increment_beyond_measured_eyes': False}, s['gates']
    r = load(SR)
    g = r['groups']['all']
    q = {k: v['scaled_mae'] for k, v in g['models'].items()}
    assert r['assessment']['people'] == 5 and r['assessment']['trials'] == 210 and r['fit']['people'] == 7 and r['fit']['trials'] == 882
    assert q['scalp'] < q['cue_median'] < q['mechanics'] < q['eye'] < q['joint'], q
    k = g['comparisons']
    assert k['scalp_vs_mechanics']['improved'] == 2 and k['scalp_vs_mechanics']['pass'] is False and k['scalp_vs_cue_median']['pass'] is False
    assert r['primary_tests'] == {'scalp': False, 'joint': False}, r['primary_tests']
    readme = (REPO / SR_README).read_text(encoding='utf-8')
    assert 'These fourth recordings were kept unopened until both the shared and separate Transformer models were frozen.' in readme
    assert 'The same five assessment people previously supplied their first three runs for a mechanical forecast.' in readme
    log('scalp: transformer the same with and without (3 of 5 lower), eye worse, cue median lowest (4 of 5), both rules failed; general model a little lower with '
        'scalp (2 of 5), cue median between, eye and joint higher, both rules failed; fourth runs unopened until frozen, earlier runs scored before',
        file=SF + '; ' + SR + '; ' + SR_README, field='methods/*/normalized_mae; contrasts; gates; groups/all/{models,comparisons}; primary_tests', full=None)
    return ''


CF = 'models/cervical-forecast/assessment.json'                     # the neck-voltage study: six new people, a transformer and a robust straight-line correction
CF_DEV = 'models/cervical-forecast/development.json'
CF_README = 'models/cervical-forecast/README.md'
CF_PAGE = 'docs/cervical-forecast/index.html'
CR = 'models/neurotranslate-0.0/cervical/assessment-summary.json'  # the same robust correction, as the general model's program runs it
CR_README = 'models/neurotranslate-0.0/cervical/README.md'
CR_PREDICT = 'models/neurotranslate-0.0/predict.py'


MM = 'models/muscle-and-motion/assessment-summary.json'               # leg muscles and the sacrum in one model: a joint transformer against two specialists
MM_DEV = 'models/muscle-and-motion/development-summary.json'
MM_README = 'models/muscle-and-motion/README.md'
MM_SOURCE = 'models/muscle-and-motion/source/README.md'
ML = 'models/neurotranslate-0.0/muscle_motion/historical.json'        # straight-line fits on the same rotations, run by the general model's program
ML_MODEL = 'models/neurotranslate-0.0/muscle_motion/model.json'
ML_README = 'models/neurotranslate-0.0/muscle_motion/README.md'
ML_DESIGN = 'models/neurotranslate-0.0/muscle_motion/DESIGN.md'


def mm_checks():
    """The muscle-and-motion study (published after the papers). People stood on and walked along a beam while the view in a headset
    rotated; from 160 samples (625 ms) of eight lower-leg muscle voltages and a sacrum marker, the posture and the rotation's direction,
    forecast each muscle's amplitude (RMS, µV) and the marker's 32 positions (mm) over the next 125 ms. One transformer learned both, two
    of the same kind each learned one. 18 people fitted (5,179 rotations); 6 others, 1,759 rotations (879 standing, 880 walking), whose
    walking recordings an earlier study of the dataset had examined. The specialists were a little closer on both; the rule (the joint
    model better on both) failed; both transformers beat holding the last amplitude and continuing the recent movement. Swapping in another
    rotation's leg voltages made the joint forecast worse on both. The general model's program fits straight lines with coefficients of
    their own (no parent_sha256): the pooled fit was behind holding the last amplitude on the muscles and behind both transformers;
    started from the walking fit, the standing fit did worse than one fitted on the same standing examples alone. The transformer's
    walking start against a fresh start on standing: both intervals cross zero."""
    a = load(MM)
    _ci95_crosses_zero = lambda x: x['ci95'][0] < 0 < x['ci95'][1]
    tc = a['transformer_and_controls']
    j, s, hv = (tc[k]['scores'] for k in ('joint', 'specialists', 'hold_velocity16'))
    assert (tc['joint']['people'], tc['joint']['events']) == (6, 1759) and a['primary_joint_advantage'] is False
    assert s['muscle_mae_uv'] < j['muscle_mae_uv'] < hv['muscle_mae_uv'] and s['path_mean_distance_mm'] < j['path_mean_distance_mm'] < hv['path_mean_distance_mm']
    d = a['contrasts']['joint_minus_specialists']['differences']
    assert d['muscle_mae_uv']['mean'] > 0 and _ci95_crosses_zero(d['muscle_mae_uv']) and d['path_mean_distance_mm']['ci95'][0] > 0
    sw = a['wrong_event']['swapped_minus_factual']['differences']
    assert sw['muscle_mae_uv']['ci95'][0] > 0 and sw['path_mean_distance_mm']['ci95'][0] > 0 and a['wrong_event']['eligible_recipient_events'] == 1759
    st = a['standing_transfer']
    assert st['scores']['stand_640']['events'] == 879
    af = st['contrasts']['adapt_full_minus_stand_640']['differences']
    assert _ci95_crosses_zero(af['muscle_mae_uv']) and _ci95_crosses_zero(af['path_mean_distance_mm'])
    dev = load(MM_DEV)
    assert (dev['people'], dev['events']) == (18, 5179)
    h = load(ML)
    m = h['primary']['methods']
    assert (h['primary']['people'], h['primary']['events'], h['postures']['standing']['events'], h['postures']['walking']['events']) == (6, 1759, 879, 880)
    assert m['persistence']['emg_mae_uv'] < m['pooled']['emg_mae_uv'] and m['pooled']['path_error_mm'] < m['persistence']['path_error_mm']
    assert j['muscle_mae_uv'] < m['pooled']['emg_mae_uv'] and j['path_mean_distance_mm'] < m['pooled']['path_error_mm']
    assert abs(m['persistence']['emg_mae_uv'] - hv['muscle_mae_uv']) < 1e-9          # the same "hold the last amplitude" in both studies
    sm = h['postures']['standing']['methods']
    assert sm['stand_limited']['emg_mae_uv'] < sm['adapted_walk']['emg_mae_uv'] and sm['stand_limited']['path_error_mm'] < sm['adapted_walk']['path_error_mm']
    assert h['postures']['standing']['adapted_minus_comparator']['stand_limited']['both_primary_upper_negative'] is False
    assert 'parent_sha256' not in load(ML_MODEL)
    assert 'This is a regularized linear benchmark alongside the separate joint Transformer.' in (REPO / ML_DESIGN).read_text(encoding='utf-8')
    assert 'Earlier work examined the six assessment participants’ walking recordings for a different outcome. Their standing recordings and the muscle and path targets were new to this study.' in (REPO / MM_SOURCE).read_text(encoding='utf-8')
    assert 'The six assessment people came from an older evaluation of walking and head movement in this dataset.' in (REPO / MM_README).read_text(encoding='utf-8')
    log('specialists closer on both; rule failed; both transformers ahead of holding the last amplitude and continuing the movement', file=MM,
        field='transformer_and_controls/{joint, specialists, hold_velocity16}/scores; contrasts/joint_minus_specialists; primary_joint_advantage', full=None,
        note='joint 9.499 µV / 1.965 mm; specialists 9.453 / 1.940; hold and continue 10.274 / 2.304; muscle difference interval across zero, path difference above zero')
    log('the straight-line fits run by the general model\'s program, with coefficients of their own', file=ML_MODEL, field='no parent_sha256', full=None,
        note='pooled 10.696 µV / 2.120 mm, behind holding the last amplitude on the muscles (10.274); walking start 6.134 / 0.867 against 6.063 / 0.844 from the same standing examples alone')
    return ''


XL = 'models/cross-limb-movement/scores.json'                         # a lifting wrist and a balancing body: one small transformer against two that each learn one
XL_DEV = 'models/cross-limb-movement/development.json'
XL_RESULTS = 'models/cross-limb-movement/RESULTS.md'
XL_EXPERIMENT = 'models/cross-limb-movement/EXPERIMENT.md'
XL_SOURCE = 'models/cross-limb-movement/source/README.md'
XC = 'models/neurotranslate-0.0/cross_limb/historical.json'           # straight-line fits on the same lifts and rotations, run by the general model's program
XC_MODEL = 'models/neurotranslate-0.0/cross_limb/model.json'
XC_README = 'models/neurotranslate-0.0/cross_limb/README.md'
XC_DESIGN = 'models/neurotranslate-0.0/cross_limb/DESIGN.md'


def xl_checks():
    """The wrist-and-sacrum study (published after the papers). Two datasets of different people: light-cued lifts (WAY-EEG-GAL: a
    tracker on the right wrist, electrodes over five muscles of the right arm and hand, three or four usable in each test lift) and
    standing or walking on a beam while the view in a headset rotated (Peterson and Ferris: a marker on the sacrum, four muscles of
    each lower leg). From 625 ms of both, a small transformer forecasts the marker's 32 positions and each muscle's amplitude over the
    next 125 ms. One learned both tasks (384 training steps, 192 on each); its comparisons each learned one, either on the same 192
    steps of their own task or for all 384. Fitted on 18 balance people (5,179 rotations) and 6 lifting people (1,764 lifts); scored on
    6 others (1,759 rotations) and 3 others (882 lifts), all nine already scored by earlier studies for other questions. Wrist path:
    the joint model closer than the 192-step model for all three people, behind the 384-step model for all three. Sacrum path: behind
    both separate models for all six. Muscles: the separate models closer in all four comparisons, only one of them outside the
    noise. The rule (all four upper bounds below zero) failed against both. Continuing the marker's last speed beat the joint model on
    the sacrum, not on the wrist; on the leg muscles holding the last strength was between the separate models and the joint one. The
    general model's program fits straight lines with coefficients of their own (no parent_sha256): learning both studies made the
    sacrum worse and the wrist a little better than learning one; every transformer closer than every one of them."""
    a = load(XL)
    lo, up = a['lower'], a['upper']

    def sc(d, m):
        return d['methods'][m]['scores']

    assert (lo['methods']['joint']['people'], lo['methods']['joint']['events'], up['methods']['joint']['people'], up['methods']['joint']['events']) == (6, 1759, 3, 882)
    assert a['joint_advantage'] == {'specialist': False, 'specialist-total': False}
    j, s1, s2, v = (sc(up, m) for m in ('joint', 'specialist', 'specialist-total', 'persistence-linear'))
    assert s2['path_mean_distance_mm'] < j['path_mean_distance_mm'] < s1['path_mean_distance_mm'] < v['path_mean_distance_mm']
    c1 = up['contrasts']['joint minus specialist']['differences']['path_mean_distance_mm']
    c2 = up['contrasts']['joint minus specialist-total']['differences']['path_mean_distance_mm']
    assert c1['ci95'][1] < 0 and c1['people_lower'] == 3 and c2['ci95'][0] > 0 and c2['people_lower'] == 0
    J, S1, S2, V = (sc(lo, m) for m in ('joint', 'specialist', 'specialist-total', 'persistence-linear'))
    assert S1['path_mean_distance_mm'] < S2['path_mean_distance_mm'] < V['path_mean_distance_mm'] < J['path_mean_distance_mm']
    for k in ('specialist', 'specialist-total'):
        c = lo['contrasts']['joint minus ' + k]['differences']['path_mean_distance_mm']
        assert c['ci95'][0] > 0 and c['people_lower'] == 0, k
    outside = []
    for dom, d in (('lower', lo), ('upper', up)):
        for k in ('specialist', 'specialist-total'):
            assert sc(d, k)['muscle_mae'] < sc(d, 'joint')['muscle_mae'], (dom, k)
            c = d['contrasts']['joint minus ' + k]['differences']['muscle_mae']
            if not c['ci95'][0] < 0 < c['ci95'][1]:
                outside.append((dom, k))
    assert outside == [('upper', 'specialist-total')], outside
    assert S1['muscle_mae'] < S2['muscle_mae'] < V['muscle_mae'] < J['muscle_mae']          # legs: holding the last strength between them
    assert max(j['muscle_mae'], s1['muscle_mae'], s2['muscle_mae']) < v['muscle_mae']       # arm: every transformer ahead of holding it
    assert up['strict_complete_input_count'] == 0 and up['strict_complete']['joint']['people'] == 0
    dev = load(XL_DEV)
    assert (dev['lower']['methods']['joint']['people'], dev['lower']['methods']['joint']['events'],
            dev['upper']['methods']['joint']['people'], dev['upper']['methods']['joint']['events']) == (18, 5179, 6, 1764)
    res = (REPO / XL_RESULTS).read_text(encoding='utf-8')
    for s in ('All nine were outside these fits and had already appeared in earlier assessments of other targets.',
              'The joint fit improved the wrist path over the shorter specialist in each of three people, then lost that advantage against the longer specialist in all three.',
              'All six balance participants had greater sacrum path error with the joint fit than either specialist.',
              'A comparison across all five arm muscles was impossible because the original authors reported electrode faults in every historical arm participant.'):
        assert s in res, s
    exp = (REPO / XL_EXPERIMENT).read_text(encoding='utf-8')
    for s in ('Its 384 updates expose it to 9,216 sampled events per study. A 192-update single-study fit sees exactly the same 9,216 target draws, in the same order.',
              'A 384-update specialist continues from that same state with its optimizer intact to see 18,432 target draws.',
              'The input covers the 625 milliseconds up to the forecast.', 'The 32 future marker positions are 1/256 second apart.'):
        assert s in exp, s
    src = (REPO / XL_SOURCE).read_text(encoding='utf-8')
    assert 'For the hand, the cutoff is 400 ms after the reach light.' in src and 'The upper five are the right anterior deltoid, brachioradialis, flexor digitorum, common extensor digitorum and first dorsal interosseous.' in src
    h = load(XC)['domains']
    b, g = h['balance']['methods'], h['grasp_lift']['methods']
    assert (h['balance']['people'], h['balance']['events'], h['grasp_lift']['people'], h['grasp_lift']['events']) == (6, 1759, 3, 882)
    assert b['leg']['mean_path_mm'] < b['pooled']['mean_path_mm'] and g['pooled']['mean_path_mm'] < g['arm']['mean_path_mm']
    assert max(J['path_mean_distance_mm'], S1['path_mean_distance_mm'], S2['path_mean_distance_mm']) < min(b['leg']['mean_path_mm'], b['pooled']['mean_path_mm'])
    assert max(j['path_mean_distance_mm'], s1['path_mean_distance_mm'], s2['path_mean_distance_mm']) < min(g['arm']['mean_path_mm'], g['pooled']['mean_path_mm'])
    assert 'parent_sha256' not in load(XC_MODEL) and sorted(load(XC_MODEL)) == ['fits', 'means', 'version']
    assert 'This complementary baseline is separate from the trainable cross-study Transformer.' in (REPO / XC_DESIGN).read_text(encoding='utf-8')
    assert 'The 882 lifts contributed three or four channels apiece.' in (REPO / XC_README).read_text(encoding='utf-8')
    log('wrist path: joint closer than the 192-step wrist model (all 3 people), behind the 384-step one (all 3); sacrum path: joint behind '
        'both balance models (all 6); muscles: separate models closer in all four, one outside the noise; rule failed against both', file=XL,
        field='{lower,upper}/methods/{joint,specialist,specialist-total,persistence-linear}/scores; contrasts/joint minus *; joint_advantage', full=None,
        note='wrist 4.870 / 5.100 / 4.394 mm, last-speed 8.391; sacrum 2.169 / 1.962 / 1.981 mm, last-speed 2.041; legs 10.279 / 10.272 / 10.273 µV, hold 10.274')
    log('the straight-line fits run by the general model\'s program, with coefficients of their own', file=XC_MODEL, field='keys version, fits, means; no parent_sha256', full=None,
        note='sacrum: both studies 3.387 mm, balance alone 2.521; wrist: both 7.365, lifts alone 7.698; every transformer closer')
    return ''


XM = 'models/cross-limb-movement/path-maps/scoring/results.json'      # the follow-up: a separate output map for each body part, against one blended map
XM_DESIGN = 'models/cross-limb-movement/path-maps/DESIGN.md'
XM_PROTOCOL = 'models/cross-limb-movement/path-maps/scoring/PROTOCOL.md'
XM_NOTE = 'models/cross-limb-movement/path-maps.md'


def xm_checks():
    """The output-map follow-up of the wrist-and-sacrum study (published after the papers). The joint transformer's last step, which
    turns its final state into a path, is either one map per body part (A for the sacrum, B for the wrist) or the same two maps blended
    by forecast time; both models have 3,975 numbers. Scored only on the development people (18 balance, 5,179 rotations; 6 lifting,
    1,764 lifts), each by a fit on the other folds, three seeds. The separate maps: pelvis path closer for all 18 people (interval
    below zero), only to the level of continuing the last 31.25 ms of the marker's speed, and both balance-only models closer still;
    wrist path unchanged (interval across zero), and the wrist model trained for all 384 steps closer. The rule (all four mean
    differences and upper limits below zero) failed."""
    a = load(XM)
    assert a['all_four_pass'] is False and a['seeds'] == [1641, 2718, 3917]
    b, w = a['studies']['balance'], a['studies']['way']
    assert (b['people'], b['events'], w['people'], w['events']) == (18, 5179, 6, 1764), (b['people'], b['events'], w['people'], w['events'])
    bm, wm = b['methods'], w['methods']

    def p(m, k):
        return m[k]['scores']['path_mean_distance_mm']

    bp = b['primary']['path_mean_distance_mm']
    assert bp['ci95'][1] < 0 and bp['people_lower'] == bp['people'] == 18
    assert 0 < p(bm, 'velocity_exact_31_25ms') - p(bm, 'separate') < 0.001      # "only as far as" continuing the last 31.25 ms of speed
    assert max(p(bm, 'specialist_exposure'), p(bm, 'specialist_steps')) < p(bm, 'separate') < p(bm, 'matched')
    wp = w['primary']['path_mean_distance_mm']
    assert wp['ci95'][0] < 0 < wp['ci95'][1]
    assert p(wm, 'specialist_steps') < min(p(wm, 'separate'), p(wm, 'matched'))
    cp = a['compute']['checkpoints']
    assert cp['separate']['parameters'] == cp['matched']['parameters'] == 3975
    d = (REPO / XM_DESIGN).read_text(encoding='utf-8')
    assert 'This development cohort and previous evaluation cohorts informed design.' in d and 'use A for balance and B for grasp' in d
    assert 'No assessment or reserve arrays, refits, other studies or prospective claims.' in (REPO / XM_PROTOCOL).read_text(encoding='utf-8')
    note = (REPO / XM_NOTE).read_text(encoding='utf-8')
    assert "Each person’s forecasts came from a model trained on other people." in note and 'Both store 3,975 fitted numbers.' in note
    log('output maps: one per body part closer on the pelvis for all 18 development people, only as far as continuing the last 31.25 ms of '
        'speed; balance-only models closer; wrist unchanged, the longer-trained wrist model closer; rule failed', file=XM,
        field='studies/{balance,way}/methods/*/scores/path_mean_distance_mm; studies/*/primary; all_four_pass', full=None,
        note='pelvis 2.582 / 2.645 mm, last 31.25 ms of speed 2.583, balance-only 2.497 and 2.481; wrist 3.878 / 3.877, wrist-only 384 steps 3.686')
    return ''


XS = 'models/cross-limb-movement/scalp/scoring/results.json'      # the second follow-up: three scalp sites given to the joint transformer, against its training averages there
XS_README = 'models/cross-limb-movement/scalp/README.md'
XS_RESULTS = 'models/cross-limb-movement/scalp/scoring/RESULTS.md'
XS_PROTOCOL = 'models/cross-limb-movement/scalp/scoring/PROTOCOL.md'


def xs_checks():
    """The scalp follow-up of the wrist-and-sacrum study (published after the papers). The joint transformer given the signed mean and
    RMS voltage at C3, Cz and C4 (the balance cap's D19, A1, B22), against the same model given the fitting fold's averages in those
    slots, with the same availability flags. Scored only on the development people (18 balance, 5,179 rotations; 6 lifting, 1,764
    lifts), each by a fit that left that person out, three seeds. Wrist path worse for all six; sacrum path worse; leg muscles a little
    better, the one outcome of four whose mean and one-sided upper limit are below zero; arm muscles a tie. The same model fed another
    trial's earlier voltages: the muscle difference's interval crosses zero. Holding each muscle's last amplitude beat the scalp model
    on the leg muscles. Not the general model: no folder of models/neurotranslate-0.0/ changed."""
    a = load(XS)
    assert a['all_four_pass'] is False and a['seeds'] == [1641, 2718, 3917]
    b, w = a['studies']['balance'], a['studies']['way']
    assert (b['people'], b['events'], w['people'], w['events']) == (18, 5179, 6, 1764), (b['people'], b['events'], w['people'], w['events'])
    passed = [(s, k) for s, st in (('balance', b), ('way', w)) for k, v in st['primary'].items() if v['mean'] < 0 and v['upper98_75'] < 0]
    assert passed == [('balance', 'muscle_mae')], passed
    wp, bp, bm = w['primary']['path_mean_distance_mm'], b['primary']['path_mean_distance_mm'], b['primary']['muscle_mae']
    assert wp['people_lower'] == 0 and wp['people'] == 6 and wp['mean'] > 0
    assert bp['mean'] > 0 and bp['people_lower'] == 6 and bm['people_lower'] == 14 and bm['people'] == 18
    wmus = w['primary']['muscle_mae']
    assert wmus['ci95'][0] < 0 < wmus['ci95'][1]                       # "left the arm muscles where they were"
    rb, rw = b['central_minus']['reference'], w['central_minus']['reference']
    assert rw['central']['path_mean_distance_mm'] > rw['comparator']['path_mean_distance_mm']
    assert rb['central']['path_mean_distance_mm'] > rb['comparator']['path_mean_distance_mm']
    assert rb['central']['muscle_mae'] < rb['comparator']['muscle_mae']
    wt = b['central_minus']['wrong_trial']['paired_intervals']['muscle_mae']
    assert wt['ci95'][0] < 0 < wt['ci95'][1]                           # "did as well on the muscles" with another trial's voltages
    v = b['central_minus']['velocity_exact_31_25ms']
    assert v['events'] == rb['events'] and v['central']['muscle_mae'] == rb['central']['muscle_mae']
    assert v['comparator']['muscle_mae'] < rb['central']['muscle_mae']   # holding each muscle's last amplitude beat the scalp model, on the same events
    readme = (REPO / XS_README).read_text(encoding='utf-8')
    assert 'One of the four prespecified outcomes passed its directional threshold.' in readme
    assert 'Scalp voltages mix multiple electrical sources' in readme
    res = (REPO / XS_RESULTS).read_text(encoding='utf-8')
    assert 'All three fits had excluded that person from training.' in res and 'C3, Cz and C4, three nominal positions on the scalp' in res
    assert "The reference model saw the fitting participants’ average feature values in the same measured slots." in res
    assert 'All of these electrical measurements can contain movement-related activity.' in res
    assert 'The intervals describe variation across held development participants' in (REPO / XS_PROTOCOL).read_text(encoding='utf-8')
    log('scalp follow-up: wrist path worse for all 6, sacrum path worse, leg muscles a little better (the one test of four that passed), '
        'as good with another trial\'s voltages; holding each muscle\'s last strength better still', file=XS,
        field='studies/{balance,way}/primary; studies/*/central_minus/{reference,wrong_trial,velocity_exact_31_25ms}/{central,comparator}; all_four_pass', full=None,
        note='wrist 4.120 / 3.905 mm; sacrum 2.699 / 2.667 mm; legs 11.370 / 11.385 µV, hold 11.355; 18 + 6 development people, three seeds')
    return ''


def start_links_all():
    """For the README's words "links to every one of the project's browser pages": every folder under docs/ with an index.html
    (papers and launchers aside, as n_pages() counts them) is linked from the start page's template."""
    tpl = (TEMPLATES / 'docs-START.html').read_text(encoding='utf-8')
    names = _site_pages()
    missing = [n for n in names if f'href="{n}/' not in tpl]
    assert not missing, ('the start page must link every browser page', missing)
    log('every one of the project\'s browser pages', file='tools/front-pages/templates/docs-START.html', field='href="<folder>/…" for each folder of n_pages()',
        full=len(names), note=', '.join(names))
    return ''


def neck_checks():
    """The neck-voltage study (published after the papers): four people's 320 events for fitting, six others' 480 for the test, opened
    after the fits were fixed, each person counted equally. Carrying the last neck reading forward beat the transformer by far; the
    transformer was lower with the right armpit recording than without it but lower still with another pulse's, one of six better than
    both; the robust correction was lowest from the four other sites, higher with the armpit and higher again with another pulse's,
    three of six better than both; neither met its rule. The general model's copy of the correction gives the same numbers, and its
    program reads only the correction's own coefficients for this task."""
    d = load(CF)
    assert d['participants'] == 6 and d['events'] == 480
    dev = load(CF_DEV)
    assert dev['people'] == 4 and dev['events_per_person'] * dev['people'] == 320
    tr, ro = d['transformer'], d['robust']
    m = {k: v['mae_uV'] for k, v in tr['macro'].items()}
    assert m['neck_persistence'] < m['transformer_same_fit_wrong'] < m['transformer_eng'] < m['transformer_noneng'], m
    assert tr['people_improved_on_both'] == 1 and tr['criterion_met'] is False
    r = {k: v['mae_uV'] for k, v in ro['macro'].items()}
    assert r['other_sites'] < r['persistence'] < r['with_axilla'] < r['wrong_event'] and r['other_sites'] == min(r.values()), r
    assert ro['people_improved_on_both'] == 3 and ro['criterion_met'] is False
    g = load(CR)
    assert {k: v['mae_uV'] for k, v in g['macro'].items()} == r and g['people_improved_on_both'] == 3 and g['criterion_met'] is False
    readme = (REPO / CF_README).read_text(encoding='utf-8')
    for s in ('Errors are averaged within each person first.', 'The participants lay still.', '“Biceps” is the label for a **surface nerve recording at the axilla**',
              'The same readout is available in NeuroTranslate 0.0. It has its own coefficients.', 'A surface voltage can mix contributions from several tissues.'):
        assert s in readme, s
    assert 'All fits were fixed before these 480 events were opened.' in (REPO / CF_PAGE).read_text(encoding='utf-8')
    gr = (REPO / CR_README).read_text(encoding='utf-8')
    assert 'The shared command dispatches this measurement to its own trained readout in `cervical/model.json`.' in gr
    assert 'The accompanying movement weights serve their original movement tasks.' in gr
    pr = (REPO / CR_PREDICT).read_text(encoding='utf-8')
    assert 'if record.get("domain") == "cervical_voltage":\n        from cervical.forecast import predict as predict_voltage, read_model\n        model = read_model(Path(checkpoint).parent / "cervical" / "model.json")\n        return predict_voltage(record, model)' in pr
    log('neck: carrying forward beat the transformer; transformer lower with the right armpit recording than without, lower still with another pulse\'s, '
        '1 of 6 better than both, rule failed; robust correction lowest from the four other sites, higher with the armpit, higher again with another '
        'pulse\'s, 3 of 6, rule failed; 4 people / 320 events fitted, 6 / 480 tested after the fits were fixed; general model\'s copy identical, own coefficients',
        file='; '.join((CF, CF_DEV, CF_README, CF_PAGE, CR, CR_README, CR_PREDICT)),
        field='transformer/macro/*/mae_uV; robust/macro/*/mae_uV; */people_improved_on_both; */criterion_met; macro; predict_record', full=None)
    return ''


BR = 'models/back-rotation/assessment.json'                         # a sensor on the back: the transformer trained for the task, on three of four new people
BR_ELIG = 'models/back-rotation/label-eligibility.json'
BR_README = 'models/back-rotation/README.md'
BR_ASSESS = 'models/back-rotation/ASSESSMENT.md'
BR_PROTOCOL = 'models/back-rotation/protocol.json'
BR_PRETEST = 'models/back-rotation/PRETEST-SHA256.json'
BS = 'models/neurotranslate-0.0/back_rotation/assess-summary.json'  # the general model's ninth task, on the same three people
BS_COPY = 'models/back-rotation/shared-assessment.json'
BS_FIT = 'models/neurotranslate-0.0/back_rotation/fit-summary.json'
BS_MODEL = 'models/neurotranslate-0.0/back_rotation/model.json'
BS_DESIGN = 'models/neurotranslate-0.0/back_rotation/DESIGN.md'
BS_WEIGHTS = 'models/neurotranslate-0.0/movement-weights.npz'      # the shared part of the general model, as every one of its tasks loads it
BS_PAGE = 'docs/shared-back-rotation/index.html'


def _sha(rel):
    import hashlib
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def back_checks():
    """The back-sensor study (published after the papers). Four people's two trials each for fitting; four others kept for the test,
    opened only after both models were fixed, but both trials of one of them name three orientation channels and a buffer, so the
    planned four-person test is incomplete and the scores describe the other three (1,152 standing and 1,152 walking forecasts). The
    transformer trained for the task did best from the sensor's turns alone, worse with both grids, about the same with another
    moment's grids, and beat the straight-line fit, carrying the last turn forward, the task's typical turn and no turn. The general
    model (the released shared part, unchanged, with a final step fitted on the same four people) tied a straight-line fit from the
    turns alone at the printed precision, was worse with both grids, behind the straight-line fit and the untrained copy given the
    same grids, and better than carrying the last turn forward."""
    d = load(BR)
    assert d['n_people'] == 3 and d['n_trials'] == 6 and d['planned_people'] == 4 and d['assessment_status'] == 'incomplete'
    assert d['n'] == {'611': 1152, '621': 1152} and d['incremental_gate_passes'] is None
    m = {k: v['balanced'] for k, v in d['mae_deg'].items()}
    assert m['motion'] == min(m.values()), m
    assert m['motion'] < m['lower'] < m['upper'] < m['ridge_motion'] < m['wrong'] < m['full'] < m['constant_speed'] < m['task_median'] < m['zero'], m
    e = load(BR_ELIG)
    assert e['qualified_people'] == 3 and e['planned_people'] == 4
    bad = sorted(k for k, v in e['labels'].items() if 'BufferChannel[A.U.]' in v)
    assert len(bad) == 2 and len({k.split('/')[0] for k in bad}) == 1, bad
    assert all(v == [f'Quaternion ({i})[A.U]' for i in range(1, 5)] for k, v in e['labels'].items() if k not in bad)
    s = load(BS)
    assert s == load(BS_COPY)
    g = {k: v['mae_deg'] for k, v in s['balanced'].items()}
    assert s['people'] == 3 and s['windows'] == 2304 and s['planned_people'] == 4 and s['assessment_status'] == 'incomplete' and s['practical_criterion'] is None
    assert round(g['shared_motion'], 3) == round(g['linear_motion'], 3) and abs(g['shared_motion'] - g['linear_motion']) < 0.0005, g
    assert g['shared_motion'] < g['linear_full'] < g['random_full'] < g['shared_full'] < g['wrong_full'] < g['recent'] < g['task_median'] < g['zero'], g
    assert s['contrasts']['shared_motion']['people_improved'] == 0 and s['contrasts']['linear_full']['people_improved'] == 1
    assert abs(g['recent'] - m['constant_speed']) < 1e-12 and abs(g['zero'] - m['zero']) < 1e-12      # the same two simple forecasts in both studies
    assert load(BS_FIT)['people'] == 4 and set(load(BR_PROTOCOL)['split']['development']) == {'S01', 'S02', 'S03', 'S05'}
    assert load(BS_MODEL)['parent_sha256'] == _sha(BS_WEIGHTS)
    design = (REPO / BS_DESIGN).read_text(encoding='utf-8')
    assert 'Use every original spatial backbone parameter from the released NeuroTranslate movement weights (project, position, self-attention, feedforward, normalization), kept fixed.' in design
    pre = load(BR_PRETEST)['sha256']
    assert pre[BS_MODEL] == _sha(BS_MODEL) and pre[BS_DESIGN] == _sha(BS_DESIGN) and pre[BS_WEIGHTS] == _sha(BS_WEIGHTS)
    readme = (REPO / BR_README).read_text(encoding='utf-8')
    for x in ('Four volunteers supplied two trials each for training. Four others supplied two trials each for the planned tests.',
              "One person's files label the four orientation rows as quaternion components 2, 3, 4 and a buffer.",
              'Both original four-person tests therefore remain incomplete.', 'A turn of one degree to the left or the right has the same size.',
              'Their signals can include muscle, heart activity and movement of the electrodes.'):
        assert x in readme, x
    assert 'Both model families had fixed weights, preprocessing, scoring rules and controls before records from four other people were opened.' in (REPO / BR_ASSESS).read_text(encoding='utf-8')
    log('back sensor: transformer best from the turns alone, worse with both grids, about the same with another moment\'s grids, ahead of the straight-line fit, '
        'the last turn carried forward, the typical turn and no turn; general model tied a straight-line fit from the turns alone, worse with both grids, behind '
        'the straight-line fit and the untrained copy with the same grids; 4 fitting people; 4 test people opened after both models were fixed, 1 without a '
        'verified orientation channel, planned test incomplete, 3 scored; the shared part is the released movement weights, unchanged and pinned before the test',
        file='; '.join((BR, BR_ELIG, BR_README, BR_ASSESS, BR_PROTOCOL, BR_PRETEST, BS, BS_FIT, BS_MODEL, BS_DESIGN)),
        field='mae_deg/*/balanced; labels; balanced/*/mae_deg; contrasts; parent_sha256; sha256', full=None)
    return ''


MT = 'models/muscle-tracking/assessment.json'                        # a shin muscle bundle in ultrasound: the transformer trained for the task, four new people
MT_PROTOCOL = 'models/muscle-tracking/PROTOCOL.md'
MT_PRETEST = 'models/muscle-tracking/PRETEST-SHA256.json'
MT_README = 'models/muscle-tracking/README.md'
MS = 'models/neurotranslate-0.0/muscle_tracking/assess-summary.json'  # the general model's tenth task, on the same four people
MS_FIT = 'models/neurotranslate-0.0/muscle_tracking/fit-summary.json'
MS_MODEL = 'models/neurotranslate-0.0/muscle_tracking/model.json'
MS_DESIGN = 'models/neurotranslate-0.0/muscle_tracking/DESIGN.md'
MS_PAGE = 'docs/shared-muscle-tracking/index.html'


def muscle_checks():
    """The shin-muscle study (published after the papers). Four people fitted, four others opened only after both models were sealed
    (776 forecasts, every candidate window). The transformer trained for the task was a little closer with the bundle's angle than
    without (three of four people) and further off with another recording's angles (all four), but a straight-line fit on the lengths
    alone beat both, and the rule for the angle failed. The general model (the released shared part, unchanged, with a final step
    fitted on the same four people) was closer with the angle than without but behind straight-line fits with and without the angle,
    the untrained copy given both was between, and every learned model beat repeating the last change, the geometric estimate, the
    typical change and no change; its rule for the angle failed."""
    a = load(MT)
    assert a['people'] == 4 and a['trials'] == 8 and a['eligible_windows'] == a['candidate_windows'] == 776
    m = a['mae_mm']
    assert m['ridge'] < m['full'] < m['length'] < m['recent'] < m['wrong'] < m['projection'] < m['typical'] < m['zero'], m
    c = a['comparisons']
    assert c['full_vs_length']['people_improved'] == 3 and c['full_vs_wrong']['people_improved'] == 4 and a['pennation_increment_supported'] is False
    assert a['study'] == 'Four previously unseen people, two distinct recordings each. All weights fixed.'
    s = load(MS)
    g = {k: v['mae_mm'] for k, v in s['scores'].items()}
    assert s['people'] == 4 and s['windows'] == 776 and s['paired_angle_criterion'] is False
    assert g['linear_both'] < g['linear_length'] < g['shared_both'] < g['random_both'] < g['shared_length'] < g['wrong_both'] < g['recent'] < g['geometry'] < g['typical'] < g['hold'], g
    assert abs(g['recent'] - m['recent']) < 1e-12 and abs(g['hold'] - m['zero']) < 1e-12        # the same simple forecasts in both studies
    assert load(MS_FIT)['people'] == 4 and load(MS_MODEL)['parent_sha256'] == _sha(BS_WEIGHTS)
    assert '(projection, positions, attention, MLP and normalization all frozen)' in (REPO / MS_DESIGN).read_text(encoding='utf-8')
    pre = load(MT_PRETEST)
    assert pre['scope'].startswith('Before any of the four assessment participants’ files were opened')
    assert all(pre['sha256'][k] == _sha(k) for k in (MS_MODEL, MS_DESIGN, BS_WEIGHTS))
    assert 'Train on A01–A04, leave each development person out in turn, then refit all four. A05–A08 may be assessed once by a separate owner after the final fit, scorer and source seals.' in (REPO / MT_PROTOCOL).read_text(encoding='utf-8')
    assert 'NeuroTranslate 0.0' in (REPO / MS_PAGE).read_text(encoding='utf-8')
    log('shin muscle: transformer a little closer with the angle (3 of 4) and further with another recording\'s (4 of 4), straight-line fit on lengths beat both, '
        'angle rule failed; general model closer with the angle, behind straight-line fits with and without it, untrained copy between, angle rule failed; every '
        'learned model ahead of repeating the last change, the geometric estimate, the typical change and no change; 4 fitted, 4 opened after sealing, 776 forecasts',
        file='; '.join((MT, MT_PROTOCOL, MT_PRETEST, MS, MS_FIT, MS_MODEL, MS_DESIGN)), field='mae_mm; comparisons; scores/*/mae_mm; parent_sha256; sha256', full=None)
    return ''


PL = 'models/pedal-load/assessment.json'                            # a fixed pedal: the transformer trained for the task, the qualified trials of two new people
PL_README = 'models/pedal-load/README.md'
PL_PRETEST = 'models/pedal-load/PRETEST-SHA256.json'
PS = 'models/neurotranslate-0.0/pedal_load/assess-summary.json'      # the general model's eleventh task, on the same trials
PS_README = 'models/neurotranslate-0.0/pedal_load/README.md'
PS_DESIGN = 'models/neurotranslate-0.0/pedal_load/DESIGN.md'
PS_MODEL = 'models/neurotranslate-0.0/pedal_load/model.json'
PS_FIT = 'models/neurotranslate-0.0/pedal_load/fit-summary.json'
PS_PAGE = 'docs/shared-pedal-load/index.html'
PEDAL_GROUPS = ('complete', 'other_angle5', 'other_angle0')            # one new person's four trials; the other's two angle5 trials; the other's one usable angle0 trial
SIMPLE_PS = ('hold', 'recent', 'setting_median', 'relaxation_setting', 'linear_load')   # the general model's simpler comparisons that do not see the muscle


def pedal_checks():
    """The fixed-pedal study (published after the papers). Two people fitted; two others kept for the test, opened after the models were
    fixed; one of their eight trials has two columns named as the load channel and no verified clock, so the planned two-person test is
    incomplete, and the seven qualified trials are described in three groups (one person's four trials; the other's two angle5 trials;
    the other's one usable angle0 trial). The general model, from the pedal's own readings and the setting, beat every simpler forecast in
    all three groups, and the muscle signal made it worse in all three. The transformer trained for the task was better with the muscle
    signal for the first person (and beat every simpler forecast there) and worse with it in both of the other person's groups."""
    s = load(PS)
    assert s['assessment_status'] == 'incomplete' and s['original_planned_people'] == 2 and s['full_roster_gates'] is None
    assert s['qualified_trials'] == 7 and s['qualified_windows'] == 446 and tuple(s['groups']) == PEDAL_GROUPS
    assert [s['groups'][g]['people'] for g in PEDAL_GROUPS] == [1, 1, 1] and [s['groups'][g]['trials'] for g in PEDAL_GROUPS] == [4, 2, 1]
    for g in PEDAL_GROUPS:
        b = {k: v['mae'] for k, v in s['groups'][g]['scores']['balanced'].items()}
        assert b['shared_load'] < min(b[k] for k in SIMPLE_PS), (g, b)
        assert b['shared_both'] > b['shared_load'], (g, b)
    a = load(PL)
    assert a['assessment_status'] == 'incomplete' and a['qualified_trials'] == 7 and tuple(a['groups']) == PEDAL_GROUPS
    m = {g: {k: v['mae'] for k, v in a['groups'][g]['scores']['balanced'].items()} for g in PEDAL_GROUPS}
    simple = ('zero', 'continue', 'typical', 'typical_condition', 'ridge_load', 'ridge_condition')
    assert m['complete']['full'] < m['complete']['load_condition'] and m['complete']['full'] < min(m['complete'][k] for k in simple)
    assert m['other_angle5']['full'] > m['other_angle5']['load_condition'] and m['other_angle0']['full'] > m['other_angle0']['load_condition']
    assert load(PS_FIT)['people'] == 2 if 'people' in load(PS_FIT) else True
    assert load(PS_MODEL)['parent_sha256'] == _sha(BS_WEIGHTS)
    design = (REPO / PS_DESIGN).read_text(encoding='utf-8')
    assert 'Use A01 and A02 for development, A03 and A04 only for assessment after the models, source handling and scoring are sealed.' in design
    assert 'Encoder models append the last hidden vector from the original 24-wide frozen shared movement Transformer' in design
    gr = (REPO / PS_README).read_text(encoding='utf-8')
    assert 'The model was fixed before the assessment, and no person or trial replaced the missing comparison.' in gr
    assert 'one neutral trial contained two columns labelled as the right load channel, with no verified 1 kHz clock for either' in gr
    assert load(PL_PRETEST)['scope'] == 'Two development people. After the weights and methods were frozen, the other two people supplied a separate assessment. All four contributed to Task 1.'
    assert 'NeuroTranslate 0.0' in (REPO / PS_PAGE).read_text(encoding='utf-8')
    log('pedal: general model from the pedal\'s readings and setting beat every simpler forecast in all 3 groups, worse with the muscle signal in all 3; transformer '
        'better with the muscle signal for the first new person (and ahead of every simpler forecast), worse for the other in both groups; 2 fitted, 2 opened after '
        'the models were fixed, 7 of 8 trials qualified, planned test incomplete', file='; '.join((PS, PL, PL_PRETEST, PS_MODEL, PS_DESIGN, PS_README)),
        field='groups/*/scores/balanced/*/mae; assessment_status; parent_sha256', full=None)
    return ''


HF = 'models/heel-and-force/aggregate.json'                          # heel and plate in the same step: a joint transformer against two specialists
HF_README = 'models/heel-and-force/README.md'
HF_PROTOCOL = 'models/heel-and-force/source/protocol.json'
HF_PRETEST = 'models/heel-and-force/PRETEST-SHA256.json'
HF_PAGE = 'docs/heel-and-force/index.html'
HS = 'models/neurotranslate-0.0/heel_force/historic-assessment-summary.json'   # the general model's twelfth task, on the same moments
HS_LATER = 'models/neurotranslate-0.0/heel_force/later-repeats-summary.json'
HS_FIT = 'models/neurotranslate-0.0/heel_force/fit-summary.json'
HS_MODEL = 'models/neurotranslate-0.0/heel_force/model.json'
HS_README = 'models/neurotranslate-0.0/heel_force/README.md'
HS_DESIGN = 'models/neurotranslate-0.0/heel_force/DESIGN.md'
HS_PAGE = 'docs/shared-heel-and-force/index.html'


def _ci_crosses_zero(d):
    lo, hi = d['participant_bootstrap_95']
    return lo < 0 < hi


def heel_checks():
    """The heel-and-force study (published after the papers). Walkers on force plates; from 24 camera frames of a heel and a forefoot
    marker, the time since the heel struck and eight right-leg muscle signals, forecast the heel marker's displacement and the plate's
    upward load 100 ms later. A transformer that learns both at once against two that each learn one. Scored on 53 moments in 16 walks
    by 8 people kept out of fitting, all previously used in other studies, and on 31 moments in 10 later walks by 6 of them. The joint
    transformer was a little closer than the specialists on both outcomes, both intervals crossing zero (its rule failed); a
    straight-line fit on the markers and timing forecast the heel better, and carrying forward the plate's current reading forecast the
    load better than every method. The muscle signals passed neither test. The general model (its movement encoder frozen, output
    layers fitted): the compressed output layer and the unrestricted one both behind a straight-line fit on the heel and behind a
    straight-line fit given the same signals on the load; carrying the plate's reading forward best; both of its rules failed."""
    a = load(HF)
    for part, people, repeats, rows in (('historical-primary', 8, 16, 53), ('historical-supplement', 6, 10, 31)):
        p = a[part]
        m = p['models']
        assert (m['joint']['heel_mm']['people'], m['joint']['heel_mm']['repeats'], m['joint']['heel_mm']['rows']) == (people, repeats, rows), part
        assert m['joint']['heel_mm']['mean'] < m['heel']['heel_mm']['mean'] and m['joint']['force_N']['mean'] < m['force']['force_N']['mean'], part
        assert _ci_crosses_zero(p['joint_minus']['heel']['heel_mm']) and _ci_crosses_zero(p['joint_minus']['force']['force_N']), part
        assert p['joint_over_specialists'] is False and p['emg_increment'] == {'heel_mm': False, 'force_N': False}, part
        if part == 'historical-primary':      # on the later walks the joint transformer was a little closer than this fit (1.024 against 1.072 mm)
            assert m['ridge_marker']['heel_mm']['mean'] < m['joint']['heel_mm']['mean'], part
        forces = {k: v['force_N']['mean'] for k, v in m.items() if v['force_N'] is not None and k != 'wrong_emg'}
        assert min(forces, key=forces.get) == 'privileged_hold', (part, forces)
    assert 'All historic assessment people are previously used in other studies.' in load(HF_PROTOCOL)['prior_exposure']
    assert load(HF_PRETEST)['scope'].startswith('This public extract identifies both fitted model families. The original joint fit manifest was sealed before the separate assessments.')
    hr = (REPO / HF_README).read_text(encoding='utf-8')
    assert 'The models were frozen before scoring the original assessment walks. Eight people from that previously used cohort supplied 53 eligible instants in 16 recordings.' in hr
    assert '| Ridge regression, markers and timing |' in hr and 'It can read the force plate before the cutoff.' in hr
    assert 'Ten others had already appeared in earlier assessments. A separate reserve of ten people remains unopened.' in (REPO / HF_PAGE).read_text(encoding='utf-8')
    for rel, people, rows in ((HS, 8, 53), (HS_LATER, 6, 31)):
        s = load(rel)
        assert (s['main']['people'], s['main']['windows']) == (people, rows), rel
        h = s['main']['methods']
        shared = ('encoder_full_rank2', 'encoder_full_unrestricted')
        assert all(h['linear_motion']['heel_error_mm'] < h[k]['heel_error_mm'] for k in shared), rel
        assert min(h, key=lambda k: h[k]['force_error_n']) == 'force_hold', rel
        assert s['rank_two_adequacy']['both_pass'] is False and s['emg_advantage']['both_pass'] is False, rel
    h = load(HS)['main']['methods']
    assert all(h['linear_full']['force_error_n'] < h[k]['force_error_n'] for k in ('encoder_full_rank2', 'encoder_full_unrestricted'))
    assert load(HS_MODEL)['parent_sha256'] == _sha(BS_WEIGHTS)
    assert 'The movement encoder released before this experiment remains frozen.' in (REPO / HS_DESIGN).read_text(encoding='utf-8')
    assert 'The movement encoder stays fixed.' in (REPO / HS_README).read_text(encoding='utf-8')
    assert 'NeuroTranslate 0.0' in (REPO / HS_PAGE).read_text(encoding='utf-8')
    log('heel and plate: joint transformer a little closer than the two specialists on both outcomes in both assessments, every interval '
        'crossing zero, rule failed; straight-line fit on markers and timing closer on the heel; carrying the plate reading forward closest on '
        'the load; muscle signals passed neither test; 8 people previously used in other studies, 53 moments, then 6 of them, 31 moments; '
        'general model: compressed and unrestricted output layers behind a straight-line fit on the heel and (first assessment) behind a '
        'straight-line fit given the same signals on the load, plate reading carried forward best, both rules failed',
        file='; '.join((HF, HF_PROTOCOL, HF_PRETEST, HS, HS_LATER, HS_MODEL, HS_DESIGN)),
        field='historical-*/models/*/{heel_mm,force_N}/mean; joint_minus; joint_over_specialists; emg_increment; main/methods/*; parent_sha256', full=None)
    return ''


VB = 'models/visual-balance/assessment-summary.json'                 # balance on a beam after the view rotates: a transformer with and without the scalp
VB_README = 'models/visual-balance/README.md'
VB_SOURCE = 'models/visual-balance/source/README.md'
VB_LIN = 'models/visual-balance/linear-comparison.json'
VB_PAGE = 'docs/visual-balance/index.html'
VB_PAPER = 'docs/papers/visual-balance/index.html'
VS = 'models/neurotranslate-0.0/visual_balance/historical.json'        # the general model's fourteenth task, on the same rotations
VS_DEV = 'models/neurotranslate-0.0/visual_balance/development.json'
VS_MODEL = 'models/neurotranslate-0.0/visual_balance/model.json'
VS_README = 'models/neurotranslate-0.0/visual_balance/README.md'
VS_DESIGN = 'models/neurotranslate-0.0/visual_balance/DESIGN.md'
VS_PAGE = 'docs/visual-balance-controls/index.html'


def _beaten_balance():
    g = {k: v['endpoint_mm'] for k, v in load(VS)['all']['methods'].items()}
    assert all(g['linear_motion'][i] < g['shared_full'][i] and g['linear_motion'][i] < g['shared_nuisance'][i] for i in (0, 1))
    return False


def balance_checks():
    """The visual-balance study (published after the papers). People walked heel to toe on a beam while the view in a headset rotated;
    from 160 samples (0.625 s) of a head and a sacrum marker, the rotation's direction and summaries of scalp, eye, neck and leg voltages,
    forecast both markers' movement over the next 125 ms. Seventeen people fitted; six others, of a dataset the project had not used, whose
    files were opened only after the models and scoring were sealed. The transformer: closer at both markers when fitted without the scalp,
    and its rule failed; it beat a straight-line fit that also had the scalp. A straight-line fit on the movement and the rotation's direction
    alone beat every method, the general model and the transformer included. The general model: worse with the scalp than without at both."""
    a = load(VB)['primary']
    assert (a['rows'], a['people'], a['training_people_in_score']) == (880, 6, 0) and a['marker_pass'] == [False, False] and a['joint_pass'] is False
    m = {k: v['marker_error_mm'] for k, v in a['methods'].items()}
    assert all(m['full'][i] > m['no_scalp'][i] for i in (0, 1)) and all(m['wrong'][i] > m['full'][i] for i in (0, 1))
    assert all(x < 0 for x in load(VB_LIN)['comparisons']['transformer_full_minus_linear_full']['mean_mm'])
    s = load(VS)['all']
    assert (s['people'], s['events']) == (6, 880) and load(VS_DEV)['all']['people'] == 17
    g = {k: v['endpoint_mm'] for k, v in s['methods'].items()}
    for i in (0, 1):
        assert min(g, key=lambda k: g[k][i]) == 'linear_motion', i
        assert g['linear_motion'][i] < m['full'][i] and g['linear_motion'][i] < m['no_scalp'][i]
        assert g['shared_full'][i] > g['shared_nuisance'][i]
    _beaten_balance()
    assert load(VS_MODEL)['parent_sha256'] == _sha(BS_WEIGHTS)
    assert 'The models and scoring rules were sealed before the assessment files were opened.' in (REPO / VB_PAGE).read_text(encoding='utf-8')
    assert 'No additional participant signals were inspected by this fitter before this design.' in (REPO / VS_DESIGN).read_text(encoding='utf-8')
    assert 'The first 17 join development, the next six form the assessment group, and the last six stay in reserve.' in (REPO / VB_SOURCE).read_text(encoding='utf-8')
    assert 'NeuroTranslate 0.0' in (REPO / VS_PAGE).read_text(encoding='utf-8')
    log('balance on a beam: transformer closer at both markers without the scalp, rule failed; straight-line fit on movement and direction '
        'closest of every method, transformer and general model included; general model worse with the scalp than without at both; 17 '
        'fitted, 6 opened after sealing, 880 rotations', file='; '.join((VB, VB_LIN, VS, VS_DEV, VS_MODEL, VS_DESIGN, VB_PAGE)),
        field='primary/methods/*/marker_error_mm; marker_pass; all/methods/*/endpoint_mm; parent_sha256', full=None)
    return ''


WI = 'models/walking-instructions/assessment-summary.json'            # two walking instructions: a transformer with and without the instruction
WI_README = 'models/walking-instructions/README.md'
WI_LIN = 'models/walking-instructions/linear-comparison.json'
WI_DEV = 'models/walking-instructions/development-summary.json'
WI_SOURCE = 'models/walking-instructions/source/README.md'
WC = 'models/neurotranslate-0.0/walking_cues/historical.json'         # the general model's thirteenth task, on the same walks
WC_DEV = 'models/neurotranslate-0.0/walking_cues/development.json'
WC_MODEL = 'models/neurotranslate-0.0/walking_cues/model.json'
WC_README = 'models/neurotranslate-0.0/walking_cues/README.md'
WC_PAGE = 'docs/walking-instruction-controls/index.html'


def walk_checks():
    """The walking-instructions study (published after the papers). People walked barefoot "as usual" or "fast but not running"; from 21
    frames (200 ms) of the pelvis and right heel, the time since the right heel struck and the instruction, forecast both landmarks 100 ms
    later. Ten people kept out of fitting, already studied in earlier work, 60 walks, 216 moments. The transformer: with the instruction a
    little closer at the pelvis and a little further at the heel than the same model trained without it, both intervals crossing zero, so
    the test failed; the opposite instruction made both worse; it beat a straight-line fit given the instruction at both landmarks. The
    general model: closer with the instruction than without it and than with the opposite one, at both landmarks, passing its test on these
    ten people and failing it in development; closer than straight-line fits with and without the instruction; a copy whose shared part was
    left untrained, given the instruction, closer still; the transformer closer than all of them."""
    a = load(WI)
    assert (a['people'], a['trials'], a['windows'], a['paired_people']) == (10, 60, 216, 10)
    m = {k: v['endpoint_mm'] for k, v in a['results']['both']['models'].items()}
    assert m['cue'][0] < m['withheld'][0] and m['cue'][1] > m['withheld'][1]
    d = a['results']['both']['cue_minus']['withheld']['ci95_mm']
    assert d[0][0] < 0 < d[0][1] and d[1][0] < 0 < d[1][1]
    assert all(m['swapped'][i] > m['cue'][i] for i in (0, 1)) and a['passes_both_context_controls_pelvis_heel'] == [False, False]
    lin = load(WI_LIN)['comparisons']['transformer_cue_minus_linear_cue']['ci95_mm']
    assert lin[0][1] < 0 and lin[1][1] < 0
    g = {k: v['endpoint_mm'] for k, v in load(WC)['methods'].items()}
    assert load(WC)['people'] == 10 and load(WC)['windows'] == 216
    for i in (0, 1):
        assert g['encoder_cue'][i] < g['encoder_motion'][i] and g['encoder_cue'][i] < g['swapped_encoder'][i]
        assert g['encoder_cue'][i] < g['linear_cue'][i] and g['encoder_cue'][i] < g['linear_motion'][i]
        assert g['random_cue'][i] < g['encoder_cue'][i] and m['cue'][i] < g['random_cue'][i]
    assert load(WC)['cue_test']['encoder_cue'] == {'passes_pelvis_heel': [True, True], 'beats_all_simple_means_pelvis_heel': [True, True]}
    assert load(WC_DEV)['cue_test']['encoder_cue']['passes_pelvis_heel'] == [False, False] and load(WC_DEV)['people'] == 30
    assert load(WC_MODEL)['parent_sha256'] == _sha(BS_WEIGHTS)
    assert 'The historical participants had already been used in earlier studies.' in (REPO / WC_README).read_text(encoding='utf-8')
    assert 'The ten assessment people had appeared in earlier movement studies.' in (REPO / WI_README).read_text(encoding='utf-8')
    assert 'NeuroTranslate 0.0' in (REPO / WC_PAGE).read_text(encoding='utf-8')
    log('walking instructions: transformer with the instruction a little closer at the pelvis, a little further at the heel than without it, '
        'both intervals crossing zero, test failed; opposite instruction worse at both; ahead of a straight-line fit given the instruction; '
        'general model closer with the instruction than without or with the opposite one at both landmarks, test passed on these ten people, '
        'failed in development; ahead of straight-line fits; untrained copy with the instruction closer; transformer closest; ten people '
        'already studied, 60 walks, 216 moments', file='; '.join((WI, WI_LIN, WC, WC_DEV, WC_MODEL)),
        field='results/both/models/*/endpoint_mm; cue_minus; methods/*/endpoint_mm; cue_test; parent_sha256', full=None)
    return ''


GENERAL_FITS = {   # every task folder of the general model -> who it was scored on; read a new folder's own files before classifying it
    'right-plate': 'unseen',          # 8 walkers; its design fixed before anyone inspected their force or muscle recordings (METHOD.md)
    'arm-transfer': 'unseen',         # 5 people, opened only after the plan, the code and the fitted model were sealed (PROTOCOL.md)
    'back_rotation': 'unseen',        # 4 people kept for the test (3 scorable), opened after the fit was fixed (PRETEST-SHA256.json)
    'muscle_tracking': 'unseen',      # 4 people, opened after the fit was sealed (PRETEST-SHA256.json)
    'visual_balance': 'unseen',       # 6 people of a dataset not used before; models and scoring sealed before their files were opened
    'pedal_load': 'unseen',           # 2 people, opened after the fit was fixed (README.md)
    'knee': 'seen',                   # 12 walkers whose earlier forecasts were already known
    'load': 'seen',                   # 3 walkers whose angles an earlier comparison had used
    'point-motion': 'seen',           # 10 walkers already studied for other questions
    'cued-arm': 'seen',               # one person's three runs, each scored by a fit on the other two
    'scalp-residual': 'seen',         # unopened fourth runs of the five arm-task people, whose first three runs had been scored
    'population': 'seen',             # previously examined test recordings of three rats
    'forearm': 'seen',                # the six people studies 1 to 3 were fitted on
    'heel_force': 'seen',             # the earlier test walkers of the same dataset, "previously used in other studies"
    'walking_cues': 'seen',           # the same ten-person test group, "already used in earlier studies" (its README)
    'cervical': 'not the general model',   # a straight-line correction with coefficients of its own (neck_checks())
    'muscle_motion': 'not the general model',   # straight-line fits with coefficients of their own, no parent_sha256 (mm_checks())
    'first_use_body': 'not the general model',  # landmark predictor with its own fitted geometry weights
    'next_neuron_prediction': 'not the general model',  # shared coefficients fitted to sorted spike histories

    'cross_person_wrist': 'not the general model',   # dedicated optical fits; see the task's README and synthetic-fit.json
    'bilateral_wrist': 'not the general model',   # a transformer per wrist with weights of its own; the movement checkpoint has no role (hw_checks())
    'cross_limb': 'not the general model',      # straight-line fits with coefficients of their own, no parent_sha256 (xl_checks())
    'wrist-source': 'not a task',          # the source recordings of the wrist-angle task
}


def _beaten_right_plate():
    rp = load(RP)['full']['mean_absolute_error_N']
    assert rp['combined_ridge'] < rp['combined_shared']
    return False


def _beaten_arm():
    u = {k: v['standardized_mae'] for k, v in load(GA)['unseen_person']['models'].items()}
    assert u['cue_median'] < u['shared_cue_motion'] and u['still'] < u['shared_cue_motion']
    return False


def _tied_back():
    back_checks()
    g = {k: v['mae_deg'] for k, v in load(BS)['balanced'].items()}
    assert round(g['shared_motion'], 3) == round(g['linear_motion'], 3) and g['linear_full'] < g['shared_full']
    return False


def _beaten_shin():
    muscle_checks()
    h = {k: v['mae_mm'] for k, v in load(MS)['scores'].items()}
    assert h['linear_length'] < h['shared_length'] and h['linear_both'] < h['shared_both']
    return False


def _won_pedal():
    pedal_checks()          # from the pedal's own readings ahead of every simpler forecast in all three groups; worse with the muscle signal
    return True


UNSEEN = {   # each test on unseen people -> a function that asserts its result and returns True if the general model beat every simpler forecast
    'right-plate': _beaten_right_plate, 'arm-transfer': _beaten_arm, 'back_rotation': _tied_back, 'muscle_tracking': _beaten_shin,
    'pedal_load': _won_pedal, 'visual_balance': lambda: _beaten_balance(),
}
TIMES = {0: 'never', 1: 'once', 2: 'twice'}
_unseen_cache = []


def _unseen():
    if not _unseen_cache:
        folders = {p.name for p in (REPO / 'models' / 'neurotranslate-0.0').iterdir() if p.is_dir()}
        assert folders == set(GENERAL_FITS), ('classify every task folder of the general model in GENERAL_FITS, after reading its files',
                                              sorted(folders ^ set(GENERAL_FITS)))
        unseen = sorted(k for k, v in GENERAL_FITS.items() if v == 'unseen')
        assert unseen == sorted(UNSEEN), ('every test on unseen people needs its result asserted in UNSEEN', unseen, sorted(UNSEEN))
        wins = [k for k in unseen if UNSEEN[k]()]
        n = len(unseen)
        heading = (f'The general model has had its first runs, and in {spell(n)} tests on unseen people it beat simpler forecasts '
                   f'{TIMES.get(len(wins), spell(len(wins)) + " times")}')
        assert GENERAL_HEADING == heading, ('GENERAL_HEADING must say', heading)
        _unseen_cache.append((n, wins))
    return _unseen_cache[0]


def _unseen_log(printed, what, full):
    n, wins = _unseen()
    log(printed, file='models/neurotranslate-0.0/*/ (each task folder classified in GENERAL_FITS); ' + '; '.join((RP, GA, BS, MS, PS)),
        field=what, full=full,
        note=f'tests on people nobody had looked at when the test was fixed: {", ".join(sorted(UNSEEN))}; beat every simpler forecast in: '
             f'{", ".join(wins)}; right foot: beaten; arm on five new people: beaten; back sensor on three new people: tied from the turns alone '
             f'(0.376 each), beaten with the grids; shin muscle on four new people: beaten with and without the angle; fixed pedal on two new '
             f'people (incomplete): ahead of every simpler forecast from the pedal\'s readings, worse with the muscle signal; balance on a beam, six '
             f'new people: a straight-line fit on the movement and the rotation\'s direction beat it, with and without the scalp')


def unseen_count(cap=False):
    """How many times the general model has been scored on people nobody had looked at when the test was fixed (GENERAL_FITS, UNSEEN)."""
    n, _ = _unseen()
    _unseen_log(spell(n, cap), 'tests of the general model on unseen people', n)
    return spell(n, cap)


def unseen_lost(cap=False):
    """Of those tests, how many a simpler forecast matched or beat."""
    n, wins = _unseen()
    _unseen_log(spell(n - len(wins), cap), 'tests on unseen people in which a simpler forecast matched or beat the general model', n - len(wins))
    return spell(n - len(wins), cap)


def unseen_won(*folders):
    """The words that name the general model's wins on unseen people (the pedal) are true only while these are exactly its wins."""
    _, wins = _unseen()
    assert sorted(wins) == sorted(folders), (wins, folders)
    _unseen_log(TIMES.get(len(wins), spell(len(wins))), 'tests on unseen people in which it beat every simpler forecast: ' + ', '.join(wins), len(wins))
    return TIMES.get(len(wins), spell(len(wins)) + ' times')


_U = []


def U(folder, group='list'):     # noqa: N802  (marks one test named in a page's list or sentence of the tests on unseen people)
    assert GENERAL_FITS.get(folder) == 'unseen', folder
    _U.append((PAGE[0], group, folder))
    return ''


def unseen_list_check(group='list'):
    """A page's list (or sentence) of the tests on unseen people names each test in the table once, and no other."""
    got = sorted(f for p, g, f in _U if p == PAGE[0] and g == group)
    assert got == sorted(UNSEEN), (PAGE[0], group, got)
    _unseen_log(str(len(got)), f'tests named in "{group}" on {PAGE[0]}', len(got))
    return ''


def unseen_check():
    """For the general-model heading and the sentences that count its tests on unseen people: the table above, every result asserted."""
    _unseen()
    n, wins = _unseen()
    _unseen_log(f'in {spell(n)} tests on unseen people it beat simpler forecasts {TIMES.get(len(wins), spell(len(wins)) + " times")}', 'the heading', None)
    return ''


def general_tasks(cap=False):
    """How many tasks the general model has: the options of its shared page (shared_tasks()) and the back-sensor, shin-muscle, pedal and
    heel-and-force tasks, which have pages of their own and load the same shared part, unchanged (their checks assert the checkpoint's hash)."""
    n = len(SHARED_TASKS) + 6
    balance_checks()
    shared_tasks()
    back_checks()
    muscle_checks()
    pedal_checks()
    heel_checks()
    walk_checks()
    assert 'NeuroTranslate 0.0' in (REPO / BS_PAGE).read_text(encoding='utf-8')
    log(spell(n, cap), file='docs/shared-motion/src/panel.html; ' + BS_MODEL + '; ' + MS_MODEL + '; ' + PS_MODEL + '; ' + HS_MODEL + '; ' + WC_MODEL + '; ' + VS_MODEL,
        field='options of select#history-select, and the back-sensor, shin-muscle, fixed-pedal, heel-and-force, walking-instruction and visual-balance tasks (parent_sha256 = sha256 of ' + BS_WEIGHTS + ')', full=n)
    return spell(n, cap)


SHARED_TASKS = ['wrist', 'wrist_angle', 'cued_arm_change', 'marker_displacement', 'right_plate_force', 'knee_moment', 'knee_angle', 'rat']


def shared_tasks(cap=False):
    """How many tasks the general model's page offers: the options of its "What should the model forecast?" list, read from the page's
    source, which must be the eight the pages describe (distance for a wrist and for a rat, wrist angles, both knees, the knees' turning
    moments, the right-foot plate, one marker and the cued arm)."""
    rel = 'docs/shared-motion/src/panel.html'
    html = (REPO / rel).read_text(encoding='utf-8')
    block = re.search(r'<select id="history-select"[^>]*>(.*?)</select>', html, flags=re.S).group(1)
    vals = re.findall(r'<option value="([^"]+)"', block)
    assert vals == SHARED_TASKS, vals
    built = (REPO / 'docs/shared-motion/index.html').read_text(encoding='utf-8')
    assert all(f'<option value="{v}"' in built for v in vals), 'the built page offers the same tasks'
    log(spell(len(vals), cap), file=rel, field='options of select#history-select', full=len(vals), note=', '.join(vals))
    return spell(len(vals), cap)


def shifted_words_check():
    """For the README's words "when the task changed, or the person had to follow a new force level shown on a screen": of the
    shifted settings, one is study 17 (a new task) and the rest are the pinch studies' new force levels (21 to 23)."""
    s = LEDGER['counts']['shifted_settings']['settings']
    assert s[0] == '17' and all(x.split('-')[0] in ('21', '22', '23') and x.split('-')[1] in ('10', '50') for x in s[1:]), s
    log('a new task, or a new force level shown on a screen', file=LEDGER_FILE, field='counts/shifted_settings/settings', full=None,
        note=', '.join(s) + ' (17: new task; 21 to 23 at 10% and 50%: force levels other than the 30% the model was fitted at)')
    return ''


# ---------------------------------------------------------------------------------------------------
NAMESPACE = {k: v for k, v in globals().items() if not k.startswith('_')}


# Pages left without the note at the top, and why. The two pages of the paper edition are pinned by the edition's
# manifest.json and copied byte for byte into the papers' download ZIP, whose checksum is published; a plain-text file
# would show the note as text.
NO_NOTE = {
    'papers-current-README.md': 'pinned by papers/current/manifest.json and held in the papers download ZIP',
    'papers-current-index.html': 'pinned by papers/current/manifest.json and held in the papers download ZIP',
    'portable-README.txt': 'plain text: a comment would be visible',
}


def source_note(name, text):
    """One comment at the top of a generated page saying where to edit it. GitHub and browsers show nothing of it.
    In an HTML page it follows the doctype line."""
    if name in NO_NOTE:
        return text
    note = (f'<!-- Generated by tools/front-pages/build_front.py from tools/front-pages/templates/{name}; '
            f'edit the template, then run the builder. -->\n')
    if name.endswith('.html'):
        first, rest = text.split('\n', 1)
        assert first.lower() == '<!doctype html>', (name, first)
        return first + '\n' + note + rest
    assert name.endswith('.md'), name
    return note + text


def render(name):
    PAGE[0] = TARGETS[name]
    text = (TEMPLATES / name).read_text(encoding='utf-8')

    def fill(m):
        try:
            return str(eval(m.group(1), NAMESPACE))
        except Exception as e:  # noqa: BLE001
            raise SystemExit(f'{name}: {{{{ {m.group(1)} }}}} failed: {e!r}')
    out = re.sub(r'\{\{\s*(.*?)\s*\}\}', fill, text, flags=re.S)
    assert '{{' not in out and '}}' not in out, name
    return source_note(name, out)


def main():
    ap = argparse.ArgumentParser(description='Write the NeuroTranslation front pages from their templates (see the top of this file).')
    ap.add_argument('--check', action='store_true', help='build in memory and list every page, "same" or "DIFFERS"; exit 1 if any differs')
    ap.add_argument('--out', help='write the pages under this folder instead of the repository (a preview)')
    ap.add_argument('--facts', help='also write a table of every number printed: page, text, file, field and unrounded value')
    args = ap.parse_args()
    missing = [t for t in ('pdftotext', 'pdfinfo') if shutil.which(t) is None]
    if missing:
        raise SystemExit('build_front.py needs ' + ' and '.join(missing) + ' on the PATH: they come with Poppler '
                         '(the poppler-utils package on most Linux systems, "brew install poppler" on macOS)')
    bad = 0
    for name, target in TARGETS.items():
        if not (TEMPLATES / name).exists():
            print(f'   (no template yet) {name}')
            continue
        text = render(name)
        path = (Path(args.out) if args.out else REPO) / target
        if args.check:
            same = path.exists() and path.read_text(encoding='utf-8') == text
            print(f"   {'same   ' if same else 'DIFFERS'} {target}")
            bad += not same
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
            print(f'   wrote {target} ({len(text.encode("utf-8"))} bytes)')
    if args.facts:
        rows = ['page\tprinted\tsource file\tfield\tunrounded value\tnote']
        seen = set()
        for row in FACTS:
            if row not in seen:
                seen.add(row)
                rows.append('\t'.join(row))
        Path(args.facts).write_text('\n'.join(rows) + '\n', encoding='utf-8')
        print(f'   {Path(args.facts).name}: {len(rows) - 1} numbers, each with its file and field')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
