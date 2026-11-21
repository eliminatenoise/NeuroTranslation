"""Trial-local history and stable log probabilities from the CC0 next-unit benchmark."""
import numpy as np


TAUS_MS = np.array([10.0, 100.0, 1000.0])


class History:
    """Trial-local state at the end of a complete occupied bin."""
    def __init__(self, units):
        self.last_tick = None
        self.count = np.zeros(units, dtype=np.int64)
        self.trace = np.zeros((units, 3), dtype=np.float64)

    def observe(self, tick, counts):
        if self.last_tick is not None:
            if tick <= self.last_tick:
                raise ValueError("Replayed an old or unordered bin")
            self.trace *= np.exp(-(tick - self.last_tick) / TAUS_MS)
        self.count += counts
        self.trace += counts[:, None]
        self.last_tick = tick
        return np.column_stack((np.log1p(self.count), np.log1p(self.trace), counts > 0))


def logprobs(scores):
    shifted = scores - np.max(scores, axis=-1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))
