"""Every fit of the ladder, derived mechanically from ALLOCATION.json and the protocol (sections 7-9).

Replicates (protocol section 7; the same scheme for every M1-type arm, admission review minor 3):
  fixed training sets (N = 12, N_max, and the two G8 sets): 50 seeds, 20261124 + j, j = 0..49;
  intermediate rungs: 10 draws x 5 seeds, draw d uses 20261124 + 5 d + s, s = 0..4;
  M2, M3 and their arms: one deterministic fit per training set (random_state 20261124 for trees).
Arms and rungs:
  M1, M2, M3, S2 (force only: M1, M2, M3), S3 (width 96, epoch-matched), S5, G9 (tuned M2, M3): every rung;
  S1 (epoch-matched M1), S4 (fixed example budget: M1, M2, M3): every rung above 12 (at N = 12 S1 is M1);
  C4 (random recurrent readout), S6 (earlier EMG: M1, M2): N = 12 and N_max;
  G8 (variety: M1, M2, M3, one walk each against three walks each): N_max.
At Q = 80 this gives 250 primary M1 fits and 1,450 M1-type fits in all, as PROTOCOL.json budgets.
Standard library only.
"""
from common import FIT12_WALKS, SEED_BASE, base_people

TORCH_ARMS = ('M1', 'C4', 'S1', 'S2-M1', 'S3', 'S4-M1', 'S6-M1', 'G8one-M1', 'G8three-M1')
SK_ARMS = ('M2', 'M3', 'S2-M2', 'S2-M3', 'S4-M2', 'S4-M3', 'S5', 'S6-M2', 'G8one-M2', 'G8three-M2',
           'G8one-M3', 'G8three-M3', 'G9-M2', 'G9-M3')
PRIMARY = ('M1', 'M2', 'M3')


def training_sets(allocation):
    """[{'N', 'added', 'draw', 'people', 'folds', 'kind'}] with kind 12 / mid / max."""
    t = allocation['sizes']['T']
    base = sorted(base_people(allocation))
    sets = [{'N': len(base), 'added': 0, 'draw': None, 'people': base, 'folds': allocation['rung_zero_inner_folds'], 'kind': '12'}]
    for rung in allocation['rungs']:
        kind = 'max' if rung['added'] == t else 'mid'
        for d in rung['draws']:
            sets.append({'N': rung['N'], 'added': rung['added'], 'draw': None if kind == 'max' else d['draw'],
                         'people': base + sorted(d['added_people']), 'folds': d['inner_folds'], 'kind': kind})
    return sets


def seeds(kind, draw):
    if kind in ('12', 'max', 'g8'):
        return [(j, SEED_BASE + j) for j in range(50)]
    return [(s, SEED_BASE + 5 * draw + s) for s in range(5)]


def walk_filter(people, one_walk=None):
    """Training walks: three per person, except the G8 one-walk arm (variety walk of each pool person)."""
    fit = dict(FIT12_WALKS)
    out = {}
    for p in people:
        if one_walk is not None and p in one_walk:
            out[p] = [one_walk[p]]
        elif p in fit:
            out[p] = list(fit[p])
        else:
            out[p] = None  # all three selected walks
    return out


def jobs(allocation, smoke=None):
    """Job list. A synthetic test allocation may carry 'smoke' (reduced seed counts); allocate.py never writes it."""
    smoke = smoke or allocation.get('smoke')
    if allocation['sizes'].get('ladder') != 'run':
        return []
    out = []
    sets = training_sets(allocation)
    variety = allocation['variety_control']
    nmax = next(s for s in sets if s['kind'] == 'max')

    def add(arm, tset, seed_rows, extra=None, label=None):
        runtime = 'torch' if arm in TORCH_ARMS else 'sk'
        for rep, seed in seed_rows:
            draw = 'x' if tset['draw'] is None else tset['draw']
            jid = f'{arm}|N{tset["N"]:03d}|d{draw}|r{rep:02d}' if seed is not None else f'{arm}|N{tset["N"]:03d}|d{draw}'
            out.append({'id': jid, 'arm': arm, 'runtime': runtime, 'N': tset['N'], 'kind': label or tset['kind'],
                        'draw': tset['draw'], 'replicate': rep, 'seed': seed, 'people': tset['people'],
                        'walks': walk_filter(tset['people'], (extra or {}).get('one_walk')), 'folds': tset['folds'],
                        'rung_draw_for_hash': 0 if tset['draw'] is None else tset['draw']})

    for tset in sets:
        torch_seeds = seeds(tset['kind'], tset['draw'])
        if smoke:
            torch_seeds = torch_seeds[:smoke.get('seeds', len(torch_seeds))]
        single = [(0, None)]
        for arm in ('M1', 'S2-M1', 'S3'):
            add(arm, tset, torch_seeds)
        for arm in ('M2', 'M3', 'S2-M2', 'S2-M3', 'S5', 'G9-M2', 'G9-M3'):
            add(arm, tset, single)
        if tset['kind'] != '12':
            add('S1', tset, torch_seeds)
            add('S4-M1', tset, torch_seeds)
            add('S4-M2', tset, single)
            add('S4-M3', tset, single)
        if tset['kind'] in ('12', 'max'):
            add('C4', tset, torch_seeds)
            add('S6-M1', tset, torch_seeds)
            add('S6-M2', tset, single)
    base = sorted(base_people(allocation))
    one = {**nmax, 'people': base + sorted(variety['one_walk_each']), 'draw': None}
    three = {**nmax, 'people': base + sorted(variety['three_walks_each']), 'draw': None}
    g8_seeds = seeds('g8', None)[:smoke.get('seeds', 50)] if smoke else seeds('g8', None)
    add('G8one-M1', one, g8_seeds, {'one_walk': variety['one_walk_each']}, 'g8')
    add('G8three-M1', three, g8_seeds, None, 'g8')
    for fam in ('M2', 'M3'):
        add(f'G8one-{fam}', one, [(0, None)], {'one_walk': variety['one_walk_each']}, 'g8')
        add(f'G8three-{fam}', three, [(0, None)], None, 'g8')
    ids = [j['id'] for j in out]
    assert len(ids) == len(set(ids)), 'duplicate job ids'
    return out


def counts(job_list):
    from collections import Counter
    return dict(Counter(j['arm'] for j in job_list))
