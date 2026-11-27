"""Shared constants and small helpers for the walking-force quantity ladder (protocol version 1).

Standard library only, so every runtime can import it. Local paths never appear in committed code:
each script takes them from a private JSON configuration (see README-CODE.md).
"""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTOCOL_VERSION = 1
DOI = '10.6084/m9.figshare.24192480.v1'
SEED_BASE = 20261124
BOOTSTRAP_SEED = 20261127
BOOTSTRAP_DRAWS = 10_000
TREE_SEED = 20261124
FIT_PREVALENCE_12 = 0.03725847908677051
MUSCLES6 = ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'RERS')
MUSCLES14 = ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'LTA', 'LVL', 'RBF', 'RERS', 'RGAS', 'RRF', 'RST', 'RTA', 'RVL')
# The 36 walks of the earlier roster's 12 fit people, in the order of the earlier fit caches. They keep
# member indices 0-35 in every rung, so the 12-person rung reproduces the sealed fits row for row.
FIT12_WALKS = (('SUBJ112', (1, 2, 3)), ('SUBJ110', (1, 2, 3)), ('SUBJ096', (1, 2, 3)), ('SUBJ024', (1, 2, 3)),
               ('SUBJ082', (1, 3, 4)), ('SUBJ062', (1, 2, 3)), ('SUBJ061', (1, 2, 3)), ('SUBJ040', (1, 2, 3)),
               ('SUBJ044', (1, 2, 3)), ('SUBJ043', (1, 2, 3)), ('SUBJ039', (1, 2, 3)), ('SUBJ038', (1, 2, 3)))
FIT12 = tuple(sorted(p for p, _ in FIT12_WALKS))
# Person order used by the earlier comparison caches for participant_index (salted hash order).
FOLD_SALT = 'NeuroTranslate common-six component baselines v1 20261124:'
THREAD_ENV = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


class Halt(Exception):
    """A stop rule fired: the stage halts and nothing is substituted (protocol section 13)."""


# Private folder layout (protocol sections 5.4 and 14). The physics-source track may be given read access
# to the training folders only ('walks' and 'arrays'). The evaluation walks (D3), their receipts and the
# EVAL-* arrays sit in folders of their own, so that access can be granted or refused by folder.
PRIVATE_FOLDERS = {'training': {'walks': 'walks', 'arrays': 'arrays', 'receipts': 'receipts'},
                   'evaluation': {'walks': 'eval-walks', 'arrays': 'eval-arrays', 'receipts': 'eval-walks/receipts'}}
PHYSICS_SOURCE_READABLE = ('walks', 'arrays')


def private_folder(cfg, group, kind):
    """group: 'training' (also 'training_pool') or 'evaluation'; kind: 'walks', 'arrays' or 'receipts'."""
    group = 'training' if group == 'training_pool' else group
    need(group in PRIVATE_FOLDERS, f'unknown group {group}')
    return Path(cfg['private_dir']) / PRIVATE_FOLDERS[group][kind]


def single_thread_env():
    """Call before numpy, torch or scikit-learn are imported."""
    for key in THREAD_ENV:
        os.environ[key] = '1'


def need(ok, message):
    if not ok:
        raise SystemExit(f'walking-force-scale: {message}')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def hash_text(text):
    return hashlib.sha256(text.encode('ascii')).hexdigest()


def canonical(obj):
    return (json.dumps(obj, indent=1, ensure_ascii=True, allow_nan=False, sort_keys=False) + '\n').encode('ascii')


def write_json(path, obj, *, exclusive=False):
    body = canonical(obj)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'xb' if exclusive else 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    return sha_bytes(body)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def load_config(path):
    """Private configuration: a JSON object of local paths. Never committed."""
    cfg = read_json(path)
    need(isinstance(cfg, dict), 'the configuration must be a JSON object')
    return {k: (Path(v) if isinstance(v, str) and k.endswith(('_dir', '_file', '_root')) else v) for k, v in cfg.items()}


def protocol_tag(protocol_path):
    digest = sha_file(protocol_path)
    return digest, f'{DOI}|walking-scale|{digest}'


def code_hashes(names=None):
    names = names or sorted(p.name for p in HERE.glob('*.py'))
    return {n: sha_file(HERE / n) for n in names}


def subject_code(text):
    """'SUBJ7', 'SUBJ07' or 'SUBJ007' -> 'SUBJ007'."""
    need(text.upper().startswith('SUBJ'), f'odd subject code {text}')
    return f'SUBJ{int(text[4:]):03d}'


def fold_order(people):
    """Earlier participant_index order: ascending sha256 digest of FOLD_SALT + code."""
    return sorted(people, key=lambda p: hashlib.sha256((FOLD_SALT + p).encode()).digest())


def publish_dir(cfg):
    """Folder for the committed stage files (QUALIFICATION, ALLOCATION, FIT-COMPLETE, FORECASTS-SEAL, P2).

    The protocol folder itself unless the configuration names another (synthetic tests only)."""
    return Path(cfg['publish_dir']) if cfg.get('publish_dir') else HERE


def base_people(allocation):
    """The 12-person rung (the earlier fit people); every rung contains them."""
    return list(allocation['twelve_person_rung'])


def n_max(allocation):
    return len(base_people(allocation)) + allocation['sizes']['T']


def rung_sizes(allocation):
    base = len(base_people(allocation))
    return [base] + [base + a for a in allocation['sizes']['added']]
