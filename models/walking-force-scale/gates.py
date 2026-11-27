"""Stage S0 engineering gates on the 12 earlier fit people only (protocol section 13).

  part-b  (runtime B)  whitelist audit; Q6 verdict of the 36 fit walks through the bounded-inflation
                       probe path; G1 feature port; tree-input and compact caches; trees R0; M2 and S5
                       at N = 12; F2 agreement; F4 refit; C2 reference; G3 for the NumPy/scikit-learn
                       methods; one-row against batched issue; tree timing.
  part-a  (runtime A)  G0 training replay; G2 end to end; reload equality; C4 and S3 smoke and timing;
                       F1 issue; G3 and one-row/batched issue for M1, C4 and F1.
  report               merge both parts into S0-GATES.json (no local paths).

Reads the earlier fit walks and sealed fit artifacts read only, by sha256. Writes only to the private
and output folders named in the configuration.
"""
import argparse
import json
import sys
import time
import zlib
from pathlib import Path

from common import (FIT12, FIT_PREVALENCE_12, HERE, code_hashes, load_config, need, read_json, sha_file,
                    single_thread_env, write_json)

PINS = {
    'belgium.npz': 'd81af88596189aeacf7b7f4ff03c30d7087d3f7a8fc1da3539d6de393803a5db',
    'MODELS.joblib': '2c3f642ecf571cf0e391895bf3e393985faf43a0d002c46835b0f16b7a8b15dd',
    'FIT.npz': 'dfe83f827a5468d01023f8f6a0848fa434768fca78e62c69d529dcf3a7fec802',
    'common-six.npz': 'aa499793a7d84488befd94bc2a628df490896700291af58d2befa0bd1d6bb3bf',
}
SEALED_THREE_PASS = read_json(HERE / 'PROTOCOL.json')['data_sources']['recipe_sources_read_only']
TOL_IMPULSE, TOL_PROB = 1e-4, 1e-6
ONNX_TOL_IMPULSE, ONNX_TOL_PROB = 0.000017, 0.00000026


def maxdiff(a, b):
    import numpy as np
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return float(np.max(np.abs(a - b))) if len(a) else 0.0


def g3_ticks(n_ticks):
    """Deterministic test ticks per walk: eight evenly spaced issue ranks, always including the last."""
    import numpy as np
    return sorted(set(np.linspace(0, n_ticks - 1, 8).round().astype(int).tolist()))


# ======================================================================================= part B
def part_b(cfg):
    single_thread_env()
    import numpy as np
    import joblib
    import c3dread
    import compact
    import extract
    import frozen
    import linear
    import qualify
    import trees
    import walks

    out, started = {}, time.perf_counter()
    private = Path(cfg['private_dir'])
    fit = walks.load_fit12(cfg)
    table = walks.walk_table([])
    pom, com = walks.person_maps(table)
    out['fit_walks'] = {'walks': len(fit), 'people': len({f[0] for f in fit}), 'sha256': {f'{s}/{t}': d for s, t, _m, _b, d in fit},
                        'checks': 'size and CRC-32 against the pinned central directory; sha256 against the earlier readback'}

    # --- whitelist audit, direct verdict and bounded-inflation probe verdict on every fit walk
    probe = []
    for s, t, m, data, _d in fit:
        audit = []
        parsed = c3dread.parse(data[:262144], audit)
        verdict, reasons, _lay, desc = c3dread.layout(parsed, m['expanded_bytes'])
        leaked = [a for a in audit if a[0] != 'group-name' and a[1] not in c3dread.NAME_GROUPS]
        valued = [a for a in audit if a[0] == 'parameter-value'
                  and c3dread.VALUE_WHITELIST[a[1]] is not None and a[2] not in c3dread.VALUE_WHITELIST[a[1]]]
        comp = zlib.compressobj(6, zlib.DEFLATED, -15)
        body = comp.compress(data) + comp.flush()
        name = m['path'].encode()
        local = qualify.LOCAL.pack(b'PK\x03\x04', 20, 0, 8, 0, 0, zlib.crc32(data), len(body), len(data), len(name), 0)
        blob = local + name + body
        member = {**m, 'compressed_bytes': len(body), 'local_header_offset': 0, 'next_header_offset': len(blob)}
        rec = qualify.probe_walk(member, lambda a, b: blob[a:b])
        p, data_start = c3dread.needed_bytes(data)
        h_end = c3dread.parameter_end(data)
        lo, hi = 0, len(body)
        while lo < hi:  # fewest compressed bytes that inflate to the parameter end (descriptive)
            mid = (lo + hi) // 2
            got = len(zlib.decompressobj(-15).decompress(body[:mid], h_end))
            lo, hi = (lo, mid) if got >= h_end else (mid + 1, hi)
        probe.append({'walk': f'{s}/{t}', 'direct_verdict': verdict, 'direct_reasons': reasons,
                      'probe_verdict': rec['verdict'], 'probe_reasons': rec['reasons'],
                      'probe_inflated_bytes': rec['inflated_bytes'], 'parameter_end_H': h_end,
                      'data_start_bytes': (data_start - 1) * 512, 'compressed_needed_level6': lo,
                      'compressed_received': rec['compressed_bytes_received'],
                      'names_or_values_decoded_outside_whitelist': len(leaked) + len(valued),
                      'groups_present': parsed['groups'], 'six_names': desc['muscle_names_present']})
    out['Q6_fit_walks'] = {
        'walks': len(probe), 'direct_Q6': sum(r['direct_verdict'] == 'Q6' for r in probe),
        'probe_Q6': sum(r['probe_verdict'] == 'Q6' for r in probe),
        'inflation_stopped_at_parameter_end': all(r['probe_inflated_bytes'] == r['parameter_end_H'] for r in probe),
        'no_sample_byte_inflated': all(r['probe_inflated_bytes'] <= r['data_start_bytes'] for r in probe),
        'decodes_outside_whitelist': sum(r['names_or_values_decoded_outside_whitelist'] for r in probe),
        'compressed_needed_level6_range': [min(r['compressed_needed_level6'] for r in probe), max(r['compressed_needed_level6'] for r in probe)],
        'groups_present': sorted({g for r in probe for g in r['groups_present']}),
        'note': 'Archive bytes of the fit walks are not cached, so each walk was re-deflated (level 6) and fed to the same probe code.',
        'passed': all(r['direct_verdict'] == 'Q6' and r['probe_verdict'] == 'Q6' for r in probe)}

    # --- G1: our C3D reader and feature port against the earlier sealed arrays
    parts_i, parts_t, lengths = [], [], {}
    for i, (s, t, m, data, _d) in enumerate(fit):
        inp, tgt, n = extract.walk_arrays(data, i, m['expanded_bytes'])
        parts_i.append(inp)
        parts_t.append(tgt)
        lengths[i] = n
    inputs = extract.concat(parts_i, extract.INPUT_FIELDS)
    targets = extract.concat(parts_t, extract.TARGET_FIELDS)
    ref = {k: dict(np.load(Path(cfg['features_ref_dir']) / f'{k}.npz')) for k in ('FEATURES', 'TARGETS', 'SUPPORT')}
    sup = extract.supports(inputs, targets)
    g1 = {'rows': int(len(inputs['plate'])), 'reference_rows': int(len(ref['FEATURES']['plate']))}
    g1['inputs_bit_identical'] = all(np.array_equal(inputs[k], ref['FEATURES'][k], equal_nan=True) for k in
                                     ('member_index', 'issue_tick', 'plate', 'emg_rms_v', 'early_emg_rms_v', 'past_force_n',
                                      'emg_ok', 'early_emg_ok', 'past_force_ok', 'state_at_issue'))
    g1['targets_bit_identical'] = all(np.array_equal(targets[k], ref['TARGETS'][k], equal_nan=True) for k in
                                      ('event_new_load', 'signed_impulse_ns', 'onset_tick', 'negative_issue_state'))
    names = {'impulse': 'impulse_matched', 'event': 'event_matched', 'impulse_early': 'impulse_early_matched', 'event_early': 'event_early_matched'}
    g1['support_identical'] = all(np.array_equal(sup[a], ref['SUPPORT'][b]) for a, b in names.items())
    g1['impulse_rows'], g1['event_rows'] = int(sup['impulse'].sum()), int(sup['event'].sum())
    g1['positive_rows'] = int(np.nansum(targets['event_new_load'][sup['event']]))
    g1['passed'] = (g1['inputs_bit_identical'] and g1['targets_bit_identical'] and g1['support_identical']
                    and (g1['rows'], g1['impulse_rows'], g1['event_rows'], g1['positive_rows']) == (9946, 9586, 9150, 324))
    out['G1_feature_port'] = g1

    # --- tree-input cache against the earlier matched-baselines rows
    matched = Path(cfg['matched_dir'])
    need(sha_file(matched / 'private/FIT.npz') == PINS['FIT.npz'], 'FIT.npz pin')
    fitnpz = dict(np.load(matched / 'private/FIT.npz'))
    tt = trees.tree_table(inputs, targets, pom)
    tree_eq = {'rows': len(tt['rows']) == len(fitnpz['plate'])}
    if tree_eq['rows']:
        for a, b in (('member', 'member_index'), ('tick', 'issue_tick'), ('history', 'history'), ('available', 'available'),
                     ('event', 'event'), ('impulse', 'impulse'), ('event_supported', 'event_supported'),
                     ('impulse_supported', 'impulse_supported'), ('person', 'participant_index')):
            tree_eq[a] = bool(np.array_equal(tt[a], fitnpz[b], equal_nan=True))
        tree_eq['plate'] = bool(np.array_equal(inputs['plate'][tt['rows']], fitnpz['plate']))
    out['tree_input_cache'] = {'equal_by_key': tree_eq, 'passed': all(tree_eq.values())}

    # --- compact cache (G2, first half) against the earlier encoded 12-person cache
    gen = Path(cfg['generalization_dir'])
    need(sha_file(gen / 'private/prepared/belgium.npz') == PINS['belgium.npz'], 'belgium.npz pin')
    belgium = dict(np.load(gen / 'private/prepared/belgium.npz'))
    ctable = compact.training_table(inputs, targets, pom)
    cache_eq = {k: bool(np.array_equal(ctable[k], belgium[k], equal_nan=True)) for k in belgium}
    out['G2_encoded_cache'] = {'equal_by_key': cache_eq, 'passed': all(cache_eq.values())}

    # --- trees R0: M3 at N = 12 against the sealed tree file
    need(sha_file(matched / 'private/trees/MODELS.joblib') == PINS['MODELS.joblib'], 'MODELS.joblib pin')
    sealed = joblib.load(matched / 'private/trees/MODELS.joblib')
    t0 = time.perf_counter()
    m3 = trees.fit_m3(tt)
    m3_seconds = time.perf_counter() - t0
    xs = trees.tree_features(tt['history'], tt['available'], sealed['center'], sealed['scale'], sealed['fallback'])
    p_ref, i_ref = sealed['models']['event'].predict_proba(xs)[:, 1], sealed['models']['impulse'].predict(xs)
    p_m3, i_m3 = trees.predict_m3(m3, tt['history'], tt['available'])
    xm = trees.tree_features(tt['history'], tt['available'], m3['center'], m3['scale'], m3['fallback'])
    out['trees_R0'] = {
        'scaling_equal': bool(np.array_equal(m3['center'], sealed['center']) and np.array_equal(m3['scale'], sealed['scale'])),
        'fallback_equal': m3['fallback'] == sealed['fallback'],
        'event_bit_identical': bool(np.array_equal(p_m3, p_ref)),
        'impulse_residual_bit_identical': bool(np.array_equal(m3['models']['impulse'].predict(xm), i_ref)),
        'rows': int(len(p_m3)), 'fit_seconds_two_trees_9586_rows': m3_seconds}
    out['trees_R0']['passed'] = all(v for k, v in out['trees_R0'].items() if k.endswith(('equal', 'identical')))

    # --- M2 and S5 at N = 12 against the sealed 12-person comparator file
    controls = joblib.load(gen / 'private/fit/00-controls.joblib')
    cols = compact.compact_columns(ctable['x'])
    m2, s5 = linear.fit_m2(ctable), trees.fit_s5(ctable)
    res = {}
    for name, mine, key in (('M2', m2, 'ridge_and_logistic'), ('S5', s5, 'histogram_gradient_boosting')):
        load, reg = controls['controls'][key]
        res[name] = {'event_bit_identical': bool(np.array_equal(mine['models']['event'].predict_proba(cols)[:, 1], load.predict_proba(cols)[:, 1])),
                     'impulse_bit_identical': bool(np.array_equal(mine['models']['impulse'].predict(cols), reg.predict(cols)))}
    res['prior_equal'] = controls['load_prior'] == FIT_PREVALENCE_12
    res['passed'] = all(all(v.values()) for k, v in res.items() if isinstance(v, dict)) and res['prior_equal']
    out['M2_S5_R0'] = res

    # --- F2 agreement with M3 at N = 12 on fit rows (reported, not a stop rule)
    repo = Path(cfg['repo_root'])
    frozen.pinned(repo)
    p_f2, i_f2 = frozen.issue_f2(repo, inputs, tt['rows'])
    out['F2_vs_M3'] = {'rows': int(len(p_f2)), 'max_abs_impulse_Ns': maxdiff(i_f2, i_m3), 'max_abs_probability': maxdiff(p_f2, p_m3),
                       'rows_beyond_impulse_tolerance': int(np.sum(np.abs(i_f2 - i_m3) > ONNX_TOL_IMPULSE)),
                       'rows_beyond_probability_tolerance': int(np.sum(np.abs(p_f2 - p_m3) > ONNX_TOL_PROB)),
                       'tolerances': [ONNX_TOL_IMPULSE, ONNX_TOL_PROB], 'stop_rule': False}

    # --- F4 refit and the vectorised predictor
    features = {**{k: inputs[k] for k in ('emg_rms_v', 'early_emg_rms_v', 'past_force_n', 'member_index', 'issue_tick')},
                'person_id': np.asarray([com[int(m)] for m in inputs['member_index']])}
    support = {'event_matched': sup['event'], 'event_early_matched': sup['event_early'],
               'impulse_matched': sup['impulse'], 'impulse_early_matched': sup['impulse_early']}
    refit = linear.f4_refit(features, targets, support)
    published = dict(np.load(repo / 'models/force-baselines/common-six.npz'))
    need(sha_file(repo / 'models/force-baselines/common-six.npz') == PINS['common-six.npz'], 'common-six pin')
    f4 = {'arrays': len(published), 'same_keys': set(refit) == set(published),
          'array_for_array_identical': all(np.array_equal(refit[k], published[k]) for k in published),
          'max_abs_difference': max(maxdiff(refit[k].ravel(), published[k].ravel()) for k in published)}
    mod, grid = frozen.f4_grid(repo)
    rows = np.flatnonzero(sup['impulse_early'])[::40]
    worst = 0.0
    for r in rows.tolist():
        for endpoint in ('event', 'impulse'):
            for group, arms in linear.F4_ARMS.items():
                for arm in arms:
                    for p in linear.PENALTY_GRID:
                        one = grid.predict(endpoint=endpoint, group=group, arm=arm, penalty=p, emg_rms_v=inputs['emg_rms_v'][r],
                                           past_force_n=inputs['past_force_n'][r], earlier_emg_rms_v=inputs['early_emg_rms_v'][r])
                        vec = linear.f4_predict(grid.coefficients, endpoint, group, arm, p, inputs['emg_rms_v'][r:r + 1],
                                                inputs['past_force_n'][r:r + 1], inputs['early_emg_rms_v'][r:r + 1])[0]
                        worst = max(worst, abs(one - vec))
    f4['vectorised_vs_published_rows_checked'] = int(len(rows))
    f4['vectorised_vs_published_max_abs'] = worst
    f4['passed'] = f4['same_keys'] and f4['array_for_array_identical'] and worst <= 1e-12
    out['F4_refit'] = f4

    # --- C1/C2 references from our own rows
    prevalence, median = trees.fit_reference(tt)
    pre = json.loads((repo / 'benchmarks/walking-neural-scaling/checkpoints/preprocessing.json').read_text())
    out['C1_C2_reference'] = {'prevalence': prevalence, 'prevalence_equal': prevalence == FIT_PREVALENCE_12,
                              'median_impulse_Ns': median, 'median_equal_published_fallback': median == pre['missing_force_fallback_ns'],
                              'passed': prevalence == FIT_PREVALENCE_12 and median == pre['missing_force_fallback_ns']}

    # --- forecasts of the NumPy / scikit-learn methods on the input-valid fit rows
    valid = np.flatnonzero(extract.input_valid(inputs))
    f3m = frozen.f3_models(repo)
    choice = {f'{e}/{g}/{a}': 1.0 for e in ('event', 'impulse') for g, arms in linear.F4_ARMS.items() for a in arms}

    def issue_all(inp, rows):
        x, pers = compact.compact_inputs(inp, rows)
        h, av = trees.tree_history(inp, rows)
        res = {'M2': linear.predict_m2(m2, x, pers), 'S5': trees.predict_compact(s5, x, pers),
               'M3': trees.predict_m3(m3, h, av), 'C1': frozen.control_c1(inp, rows),
               'C2': frozen.control_c2(rows, median), 'C3': frozen.control_c3(inp, rows),
               'F2': frozen.issue_f2(repo, inp, rows)}
        res.update(frozen.issue_f3(f3m, inp, rows))
        res.update(frozen.issue_f4(grid, choice, inp, rows))
        return res

    batch = issue_all(inputs, valid)
    again = issue_all(inputs, valid)
    repeat_identical = all(np.array_equal(batch[k][j], again[k][j], equal_nan=True) for k in batch for j in (0, 1))
    sample = valid[np.linspace(0, len(valid) - 1, 240).round().astype(int)]
    one_row = {k: ([], []) for k in batch}
    for r in sample.tolist():
        got = issue_all(inputs, np.array([r]))
        for k, (p, i) in got.items():
            one_row[k][0].append(p[0])
            one_row[k][1].append(i[0])
    pos = np.searchsorted(valid, sample)
    batch_vs_row = {}
    for k in batch:
        bi, bp = batch[k][1][pos], batch[k][0][pos]
        ri, rp = np.asarray(one_row[k][1]), np.asarray(one_row[k][0])
        fin = np.isfinite(bi)
        batch_vs_row[k] = {'impulse': maxdiff(bi[fin], ri[fin]), 'probability': maxdiff(bp[fin], rp[fin]),
                           'nan_pattern_equal': bool(np.array_equal(np.isnan(bi), np.isnan(ri)))}
    out['issue_numpy_sklearn'] = {
        'methods': sorted(batch), 'rows': int(len(valid)), 'fixed_order_repeat_bit_identical': repeat_identical,
        'one_row_vs_batch_rows': int(len(sample)), 'one_row_vs_batch_max_abs': batch_vs_row,
        'passed': repeat_identical and all(v['impulse'] <= TOL_IMPULSE and v['probability'] <= TOL_PROB and v['nan_pattern_equal']
                                           for v in batch_vs_row.values())}

    # --- G3: replace every sample after t with noise
    rng = np.random.default_rng(20261127)
    pert_parts, orig_rows, g3_inputs_ok, tested = [], [], True, 0
    offsets = np.concatenate(([0], np.cumsum([len(p['plate']) for p in parts_i])))
    for i, (s, t, m, data, _d) in enumerate(fit):
        emg, force = extract.read_walk(data, m['expanded_bytes'])
        ticks = extract.issue_ticks(len(force))
        for rank in g3_ticks(len(ticks)):
            tick = int(ticks[rank])
            e2, f2 = emg.copy(), force.copy()
            e2[tick + 1:] = rng.normal(0, 3 * np.nanstd(emg), size=e2[tick + 1:].shape)
            f2[tick + 1:] = rng.normal(0, 3 * np.nanstd(force), size=f2[tick + 1:].shape)
            got = extract.issue_inputs(e2, f2, i)
            keep = got['issue_tick'] <= tick
            mine = {k: v[keep] for k, v in got.items()}
            base_rows = np.arange(offsets[i], offsets[i + 1])[parts_i[i]['issue_tick'] <= tick]
            same = all(np.array_equal(mine[k], inputs[k][base_rows], equal_nan=True) for k in extract.INPUT_FIELDS)
            g3_inputs_ok &= same
            tested += 1
            at = got['issue_tick'] == tick
            pert_parts.append({k: v[at] for k, v in got.items()})
            orig_rows.append(np.arange(offsets[i], offsets[i + 1])[parts_i[i]['issue_tick'] == tick])
    pert = extract.concat(pert_parts, extract.INPUT_FIELDS)
    orig_rows = np.concatenate(orig_rows)
    pv = np.flatnonzero(extract.input_valid(pert))
    f_pert = issue_all(pert, pv)
    f_orig = issue_all(inputs, orig_rows[pv])
    g3_forecasts_ok = all(np.array_equal(f_pert[k][j], f_orig[k][j], equal_nan=True) for k in f_pert for j in (0, 1))
    out['G3_numpy_sklearn'] = {'walk_tick_cases': tested, 'inputs_unchanged_all_earlier_rows': bool(g3_inputs_ok),
                               'forecast_rows': int(len(pv)), 'methods': sorted(f_pert),
                               'forecasts_unchanged': bool(g3_forecasts_ok), 'passed': bool(g3_inputs_ok and g3_forecasts_ok)}

    # --- private arrays for part A (fit people only; never committed)
    for name, arrays, fields in (('FIT12-INPUTS.npz', inputs, extract.INPUT_FIELDS), ('FIT12-TARGETS.npz', targets, extract.TARGET_FIELDS),
                                 ('G3-PERTURBED-INPUTS.npz', pert, extract.INPUT_FIELDS)):
        path = private / name
        if path.exists():
            path.unlink()
        extract.save_npz(path, arrays, fields)
    np.save(private / 'G3-ORIGINAL-ROWS.npy', orig_rows)
    np.savez(private / 'FIT12-CTABLE.npz', **ctable)
    out['runtime'] = runtime_info()
    out['seconds'] = time.perf_counter() - started
    return out


# ======================================================================================= part A
def part_a(cfg):
    single_thread_env()
    import numpy as np
    import torch
    from safetensors.torch import load_file
    import compact
    import extract
    import frozen
    import threepass
    import walks

    threepass.setup_runtime()
    out, started = {}, time.perf_counter()
    private, scratch = Path(cfg['private_dir']), Path(cfg['scratch_dir'])
    gen = Path(cfg['generalization_dir'])
    need(sha_file(gen / 'private/prepared/belgium.npz') == PINS['belgium.npz'], 'belgium.npz pin')
    belgium = dict(np.load(gen / 'private/prepared/belgium.npz'))
    ours = dict(np.load(private / 'FIT12-CTABLE.npz'))
    out['our_cache_equals_earlier_cache'] = all(np.array_equal(ours[k], belgium[k], equal_nan=True) for k in belgium)

    def replay(table, label, save_dir=None):
        batch = threepass.TrainingBatch(table)
        runs = []
        for method, passes in (('loop3', 3), ('lstm', None)):
            for seed in (20261124, 20261125, 20261126):
                model, loss, seconds = threepass.train(batch, seed, passes=passes)
                name = f'00-{method}-{seed}'
                ref_path = gen / 'private/fit' / f'{name}.safetensors'
                # The sealed three-pass references are pinned in PROTOCOL.json; check the file before it is used.
                # The LSTM references have no protocol pin (they are not a protocol model); their sha256 is recorded.
                ref_sha = sha_file(ref_path)
                ref_pin = SEALED_THREE_PASS['sealed_12_person_three_pass'].get(str(seed)) if method == 'loop3' else None
                need(ref_pin is None or ref_sha == ref_pin, f'reference checkpoint {name} differs from its PROTOCOL.json pin')
                ref = load_file(str(ref_path))
                mine = threepass.state_tensors(model)
                receipt = read_json(gen / 'private/fit' / f'{name}.json')
                row = {'name': name, 'reference_sha256': ref_sha, 'reference_protocol_pin': ref_pin,
                       'reference_equals_protocol_pin': None if ref_pin is None else ref_sha == ref_pin,
                       'tensors_identical': set(ref) == set(mine) and all(torch.equal(ref[k], mine[k]) for k in ref),
                       'last_batch_loss': loss, 'sealed_last_batch_loss': receipt['last_batch_loss'],
                       'loss_identical': loss == receipt['last_batch_loss'], 'seconds_900_updates': seconds}
                if save_dir is not None:
                    path = save_dir / f'{name}.safetensors'
                    if path.exists():
                        path.unlink()
                    row['tensor_sha256'] = threepass.save(model, path)
                    row['file_sha256_no_metadata'] = sha_file(path)
                    pin = SEALED_THREE_PASS['same_three_pass_saved_without_metadata'].get(str(seed)) if method == 'loop3' else None
                    if pin:
                        row['file_equals_protocol_pin'] = row['file_sha256_no_metadata'] == pin
                    reloaded = threepass.load(path, passes=passes)
                    x = torch.from_numpy(table['x'])  # every row of the table, as protocol section 13 asks
                    with torch.inference_mode():
                        row['reload_forecasts_identical'] = bool(torch.equal(reloaded(x), model.eval()(x)))
                    row['reload_rows_checked'] = int(x.shape[0])
                runs.append(row)
        return {'label': label, 'fit_rows': batch.rows, 'prior': batch.prior, 'runs': runs,
                'passed': all(r['tensors_identical'] and r['loss_identical'] and r.get('file_equals_protocol_pin', True)
                              and r['reference_equals_protocol_pin'] is not False
                              and r.get('reload_forecasts_identical', True) for r in runs)}

    out['G0_training_replay'] = replay(belgium, 'earlier encoded 12-person cache')
    ckdir = scratch / 'g2-checkpoints'
    ckdir.mkdir(parents=True, exist_ok=True)
    out['G2_end_to_end'] = replay(ours, 'our C3D reader, feature port and encoding', ckdir)
    out['G2_end_to_end']['passed'] &= out['our_cache_equals_earlier_cache']

    # --- C4 and S3 smoke and timing at N = 12
    batch = threepass.TrainingBatch(ours)
    torch.manual_seed(20261124)
    init = threepass.state_tensors(threepass.RecordedForecast(24, 3).float())
    c4, c4_loss, c4_seconds = threepass.train(batch, 20261124, readout_only=True)
    after = threepass.state_tensors(c4)
    out['C4_readout_smoke'] = {'frozen_layers_unchanged': all(torch.equal(init[k], after[k]) for k in init if not k.startswith('out.')),
                               'readout_changed': any(not torch.equal(init[k], after[k]) for k in init if k.startswith('out.')),
                               'last_batch_loss': c4_loss, 'seconds': c4_seconds}
    out['C4_readout_smoke']['passed'] = out['C4_readout_smoke']['frozen_layers_unchanged'] and out['C4_readout_smoke']['readout_changed']
    _s3, s3_loss, s3_seconds = threepass.train(batch, 20261124, width=96, updates=900)
    out['S3_width96_smoke'] = {'last_batch_loss': s3_loss, 'seconds_900_updates': s3_seconds}

    # --- issue: M1 (seed 20261124 replay), C4, F1 on the input-valid fit rows
    inputs = extract.load_npz(private / 'FIT12-INPUTS.npz', extract.INPUT_FIELDS)
    repo = Path(cfg['repo_root'])
    frozen.pinned(repo)
    m1 = threepass.load(ckdir / '00-loop3-20261124.safetensors')
    valid = np.flatnonzero(extract.input_valid(inputs))

    def issue_all(inp, rows):
        x, pers = compact.compact_inputs(inp, rows)
        return {'M1': threepass.forecast(m1, x, pers, batch.prior), 'C4': threepass.forecast(c4, x, pers, batch.prior),
                'F1': frozen.issue_f1(repo, inp, rows)}

    full = issue_all(inputs, valid)
    again = issue_all(inputs, valid)
    sample = valid[np.linspace(0, len(valid) - 1, 240).round().astype(int)]
    pos = np.searchsorted(valid, sample)
    rows1 = {k: [issue_all(inputs, np.array([r]))[k] for r in sample.tolist()] for k in full}
    bvr = {k: {'impulse': maxdiff(full[k][1][pos], [v[1][0] for v in rows1[k]]),
               'probability': maxdiff(full[k][0][pos], [v[0][0] for v in rows1[k]])} for k in full}
    out['issue_torch'] = {'rows': int(len(valid)), 'fixed_order_repeat_bit_identical':
                          all(np.array_equal(full[k][j], again[k][j]) for k in full for j in (0, 1)),
                          'one_row_vs_batch_max_abs': bvr, 'finite': all(np.isfinite(full[k][j]).all() for k in full for j in (0, 1))}
    out['issue_torch']['passed'] = (out['issue_torch']['fixed_order_repeat_bit_identical'] and out['issue_torch']['finite']
                                    and all(v['impulse'] <= TOL_IMPULSE and v['probability'] <= TOL_PROB for v in bvr.values()))

    # --- G3 for the torch methods
    pert = extract.load_npz(private / 'G3-PERTURBED-INPUTS.npz', extract.INPUT_FIELDS)
    orig = np.load(private / 'G3-ORIGINAL-ROWS.npy')
    pv = np.flatnonzero(extract.input_valid(pert))
    fp, fo = issue_all(pert, pv), issue_all(inputs, orig[pv])
    same = all(np.array_equal(fp[k][j], fo[k][j]) for k in fp for j in (0, 1))
    out['G3_torch'] = {'forecast_rows': int(len(pv)), 'methods': sorted(fp), 'forecasts_unchanged': bool(same), 'passed': bool(same)}
    out['runtime'] = runtime_info()
    out['seconds'] = time.perf_counter() - started
    return out


def runtime_info():
    import os
    import platform
    info = {'python': platform.python_version(), 'cpus': sorted(os.sched_getaffinity(0))}
    for name in ('numpy', 'torch', 'safetensors', 'sklearn', 'joblib', 'onnxruntime'):
        mod = sys.modules.get(name)
        if mod is not None:
            info[name] = getattr(mod, '__version__', '?')
    return info


def report(cfg):
    out_dir = Path(cfg['out_dir'])
    a, b = read_json(out_dir / 'S0-PART-A.json'), read_json(out_dir / 'S0-PART-B.json')
    gates = {
        'G0_training_replay': a['G0_training_replay']['passed'], 'G1_feature_port': b['G1_feature_port']['passed'],
        'G2_end_to_end': a['G2_end_to_end']['passed'] and b['G2_encoded_cache']['passed'],
        'trees_R0': b['trees_R0']['passed'], 'M2_S5_R0': b['M2_S5_R0']['passed'],
        'G3_past_only': b['G3_numpy_sklearn']['passed'] and a['G3_torch']['passed'],
        'one_row_vs_batch_and_fixed_order': b['issue_numpy_sklearn']['passed'] and a['issue_torch']['passed'],
        'F4_refit': b['F4_refit']['passed'], 'Q6_on_36_fit_walks': b['Q6_fit_walks']['passed'],
        'whitelist_reader': b['Q6_fit_walks']['decodes_outside_whitelist'] == 0,
        'tree_input_cache': b['tree_input_cache']['passed'], 'C1_C2_reference': b['C1_C2_reference']['passed'],
        'reload_equality': all(r.get('reload_forecasts_identical', False) for r in a['G2_end_to_end']['runs']),
        'reference_checkpoints_match_protocol_pins': all(
            r['reference_equals_protocol_pin'] for part in ('G0_training_replay', 'G2_end_to_end')
            for r in a[part]['runs'] if r['reference_protocol_pin'] is not None),
        'C4_readout_smoke': a['C4_readout_smoke']['passed'],
    }
    tests = {}
    for name in ('test_fetch_probe', 'test_assign', 'test_trend_score', 'smoke_pipeline'):
        path = out_dir / 'tests' / f'{name}.json'
        tests[name] = read_json(path) if path.exists() else 'not run'
    test_code = {f'tests/{p.name}': sha_file(p) for p in sorted((HERE / 'tests').glob('*.py'))}
    body = {'schema': 'walking-force-scale-s0-gates-v1', 'protocol_sha256': sha_file(HERE / 'PROTOCOL.json'),
            'scope': 'Stage S0 on the 12 earlier fit people only (36 walks). No new byte downloaded; no evaluation, '
                     'reserved, physics or supplement byte opened. Tests use the same 36 walks, patched copies of them '
                     'and synthetic numbers only, served by a local emulator.',
            'all_gates_passed': all(gates.values()), 'gates': gates,
            'all_tests_passed': all(isinstance(t, dict) and t.get('passed') for t in tests.values()),
            'F2_onnx_agreement_reported': b['F2_vs_M3'],
            'timing_one_thread': {'three_pass_900_updates_s': [r['seconds_900_updates'] for r in a['G0_training_replay']['runs'] if 'loop3' in r['name']],
                                  'width96_900_updates_s': a['S3_width96_smoke']['seconds_900_updates'],
                                  'readout_only_900_updates_s': a['C4_readout_smoke']['seconds'],
                                  'tree_pair_9586_rows_s': b['trees_R0']['fit_seconds_two_trees_9586_rows']},
            'interface_for_physics_source': {f: sha_file(HERE / f) for f in ('extract.py', 'c3dread.py', 'compact.py', 'threepass.py')},
            'code_sha256': {**code_hashes(), **test_code}, 'tests': tests, 'part_a': a, 'part_b': b}
    digest = write_json(HERE / 'S0-GATES.json', body)
    print(json.dumps({'all_gates_passed': body['all_gates_passed'], 'gates': gates, 'sha256': digest}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('step', choices=('part-a', 'part-b', 'report'))
    ap.add_argument('--config', required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.step == 'report':
        report(cfg)
        return
    result = (part_a if args.step == 'part-a' else part_b)(cfg)
    write_json(Path(cfg['out_dir']) / f'S0-{args.step.upper()}.json', result)
    print(json.dumps({k: v.get('passed') for k, v in result.items() if isinstance(v, dict) and 'passed' in v}, indent=1))


if __name__ == '__main__':
    main()
