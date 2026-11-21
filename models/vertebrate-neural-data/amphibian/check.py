"""Check each primary trial independently from archive sample counts and scalar clocks."""
import argparse
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from scipy.io import loadmat

from acquire import verify_archive


def assess(path, result_path):
    saved = json.loads(result_path.read_text())
    assert verify_archive(path) == saved['archive_sha256']
    weights = json.loads((Path(__file__).parent/'reference/weights.json').read_text())['weights']
    methods = ['shared_model', 'online_rate', 'recency', 'uniform']
    total, largest = 0, 0.0
    with ZipFile(path) as archive:
        for experiment, record in saved['experiments'].items():
            data = loadmat(BytesIO(archive.read(f'mode_paper_data/{experiment}/data.mat')),
                           squeeze_me=True, struct_as_record=False)['data']
            k = len(data.spike_times.all_spike_times)
            rate = int(data.spike_times.sampling_rate_in_Hz)
            assert rate == 10000 and k == record['candidate_units']
            start, end = data.stimulus.repeat_begin_times, data.stimulus.repeat_end_times
            eligible = np.flatnonzero(end - start >= rate * 10)[:10]
            valid, invalid = [], []
            for i in eligible:
                source_row = int(i + 1)
                begin, stop = int(start[i]), int(start[i] + 10 * rate)
                cells = []
                for cell in data.spike_times.all_spike_times:
                    a = np.atleast_1d(cell)
                    cells.append(a[(a > begin) & (a < stop)])
                if any((np.diff(c.astype(np.int64)) < 0).any() for c in cells):
                    invalid.append(source_row)
                    continue
                first_bin = (begin + 9)//10
                stop_bound = stop//10
                n = np.zeros((stop_bound-first_bin, k), dtype=np.int64)
                for u, events in enumerate(cells):
                    bins = (events.astype(np.int64) + 9)//10 - 1
                    bins = bins[(bins >= first_bin) & (bins < stop_bound)]
                    np.add.at(n[:,u], bins-first_bin, 1)
                occupied = np.flatnonzero(n.sum(axis=1))
                next_count = n[occupied[1:]].sum(axis=1)
                assert int((next_count>1).sum()) == record['qc_by_trial'][len(valid)]['unresolved_multi_spike_targets']
                tally = np.zeros((4,3))
                cumulative = np.zeros(k)
                trace = np.zeros((3,k))
                denom = 0
                for j, (tick, next_tick) in enumerate(zip(occupied[:-1], occupied[1:])):
                    obs = n[tick]
                    if j:
                        trace *= np.exp(-(tick-occupied[j-1])/np.array([10.,100.,1000.]))[:,None]
                    trace += obs
                    cumulative += obs
                    if n[next_tick].sum() != 1:
                        continue
                    winner = np.flatnonzero(n[next_tick])[0]
                    logcount = np.log1p(cumulative)
                    lt = np.log1p(trace)
                    score = weights[0]*logcount + weights[1]*lt[0] + weights[2]*lt[1] + weights[3]*lt[2] + weights[4]*(obs>0)
                    logits = np.stack([score, logcount, logcount + lt[1], np.zeros(k)])
                    y = logits[:,winner]
                    greater = (logits>y[:,None]).sum(axis=1)
                    equal = (logits==y[:,None]).sum(axis=1)
                    loss = np.log(np.exp(logits - y[:,None]).sum(axis=1))
                    tally += np.column_stack([loss, (greater==0)/equal, 1+greater+(equal-1)/2])
                    denom += 1
                for key, actual in zip(methods, tally/denom, strict=True):
                    item = record['methods'][key]['by_trial'][len(valid)]
                    assert item['trial'] == source_row and item['rows'] == denom
                    want = np.array([item[q] for q in ['log_loss','top1','mean_rank']])
                    err = float(np.max(np.abs(actual-want)))
                    largest = max(largest, err)
                    if err > 1e-9:
                        raise ValueError(f'{experiment} repeat {source_row} {key}: {actual} differs from {want}')
                total += denom
                valid.append(source_row)
            assert valid == [i['source_repeat_row'] for i in record['intervals']]
            assert invalid == [i['source_repeat_row'] for i in record['rejected_packets']]
    return dict(primary_resolved_forecasts=total, largest_trial_metric_error=largest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.archive, args.results), indent=2))
