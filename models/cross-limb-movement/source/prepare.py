"""Build private, paired muscle/trajectory windows from two independent studies."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

import numpy as np
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
CATALOG = json.loads((HERE / "way-catalogue.json").read_bytes())
NAMES = ("Anterior Deltoid", "Brachoradial", "Flexor Digitorum",
         "Common Extensor Digitorum", "First Dorsal Interosseus")
MUSCLES = tuple(side + " " + muscle for side in ("left","right") for muscle in
                ("tibialis anterior","soleus","medial gastrocnemius","peroneus longus")) + (
                "right anterior deltoid","right brachioradialis","right flexor digitorum",
                "right common extensor digitorum","right first dorsal interosseous")
END = np.arange(-19, 1, dtype=float) / 32
FUTURE = np.arange(1, 33, dtype=float) / 256
TOL = 1.e-9


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def acquire(path, url, sha):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            temp = Path(tmp.name)
        try:
            with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as f:
                shutil.copyfileobj(response, f, length=2**20)
            require(digest(temp) == sha, "Downloaded bytes differ from the bound source")
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
    require(digest(path) == sha, f"Source checksum differs at {path.name}")


def source_masks(supplement):
    require(digest(supplement) == CATALOG["supplement_sha256"], "Supplement 1 checksum differs")
    page = subprocess.check_output(["pdftotext", "-f", "6", "-l", "6", "-layout",
                                   str(supplement), "-"]).decode("utf-8")
    # Read only numbered EMG references in the original participant-notes table.
    table = page.split("Laterality   Notes", 1)[-1].split("*)", 1)[0]
    starts = list(re.finditer(r"^\s*(\d{1,2})\s+[MF]\s+10\s+328\s+", table, re.M))
    require([int(m[1]) for m in starts] == list(range(1,13)), "Unrecognized source notes table")
    result = {}
    for i,m in enumerate(starts):
        note = table[m.end():starts[i+1].start() if i+1<len(starts) else len(table)]
        channels = re.findall(r"EMG\s*[-‐‑–]\s*([1-5])", note)
        result[int(m[1])] = {int(a)-1 for a in channels}
    return result


def longest_equal(values):
    same = np.all(values[1:] == values[:-1], axis=1)
    edges = np.flatnonzero(np.diff(np.r_[False,same,False]))
    return int(np.max(edges[1::2] - edges[::2], initial=0))


def near(times, target):
    index = int(np.argmin(np.abs(times - target)))
    require(abs(times[index] - target) < TOL, "anchor_off_grid")
    return index


def position_at(times, xyz, query):
    query = np.atleast_1d(query)
    require(query.min() >= times[0] - TOL and query.max() <= times[-1] + TOL,
            "unbracketed_position")
    return np.column_stack([np.interp(query, times, x) for x in xyz.T])


def way_window(trial, faults):
    ktime, etime = (np.asarray(trial[key], dtype=float) for key in ("eeg_t","emg_t"))
    kin, emg = np.asarray(trial["kin"]), np.asarray(trial["emg"])
    require(ktime.ndim == etime.ndim == 1 and min(len(ktime),len(etime)) > 1, "clock_dimensions")
    require(kin.shape == (len(ktime),45) and emg.shape == (len(etime),5), "signal_dimensions")
    require(np.isfinite(ktime).all() and np.isfinite(etime).all(), "nonfinite_clock")
    k_error, e_error = (np.max(np.abs(np.diff(t) - dt)) for t,dt in [(ktime,.002),(etime,.00025)])
    require(k_error <= TOL and e_error <= TOL, "clock_cadence")
    cue = float(trial["LEDon"])
    cut = cue + .4
    near(ktime, cue)
    k, e = near(ktime, cut), near(etime, cut)
    require(k >= 313 and k+63 < len(ktime) and e >= 2499 and e+500 < len(etime), "window_bounds")
    kt = ktime[k-313:k+64] - cut
    et = etime[e-2499:e+501] - cut
    require(np.max(np.abs(kt - np.arange(-313,64)/500)) < TOL and
            np.max(np.abs(et - np.arange(-2499,501)/4000)) < TOL, "clock_drift")
    xyz = kin[k-313:k+64, [21,25,29]].astype(float) * 10
    voltage = emg[e-2499:e+501].astype(float)
    wrist_flat = longest_equal(xyz)
    common = []
    if not np.isfinite(xyz).all():
        common.append("nonfinite_wrist")
    if np.any(np.all(xyz == 0, axis=1)):
        common.append("all_zero_wrist")
    if wrist_flat/500 >= .125:
        common.append("constant_wrist_125ms")
    finite = np.isfinite(voltage).all(axis=0)
    flat = np.array([longest_equal(col[:,None]) for col in voltage.T])
    good = finite & (flat < 500)
    good[list(faults)] = False
    strict = list(common)
    if faults:
        strict.append("author_unreliable_muscle")
    if not finite.all():
        strict.append("nonfinite_muscle")
    if (flat >= 500).any():
        strict.append("constant_muscle_125ms")
    if np.any(np.all(voltage == 0,axis=1)):
        strict.append("all_five_zero")
    masked = list(common)
    if int(good.sum()) < 3:
        masked.append("fewer_than_three_usable_muscles")
    if good.any() and np.any(np.all(voltage[:,good] == 0, axis=1)):
        masked.append("all_usable_zero")
    qc = dict(strict_flags=strict, named_flags=masked, author_bad=sorted(faults),
              nonfinite=np.flatnonzero(~finite).tolist(), flat_125ms=np.flatnonzero(flat>=500).tolist(),
              longest_flat_emg_intervals=flat.tolist(), longest_flat_wrist_intervals=wrist_flat,
              repeated_wrist_intervals=int(np.all(xyz[1:]==xyz[:-1],axis=1).sum()),
              clock_step_max_abs_error_s=[float(k_error),float(e_error)], good_channels=np.flatnonzero(good).tolist())
    if masked:
        return None, qc
    # Off-domain and unobserved values are exactly zero. Check masks before pooling.
    available = np.r_[np.zeros(8,bool),good]
    history = np.zeros((20,13))
    previous = np.zeros(13)
    future = np.zeros(13)
    history[:,available] = np.sqrt((voltage[:2500,good].reshape(20,125,-1)**2).mean(axis=1))
    previous[available] = np.sqrt((voltage[2000:2500,good]**2).mean(axis=0))
    future[available] = np.sqrt((voltage[2500:,good]**2).mean(axis=0))
    # Integral index on the validated relative clock prevents roundoff at exact ties.
    latest = 313 + np.floor(END*500).astype(int)
    age = np.maximum(0, END - kt[latest])
    require(latest.max()==313 and age.max()<.002+TOL, "causal_wrist_end")
    earlier = position_at(kt[:314],xyz[:314],-.125)[0]
    repeat = position_at(kt[:314],xyz[:314],FUTURE-.125)-earlier
    cut_in_series = float(trial["trial_start_time"]) + cut
    require(np.isfinite(cut_in_series), "invalid_series_start")
    return dict(domain=1, direction=0, cutoff=int(round(cut_in_series*500)),
                cutoff_s=cut_in_series, patch_rms=history, muscle_mask=available,
                patch_xyz_mm=xyz[latest]-xyz[313], age_s=age, past_rms=previous,
                repeat_path_mm=repeat, future_rms=future,
                future_path_mm=position_at(kt,xyz,FUTURE)-xyz[313],complete=not strict), qc


def way_person(root, person, faults):
    spec = CATALOG["archives"][str(person)]
    path = root / f"P{person}.zip"
    require(path.stat().st_size==spec["bytes"] and digest(path)==spec["sha256"], "Incorrect WAY archive")
    rows, series = [], {}
    with zipfile.ZipFile(path) as package:
        available = [i for i in package.infolist() if re.fullmatch(
            rf"WS_P{person}_S\d+\.mat",Path(i.filename).name)]
        actual = {Path(i.filename).name:i for i in available}
        require(len(actual)==len(available) and set(actual)=={m["filename"] for m in spec["members"]},
                "Numbered WAY members differ from the released catalogue")
        for member in spec["members"]:
            s, name = member["series"], member["filename"]
            info = actual[name]
            require(info.file_size==member["bytes"],"Unexpected member size")
            raw = package.read(info)
            require(hashlib.sha256(raw).hexdigest()==member["sha256"],"Incorrect member digest")
            ws = loadmat(io.BytesIO(raw), variable_names=["ws"], simplify_cells=True)["ws"]
            del raw
            require((int(ws["participant"]),int(ws["series"]))==(person,s) and
                    tuple(ws["names"]["emg"])==NAMES, "Unexpected source/channel identity")
            require([ws["names"]["kin"][i] for i in (21,25,29)]==
                    [f"P{a}4 - position {a} sensor 4" for a in "xyz"], "Unexpected wrist identity")
            windows = ws["win"]
            require(len(windows)==member["trial_count"], "Changed number of lifts")
            q = {}
            for j,w in enumerate(windows,1):
                try:
                    row, detail = way_window(w, faults)
                except ValueError as exc:
                    row, detail = None, {"strict_flags":[str(exc)], "named_flags":[str(exc)]}
                q[j] = detail
                if row is not None:
                    rows.append(row | dict(person=f"way:P{person:02d}", session=s, event=j,
                                           block=min(2, 3*(j-1)//len(windows))))
            series[s] = {"design":member["design"],"original":len(windows),"events":q}
            del ws,windows
    return rows, series


def lower(stage, work):
    integrity=json.loads((HERE/"balance-source/integrity.json").read_bytes())["stages"][stage]
    # Verify canonical typed arrays and the original source catalogue, even if a
    # different ZIP library produced different compressed bytes.
    subprocess.run([__import__("sys").executable, str(HERE/"balance-source/verify.py"),stage,str(work)], check=True)
    with np.load(work / f"{stage}.npz", allow_pickle=False) as z:
        a = dict(z)
    take = a["paired"].astype(bool)
    pos = a["sacrum_mm"][take].astype(float)
    v = a["leg_uv"][take].astype(float)
    n=len(v)
    require(n==integrity["totals"]["paired_rows"] and np.isfinite(v).all(), "Unexpected balanced support")
    rms = np.zeros((n,20,13))
    rms[:,:,:8] = np.sqrt((v.reshape(n,20,8,8)**2).mean(axis=2))
    mask = np.zeros((n,13),bool)
    mask[:,:8]=True
    previous = np.zeros((n,13))
    previous[:,:8] = np.sqrt((v[:,-32:]**2).mean(axis=1))
    future = np.zeros((n,13))
    future[:,:8] = a["future_rms_uv"][take]
    c=a["cutoff"][take]
    return dict(person=np.char.add("balance:",a["person"][take]),domain=np.zeros(n,int),
                session=a["posture"][take],event=a["event"][take],direction=a["direction"][take],
                block=a["block"][take],cutoff=c,cutoff_s=c.astype(float)/256,
                patch_rms=rms,muscle_mask=mask,patch_xyz_mm=pos[:,7::8]-pos[:,-1:],
                age_s=np.zeros((n,20)),past_rms=previous,repeat_path_mm=pos[:,-32:]-pos[:,-33:-32],
                future_rms=future,future_path_mm=a["future_path_mm"][take],complete=np.ones(n,bool))


def prepare(stage, way, balance, supplement, output, jobs):
    output.mkdir(parents=True,exist_ok=True)
    masks = source_masks(supplement)
    base = lower(stage,balance)
    way_rows, details = [], {}
    people=CATALOG["stages"][stage]
    with ThreadPoolExecutor(jobs) as pool:
        for p,(rows,qc) in zip(people, pool.map(lambda p:way_person(way,p,masks[p]),people),strict=True):
            way_rows.extend(rows)
            details[p] = qc
    result = {k:np.concatenate([v,np.asarray([r[k] for r in way_rows],dtype=v.dtype if v.dtype.kind!="U" else None)])
              for k,v in base.items()}
    require(len(set(zip(result["person"],result["session"],result["event"],strict=True)))==
            len(result["person"]), "Duplicated within-source observation")
    pairs = result["domain"]==1
    require(all(np.all(result[k][~result["muscle_mask"]]==0) for k in ("future_rms","past_rms")) and
            np.all((~result["muscle_mask"][:,None,:])*result["patch_rms"]==0), "Nonzero unavailable amplitude")
    # Save data only once all requested source identities, shapes and masks pass.
    target = output/f"{stage}.npz"
    tmp = target.with_suffix(".partial.npz")
    np.savez_compressed(tmp,**result)
    tmp.replace(target)
    all_events=[e for sessions in details.values() for q in sessions.values() for e in q["events"].values()]
    summary={"people_by_domain":[len(np.unique(result["person"][~pairs])),len(np.unique(result["person"][pairs]))],
        "rows_by_domain":[int((~pairs).sum()),int(pairs.sum())], "upper_original":len(all_events),
        "upper_named":int(pairs.sum()),"upper_strict":int(result["complete"][pairs].sum()),
        "upper_per_channel_retained":result["muscle_mask"][pairs,8:].sum(axis=0).tolist(),
        "upper_named_flag_counts":dict(Counter(r for e in all_events for r in e["named_flags"])),
        "upper_strict_flag_counts":dict(Counter(r for e in all_events for r in e["strict_flags"]))}
    dump(output/f"{stage}-qc.json",dict(stage=stage, npz_sha256=digest(target),
        upper_per_person=details,lower_source_qc_sha256=digest(balance/f"{stage}-qc.json"), summary=summary))
    return summary


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action",choices=("acquire","prepare"))
    cli.add_argument("stage",choices=("development","assessment"))
    cli.add_argument("--way",type=Path,required=True,help="Folder containing selected WAY P*.zip archives")
    cli.add_argument("--supplement",type=Path,required=True,help="Supplementary file 1 of the WAY descriptor")
    cli.add_argument("--balance",type=Path,help="Directory created by the supplied balance-source reader")
    cli.add_argument("--output",type=Path,help="Private directory for derived arrays and QA")
    cli.add_argument("--jobs",type=int,choices=(1,2),default=1)
    args=cli.parse_args()
    if args.action=="acquire":
        acquire(args.supplement,CATALOG["supplement_url"],CATALOG["supplement_sha256"])
        for p in CATALOG["stages"][args.stage]:
            src=CATALOG["archives"][str(p)]
            acquire(args.way/f"P{p}.zip",src["url"],src["sha256"])
    else:
        if args.balance is None or args.output is None:
            cli.error("prepare requires --balance and --output")
        print(json.dumps(prepare(args.stage,args.way,args.balance,args.supplement,args.output,args.jobs)))
if __name__=="__main__":
    main()
