"""Supplement to the S-c results (protocol sections 1, 6, 9 and 10). Runtime B.

  supplement.py --config CFG --results-sha SHA

Written and run after S-c, when RESULTS.json had been read. It changes no number in RESULTS.json and
refuses to run unless RESULTS.json in this folder has sha256 SHA and is committed at the repository HEAD.
It uses the scorer of score.py unchanged (same sealed forecasts, same weights, same bootstrap index
matrices) and writes RESULTS-SUPPLEMENT.json with the predeclared tables RESULTS.json does not hold:

  grid24               every method on the published 24-position schedule (protocol section 6)
  early_rows           the two F4 earlier-EMG arms against each other and against our fits, and S6 with means
  same_rung            every secondary arm against its family at the same rung; C4 against M2 and M3
  ranking              all families, controls and frozen checkpoints at each rung, with their means (S9)
  subgroups            counts by plate and plate state, row-wise errors and reliability bins of more methods (S8)
  training_per_rung    people, walks, rows, onsets, updates and examples per rung, from FIT-COMPLETE.json

Every recomputed full-grid value is compared with RESULTS.json and the run stops on any difference.
"""
import argparse
import json
from pathlib import Path

from common import (HERE, base_people, load_config, n_max as top_rung, need, read_json, rung_sizes, sha_file,
                    single_thread_env, write_json)
from score import P2_NAME, PRIMARY, Scorer, committed_sha, family_ids, holm, label, rung_person_means, score_lock

FIXED = ('C1', 'C2', 'C3', 'F1', 'F2', 'F3_gate_trainable', 'F3_gate_frozen', 'F3_expanded_frozen', 'F3_expanded_trainable',
         'F4_main_emg', 'F4_main_force', 'F4_main_force_emg')
EARLY = ('F4_early_force_emg', 'F4_early_force_earlier_emg')
BASE_OF = {'C4': 'M1', 'S1': 'M1', 'S2-M1': 'M1', 'S2-M2': 'M2', 'S2-M3': 'M3', 'S3': 'M1', 'S4-M1': 'M1', 'S4-M2': 'M2',
           'S4-M3': 'M3', 'S5': 'M3', 'G9-M2': 'M2', 'G9-M3': 'M3'}
TOLERANCE = 1e-12


class Tables:
    def __init__(self, scorer):
        self.sc, self.np, self.allocation = scorer, scorer.np, scorer.allocation
        self.n_max, self.b12 = top_rung(self.allocation), len(base_people(self.allocation))
        self.rungs = rung_sizes(self.allocation)
        self._means = {}
        for endpoint in ('impulse', 'event'):  # earlier-EMG rows that are also on the 24-position schedule
            scorer.masks[f'{endpoint}_early_grid24'] = scorer.masks[f'{endpoint}_early'] & scorer.masks[f'{endpoint}_grid24']

    def mean(self, v):
        return float(self.np.nanmean(v))

    def means(self, arm, endpoint, mask_key):
        key = (arm, endpoint, mask_key)
        if key not in self._means:
            self._means[key] = rung_person_means(self.sc, self.allocation, arm, endpoint, mask_key)
        return self._means[key]

    def rows(self, mask_key, endpoint):
        mask = self.sc.masks[mask_key]
        _, present = self.sc.weights(mask_key, endpoint)
        return {'rows': int(mask.sum()), 'people_with_rows': int(present.sum()), 'walks_with_rows': len(set(self.sc.member[mask].tolist()))}

    # ------------------------------------------------------------------------------ families
    def families(self, endpoint, mask_key):
        np, sc = self.np, self.sc
        curves, contrasts = {}, {}
        for fam in PRIMARY:
            means = self.means(fam, endpoint, mask_key)
            curves[fam] = {str(n): {'mean': self.mean(v[0]), 'fits_used': v[1], 'fits_failed': v[2],
                                    'per_person': dict(zip(sc.people[endpoint], v[0].tolist()))} for n, v in sorted(means.items())}
            contrasts[fam] = sc.contrast(means[self.n_max][0], means[self.b12][0], endpoint)
            ns = np.asarray(sorted(means), float)
            ys = np.asarray([np.nanmean(means[n][0]) for n in sorted(means)])
            contrasts[fam]['slope_per_log2N'] = float(np.polyfit(np.log2(ns), ys, 1)[0])
        adjusted = holm([contrasts[f]['p_two_sided'] for f in PRIMARY])
        for fam, a in zip(PRIMARY, adjusted):
            contrasts[fam]['holm_adjusted_p'] = a
            contrasts[fam]['label_rule_applied_descriptively'] = label(contrasts[fam], a)
        return {'curves': curves, 'N_max_minus_12': contrasts}

    # ------------------------------------------------------------------- fixed methods and controls
    def fixed(self, endpoint, mask_key, names=FIXED):
        out = {}
        for name in names:
            v = self.sc.person_error(name, endpoint, mask_key)
            if v is None:
                out[name] = 'not issued'
                continue
            entry = {'mean': self.mean(v)}
            for fam in PRIMARY:
                means = self.means(fam, endpoint, mask_key)
                for n in (self.b12, self.n_max):
                    entry[f'minus_{fam}_N{n}'] = self.sc.contrast(v, means[n][0], endpoint)
            out[name] = entry
        return out

    # ------------------------------------------------------------------------------ secondary arms
    def arms(self, endpoint, mask_key, curves=True):
        sc, out = self.sc, {}
        for arm, fam in BASE_OF.items():
            means = dict(self.means(arm, endpoint, mask_key))
            base = self.means(fam, endpoint, mask_key)
            own = sorted(means)  # the rungs this arm was fitted at
            if arm == 'S1':
                means[self.b12] = base[self.b12]  # S1 at N = 12 is M1
            entry = {}
            if curves:
                entry['curve'] = {str(n): self.mean(v[0]) for n, v in sorted(means.items())}
                entry['fits_used'] = {str(n): v[1] for n, v in sorted(means.items())}
                ref12 = base[self.b12][0] if arm.startswith('S4-') else (means[self.b12][0] if self.b12 in means else None)
                if ref12 is not None and self.n_max in means:  # S4 has no 12-person fit: the reference is its family at 12
                    entry['delta_N_max_vs_12'] = sc.contrast(means[self.n_max][0], ref12, endpoint)
                if arm.startswith('S2-'):
                    gain = {n: means[n][0] - base[n][0] for n in own if n in base}
                    entry['emg_gain_per_rung'] = {str(n): self.mean(g) for n, g in gain.items()}
                    if self.b12 in gain and self.n_max in gain:
                        entry['emg_gain_change_N_max_minus_12'] = sc.contrast(gain[self.n_max], gain[self.b12], endpoint)
            others = PRIMARY if arm == 'C4' else (fam,)
            for other in others:
                ref = self.means(other, endpoint, mask_key)
                entry[f'minus_{other}_same_rung'] = {str(n): sc.contrast(means[n][0], ref[n][0], endpoint) for n in own if n in ref}
            out[arm] = entry
        return out

    def g8(self, endpoint, mask_key):
        out = {}
        for fam in PRIMARY:
            one = self.means(f'G8one-{fam}', endpoint, mask_key)
            three = self.means(f'G8three-{fam}', endpoint, mask_key)
            if self.n_max in one and self.n_max in three:
                out[fam] = {'one_walk_each_mean': self.mean(one[self.n_max][0]), 'three_walks_each_mean': self.mean(three[self.n_max][0]),
                            'one_minus_three': self.sc.contrast(one[self.n_max][0], three[self.n_max][0], endpoint)}
        return out

    # ------------------------------------------------------------------------------ earlier-EMG rows
    def early(self, endpoint, suffix=''):
        sc = self.sc
        mk = f'{endpoint}_early{suffix}'
        out = {'support': self.rows(mk, endpoint)}
        s6 = {}
        for fam in ('M1', 'M2'):
            early = rung_person_means(sc, self.allocation, f'S6-{fam}', endpoint, mask_key=mk, rungs=[self.b12, self.n_max])
            same = self.means(fam, endpoint, mk)
            s6[fam] = {str(n): {'earlier_emg_mean': self.mean(early[n][0]), 'contemporaneous_mean': self.mean(same[n][0]),
                                'earlier_minus_contemporaneous': sc.contrast(early[n][0], same[n][0], endpoint)}
                       for n in (self.b12, self.n_max) if n in early and n in same}
        out['S6'] = s6
        contemporaneous, earlier = (sc.person_error(name, endpoint, mk) for name in EARLY)
        if contemporaneous is None or earlier is None:
            out['F4'] = 'not issued'
            return out
        f4 = {'force_emg_mean': self.mean(contemporaneous), 'force_earlier_emg_mean': self.mean(earlier),
              'earlier_minus_contemporaneous': sc.contrast(earlier, contemporaneous, endpoint)}
        control = sc.person_error('C1', endpoint, mk)
        for name, v in zip(EARLY, (contemporaneous, earlier)):
            block = {'minus_C1': sc.contrast(v, control, endpoint)}
            for fam in PRIMARY:
                ref = self.means(fam, endpoint, mk)
                for n in (self.b12, self.n_max):
                    block[f'minus_{fam}_N{n}'] = sc.contrast(v, ref[n][0], endpoint)
            f4[name] = block
        out['F4'] = f4
        return out

    # ------------------------------------------------------------------------------ ranking (S9)
    def ranking(self, endpoint, mask_key):
        fixed = {}
        for name in FIXED:
            v = self.sc.person_error(name, endpoint, mask_key)
            if v is not None:
                fixed[name] = self.mean(v)
        out = {}
        for n in self.rungs:
            merged = dict(fixed)
            for arm in PRIMARY + ('C4',):
                means = self.means(arm, endpoint, mask_key)
                if n in means:
                    merged[f'{arm}_N{n}'] = self.mean(means[n][0])
            out[str(n)] = [{'method': k, 'mean': merged[k]} for k in sorted(merged, key=merged.get)]
        return out

    # ------------------------------------------------------------------------------ subgroups (S8)
    def subgroups(self):
        np, sc = self.np, self.sc
        groups = {'unloaded': sc.state == 1, 'loaded_or_pending': np.isin(sc.state, (2, 3)), 'unknown': sc.state == 0,
                  'plate1': sc.plate == 1, 'plate2': sc.plate == 2}
        positive = sc.masks['event'] & (sc.event == 1)
        counts = {}
        for g, sel in groups.items():
            pos = positive & sel
            onsets = {(int(m), int(p), int(o)) for m, p, o in zip(sc.member[pos], sc.plate[pos], sc.onset[pos])}
            counts[g] = {'issued_rows': int(sel.sum()), 'impulse_rows': int((sc.masks['impulse'] & sel).sum()),
                         'event_rows': int((sc.masks['event'] & sel).sum()), 'positive_rows': int(pos.sum()), 'distinct_onsets': len(onsets)}
        names = {name: [name] for name in FIXED}
        for arm in PRIMARY + ('C4',):
            for n in self.rungs:
                ids = family_ids(self.allocation, arm, None, n)
                if ids:
                    names[f'{arm}_N{n}'] = ids
        rowwise = {}
        for name, ids in names.items():
            block = {}
            for g, sel in groups.items():
                m = sc.masks['impulse'] & sel
                vals = [float(np.mean(np.abs(s[1][m] - sc.impulse[m]))) for s in (sc.series(i) for i in ids) if s is not None and m.any()]
                block[g] = float(np.mean(vals)) if vals else None
            rowwise[name] = block
        m = sc.masks['event']
        reliability = {}
        for name, ids in names.items():
            if name.startswith('C4') or not name.endswith((f'_N{self.b12}', f'_N{self.n_max}')) and name not in FIXED:
                continue
            probs = [s[0][m] for s in (sc.series(i) for i in ids) if s is not None]
            if not probs:
                continue
            p = np.mean(probs, axis=0)
            bins = np.minimum((p * 10).astype(int), 9)
            reliability[name] = [{'bin': b, 'rows': int((bins == b).sum()),
                                  'mean_forecast': float(p[bins == b].mean()) if (bins == b).any() else None,
                                  'observed_rate': float(sc.event[m][bins == b].mean()) if (bins == b).any() else None} for b in range(10)]
        return {'counts': counts, 'mean_abs_error_rowwise': rowwise, 'reliability_bins_replicate_mean_probability': reliability}


def training_per_rung(fit_complete):
    """People, walks, rows and onsets of every training set, and updates and examples of every fit, by rung."""
    fields = ('walks', 'issue_rows', 'impulse_rows', 'event_rows', 'positive_rows', 'distinct_onsets')
    sets = {}
    for key, entry in fit_complete['training_sets'].items():
        sets.setdefault(int(key[1:4]), []).append(entry)
    table = {}
    for n, entries in sorted(sets.items()):
        row = {'training_sets': len(entries), 'people': n}
        for f in fields:
            vals = [e[f] for e in entries]
            row[f] = {'mean': sum(vals) / len(vals), 'min': min(vals), 'max': max(vals)}
        table[str(n)] = row
    fits = {}
    for c in fit_complete['checkpoints']:
        arm, rung = c['id'].split('|')[:2]
        e = fits.setdefault(arm, {}).setdefault(str(int(rung[1:])), {'fits': 0, 'rows': [], 'updates': [], 'examples_drawn': []})
        e['fits'] += 1
        for f in ('rows', 'updates', 'examples_drawn'):
            if c.get(f) is not None:
                e[f].append(c[f])
    for arm in fits.values():
        for e in arm.values():
            for f in ('rows', 'updates', 'examples_drawn'):
                e[f] = {'min': min(e[f]), 'max': max(e[f])} if e[f] else None
    return {'training_sets': table, 'fits_by_arm_and_rung': fits}


def clean(obj):
    """NaN and infinity (a person without a row in a mask) become null so the file is strict JSON."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, float) and (obj != obj or obj in (float('inf'), float('-inf'))):
        return None
    return obj


def check_against_results(tables, results):
    """Recompute full-grid values that RESULTS.json holds; return the largest absolute difference."""
    worst = 0.
    for endpoint in ('impulse', 'event'):
        for fam in PRIMARY:
            means = tables.means(fam, endpoint, endpoint)
            for n, v in means.items():
                worst = max(worst, abs(tables.mean(v[0]) - results['curves'][endpoint][fam][str(n)]['mean']))
        for arm, block in tables.arms(endpoint, endpoint).items():
            held = results['secondary_arms'][arm][endpoint]
            for n, value in block['curve'].items():
                worst = max(worst, abs(value - held['curve'][n]))
            if 'delta_N_max_vs_12' in block:
                worst = max(worst, abs(block['delta_N_max_vs_12']['delta'] - held['delta_N_max_vs_12']['delta']))
    first = results['F3_past_load_gate_first_test']['grid24']
    again = tables.sc.contrast(tables.sc.person_error('F3_gate_trainable', 'impulse', 'impulse_grid24'),
                               tables.sc.person_error('C1', 'impulse', 'impulse_grid24'), 'impulse')
    for key in ('delta', 'base_mean', 'p_two_sided'):
        worst = max(worst, abs(again[key] - first[key]))
    need(results['counts']['grid24_impulse_rows'] == int(tables.sc.masks['impulse_grid24'].sum()), 'grid rows differ from RESULTS.json')
    need(worst <= TOLERANCE, f'recomputed values differ from RESULTS.json by {worst}')
    return worst


def run(cfg, allocation_path, fit_complete_path, seal_path, results_sha):
    single_thread_env()
    results_path = HERE / 'RESULTS.json'
    need(sha_file(results_path) == results_sha, 'RESULTS.json differs from the given sha256')
    repo = Path(cfg.get('publish_repo') or cfg['repo_root'])
    rel = results_path.resolve().relative_to(repo.resolve()).as_posix()
    need(committed_sha(repo, rel) == results_sha, 'RESULTS.json is not committed at HEAD with that sha256')
    results = read_json(results_path)
    need(results['forecasts_seal_sha256'] == sha_file(seal_path) and results['fit_complete_sha256'] == sha_file(fit_complete_path)
         and results['p2_sha256'] == sha_file(HERE / P2_NAME), 'RESULTS.json was made from other seals')
    scorer = Scorer(cfg, allocation_path, fit_complete_path, seal_path, allowed_groups=('PRIMARY-BELOW-NMAX', 'NMAX', 'OTHER'))
    score_lock(cfg, 'SUP', scorer, {'results_sha256': results_sha})
    t = Tables(scorer)
    worst = check_against_results(t, results)
    sup = {'schema': 'walking-force-scale-results-supplement-v1', 'protocol_sha256': sha_file(HERE / 'PROTOCOL.json'),
           'results_sha256': results_sha, 'p2_sha256': results['p2_sha256'], 'fit_complete_sha256': results['fit_complete_sha256'],
           'forecasts_seal_sha256': results['forecasts_seal_sha256'], 'n_max': t.n_max, 'rungs': t.rungs,
           'status': 'Computed after S-c, when RESULTS.json had been read, by code written afterwards, from the same sealed '
                     'forecasts with the scorer of score.py. No number in RESULTS.json is changed. Every table here is '
                     'descriptive; the labels of the success rule are those of RESULTS.json (full grid).',
           'max_abs_difference_from_RESULTS_json': worst}
    grid = {'schedule': 'per walk, 8 groups of 3 consecutive eligible times spread evenly over t < n - 119; 48 plate rows; '
                        'walks with fewer than 24 eligible times are left out',
            'support': {e: t.rows(f'{e}_grid24', e) for e in ('impulse', 'event')}}
    positive = scorer.masks['event_grid24'] & (scorer.event == 1)
    grid['support']['event']['positive_rows'] = int(positive.sum())
    grid['support']['event']['distinct_onsets'] = len({(int(m), int(p), int(o)) for m, p, o in
                                                       zip(scorer.member[positive], scorer.plate[positive], scorer.onset[positive])})
    for e in ('impulse', 'event'):
        mk = f'{e}_grid24'
        grid[e] = {'families': t.families(e, mk), 'frozen_and_controls': t.fixed(e, mk), 'secondary_arms': t.arms(e, mk),
                   'G8_one_walk_each_minus_three_walks_each': t.g8(e, mk), 'earlier_emg_rows': t.early(e, '_grid24'), 'ranking': t.ranking(e, mk)}
    sup['grid24'] = grid
    sup['early_rows'] = {e: t.early(e) for e in ('impulse', 'event')}
    sup['same_rung'] = {e: t.arms(e, e, curves=False) for e in ('impulse', 'event')}
    sup['G8_means'] = {e: t.g8(e, e) for e in ('impulse', 'event')}
    sup['ranking'] = {e: t.ranking(e, e) for e in ('impulse', 'event')}
    sup['subgroups'] = t.subgroups()
    sup['training_per_rung'] = training_per_rung(scorer.fit_complete)
    digest = write_json(Path(cfg['out_dir']) / 'RESULTS-SUPPLEMENT.json', clean(sup), exclusive=True)
    return sup, digest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--config', required=True)
    ap.add_argument('--allocation', default=str(HERE / 'ALLOCATION.json'))
    ap.add_argument('--fit-complete', default=str(HERE / 'FIT-COMPLETE.json'))
    ap.add_argument('--seal', default=str(HERE / 'FORECASTS-SEAL.json'))
    ap.add_argument('--results-sha', required=True)
    args = ap.parse_args()
    sup, digest = run(load_config(args.config), args.allocation, args.fit_complete, args.seal, args.results_sha)
    print(json.dumps({'max_abs_difference_from_RESULTS_json': sup['max_abs_difference_from_RESULTS_json'], 'sha256': digest}))


if __name__ == '__main__':
    main()
