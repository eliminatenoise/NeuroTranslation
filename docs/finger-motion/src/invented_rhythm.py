# SPDX-License-Identifier: CC0-1.0
"""An invented four-token input with one adjustable rhythm. No recordings required."""
import numpy as np

AMPLITUDES = np.arange(9) / 4
ELAPSED_MS = 920

def waveform(amplitude):
    """Invented amplifier counts on 46 channels sampled at 1 kHz for 280 ms."""
    t = np.arange(280)[:, None] / 1000
    contact = np.arange(46)[None, :]
    slow = 270 * (1 + 0.25 * np.cos(contact * 0.37))
    fast = 150 * (0.35 + 0.65 * np.sin(contact * 0.14 + 0.30) ** 2)
    envelope = 0.35 + 0.65 * t / 0.279
    return (slow * np.sin(2 * np.pi * 24 * t + 0.31 * contact) +
            amplitude * envelope * fast * np.sin(2 * np.pi * 90 * t + 0.19 * contact))
