"""Portable inference for the two measured movement domains. Requires NumPy only."""
from pathlib import Path
import json
import numpy as np

DOMAINS = ("wrist", "rat")
DEFAULT_CHECKPOINT = Path(__file__).resolve().parent / "shared-weights.npz"


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


def _norm(x, weight, bias):
    mean = x.mean(axis=-1, keepdims=True)
    var = ((x - mean)**2).mean(axis=-1, keepdims=True)
    return (x - mean) / np.sqrt(var + 1e-5) * weight + bias


def forecast(raw, domains, checkpoint=DEFAULT_CHECKPOINT):
    """Predict centimetres, one row per window. Each domain is 'wrist' or 'rat'."""
    x, recent = physical_features(raw)
    if isinstance(domains, str):
        raise ValueError("Supply one domain label per input row")
    domains = list(domains)
    if len(domains) != len(x) or any(d not in DOMAINS for d in domains):
        raise ValueError("Each row must name its measured domain: wrist or rat")
    ids = np.asarray([DOMAINS.index(d) for d in domains], dtype=int)
    with np.load(checkpoint, allow_pickle=False) as saved:
        w = {k: saved[k].astype(np.float64) for k in saved.files if k != 'configuration'}
        config = json.loads(str(saved['configuration']))
    if config["format"] != 1 or tuple(config["domains"]) != DOMAINS:
        raise ValueError("Unsupported checkpoint format or domain order")

    def linear(key, z):
        return z @ w[key+'.weight'].T + w[key+'.bias']

    def norm(key, z):
        return _norm(z, w[key+'.weight'], w[key+'.bias'])

    n, tokens = x.shape[:2]
    width, heads = config['width'], config['heads']
    z = linear('project', x) + w['position']
    for block in range(config['layers']):
        key = f'blocks.{block}.'
        qkv = linear(key+'qkv', norm(key+'attention_norm', z))
        q, k, v = qkv.reshape(n, tokens, 3, heads, width//heads).transpose(2, 0, 3, 1, 4)
        score = (q @ k.swapaxes(-2, -1)) / np.sqrt(width//heads)
        weights = np.exp(score - score.max(axis=-1, keepdims=True))
        weights /= weights.sum(axis=-1, keepdims=True)
        mix = (weights @ v).transpose(0, 2, 1, 3).reshape(n, tokens, width)
        z = z + linear(key+'attention_out', mix)
        hidden = np.maximum(linear(key+'ff_in', norm(key+'ff_norm', z)), 0)
        z = z + linear(key+'ff_out', hidden)
    all_outputs = linear('readout', norm('last_norm', z[:, -1]))
    log_distance = np.log1p(recent) + all_outputs[np.arange(n), ids]
    return np.expm1(np.maximum(log_distance, 0))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON with x [batch,4,5] and domain [batch]")
    parser.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    print(json.dumps({"distance_cm":forecast(data["x"], data["domain"], args.checkpoint).tolist()}))
