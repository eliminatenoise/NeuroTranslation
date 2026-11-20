"""Predict three later instrument changes from a limited vocabulary and four history bins."""
import numpy as np

CUES = ("elbow flexion", "elbow extension", "supination", "pronation", "hand close", "hand open", "rest")
MODES = ("still", "cue", "motion", "cue_motion", "shared_motion", "shared_cue_motion", "shuffled_cue_motion")
USES_CUE = {"cue", "cue_motion", "shared_cue_motion", "shuffled_cue_motion"}
USES_MOTION = set(MODES) - {"still", "cue"}
ENCODE = {"shared_motion", "shared_cue_motion", "shuffled_cue_motion"}
CHANNELS = ("elbow", "forearm rotation", "index near")
DELAYS = (0.5, 1.0, 1.5)


def tokens_and_anchor(bins):
    tokens = bins.copy()
    anchor = bins[:, -1, :3].copy()
    tokens[:, :, :3] -= anchor[:, None, :]
    return tokens, anchor


def scramble(w):
    rng = np.random.default_rng(20495)
    names = sorted(k for k in w if k == "position" or k.startswith(("project.", "blocks.", "last_norm.")))
    return {k:rng.permutation(w[k].ravel()).reshape(w[k].shape) for k in names}


def design(mode, ids, bins, config, w, linear, encode):
    columns = []
    if mode in USES_CUE:
        columns.append(np.eye(len(CUES))[ids])
    if mode in USES_MOTION:
        tokens, anchor = tokens_and_anchor(bins)
        columns.extend((tokens.reshape(len(bins), 24), anchor))
        if mode in ENCODE:
            core = scramble(w) if mode == "shuffled_cue_motion" else w
            z = (tokens - w["cued_arm.token.mean"]) / w["cued_arm.token.sd"]
            columns.append(encode(config, core, linear(core, "project", z)))
    return np.column_stack(columns)


def batch(mode, ids, bins, config, w, linear, encode):
    if mode == "still":
        return np.zeros((len(ids), 3, 3))
    x = design(mode, ids, bins, config, w, linear, encode)
    prefix = "cued_arm." + mode + "."
    x = (x-w[prefix+"mean"]) / w[prefix+"sd"]
    return (x @ w[prefix+"coef"] + w[prefix+"bias"]).reshape(-1,3,3)


def forecast(record, config, w, linear, encode):
    from knee.adapter import contains_boolean
    mode = record.get("mode")
    if not config.get("cued_arm") or not isinstance(mode, str) or mode not in MODES:
        raise ValueError("Choose a cued arm method supported by this model.")
    fields = {"domain", "mode"}
    cue, bins = 0, None
    if mode in USES_CUE:
        fields.add("cue")
        if record.get("cue") not in CUES:
            raise ValueError("Choose one of the seven source action categories.")
        cue = CUES.index(record["cue"])
    if mode in USES_MOTION:
        fields.add("bins")
        raw = record.get("bins")
        a = np.asarray(raw)
        if a.shape != (4,6) or a.dtype.kind not in "fiu" or contains_boolean(raw) or not np.isfinite(a).all():
            raise ValueError("Supply four rows of six finite instrument readings.")
        bins = a.astype(float)[None]
    if set(record) != fields:
        raise ValueError("The selected method takes exactly: " + ", ".join(sorted(fields)))
    with np.errstate(over="ignore",invalid="ignore"):
        y = batch(mode, np.array([cue]), bins, config, w, linear, encode)[0]
    if not np.isfinite(y).all():
        raise ValueError("Instrument readings exceed the numerical range.")
    return {"mode":mode,"horizon_after_cutoff_s":list(DELAYS),"channels":list(CHANNELS),
            "change_native_units":y.tolist()}
