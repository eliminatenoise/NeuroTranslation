"""Shared pieces of the NeuroTranslate 0.2 data steps P1 (downloads) and P2 (tokens, gates, audits).

Nothing here holds a path on any machine. Every script takes a private JSON file of local paths
(argument --paths, or the environment variable NT02_PATHS) so that committed files name no folder.

Step clock (PROTOCOL.json, representation.clock): step k covers [20k, 20k + 20) ms of a recording
and becomes available at its end. A sample at time t (seconds from the recording origin) belongs to
step floor(t / 0.02). Every feature below uses only samples inside or before its step.

Groups written by this part of P2 (spikes and field are written by the neural part):
  emg   1 feature  : log RMS of the raw signal within the step after a causal 20 Hz high-pass
                     (4th-order Butterworth run forward only, state started from the first sample);
                     shipped envelopes give log(envelope value at the step end), labelled derived
  kin   2 features : last sample in the step, change from the last sample of the previous step
  force 2 features : last sample in the step, mean of the samples inside the step
Masks are per step, channel and feature: a value is present only if every sample it uses is finite.
"""
import fcntl
import hashlib
import json
import math
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

STEP_S = 0.02
WINDOW_STEPS = 60  # 1.2 s, the counting unit
SALT = "pooled-encoder-0.2"
LOG_FLOOR = 1e-12
GROUP_FEATURES = {
    "emg": ["log_rms"],
    "kin": ["last", "change"],
    "force": ["last", "step_mean"],
}


# ---------------------------------------------------------------------------
# paths, hashes, locked JSON files
# ---------------------------------------------------------------------------
def load_paths(arg=None):
    src = arg or os.environ.get("NT02_PATHS")
    if not src:
        raise SystemExit("give --paths FILE or set NT02_PATHS")
    return json.loads(Path(src).read_text())


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def atomic_write_json(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp-%d" % os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=False, allow_nan=False)
        f.write("\n")
    os.replace(tmp, path)


def locked_update(path, update, default, lock_path=None):
    """Read-modify-write a JSON file under an exclusive lock on PATH.lock (or lock_path).

    Several workers (and the neural part of P2) append to the same files, so every write
    re-reads the file inside the lock and keeps entries it does not own."""
    path = Path(path)
    with open(str(lock_path or (str(path) + ".lock")), "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            obj = json.loads(path.read_text()) if path.exists() else default()
            obj = update(obj)
            atomic_write_json(path, obj)
            return obj
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def log_download(paths, entry):
    """Append one record to DOWNLOADS.json (URL, range, bytes, sha256, ...)."""
    entry = dict(entry)
    entry.setdefault("when", now_iso())

    def upd(obj):
        if isinstance(obj, list):
            obj.append(entry)
            return obj
        obj.setdefault("downloads", []).append(entry)
        return obj

    locked_update(paths["downloads_json"], upd,
                  lambda: {"schema": "neurotranslate-0.2-pooled-encoder-downloads", "downloads": []})


def log_downloads(paths, entries):
    """Append several records to DOWNLOADS.json in one locked write (used for many small range reads)."""
    entries = [dict(e) for e in entries]
    if not entries:
        return
    for e in entries:
        e.setdefault("when", now_iso())

    def upd(obj):
        if isinstance(obj, list):
            obj.extend(entries)
            return obj
        obj.setdefault("downloads", []).extend(entries)
        return obj

    locked_update(paths["downloads_json"], upd,
                  lambda: {"schema": "neurotranslate-0.2-pooled-encoder-downloads", "downloads": []})


def protocol_head(paths):
    """The commit and file hashes of the protocol branch at the moment a dataset is started."""
    import subprocess
    wt = paths["protocol_worktree"]
    head = subprocess.run(["git", "-C", wt, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    branch_head = subprocess.run(["git", "-C", wt, "rev-parse", "refs/heads/pooled-encoder-protocol"],
                                 capture_output=True, text=True).stdout.strip()
    d = Path(wt) / "models" / "neurotranslate-0.2"
    return {"worktree_head": head, "branch_head": branch_head,
            "PROTOCOL.json": sha256_file(d / "PROTOCOL.json"),
            "ALLOCATION.json": sha256_file(d / "ALLOCATION.json"),
            "PROTOCOL.md": sha256_file(d / "PROTOCOL.md"),
            "read_at": now_iso()}


def protocol_files(paths):
    d = Path(paths["protocol_worktree"]) / "models" / "neurotranslate-0.2"
    return json.loads((d / "PROTOCOL.json").read_text()), json.loads((d / "ALLOCATION.json").read_text())


# ---------------------------------------------------------------------------
# polite HTTP: at most one request per second per host, stop on 429
# ---------------------------------------------------------------------------
class Stop429(Exception):
    pass


PACING_DIR = os.environ.get("NT02_PACING_DIR") or os.path.join(tempfile.gettempdir(), "nt02-host-pacing")


class Pacer:
    """At most one request per min_interval per host, across every process of the data step.

    The time of the last request to each host is kept in one small file per host under PACING_DIR and is
    read and rewritten under an exclusive lock, so two processes that fetch from the same host at the same
    time (for example a range fetch and a licence check) still keep the spacing. A process that has to wait
    holds the lock for the pause, so the other processes queue behind it."""

    def __init__(self, min_interval=1.05, directory=None):
        self.min_interval = min_interval
        self.dir = Path(directory or PACING_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)

    def wait(self, host):
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in host) or "_"
        with open(self.dir / name, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                s = f.read().strip()
                last = float(s) if s else None
                now = time.time()
                if last is not None and 0 <= now - last < self.min_interval:
                    time.sleep(self.min_interval - (now - last))  # single in-request pause, not a wait loop
                f.seek(0)
                f.truncate()
                f.write("%.6f" % time.time())
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)
USER_AGENT = "neurotranslate-0.2-pooled-encoder-data-step (polite, 1 request/s per host)"


def http_get(url, pacer, headers=None, out_path=None, timeout=120, max_redirects=5, md5=False):
    """GET with manual redirects so that every host is paced. Returns (status, headers, body or None,
    final_url_without_query, hosts). A 429 from any host raises Stop429 and nothing is retried.
    With md5=True the result also holds the MD5 of the body (publisher checksums of some deposits)."""
    hdrs = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    hdrs.update(headers or {})
    hosts = []
    cur = url
    for _ in range(max_redirects + 1):
        host = urllib.parse.urlsplit(cur).netloc
        pacer.wait(host)
        hosts.append(host)
        req = urllib.request.Request(cur, headers=hdrs)
        try:
            resp = _opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise Stop429("429 from %s" % host)
            if e.code in (301, 302, 303, 307, 308):
                cur = urllib.parse.urljoin(cur, e.headers["Location"])
                continue
            raise
        status = resp.status
        rh = dict(resp.headers.items())
        hm = hashlib.md5() if md5 else None
        if out_path is not None:
            h = hashlib.sha256()
            n = 0
            with open(out_path, "wb") as f:
                while True:
                    b = resp.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
                    h.update(b)
                    if hm is not None:
                        hm.update(b)
                    n += len(b)
            resp.close()
            body = None
            digest, nbytes = h.hexdigest(), n
        else:
            body = resp.read()
            resp.close()
            digest, nbytes = sha256_bytes(body), len(body)
            if hm is not None:
                hm.update(body)
        final = urllib.parse.urlsplit(cur)
        out = {"status": status, "headers": rh, "body": body, "sha256": digest, "bytes": nbytes,
               "final_url": "%s://%s%s" % (final.scheme, final.netloc, final.path), "hosts": hosts}
        if hm is not None:
            out["md5"] = hm.hexdigest()
        return out
    raise RuntimeError("too many redirects for %s" % url)


# ---------------------------------------------------------------------------
# step grid and causal features
# ---------------------------------------------------------------------------
def n_steps_for(duration_s):
    """Number of full 20 ms steps in [0, duration)."""
    return int(math.floor(duration_s / STEP_S + 1e-9))


def step_bounds(n_samples, fs, t0, n_steps):
    """For uniformly sampled data with sample i at time t0 + i/fs (seconds from the recording origin),
    return lo, hi (int arrays of length n_steps): samples of step k are [lo[k], hi[k])."""
    k = np.arange(n_steps + 1, dtype=np.float64)
    edges = np.ceil((k * STEP_S - t0) * fs - 1e-6).astype(np.int64)
    edges = np.clip(edges, 0, n_samples)
    return edges[:-1], edges[1:]


def step_bounds_times(times, n_steps):
    """Same as step_bounds for explicit, non-decreasing sample times (seconds from the origin)."""
    k = np.arange(n_steps + 1, dtype=np.float64) * STEP_S
    edges = np.searchsorted(times, k - 1e-9, side="left")
    return edges[:-1], edges[1:]


def feat_last(x, lo, hi):
    """Last sample inside each step. x: [n, C]. Returns values [S, C] and mask [S, C]."""
    S, C = len(lo), x.shape[1]
    val = np.zeros((S, C), np.float32)
    msk = np.zeros((S, C), bool)
    has = hi > lo
    idx = np.where(has, hi - 1, 0)
    if x.shape[0]:
        v = x[idx]
        ok = has[:, None] & np.isfinite(v)
        val[ok] = v[ok]
        msk = ok
    return val, msk


def feat_hold(x, hi):
    """Value at the step end: the latest sample before the step end (used only for a continuous shipped
    envelope, whose samples are 62 ms apart, so most steps hold no sample of their own)."""
    S, C = len(hi), x.shape[1]
    val = np.zeros((S, C), np.float32)
    idx = hi - 1
    ok_i = idx >= 0
    v = x[np.clip(idx, 0, None)]
    ok = ok_i[:, None] & np.isfinite(v)
    val[ok] = v[ok]
    return val, ok


def kin_features(x, lo, hi):
    """kin group: [last, change from previous step's last]. Returns val [S, C, 2], msk [S, C, 2]."""
    last, m = feat_last(x, lo, hi)
    S, C = last.shape
    val = np.zeros((S, C, 2), np.float32)
    msk = np.zeros((S, C, 2), bool)
    val[:, :, 0] = last
    msk[:, :, 0] = m
    if S > 1:
        dm = m[1:] & m[:-1]
        d = last[1:] - last[:-1]
        val[1:, :, 1] = np.where(dm, d, 0)
        msk[1:, :, 1] = dm
    return val, msk


def force_features(x, lo, hi):
    """force group: [last, mean within the step]."""
    last, m = feat_last(x, lo, hi)
    S, C = last.shape
    val = np.zeros((S, C, 2), np.float32)
    msk = np.zeros((S, C, 2), bool)
    val[:, :, 0] = last
    msk[:, :, 0] = m
    if x.shape[0]:
        fin = np.isfinite(x)
        xz = np.where(fin, x, 0.0).astype(np.float64)
        cs = np.vstack([np.zeros((1, C)), np.cumsum(xz, axis=0)])
        cn = np.vstack([np.zeros((1, C), np.int64), np.cumsum(~fin, axis=0)])
        cnt = (hi - lo)[:, None]
        bad = cn[hi] - cn[lo]
        s = cs[hi] - cs[lo]
        ok = (cnt > 0) & (bad == 0)
        mean = np.where(ok, s / np.maximum(cnt, 1), 0.0)
        val[:, :, 1] = mean.astype(np.float32)
        msk[:, :, 1] = ok
    return val, msk


FORCE_LIMIT_N = 10000.0


def mask_implausible_force(F, limit=FORCE_LIMIT_N):
    """Plate forces above 10 kN on any axis (several times any human ground reaction) are corrupt samples in a
    few published files; the whole 3-axis sample is set missing. Returns (F, number of samples masked)."""
    F = np.array(F, np.float64, copy=True)
    bad = np.any(np.abs(F) > limit, axis=1)
    F[bad] = np.nan
    return F, int(bad.sum())


_HP_CACHE = {}


def causal_highpass(x, fs, fc=20.0, order=4):
    """Forward-only Butterworth high-pass, per channel, restarted at every finite run so that a
    missing sample never contaminates later steps. State starts from the run's first sample."""
    from scipy.signal import butter, lfilter, lfilter_zi
    key = (float(fs), fc, order)
    if key not in _HP_CACHE:
        b, a = butter(order, fc / (fs / 2.0), btype="highpass")
        _HP_CACHE[key] = (b, a, lfilter_zi(b, a))
    b, a, zi = _HP_CACHE[key]
    x = np.asarray(x, np.float64)
    out = np.full_like(x, np.nan)
    fin = np.isfinite(x)
    if fin.all():
        zi0 = zi[:, None] * x[0][None, :]
        out, _ = lfilter(b, a, x, axis=0, zi=zi0)
        return out
    for c in range(x.shape[1]):
        f = fin[:, c]
        if not f.any():
            continue
        d = np.diff(np.concatenate([[0], f.astype(np.int8), [0]]))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        for s, e in zip(starts, ends):
            seg = x[s:e, c]
            y, _ = lfilter(b, a, seg, zi=zi * seg[0])
            out[s:e, c] = y
    return out


def emg_features(x, fs, lo, hi, already_filtered=False):
    """emg group: log RMS within each step after the causal 20 Hz high-pass. val [S, C, 1]."""
    y = x if already_filtered else causal_highpass(x, fs)
    S, C = len(lo), x.shape[1]
    fin = np.isfinite(y)
    y2 = np.where(fin, y, 0.0) ** 2
    cs = np.vstack([np.zeros((1, C)), np.cumsum(y2, axis=0)])
    cn = np.vstack([np.zeros((1, C), np.int64), np.cumsum(~fin, axis=0)])
    cnt = (hi - lo)[:, None]
    bad = cn[hi] - cn[lo]
    ms = (cs[hi] - cs[lo]) / np.maximum(cnt, 1)
    ok = (cnt > 0) & (bad == 0) & (ms > 0)
    val = np.zeros((S, C, 1), np.float32)
    msk = np.zeros((S, C, 1), bool)
    val[:, :, 0] = np.where(ok, 0.5 * np.log(np.maximum(ms, LOG_FLOOR ** 2)), 0.0)
    msk[:, :, 0] = ok
    return val, msk


def envelope_features(x, hi):
    """Shipped envelope (derived): log of the envelope value at the step end."""
    v, m = feat_hold(x, hi)
    ok = m & (v > 0)
    val = np.zeros(v.shape + (1,), np.float32)
    val[:, :, 0] = np.where(ok, np.log(np.maximum(v, LOG_FLOOR)), 0.0)
    return val, ok[:, :, None]


# ---------------------------------------------------------------------------
# recordings and shards
# ---------------------------------------------------------------------------
class Recording:
    """Tokens of one recording on the 20 ms grid. groups[g] = (val [S, C_g, F_g], msk [S, C_g, F_g])
    with channels in the dataset's fixed channel order for that group."""

    def __init__(self, rec_id, unit, n_steps, meta):
        self.rec_id = rec_id
        self.unit = unit
        self.n_steps = int(n_steps)
        self.meta = dict(meta)
        self.groups = {}

    def put(self, group, chan_index, val, msk, n_channels):
        """Place val/msk for the channels chan_index (positions in the dataset channel list)."""
        S = self.n_steps
        F = len(GROUP_FEATURES[group])
        if group not in self.groups:
            self.groups[group] = (np.zeros((S, n_channels, F), np.float32), np.zeros((S, n_channels, F), bool))
        gv, gm = self.groups[group]
        gv[:, chan_index, :] = val[:S]
        gm[:, chan_index, :] = msk[:S]

    def step_present(self):
        p = np.zeros(self.n_steps, bool)
        for g, (v, m) in self.groups.items():
            p |= m.any(axis=(1, 2))
        return p


def write_unit_shard(path, unit, recordings, channels):
    """One .npz per individual: per group the step-concatenated values and masks, plus offsets.
    Groups missing from a recording are written as all-masked rows so offsets stay shared."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    offs = np.zeros(len(recordings) + 1, np.int64)
    for i, r in enumerate(recordings):
        offs[i + 1] = offs[i] + r.n_steps
    arrays = {"rec_offsets": offs,
              "rec_ids": np.array([r.rec_id for r in recordings]),
              "unit": np.array(unit)}
    for g, chans in channels.items():
        C = len(chans)
        if C == 0:
            continue
        F = len(GROUP_FEATURES[g])
        val = np.zeros((offs[-1], C, F), np.float32)
        msk = np.zeros((offs[-1], C, F), bool)
        for i, r in enumerate(recordings):
            if g in r.groups:
                v, m = r.groups[g]
                val[offs[i]:offs[i + 1]] = v
                msk[offs[i]:offs[i + 1]] = m
        arrays[g + "_val"] = val
        arrays[g + "_msk"] = msk
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, **arrays)
    os.replace(tmp, path)
    return sha256_file(path), path.stat().st_size


def count_recording(r, chan_kinds):
    """Counts used by MIXTURE-MANIFEST.json for one recording."""
    present = r.step_present()
    n_present = int(present.sum())
    windows = r.n_steps // WINDOW_STEPS
    full_windows = 0
    for w in range(windows):
        if present[w * WINDOW_STEPS:(w + 1) * WINDOW_STEPS].all():
            full_windows += 1
    chs = {}
    for g, (v, m) in r.groups.items():
        anyf = m.any(axis=2)  # [S, C]
        for kind, idx in chan_kinds.get(g, {}).items():
            if len(idx):
                chs[g + ":" + kind] = float(anyf[:, idx].sum()) * STEP_S
    return {"steps": r.n_steps, "steps_with_data": n_present, "windows": windows,
            "windows_all_steps_with_data": full_windows, "channel_seconds": chs}


def inner_fold_of(alloc, dataset, unit):
    f = alloc["inner_folds"][dataset]
    for row in f["rows"]:
        if row["unit"] == unit:
            return row["fold"]
    return None


def fold_rule_check(dataset, units, alloc):
    """Recompute the published inner-fold rule and compare with ALLOCATION.json."""
    ranked = sorted(units, key=lambda u: (sha256_text("%s|fold|%s|%s" % (SALT, dataset, u)), u))
    mine = {u: i % 5 for i, u in enumerate(ranked)}
    pub = {row["unit"]: row["fold"] for row in alloc["inner_folds"][dataset]["rows"]}
    return mine == pub, mine
