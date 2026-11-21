"""Reconstruct chronological 1-ms trials and write a local, regenerable feature cache."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from scipy.io import loadmat

import reference as ref

HERE = Path(__file__).resolve().parent
SOURCES = json.loads((HERE/'sources.json').read_text())
RETINA = ('repeated_natural_movie', 'white_noise_checkerboard', 'randomly_moving_bar')


def checked(path, expected):
    if ref.digest(path) != expected:
        raise ValueError(f'Source checksum differs: {path.name}')


def integer_packet(number, cells, ids, start, stop, hz):
    times = np.concatenate(cells)
    seconds = times / hz
    native_ms = hz // 1000
    lows, highs = ref.millisecond_edges(seconds)
    if not (np.array_equal(lows, times // native_ms) and
            np.array_equal(highs, (times + native_ms - 1) // native_ms)):
        raise ValueError('Seconds and native event clock disagree')
    boundaries = np.array([start, stop], dtype=np.int64)
    lows, highs = ref.millisecond_edges(boundaries / hz)
    if not (np.array_equal(lows, boundaries // native_ms) and
            np.array_equal(highs, (boundaries + native_ms - 1) // native_ms)):
        raise ValueError('Seconds and native boundary clock disagree')
    packet = BytesIO()
    np.savez(packet, trial_id=number, unit_id=ids, start_s=start/hz, stop_s=stop/hz,
             spike_time_s=seconds, spike_end=np.cumsum(list(map(len, cells))))
    packet.seek(0)
    return ref.read_trial(packet, number)


def store(cache, family, trial, metadata=None):
    key = f'{family}-{trial.number:03d}'
    for name, a in [('x',trial.features),('y',trial.targets),('o',trial.source_ordinals)]:
        np.save(cache/f'{key}-{name}.npy', a, allow_pickle=False)
    return dict(key=key, family=family, trial=trial.number, units=trial.units.tolist(),
                targets_per_unit=np.bincount(trial.targets,minlength=len(trial.units)).tolist(),
                qc=trial.qc, metadata=metadata or {})


def rats(cache, family, location):
    for row, digest in SOURCES[family].items():
        path = location/f'trial-{int(row):03d}.npz'
        checked(path, digest)
        yield store(cache, family, ref.read_trial(path,int(row)), {'packet_sha256':digest})


def native(values, factor=1):
    a = np.asarray(values, dtype=float).reshape(-1)*factor
    if not np.isfinite(a).all() or np.any(a<0) or np.any(np.abs(a-np.rint(a)) > (1e-6 if factor == 20 else 0)):
        raise ValueError('Invalid acquisition sample')
    return np.rint(a).astype(np.int64)


def salamander(cache, path, rejects):
    checked(path, SOURCES['salamander']['verified_sha256'])
    with ZipFile(path) as archive:
        for family in RETINA:
            raw = archive.read(f'mode_paper_data/{family}/data.mat')
            data = loadmat(BytesIO(raw),struct_as_record=False,squeeze_me=True)['data']
            spikes = data.spike_times
            if spikes.sampling_rate_in_Hz != 10000:
                raise ValueError('Incorrect sampling rate')
            cells = [native(v) for v in spikes.all_spike_times]
            begin = native(data.stimulus.repeat_begin_times)
            ends = native(data.stimulus.repeat_end_times)
            if np.any(ends<=begin) or np.any(begin[1:]<ends[:-1]):
                raise ValueError('Overlapping or invalid repeats')
            for i in np.flatnonzero(ends-begin >= 100000)[:10]:
                start, stop, number = int(begin[i]), int(begin[i]+100000), int(i+1)
                selected = [v[(v>start)&(v<stop)] for v in cells]
                if any(np.any(np.diff(v)<0) for v in selected):
                    rejects.append(dict(family=family,trial=number,reason='within-unit timestamp inversion'))
                    continue
                trial = integer_packet(number, selected, np.arange(1,len(cells)+1), start,stop,10000)
                yield store(cache,family,trial,dict(start_sample=start,stop_sample=stop,
                            member_sha256=hashlib.sha256(raw).hexdigest()))


def turtle(cache, path):
    checked(path, SOURCES['turtle_mat_sha256'])
    data = loadmat(path,simplify_cells=True)['spikes']
    times, onsets = native(data['spiketime'],20), native(data['onStim_sorted'],20)
    ids = np.asarray(data['cluster'],int)
    declared = np.asarray(data['clusterIdentity'],int)
    if len(np.unique(declared)) != len(declared) or not np.isin(ids,declared).all():
        raise ValueError('Invalid source roster')
    windows = []
    for idx in np.argsort(onsets,kind='stable'):
        start,stop = int(onsets[idx]-10000),int(onsets[idx]+50000)
        if start<times.min() or stop>times.max() or (windows and start<windows[-1][2]):
            continue
        windows.append((int(idx),start,stop))
        if len(windows)==40:
            break
    if len(windows)!=40:
        raise ValueError('Insufficient coverage')
    seen = np.unique(np.concatenate([ids[(times>a)&(times<b)] for _,a,b in windows[:20]]))
    for family, roster in [('turtle',seen),('turtle_declared',np.sort(declared))]:
        for row,start,end in windows[20:]:
            within = (times>start)&(times<end)
            unknown = within & ~np.isin(ids,roster)
            stop = int(times[unknown].min()) if unknown.any() else end
            use = within & (times<stop)
            cells = [np.sort(times[use&(ids==c)]) for c in roster]
            yield store(cache,family,integer_packet(row,cells,roster,start,stop,20000),
                        dict(start_sample=start,stop_sample=stop,scheduled_end_sample=end,
                             roster_initialization_rows=[w[0] for w in windows[:20]]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('js14','er1','retina','turtle','cache'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    cache = args.cache
    cache.mkdir(parents=True,exist_ok=True)
    checked(HERE/'reference.py',SOURCES['reference_sha256'])
    checked(HERE/'reference-weights.json',SOURCES['reference_weights_sha256'])
    rejects = []
    rows = list(rats(cache,'JS14',args.js14))
    rows.extend(salamander(cache,args.retina,rejects))
    rows.extend(rats(cache,'ER1',args.er1))
    rows.extend(turtle(cache,args.turtle))
    counts = {f:sum(r['qc']['resolved_targets'] for r in rows if r['family']==f)
              for f in ('JS14','ER1',*RETINA,'turtle','turtle_declared')}
    if list(counts.values()) != [54578,56926,14505,10213,9772,6978,10298]:
        raise ValueError(f'Disagreement with independently verified source counts: {counts}')
    ref.dump(cache/'groups.json',dict(rows=rows,rejected=rejects,counts=counts))
    print(counts)


if __name__=='__main__':
    main()
