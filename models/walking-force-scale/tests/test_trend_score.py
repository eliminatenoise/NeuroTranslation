"""Trend forms, vectorised bootstrap fits, Holm adjustment, labels and the paired-bootstrap p-value on
synthetic numbers.

  python -B tests/test_trend_score.py --config CFG     (runtime B)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402

import score  # noqa: E402
import trend  # noqa: E402
from common import BOOTSTRAP_DRAWS, BOOTSTRAP_SEED, load_config, write_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    cfg = load_config(ap.parse_args().config)
    r = {}
    n = np.array([12., 18., 24., 36.])
    y = 2.3 + 1.4 / np.sqrt(n)
    pred, params = trend.predictions(n, y, 56)
    r['inverse_sqrt_recovers'] = abs(params['inverse_sqrt'][0] - 2.3) < 1e-12 and abs(pred['inverse_sqrt'] - (2.3 + 1.4 / np.sqrt(56))) < 1e-12
    y2 = 0.2 + 30 / np.sqrt(n) - 0.01 * n  # free fit gives L < 0
    p2 = trend.fit_forms(n, y2)['inverse_sqrt']
    u = 1 / np.sqrt(n)
    r['nonnegative_L_refit'] = p2[0] == 0.0 and abs(p2[1] - (u @ y2) / (u @ u)) < 1e-12
    y3 = 3.0 - 0.2 * np.log2(n)
    r['log2_recovers'] = abs(trend.predictions(n, y3, 56)[0]['log2'] - (3.0 - 0.2 * np.log2(56))) < 1e-12
    r['carry_forward_is_largest_rung_below'] = trend.predictions(n, y3, 56)[0]['carry_forward'] == y3[-1]
    rng = np.random.default_rng(7)
    vals = 2.5 + rng.normal(0, .3, size=(4, 20)) + (1 / np.sqrt(n))[:, None]
    idx = np.random.default_rng(BOOTSTRAP_SEED).integers(0, 20, size=(200, 20))
    boot = trend.bootstrap_predictions(n, vals, idx, 56)
    loop = np.array([trend.predictions(n, vals[:, i].mean(axis=1), 56)[0]['inverse_sqrt'] for i in idx])
    r['vectorised_bootstrap_equals_loop'] = float(np.max(np.abs(boot['inverse_sqrt'] - loop))) < 1e-12
    tt = trend.trend_test(1.0, np.full(100, 1.0) + np.linspace(-.1, .1, 100), 0.5, np.full(100, 0.5))
    r['trend_label_slower'] = tt['label'] == 'slower'
    adj = score.holm([0.01, 0.04, 0.03])
    r['holm'] = np.allclose(adj, [0.03, 0.06, 0.06])
    s = score.Scorer.__new__(score.Scorer)
    s.np = np
    people = 16
    s.idx = {'impulse': np.random.default_rng(BOOTSTRAP_SEED).integers(0, people, size=(BOOTSTRAP_DRAWS, people))}
    base = 2.6 + np.random.default_rng(3).normal(0, .2, people)
    c = s.contrast(base * 0.9, base, 'impulse')
    r['all_negative_p_value'] = c['p_two_sided'] == 2 / (BOOTSTRAP_DRAWS + 1) and abs(c['relative'] + 0.1) < 1e-12
    r['label_helped'] = score.label(c, 0.01) == 'HELPED'
    c0 = s.contrast(base + np.random.default_rng(5).normal(0, 0.001, people), base, 'impulse')
    r['label_no_change'] = score.label(c0, 0.9) == 'PRACTICALLY NO CHANGE'
    r['label_harmed'] = score.label(s.contrast(base * 1.1, base, 'impulse'), 0.001) == 'HARMED'
    noisy = base + np.random.default_rng(9).normal(0, 0.4, people)
    r['label_inconclusive'] = score.label(s.contrast(noisy, base, 'impulse'), 0.5) == 'INCONCLUSIVE'
    partial = base.copy()
    partial[:3] = np.nan
    cp = s.contrast(partial * 0.95, base, 'impulse')
    r['secondary_support_drops_absent_people'] = cp['people'] == people - 3
    p1 = trend.p1_curve({'0': {12: 2.8, 18: 2.7, 24: 2.65}, '1': {12: 2.9, 18: 2.75, 24: 2.7}}, 56)
    r['p1_curve'] = p1['N'] == [12, 18, 24] and p1['predicted_relative_gain']['inverse_sqrt'] < 0
    r['passed'] = all(v for v in r.values())
    write_json(Path(cfg['out_dir']) / 'tests' / 'test_trend_score.json', {k: bool(v) for k, v in r.items()})
    print(json.dumps({k: bool(v) for k, v in r.items()}, indent=1))
    sys.exit(0 if r['passed'] else 1)


if __name__ == '__main__':
    main()
