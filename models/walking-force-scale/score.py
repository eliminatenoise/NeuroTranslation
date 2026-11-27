"""Scoring stages S-b and S-c (protocol sections 10, 11 and 14). Runtime B.

  score.py below --config CFG          S-b: scores M1, M2, M3 at the rungs below N_max only, fits the trend
                                       forms and writes P2-TREND-PREDICTION.json (to be committed in C5).
                                       It opens only the PRIMARY-BELOW-NMAX forecast files.
  score.py final --config CFG --p2-sha SHA
                                       S-c: refuses to run unless P2-TREND-PREDICTION.json has sha256 SHA and
                                       the same bytes are committed at the repository HEAD; then scores N_max,
                                       the frozen checkpoints, the controls and every secondary arm.

Metrics: impulse MAE (N s) and new-load Brier score with the published person weights (people equal,
then walks, issue ticks and represented plates), on the common support only. Each replicate's
per-person error is averaged over the rung's replicates and draws before people are averaged.
Intervals: paired bootstrap over scoreable people, 10,000 resamples from default_rng(20261127), drawn
once for the impulse-scoreable and once (fresh generator) for the event-scoreable people, ascending
code order; percentile 95% intervals; two-sided p = min(1, 2 min(1 + #(D* >= 0), 1 + #(D* <= 0)) / 10,001).
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from common import (BOOTSTRAP_DRAWS, BOOTSTRAP_SEED, HERE, base_people, code_hashes, load_config, n_max as top_rung, need,
                    private_folder, publish_dir, read_json, rung_sizes, sha_file, single_thread_env, write_json)

Z_ALPHA, Z_POWER, Z_HOLM1 = 1.95996, 0.84162, 2.39398
THRESHOLD = 0.03
PRIMARY = ('M1', 'M2', 'M3')
P2_NAME = 'P2-TREND-PREDICTION.json'


class Scorer:
    def __init__(self, cfg, allocation_path, fit_complete_path, seal_path, allowed_groups):
        import numpy as np
        import extract
        self.np = np
        self.cfg, self.allocation = cfg, read_json(allocation_path)
        self.fit_complete = read_json(fit_complete_path)
        self.seal = read_json(seal_path)
        need(self.fit_complete['allocation_sha256'] == sha_file(allocation_path), 'FIT-COMPLETE.json allocation')
        need(self.seal['fit_complete_sha256'] == sha_file(fit_complete_path), 'FORECASTS-SEAL.json fit seal')
        folder = private_folder(cfg, 'evaluation', 'arrays')
        meta = read_json(folder / 'EVAL-WALKS.json')
        need(sha_file(folder / 'EVAL-INPUTS.npz') == meta['inputs_sha256'] == self.seal['eval_inputs_sha256'], 'inputs')
        need(sha_file(folder / 'EVAL-TARGETS.npz') == meta['targets_sha256'], 'targets')
        inputs = extract.load_npz(folder / 'EVAL-INPUTS.npz', extract.INPUT_FIELDS)
        targets = extract.load_npz(folder / 'EVAL-TARGETS.npz', extract.TARGET_FIELDS)
        self.forecasts = {}
        ffolder = Path(cfg['private_dir']) / 'forecasts'
        for name, entry in self.seal['files'].items():
            group = name[len('FORECASTS-'):].rsplit('-', 1)[0]
            if group not in allowed_groups:
                continue
            need(sha_file(ffolder / name) == entry['sha256'], f'{name} differs from FORECASTS-SEAL.json')
            self.forecasts[name] = np.load(ffolder / name)
        need(self.forecasts, 'no forecast file admitted for this stage')
        first = next(iter(self.forecasts.values()))
        rows = first['rows']
        need(np.array_equal(rows, np.flatnonzero(extract.input_valid(inputs))), 'issued rows differ from input-valid rows')
        sup = extract.supports(inputs, targets)
        self.masks = {k: v[rows] for k, v in sup.items()}
        self.masks['impulse_grid24'] = self.masks['impulse'] & inputs['grid24'][rows]
        self.masks['event_grid24'] = self.masks['event'] & inputs['grid24'][rows]
        com = {w['member_index']: w['subject'] for w in meta['walks']}
        self.code = np.asarray([com[int(m)] for m in inputs['member_index'][rows]])
        self.member, self.tick, self.plate = inputs['member_index'][rows], inputs['issue_tick'][rows], inputs['plate'][rows]
        self.state = inputs['state_at_issue'][rows]
        self.event = targets['event_new_load'][rows]
        self.impulse = targets['signed_impulse_ns'][rows]
        self.onset = targets['onset_tick'][rows]
        self.assigned = sorted(p['subject'] for p in self.allocation['groups']['evaluation'])
        self.people = {e: sorted(set(self.code[self.masks[e]])) for e in ('impulse', 'event')}
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        self.idx = {'impulse': rng.integers(0, len(self.people['impulse']), size=(BOOTSTRAP_DRAWS, len(self.people['impulse'])))}
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        self.idx['event'] = rng.integers(0, len(self.people['event']), size=(BOOTSTRAP_DRAWS, len(self.people['event'])))
        self._weights = {}

    # ------------------------------------------------------------------------------ per-person errors
    def weights(self, mask_key, endpoint):
        """people x rows matrix of within-person normalised published weights."""
        cache = (mask_key, endpoint)
        if cache not in self._weights:
            import compact
            np = self.np
            mask = self.masks[mask_key]
            w = compact.participant_weights(self.code, self.member, self.tick, mask) if mask.any() else np.zeros(len(mask))
            people = self.people[endpoint]
            a = np.zeros((len(people), len(mask)))
            for k, p in enumerate(people):
                sel = mask & (self.code == p)
                if sel.any():
                    a[k, sel] = w[sel] / w[sel].sum()
            present = np.asarray([bool((mask & (self.code == p)).any()) for p in people])
            self._weights[cache] = (a, present)
        return self._weights[cache]

    def series(self, name):
        for z in self.forecasts.values():
            if f'{name}::p' in z.files:
                return z[f'{name}::p'], z[f'{name}::i']
        return None

    def person_error(self, name, endpoint, mask_key=None):
        """Vector over the scoreable people of `endpoint` (NaN where the person has no row in the mask)."""
        np = self.np
        got = self.series(name)
        if got is None:
            return None
        prob, imp = got
        mask_key = mask_key or endpoint
        a, present = self.weights(mask_key, endpoint)
        mask = self.masks[mask_key]
        if endpoint == 'impulse':
            err = np.where(mask, np.abs(imp - np.nan_to_num(self.impulse)), 0.)
        else:
            err = np.where(mask, np.square(prob - np.nan_to_num(self.event)), 0.)
        need(np.isfinite(err).all(), f'a forecast is missing on the common support: {name}')
        out = a @ err
        return np.where(present, out, np.nan)

    def replicate_matrix(self, ids, endpoint, mask_key=None):
        """people x replicates of per-person errors; failed (not issued) fits are skipped and counted."""
        np = self.np
        cols = [v for v in (self.person_error(i, endpoint, mask_key) for i in ids) if v is not None]
        return (np.column_stack(cols) if cols else np.zeros((len(self.people[endpoint]), 0))), len(ids) - len(cols)

    # ------------------------------------------------------------------------------------ inference
    def contrast(self, a, b, endpoint):
        """Delta = mean(a - b) over people with both values; paired bootstrap with the shared index matrix."""
        np = self.np
        idx = self.idx[endpoint]
        ok = np.isfinite(a) & np.isfinite(b)
        if not ok.all():  # restrict to people with both (secondary supports); fresh indices are not drawn
            keep = np.flatnonzero(ok)
            remap = -np.ones(len(a), dtype=int)
            remap[keep] = np.arange(len(keep))
            a, b = a[keep], b[keep]
            idx = np.where(np.isin(idx, keep), remap[idx], -1)
        d = a - b
        if len(d) == 0:
            return {'people': 0}
        delta, base = float(d.mean()), float(b.mean())
        if (idx < 0).any():
            boot = np.array([d[r[r >= 0]].mean() if (r >= 0).any() else np.nan for r in idx])
            bb = np.array([b[r[r >= 0]].mean() if (r >= 0).any() else np.nan for r in idx])
        else:
            boot, bb = d[idx].mean(axis=1), b[idx].mean(axis=1)
        rel_boot = boot / bb
        lo, hi = np.nanpercentile(boot, [2.5, 97.5])
        rlo, rhi = np.nanpercentile(rel_boot, [2.5, 97.5])
        p = min(1., 2 * min(1 + int(np.sum(boot >= 0)), 1 + int(np.sum(boot <= 0))) / (BOOTSTRAP_DRAWS + 1))
        sd = float(np.std(d, ddof=1)) if len(d) > 1 else float('nan')
        mde = {'alpha_0.05': (Z_ALPHA + Z_POWER) * sd / np.sqrt(len(d)) / base,
               'holm_first_step': (Z_HOLM1 + Z_POWER) * sd / np.sqrt(len(d)) / base}
        return {'people': int(len(d)), 'delta': delta, 'interval95': [float(lo), float(hi)], 'base_mean': base,
                'relative': delta / base, 'relative_interval95': [float(rlo), float(rhi)], 'p_two_sided': p,
                'sd_per_person_difference': sd, 'minimum_detectable_relative_effect': mde,
                'share_of_people_improved': float(np.mean(d < 0))}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adjusted, running = [0.] * len(ps), 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (len(ps) - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def label(c, adjusted):
    if adjusted < 0.05 and c['delta'] > 0:
        return 'HARMED'
    if adjusted < 0.05 and c['delta'] < 0 and c['relative'] <= -THRESHOLD:
        return 'HELPED'
    lo, hi = c['relative_interval95']
    if -THRESHOLD < lo and hi < THRESHOLD:
        return 'PRACTICALLY NO CHANGE'
    return 'INCONCLUSIVE'


def family_ids(allocation, arm, kind_filter=None, n=None):
    import plan
    return [j['id'].replace('|', '_') for j in plan.jobs(allocation)
            if j['arm'] == arm and (kind_filter is None or j['kind'] in kind_filter) and (n is None or j['N'] == n)]


def rung_person_means(scorer, allocation, arm, endpoint, mask_key=None, rungs=None):
    """{N: (person vector averaged over replicates and draws, fits used, fits failed)}."""
    out = {}
    for n in rungs or rung_sizes(allocation):
        kinds = ('g8',) if arm.startswith('G8') else None
        mat, failed = scorer.replicate_matrix(family_ids(allocation, arm, kinds, n), endpoint, mask_key)
        if mat.shape[1]:
            out[n] = (scorer.np.nanmean(mat, axis=1), mat.shape[1], failed, mat)
    return out


def score_lock(cfg, stage, scorer, extra):
    body = {'stage': stage, 'utc': datetime.now(timezone.utc).isoformat(), 'code_sha256': code_hashes(),
            'forecast_files': {n: sha_file(Path(cfg['private_dir']) / 'forecasts' / n) for n in scorer.forecasts},
            'eval_targets_sha256': sha_file(private_folder(cfg, 'evaluation', 'arrays') / 'EVAL-TARGETS.npz'), **extra}
    write_json(Path(cfg['out_dir']) / f'SCORE-LOCK-{stage}.json', body, exclusive=True)


# ========================================================================================== S-b
def stage_below(cfg, allocation_path, fit_complete_path, seal_path):
    single_thread_env()
    import trend
    scorer = Scorer(cfg, allocation_path, fit_complete_path, seal_path, allowed_groups=('PRIMARY-BELOW-NMAX',))
    need(all('BELOW-NMAX' in n for n in scorer.forecasts), 'S-b may read only the below-N_max forecasts')
    score_lock(cfg, 'SB', scorer, {'reads': sorted(scorer.forecasts)})
    allocation = scorer.allocation
    n_max = top_rung(allocation)
    below = [n for n in rung_sizes(allocation) if n < n_max]
    np = scorer.np
    families = {}
    for fam in PRIMARY:
        means = rung_person_means(scorer, allocation, fam, 'impulse', rungs=below)
        vals = np.vstack([means[n][0] for n in below])
        entry = {'rung_means': {str(n): float(np.nanmean(means[n][0])) for n in below},
                 'fits_used': {str(n): means[n][1] for n in below}, 'fits_failed': {str(n): means[n][2] for n in below},
                 'per_person': {str(n): dict(zip(scorer.people['impulse'], means[n][0].tolist())) for n in below}}
        if trend.needs_trend(below):
            point, params = trend.predictions(below, vals.mean(axis=1), n_max)
            boot = trend.bootstrap_predictions(np.asarray(below, float), vals, scorer.idx['impulse'], n_max)
            entry.update(point_predictions=point, params={f: list(params[f]) for f in trend.FORMS},
                         bootstrap_predictions={f: boot[f].tolist() for f in trend.FORMS})
        families[fam] = entry
    body = {'schema': 'walking-force-scale-p2-v1', 'protocol_sha256': sha_file(HERE / 'PROTOCOL.json'),
            'fit_complete_sha256': sha_file(fit_complete_path), 'forecasts_seal_sha256': sha_file(seal_path),
            'impulse_scoreable_people': scorer.people['impulse'], 'rungs_below_n_max': below, 'n_max': n_max,
            'trend_test': trend.needs_trend(below), 'bootstrap': {'seed': BOOTSTRAP_SEED, 'draws': BOOTSTRAP_DRAWS},
            'families': families}
    digest = write_json(publish_dir(cfg) / P2_NAME, body)
    return body, digest


# ========================================================================================== S-c
def committed_sha(repo_root, relpath):
    import hashlib
    blob = subprocess.run(['git', '-C', str(repo_root), 'show', f'HEAD:{relpath}'], capture_output=True, check=True).stdout
    return hashlib.sha256(blob).hexdigest()


def stage_final(cfg, allocation_path, fit_complete_path, seal_path, p2_sha):
    single_thread_env()
    import trend
    p2_path = publish_dir(cfg) / P2_NAME
    need(sha_file(p2_path) == p2_sha, 'P2-TREND-PREDICTION.json differs from the given sha256')
    repo = Path(cfg.get('publish_repo') or cfg['repo_root'])
    rel = p2_path.resolve().relative_to(repo.resolve()).as_posix()
    need(committed_sha(repo, rel) == p2_sha, 'P2-TREND-PREDICTION.json is not committed at HEAD with that sha256')
    p2 = read_json(p2_path)
    scorer = Scorer(cfg, allocation_path, fit_complete_path, seal_path, allowed_groups=('PRIMARY-BELOW-NMAX', 'NMAX', 'OTHER'))
    need(p2['impulse_scoreable_people'] == scorer.people['impulse'] and p2['forecasts_seal_sha256'] == sha_file(seal_path),
         'P2 was made for other people or another forecast seal')
    score_lock(cfg, 'SC', scorer, {'p2_sha256': p2_sha})
    np, allocation = scorer.np, scorer.allocation
    n_max = top_rung(allocation)
    base_n = len(base_people(allocation))
    rungs = rung_sizes(allocation)
    res = {'schema': 'walking-force-scale-results-v1', 'protocol_sha256': sha_file(HERE / 'PROTOCOL.json'),
           'p2_sha256': p2_sha, 'fit_complete_sha256': sha_file(fit_complete_path), 'forecasts_seal_sha256': sha_file(seal_path),
           'n_max': n_max, 'rungs': rungs}
    res['counts'] = counts(scorer)
    floors = {'impulse': len(scorer.people['impulse']) >= 12,
              'event': sum(1 for p in scorer.people['event'] if both_classes(scorer, p)) >= 10}
    res['floors'] = {'impulse_scoreable_people': len(scorer.people['impulse']), 'impulse_floor_met': floors['impulse'],
                     'event_people_with_both_classes': sum(1 for p in scorer.people['event'] if both_classes(scorer, p)),
                     'event_floor_met': floors['event'],
                     'assigned_unscoreable_impulse': sorted(set(scorer.assigned) - set(scorer.people['impulse'])),
                     'assigned_unscoreable_event': sorted(set(scorer.assigned) - set(scorer.people['event']))}
    curves, primary = {}, {}
    for endpoint in ('impulse', 'event'):
        curves[endpoint] = {}
        contrasts = {}
        for fam in PRIMARY:
            means = rung_person_means(scorer, allocation, fam, endpoint)
            curves[endpoint][fam] = {str(n): {'mean': float(np.nanmean(v[0])), 'fits_used': v[1], 'fits_failed': v[2],
                                              'per_person': dict(zip(scorer.people[endpoint], v[0].tolist()))}
                                     for n, v in means.items()}
            c = scorer.contrast(means[n_max][0], means[base_n][0], endpoint)
            c['sensitivity_people_then_replicates'] = hierarchical(scorer, means[n_max][3], means[base_n][3], endpoint)
            ns = np.asarray(sorted(means), float)
            ys = np.asarray([np.nanmean(means[n][0]) for n in sorted(means)])
            c['descriptive'] = {'slope_per_log2N': float(np.polyfit(np.log2(ns), ys, 1)[0]),
                                'gain_per_doubling_lower_vs_upper_half': halves(ns, ys)}
            contrasts[fam] = c
        adj = holm([contrasts[f]['p_two_sided'] for f in PRIMARY])
        for f, a in zip(PRIMARY, adj):
            contrasts[f]['holm_adjusted_p'] = a
            contrasts[f]['label'] = label(contrasts[f], a) if floors[endpoint] else 'DESCRIPTIVE (below floor)'
        primary[endpoint] = contrasts
    res['primary_impulse'] = primary['impulse']
    res['secondary_brier_family'] = primary['event']
    res['curves'] = curves
    res['compact_model_claim_allowed'] = primary['impulse']['M1']['label'] == 'HELPED'
    # --- trend test against the sealed P2
    if p2['trend_test']:
        tt = {}
        for fam in PRIMARY:
            actual = rung_person_means(scorer, allocation, fam, 'impulse', rungs=[n_max])[n_max][0]
            boot_actual = actual[scorer.idx['impulse']].mean(axis=1)
            fam_p2 = p2['families'][fam]
            tt[fam] = {f: trend.trend_test(float(actual.mean()), boot_actual, fam_p2['point_predictions'][f],
                                           np.asarray(fam_p2['bootstrap_predictions'][f])) for f in trend.FORMS}
            tt[fam]['primary_beat_carry_forward'] = tt[fam]['inverse_sqrt']['absolute_miss'] < tt[fam]['carry_forward']['absolute_miss']
        res['trend_test'] = tt
    else:
        res['trend_test'] = 'fewer than three rungs below N_max: no trend test; the curve is descriptive'
    res['P1_pool_tail_prediction'] = scorer.fit_complete.get('P1_pool_tail_prediction')
    # --- first held test of the 0.0 preview
    res['F3_past_load_gate_first_test'] = {
        grid: scorer.contrast(scorer.person_error('F3_gate_trainable', 'impulse', mk), scorer.person_error('C1', 'impulse', mk), 'impulse')
        for grid, mk in (('full_grid', 'impulse'), ('grid24', 'impulse_grid24'))}
    for v in res['F3_past_load_gate_first_test'].values():
        if v.get('people'):
            lo, hi = v['interval95']
            v['reading'] = 'lower error than persistence' if hi < 0 else ('higher error than persistence' if lo > 0 else 'no detectable difference')
    # --- frozen checkpoints and controls against N = 12 and N_max (descriptive)
    names = ['C1', 'C2', 'C3', 'F1', 'F2', 'F3_gate_trainable', 'F3_gate_frozen', 'F3_expanded_frozen', 'F3_expanded_trainable',
             'F4_main_emg', 'F4_main_force', 'F4_main_force_emg']
    res['frozen_and_controls'] = {}
    for endpoint in ('impulse', 'event'):
        block = {}
        for name in names:
            v = scorer.person_error(name, endpoint)
            if v is None:
                block[name] = 'not issued'
                continue
            block[name] = {'mean': float(np.nanmean(v))}
            for fam in PRIMARY:
                for n in (base_n, n_max):
                    ref = np.asarray(list(curves[endpoint][fam][str(n)]['per_person'].values()))
                    block[name][f'minus_{fam}_N{n}'] = scorer.contrast(v, ref, endpoint)
        for name in ('F4_early_force_emg', 'F4_early_force_earlier_emg'):
            v = scorer.person_error(name, endpoint, f'{endpoint}_early')
            block[name] = {'mean_on_rows_with_earlier_history': float(np.nanmean(v))} if v is not None else 'not issued'
        res['frozen_and_controls'][endpoint] = block
    res['F2_vs_M3_N12_agreement'] = onnx_agreement(scorer)
    res['F5_research_edition'] = 'not issued (optional; not run in this stage)'
    res['secondary_arms'] = secondary(scorer, allocation, n_max, base_n, curves)
    res['S8_subgroups'] = subgroups(scorer, allocation, n_max, base_n)
    res['S9_ranking'] = ranking(scorer, curves, rungs)
    digest = write_json(Path(cfg['out_dir']) / 'RESULTS.json', res)
    return res, digest


def both_classes(scorer, person):
    sel = scorer.masks['event'] & (scorer.code == person)
    vals = scorer.event[sel]
    return bool((vals == 1).any() and (vals == 0).any())


def halves(ns, ys):
    np = __import__('numpy')
    if len(ns) < 3:
        return None
    mid = len(ns) // 2
    lower = (ys[mid] - ys[0]) / (np.log2(ns[mid]) - np.log2(ns[0]))
    upper = (ys[-1] - ys[mid]) / (np.log2(ns[-1]) - np.log2(ns[mid]))
    return {'lower_half': float(lower), 'upper_half': float(upper)}


def hierarchical(scorer, rmax, r12, endpoint):
    """Sensitivity: resample people (shared indices), then each person's replicates with replacement."""
    np = scorer.np
    idx = scorer.idx[endpoint]
    rng = np.random.default_rng(BOOTSTRAP_SEED + 1)
    pick_max = rng.integers(0, rmax.shape[1], size=(idx.shape[0], idx.shape[1], rmax.shape[1]))
    pick_12 = rng.integers(0, r12.shape[1], size=(idx.shape[0], idx.shape[1], r12.shape[1]))
    a = np.take_along_axis(rmax[idx], pick_max, axis=2).mean(axis=2)
    b = np.take_along_axis(r12[idx], pick_12, axis=2).mean(axis=2)
    d = np.nanmean(a - b, axis=1)
    lo, hi = np.nanpercentile(d, [2.5, 97.5])
    rel = d / np.nanmean(b, axis=1)
    rlo, rhi = np.nanpercentile(rel, [2.5, 97.5])
    return {'interval95': [float(lo), float(hi)], 'relative_interval95': [float(rlo), float(rhi)]}


def counts(scorer):
    np = scorer.np
    pos = scorer.masks['event'] & (scorer.event == 1)
    onsets = {(int(m), int(p), int(o)) for m, p, o in zip(scorer.member[pos], scorer.plate[pos], scorer.onset[pos])}
    return {'assigned_people': len(scorer.assigned), 'impulse_scoreable_people': len(scorer.people['impulse']),
            'event_scoreable_people': len(scorer.people['event']), 'walks': len(set(scorer.member.tolist())),
            'issued_rows': int(len(scorer.code)), 'issued_rows_per_plate': {str(p): int((scorer.plate == p).sum()) for p in (1, 2)},
            'impulse_rows': int(scorer.masks['impulse'].sum()), 'event_rows': int(scorer.masks['event'].sum()),
            'positive_rows': int(pos.sum()), 'distinct_onsets': len(onsets), 'grid24_impulse_rows': int(scorer.masks['impulse_grid24'].sum()),
            'sites': 1, 'tasks': 1}


def onnx_agreement(scorer):
    np = scorer.np
    a, b = scorer.series('F2'), scorer.series(family_ids(scorer.allocation, 'M3', ('12',))[0])
    if a is None or b is None:
        return 'not available'
    return {'max_abs_impulse_Ns': float(np.max(np.abs(a[1] - b[1]))), 'max_abs_probability': float(np.max(np.abs(a[0] - b[0]))),
            'rows_beyond_impulse_tolerance': int(np.sum(np.abs(a[1] - b[1]) > 0.000017)),
            'rows_beyond_probability_tolerance': int(np.sum(np.abs(a[0] - b[0]) > 0.00000026)), 'stop_rule': False}


def secondary(scorer, allocation, n_max, b12, curves):
    np = scorer.np
    out = {}
    arms = {'C4': ['12', 'max'], 'S1': None, 'S2-M1': None, 'S2-M2': None, 'S2-M3': None, 'S3': None, 'S4-M1': None,
            'S4-M2': None, 'S4-M3': None, 'S5': None, 'G9-M2': None, 'G9-M3': None}
    for arm in arms:
        block = {}
        for endpoint in ('impulse', 'event'):
            means = rung_person_means(scorer, allocation, arm, endpoint)
            if arm == 'S1':
                means[b12] = rung_person_means(scorer, allocation, 'M1', endpoint, rungs=[b12])[b12]  # S1 at N = 12 is M1
            curve = {str(n): float(np.nanmean(v[0])) for n, v in sorted(means.items())}
            entry = {'curve': curve, 'fits_used': {str(n): v[1] for n, v in sorted(means.items())},
                     'fits_failed': {str(n): v[2] for n, v in sorted(means.items())}}
            base_arm = {'S4-M1': 'M1', 'S4-M2': 'M2', 'S4-M3': 'M3'}.get(arm)
            if base_arm:  # S4 has no 12-person fit of its own: rows_12 equals the 12-person rung
                ref12 = rung_person_means(scorer, allocation, base_arm, endpoint, rungs=[b12])[b12][0]
                entry['delta_N_max_vs_12'] = scorer.contrast(means[n_max][0], ref12, endpoint)
            elif b12 in means and n_max in means:
                entry['delta_N_max_vs_12'] = scorer.contrast(means[n_max][0], means[b12][0], endpoint)
            if arm.startswith('S2-'):
                fam = arm[3:]
                full = rung_person_means(scorer, allocation, fam, endpoint)
                gain = {n: means[n][0] - full[n][0] for n in means if n in full}
                entry['emg_gain_per_rung'] = {str(n): float(np.nanmean(g)) for n, g in gain.items()}
                if b12 in gain and n_max in gain:
                    entry['emg_gain_change_N_max_minus_12'] = scorer.contrast(gain[n_max], gain[b12], endpoint)
            if arm == 'C4':
                m1 = rung_person_means(scorer, allocation, 'M1', endpoint, rungs=[b12, n_max])
                entry['minus_M1'] = {str(n): scorer.contrast(means[n][0], m1[n][0], endpoint) for n in (b12, n_max) if n in means}
            block[endpoint] = entry
        out[arm] = block
    s6 = {}
    for fam in ('M1', 'M2'):
        for endpoint in ('impulse', 'event'):
            mk = f'{endpoint}_early'
            early = rung_person_means(scorer, allocation, f'S6-{fam}', endpoint, mask_key=mk, rungs=[b12, n_max])
            same = rung_person_means(scorer, allocation, fam, endpoint, mask_key=mk, rungs=[b12, n_max])
            s6[f'{fam}/{endpoint}'] = {str(n): scorer.contrast(early[n][0], same[n][0], endpoint) for n in (b12, n_max) if n in early and n in same}
    out['S6_earlier_emg_minus_contemporaneous'] = s6
    g8 = {}
    for fam in PRIMARY:
        for endpoint in ('impulse', 'event'):
            one = rung_person_means(scorer, allocation, f'G8one-{fam}', endpoint, rungs=[n_max])
            three = rung_person_means(scorer, allocation, f'G8three-{fam}', endpoint, rungs=[n_max])
            if n_max in one and n_max in three:
                g8[f'{fam}/{endpoint}'] = scorer.contrast(one[n_max][0], three[n_max][0], endpoint)
    out['G8_one_walk_each_minus_three_walks_each'] = g8
    return out


def subgroups(scorer, allocation, n_max, b12):
    """S8 (descriptive): plate state at issue, plate number, reliability bins, distinct onsets."""
    np = scorer.np
    out = {}
    groups = {'unloaded': scorer.state == 1, 'loaded_or_pending': np.isin(scorer.state, (2, 3)), 'unknown': scorer.state == 0,
              'plate1': scorer.plate == 1, 'plate2': scorer.plate == 2}
    names = {'C1': 'C1'}
    for fam in PRIMARY:
        for n in (b12, n_max):
            names[f'{fam}_N{n}'] = family_ids(allocation, fam, None, n)
    for label_, ids in names.items():
        ids = [ids] if isinstance(ids, str) else ids
        block = {}
        for g, sel in groups.items():
            m = scorer.masks['impulse'] & sel
            vals = []
            for i in ids:
                s = scorer.series(i)
                if s is not None and m.any():
                    vals.append(float(np.mean(np.abs(s[1][m] - scorer.impulse[m]))))
            block[g] = {'rows': int(m.sum()), 'mean_abs_error_rowwise': float(np.mean(vals)) if vals else None}
        out[label_] = block
    rel = {}
    m = scorer.masks['event']
    for label_, ids in ((f'M1_N{b12}', family_ids(allocation, 'M1', None, b12)), (f'M1_N{n_max}', family_ids(allocation, 'M1', None, n_max))):
        probs = [scorer.series(i)[0][m] for i in ids if scorer.series(i) is not None]
        if probs:
            p = np.mean(probs, axis=0)
            bins = np.minimum((p * 10).astype(int), 9)
            rel[label_] = [{'bin': b, 'rows': int((bins == b).sum()), 'mean_forecast': float(p[bins == b].mean()) if (bins == b).any() else None,
                            'observed_rate': float(scorer.event[m][bins == b].mean()) if (bins == b).any() else None} for b in range(10)]
    out['reliability_bins_replicate_mean_probability'] = rel
    return out


def ranking(scorer, curves, rungs):
    out = {}
    for n in rungs:
        entries = {fam: curves['impulse'][fam][str(n)]['mean'] for fam in PRIMARY if str(n) in curves['impulse'][fam]}
        out[str(n)] = sorted(entries, key=entries.get)
    fixed = {}
    for name in ('C1', 'C2', 'C3', 'F1', 'F2', 'F3_gate_trainable', 'F3_gate_frozen', 'F3_expanded_frozen', 'F3_expanded_trainable',
                 'F4_main_emg', 'F4_main_force', 'F4_main_force_emg'):
        v = scorer.person_error(name, 'impulse')
        if v is not None:
            fixed[name] = float(scorer.np.nanmean(v))
    for n in rungs:
        merged = {**fixed, **{f'{fam}_N{n}': curves['impulse'][fam][str(n)]['mean'] for fam in PRIMARY if str(n) in curves['impulse'][fam]}}
        out[f'with_fixed_methods_N{n}'] = sorted(merged, key=merged.get)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('step', choices=('below', 'final'))
    ap.add_argument('--config', required=True)
    ap.add_argument('--allocation', default=str(HERE / 'ALLOCATION.json'))
    ap.add_argument('--fit-complete', default=str(HERE / 'FIT-COMPLETE.json'))
    ap.add_argument('--seal', default=str(HERE / 'FORECASTS-SEAL.json'))
    ap.add_argument('--p2-sha')
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.step == 'below':
        body, digest = stage_below(cfg, args.allocation, args.fit_complete, args.seal)
        print(json.dumps({'trend_test': body['trend_test'], 'sha256': digest}))
    else:
        need(args.p2_sha, '--p2-sha (the committed P2 file sha256) is required')
        res, digest = stage_final(cfg, args.allocation, args.fit_complete, args.seal, args.p2_sha)
        print(json.dumps({f: res['primary_impulse'][f]['label'] for f in PRIMARY} | {'sha256': digest}))


if __name__ == '__main__':
    main()
