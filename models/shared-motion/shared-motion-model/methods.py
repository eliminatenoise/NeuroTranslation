"""Deterministic fit schedule and domain-specific linear controls."""
import hashlib
import json
from pathlib import Path
import numpy as np

from predict import DOMAINS, physical_features

SEEDS = (27181, 27182, 27183)
STEPS = 400
SOURCE = Path(__file__).resolve().parent.parent / 'shared-motion-data'
ARMS = ('joint', 'wrist32', 'rat32', 'wrist64', 'rat64')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_hash(a):
    return hashlib.sha256(np.ascontiguousarray(a).astype('<i8').tobytes()).hexdigest()


def load_data(path, role):
    if role not in ("train", "assessment"):
        raise ValueError("Unexpected role")
    contract_path = SOURCE/'contract.json'
    contract_hash = digest(contract_path)
    if contract_hash != "48d3dc03e05fce2b1c95e10aeca45ef934e3cd0108b7a53036b1616b29fc40a2":
        raise ValueError("Data contract hash differs")
    count_record = json.loads((SOURCE/f"{role}-counts.json").read_text())
    packet_hash = digest(path)
    if count_record["contract_sha256"] != contract_hash or count_record["packet_sha256"] != packet_hash:
        raise ValueError("Input packet differs from the data owner's verified partition receipt")
    if role == "train" and packet_hash != "2b7991fe685c05bf5edb9c9a9de002034bacb5ce96d03281d0cdedcf835d8194":
        raise ValueError("Training input differs from the frozen model cohort")
    with np.load(path, allow_pickle=False) as archive:
        data = {key:archive[key] for key in ('x', 'y', 'domain', 'group', 'recording', 'cutoff_s')}
    contracts = json.loads(contract_path.read_text())["records"]
    allowed = {(r["domain"],r["group"],r["recording"]) for r in contracts if r["role"]==role}
    if not set(zip(data["domain"],data["group"],data["recording"])).issubset(allowed):
        raise ValueError("Packet contains an unapproved source recording or group")
    x, y, domains, groups = (data[k] for k in ('x', 'y', 'domain', 'group'))
    physical_features(x)
    if not (y.ndim == 1 and len(x)==len(y)==len(domains)==len(groups) and np.isfinite(y).all()
            and np.all(y >= 0) and set(domains) == set(DOMAINS)):
        raise ValueError('Invalid response or domain shape/values')
    if set(groups[domains=='wrist']) & {'R031'}:
        raise ValueError("Protected gallery session")
    human_assessment = {'R035','R037','R042','R045','R072','R074'}
    human = set(groups[domains=='wrist'])
    rat = {int(t.split('-')[-1]) for t in groups[domains=='rat']}
    if role=='train':
        if human & human_assessment or not rat <= set(range(55,79)):
            raise ValueError("Training split mismatch")
    elif role=='assessment':
        if human != human_assessment or rat != set(range(81,90)):
            raise ValueError("Assessment split mismatch")
    else:
        raise ValueError('Unexpected role')
    return data


def schedule(data, seed):
    plan = {}
    for i, domain in enumerate(DOMAINS):
        rng = np.random.default_rng(np.random.SeedSequence([seed, i]))
        domain_idx = np.flatnonzero(data['domain'] == domain)
        group = data['group'][domain_idx]
        ids = [domain_idx[group == g] for g in np.unique(group)]
        group_draws = rng.integers(len(ids), size=(STEPS, 64))
        indices = np.empty_like(group_draws)
        for j, eligible in enumerate(ids):
            mask = group_draws == j
            indices[mask] = rng.choice(eligible, size=mask.sum(), replace=True)
        plan[domain] = indices
    return plan


def arm_indices(plan, arm):
    if arm == 'joint':
        return np.concatenate([plan[d][:,:32] for d in DOMAINS], axis=1)
    return plan[arm[:-2]][:, :int(arm[-2:])]


def ridge_design(x):
    z, recent = physical_features(x)
    lengths = x[:,:,0]
    scaled = .25 * lengths / x[:,:,1]
    extra = [f(v, axis=1)[:,None] for v in (lengths, scaled)
             for f in (np.mean, np.median, np.max)]
    return np.concatenate([z.reshape(len(x), -1), lengths, scaled, x[:,:,3],
                           recent[:,None], *extra], axis=1)


def fit_ridges(x, y, group):
    X = ridge_design(x)
    _, group_id, counts = np.unique(group, return_inverse=True, return_counts=True)
    weights = 1. / (len(counts) * counts[group_id])
    mu = weights @ X
    sd = np.sqrt(weights @ ((X-mu)**2))
    sd[sd < 1e-12] = 1.
    z = (X-mu)/sd
    answers = np.stack([y, np.log1p(y)], axis=1)
    intercept = weights @ answers
    gram = z.T @ (weights[:,None] * z) + .01 * np.eye(z.shape[1])
    coef = np.linalg.solve(gram, z.T @ (weights[:,None] * (answers-intercept)))
    return dict(mu=mu, sd=sd, coef=coef, intercept=intercept)


def ridge_predictions(x, fit):
    v = ((ridge_design(x) - fit['mu']) / fit['sd']) @ fit['coef'] + fit['intercept']
    return np.maximum(v[:,0], 0), np.expm1(np.maximum(v[:,1], 0))
