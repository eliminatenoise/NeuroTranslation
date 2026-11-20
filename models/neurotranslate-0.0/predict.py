"""CPU/NumPy reader for movement distance, wrist angles and paired rat population histories."""
import argparse
import json
from pathlib import Path

import numpy as np

DEFAULT_CHECKPOINT = Path(__file__).with_name("movement-weights.npz")
DOMAINS = ("wrist", "rat")
MODES = {"motion": 2, "emg": 6, "full": 14}
AXES = ["extension", "radial_deviation"]


def physical_features(raw):
    """Transform four already admitted past intervals; missing or stale input abstains."""
    x = np.asarray(raw, dtype=np.float64)
    if x.ndim != 3 or x.shape[1:] != (4, 5) or not np.isfinite(x).all():
        raise ValueError("Expected finite [batch,4,5] past-only motion intervals")
    length, duration, age, two_step, cosine = x.transpose(2, 0, 1)
    if (np.any(length < 0) or np.any(two_step < 0)
            or np.any((duration < .2-1e-7) | (duration > .3+1e-7))
            or np.any((age < -1e-7) | (age > .05+1e-7))
            or np.any(np.abs(cosine) > 1+1e-6)
            or np.any(np.abs(two_step[:, 0]) > 1e-7) or np.any(np.abs(cosine[:, 0]) > 1e-7)):
        raise ValueError("History is outside the measured interval contract")
    scaled = .25 * length / duration
    z = np.stack([np.log1p(length), (duration-.25)/.05, age/.05, np.log1p(two_step),
                  cosine, np.log1p(scaled)], axis=-1)
    recent = length[:, -1] / duration[:, -1] * (.25 + age[:, -1])
    return z, recent


def angular_tokens(bins, anchor_deg, slot, mode, stats):
    """Prepare only the required, available channels. The caller enforces clock alignment."""
    if mode not in MODES:
        raise ValueError("Select motion, emg or full wrist input")
    bins = np.asarray(bins, dtype=np.float64)
    anchor = np.asarray(anchor_deg, dtype=np.float64)
    slot = np.asarray(slot)
    n = len(anchor) if anchor.ndim else 0
    channels = MODES[mode]
    if n == 0 or bins.shape != (n, 16, channels) or anchor.shape != (n, 2):
        raise ValueError(f"Expected bins [N,16,{channels}] and anchor_deg [N,2] for a nonempty batch")
    if slot.shape != (n,) or slot.dtype.kind not in "iu" or np.any((slot < 0) | (slot >= 6)):
        raise ValueError("Each row needs one integer cue slot 0 through 5")
    if not np.isfinite(bins).all() or not np.isfinite(anchor).all():
        raise ValueError("All measurements required for this mode must be finite")
    if channels >= 6 and (bins[:, :, 2:6] < 0).any():
        raise ValueError("Bipolar EMG RMS amplitudes must be nonnegative")
    encoded = np.zeros((n, 16, 14), dtype=np.float64)
    encoded[:, :, :channels] = (bins - stats["bins_center"][:channels]) / stats["bins_scale"][:channels]
    anchor_z = (anchor - stats["anchor_center"]) / stats["anchor_scale"]
    context = np.concatenate((anchor_z, np.eye(6)[slot]), axis=1)
    return np.concatenate((encoded.reshape(n, 4, 56), np.broadcast_to(context[:, None], (n, 4, 8))), axis=2)


def read_checkpoint(path):
    with np.load(path, allow_pickle=False) as saved:
        config = json.loads(str(saved["configuration"]))
        w = {k: saved[k].astype(np.float64) for k in saved.files if k != "configuration"}
    if config.get("format") != 1 or tuple(config.get("domains", ())) != DOMAINS:
        raise ValueError("Unsupported original spatial configuration")
    return config, w


def linear(w, name, x):
    return x @ w[name + ".weight"].T + w[name + ".bias"]


def norm(w, name, x):
    mean = x.mean(axis=-1, keepdims=True)
    var = ((x - mean)**2).mean(axis=-1, keepdims=True)
    return (x - mean) / np.sqrt(var + 1e-5) * w[name + ".weight"] + w[name + ".bias"]


def encode(config, w, projected, *, all_tokens=False):
    """Both distance and angle heads execute this same temporal encoder."""
    z = projected + w["position"]
    n, tokens, width = z.shape
    heads = config["heads"]
    for block in range(config["layers"]):
        key = f"blocks.{block}."
        qkv = linear(w, key + "qkv", norm(w, key + "attention_norm", z))
        q, k, v = qkv.reshape(n, tokens, 3, heads, width//heads).transpose(2, 0, 3, 1, 4)
        score = (q @ k.swapaxes(-2, -1)) / np.sqrt(width//heads)
        weights = np.exp(score - score.max(axis=-1, keepdims=True))
        weights /= weights.sum(axis=-1, keepdims=True)
        mix = (weights @ v).transpose(0, 2, 1, 3).reshape(n, tokens, width)
        z = z + linear(w, key + "attention_out", mix)
        hidden = np.maximum(linear(w, key + "ff_in", norm(w, key + "ff_norm", z)), 0)
        z = z + linear(w, key + "ff_out", hidden)
    return norm(w, "last_norm", z if all_tokens else z[:, -1])


def forecast(raw, domains, checkpoint=DEFAULT_CHECKPOINT):
    """Existing spatial API. Each labelled row returns one distance in centimetres."""
    x, recent = physical_features(raw)
    if isinstance(domains, str):
        raise ValueError("Supply one domain label per input row")
    domains = list(domains)
    if len(domains) != len(x) or any(d not in DOMAINS for d in domains):
        raise ValueError("Each row must name its measured spatial domain: wrist or rat")
    ids = np.asarray([DOMAINS.index(d) for d in domains], dtype=int)
    config, w = read_checkpoint(checkpoint)
    all_outputs = linear(w, "readout", encode(config, w, linear(w, "project", x)))
    log_distance = np.log1p(recent) + all_outputs[np.arange(len(x)), ids]
    return np.expm1(np.maximum(log_distance, 0))


def forecast_angles(bins, anchor_deg, slot, mode, checkpoint=DEFAULT_CHECKPOINT, *, forearm_residual=None):
    """Return absolute angles [N,2] in degrees, nominally 128 stored ticks after the anchor."""
    config, w = read_checkpoint(checkpoint)
    if config.get("angular", {}).get("format") != 1:
        raise ValueError("This checkpoint has no supported angular adapter")
    stats = {k.removeprefix("angular.stats."): v for k, v in w.items() if k.startswith("angular.stats.")}
    if forearm_residual is not None:
        from forearm.residual import ARMS, apply
        if forearm_residual not in ARMS or mode != forearm_residual:
            raise ValueError("Match forearm_residual and mode to motion or emg")
        if config["angular"].get("forearm_residual", {}).get("format") != 1:
            raise ValueError("This checkpoint has no supported forearm correction")
        # Both corrections receive the same motion forecast. Electrode inputs enter only the correction.
        x = angular_tokens(np.asarray(bins)[..., :2], anchor_deg, slot, "motion", stats)
        prefix = "angular.motion."
        latent = encode(config, w, linear(w, prefix + "project", x))
        change = linear(w, prefix + "readout", latent) * stats["residual_scale"] + stats["residual_center"]
        base = change + np.asarray(anchor_deg, dtype=np.float64)
        key = "angular.residual." + forearm_residual + "."
        state = {field: w[key + field] for field in ("center", "scale", "coef")}
        return apply(bins, anchor_deg, base, slot, forearm_residual, state)
    x = angular_tokens(bins, anchor_deg, slot, mode, stats)
    prefix = "angular." + mode + "."
    latent = encode(config, w, linear(w, prefix + "project", x))
    y = linear(w, prefix + "readout", latent)
    return y * stats["residual_scale"] + stats["residual_center"] + np.asarray(anchor_deg, dtype=np.float64)


def population_states(config, w, cutoff_s, prior_time_s, prior_xy_cm):
    from population.adapter import camera_tokens
    tokens, scaled_speed = camera_tokens(cutoff_s, prior_time_s, prior_xy_cm)
    states = encode(config, w, linear(w, "project", tokens), all_tokens=True)
    rat_correction = linear(w, "readout", states)[:, :, DOMAINS.index("rat")]
    return scaled_speed, states, rat_correction


def forecast_population(cutoff_s, prior_time_s, prior_xy_cm, mode, checkpoint=DEFAULT_CHECKPOINT,
                        *, regional_counts=None, unit_counts=None):
    """Predict straight-line displacement in cm. Accept one history or a batch and return a 1D array."""
    from population.adapter import rates_for_bins, readout_features, ridge_prediction
    if mode not in ("motion", "combined"):
        raise ValueError("Select motion or combined rat_population mode")
    config, w = read_checkpoint(checkpoint)
    if config.get("rat_population", {}).get("format") != 1:
        raise ValueError("This checkpoint has no rat_population head")
    camera = population_states(config, w, cutoff_s, prior_time_s, prior_xy_cm)
    rates = rates_for_bins(regional_counts, unit_counts, len(camera[0])) if mode == "combined" else None
    features = readout_features(*camera, rates)
    prefix = "population." + mode + "."
    state = {key: w[prefix + key] for key in ("mean", "scale", "coef", "intercept")}
    return ridge_prediction(features, state)


def predict_record(record, checkpoint=DEFAULT_CHECKPOINT):
    if record.get("domain") == "muscle_motion":
        from muscle_motion.forecast import forecast as predict_muscles_and_path
        source = Path(checkpoint)
        state = json.loads((source.parent / "muscle_motion/model.json").read_bytes())
        return predict_muscles_and_path(record, state)
    if record.get("domain") == "visual_balance":
        from visual_balance.forecast import forecast as predict_visual_balance
        import hashlib
        source = Path(checkpoint)
        state = json.loads((source.parent / "visual_balance/model.json").read_bytes())
        if hashlib.sha256(source.read_bytes()).hexdigest() != state["parent_sha256"]:
            raise ValueError("The visual-balance forecast requires its matching movement checkpoint.")
        return predict_visual_balance(record, state, read_checkpoint(source))
    if record.get("domain") == "walking_cues":
        from walking_cues.forecast import forecast as predict_walk, load_encoders
        import hashlib
        source = Path(checkpoint)
        state = json.loads((source.parent / "walking_cues/model.json").read_bytes())
        if hashlib.sha256(source.read_bytes()).hexdigest() != state["parent_sha256"]:
            raise ValueError("The walking forecast requires its matching movement checkpoint.")
        return predict_walk(record, state, load_encoders(source, record.get("mode")))
    if record.get("domain") == "heel_force":
        from heel_force.forecast import forecast as predict_heel_force
        import hashlib
        source = Path(checkpoint)
        state = json.loads((source.parent / "heel_force/model.json").read_bytes())
        if hashlib.sha256(source.read_bytes()).hexdigest() != state["parent_sha256"]:
            raise ValueError("The heel and force readout requires its matching movement checkpoint.")
        config, weights = read_checkpoint(source)
        comparison = {}
        if record.get("mode") == "random_full_rank2":
            comparison = {k: np.asarray(v) for k, v in json.loads(
                (source.parent / "back_rotation/random-encoder.json").read_bytes()).items()}
        return predict_heel_force(record, state, (config, weights, comparison))
    if record.get("domain") == "pedal_load":
        from pedal_load.forecast import forecast as predict_load_cell
        import hashlib
        source = Path(checkpoint)
        state = json.loads((source.parent / "pedal_load/model.json").read_bytes())
        if hashlib.sha256(source.read_bytes()).hexdigest() != state["parent_sha256"]:
            raise ValueError("This load readout requires its matching movement checkpoint.")
        random = {}
        if record.get("mode") == "random_both":
            raw = json.loads((source.parent / "back_rotation/random-encoder.json").read_bytes())
            random = {k: np.asarray(v, dtype=float) for k, v in raw.items()}
        config, weights = read_checkpoint(source)
        return predict_load_cell(record, state, weights, random, config, linear, encode)
    if record.get("domain") == "muscle_tracking":
        from muscle_tracking.forecast import forecast as predict_tracking
        import hashlib
        source = Path(checkpoint)
        state = json.loads((source.parent / "muscle_tracking/model.json").read_bytes())
        if hashlib.sha256(source.read_bytes()).hexdigest() != state["parent_sha256"]:
            raise ValueError("This tracking readout requires its matching movement checkpoint.")
        random = {}
        if record.get("mode") == "random_both":
            raw = json.loads((source.parent / "back_rotation/random-encoder.json").read_bytes())
            random = {k: np.asarray(v, dtype=float) for k, v in raw.items()}
        config, weights = read_checkpoint(source)
        return predict_tracking(record, state, weights, random, config, linear, encode)
    if record.get("domain") == "back_rotation":
        from back_rotation.forecast import forecast as predict_rotation
        import hashlib
        source = Path(checkpoint)
        folder = source.parent / "back_rotation"
        model = json.loads((folder / "model.json").read_bytes())
        if hashlib.sha256(source.read_bytes()).hexdigest() != model["parent_sha256"]:
            raise ValueError("This rotation adapter requires its matching movement checkpoint.")
        if record.get("mode") == "random_full":
            model["random_encoder"] = json.loads((folder / "random-encoder.json").read_bytes())
        cfg, weights = read_checkpoint(source)
        return predict_rotation(record, model, cfg, weights, linear, encode)
    if record.get("domain") == "cervical_voltage":
        from cervical.forecast import predict as predict_voltage, read_model
        model = read_model(Path(checkpoint).parent / "cervical" / "model.json")
        return predict_voltage(record, model)
    if record.get("domain") == "early_signal_change":
        from scalp_residual import forecast as early_forecast
        config, weights = read_checkpoint(checkpoint)
        return early_forecast(record, config, weights, linear, encode)
    if record.get("domain") == "group_arm_change":
        from group_arm import forecast as group_arm_forecast
        config, weights = read_checkpoint(checkpoint)
        return group_arm_forecast(record, config, weights, linear, encode)
    if record.get("domain") == "cued_arm_change":
        from cued_arm import forecast as cued_arm_forecast
        config, weights = read_checkpoint(checkpoint)
        return cued_arm_forecast(record, config, weights, linear, encode)
    if record.get("domain") == "marker_displacement":
        from point_motion import forecast as point_forecast
        config, weights = read_checkpoint(checkpoint)
        return point_forecast(record, config, weights, linear, encode)
    if record.get("domain") == "wrist_angle":
        y = forecast_angles(record["bins"], record["anchor_deg"], record["slot"], record["mode"], checkpoint,
                            forearm_residual=record.get("forearm_residual"))
        return {"axes": AXES, "angle_deg": y.tolist(), "horizon_stored_ticks": 128, "stored_hz": 512}
    if record.get("forearm_residual") is not None:
        raise ValueError("Forearm corrections apply only to wrist_angle inputs")
    if record.get("domain") == "right_plate_force":
        from right_plate import forecast as plate_forecast
        config, weights = read_checkpoint(checkpoint)
        return plate_forecast(record, config, weights, linear, encode)
    if record.get("domain") == "knee_moment":
        from load.adapter import forecast as knee_moment
        if set(record) != {"domain", "frames", "angles_deg", "mode"}:
            raise ValueError("Knee moment requires domain, frames, angles_deg and mode.")
        config, weights = read_checkpoint(checkpoint)
        y, periods = knee_moment(record["frames"], record["angles_deg"], record["mode"],
                                config, weights, linear, encode)
        return {"axes": ["right", "left"], "internal_knee_moment_Nm_per_kg": y.tolist(),
                "positive": "flexion", "period_frames": periods.tolist(),
                "horizon_stored_frames": 25, "stored_hz": 100}
    if record.get("domain") == "knee_angle":
        allowed = {"domain", "mode", "frames", "knee_deg"}
        if set(record) != allowed:
            raise ValueError("A knee forecast requires exactly domain, mode, frames and knee_deg.")
        from knee.adapter import forecast as knee_forecast
        config, weights = read_checkpoint(checkpoint)
        angles, period = knee_forecast(record["frames"], record["knee_deg"], record["mode"],
                                       config, weights, linear, encode)
        return {"axes": ["right_knee_flexion_extension", "left_knee_flexion_extension"],
                "angle_deg": angles.tolist(), "period_frames": period.tolist(),
                "horizon_stored_frames": 15, "stored_hz": 60}
    if record.get("domain") == "rat_population":
        distance = forecast_population(record["cutoff_s"], record["prior_time_s"], record["prior_xy_cm"],
                                       record["mode"], checkpoint, regional_counts=record.get("regional_counts"),
                                       unit_counts=record.get("unit_counts"))
        return {"distance_cm": distance.tolist()}
    return {"distance_cm": forecast(record["x"], record["domain"], checkpoint).tolist()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON muscle activity and sacrum path, visual balance, walking instruction, heel movement and force, pedal load change, muscle length change, back-sensor rotation, cervical voltage, right-plate force, knee-moment, wrist-angle, knee-angle, spatial or rat population input")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    args = parser.parse_args()
    try:
        print(json.dumps(predict_record(json.loads(args.input.read_text()), args.checkpoint), allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Input or checkpoint error: {exc}\n")
