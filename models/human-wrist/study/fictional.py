"""A deterministic fictional practice dataset, made entirely from equations and random numbers."""

import numpy as np

from bilateral import CONTACTS


def generate(day, stage):
    rng = np.random.default_rng(731000 + day)
    n = 60 if day == 3 else 58
    times = np.linspace(61, 14 * 3600 if day == 3 else 23 * 3600, n)
    data = dict(
        native_event_row=np.arange(n), onset_s=times, source_block=(times // 120).astype(int)
    )
    # A moving shoulder and two rotating segments in an imaginary camera plane.
    origins = rng.uniform(130, 320, (n, 1, 2, 2))
    phase = rng.uniform(-np.pi, np.pi, (n, 1, 2, 2))
    rate = rng.uniform(0.035, 0.12, (n, 1, 2, 2))
    length = rng.uniform(20, 48, (n, 1, 2, 2))

    def positions(frames):
        frame = np.asarray(frames)[None, :, None, None]
        angles = phase + rate * frame
        shoulder = origins + 4 * np.sin(0.33 * angles)
        unit = np.stack([np.cos(angles), np.sin(angles)], axis=-1)
        segments = unit * length[..., None]
        elbow = shoulder + segments[..., 0, :]
        wrist = elbow + segments[..., 1, :]
        return np.stack((wrist, elbow, shoulder), axis=3)

    if stage != "targets":
        pose = positions(np.arange(-14, 1)).reshape(n, 15, 6, 2)
        t = np.arange(250)[None, :, None] / 500
        sinusoid = np.sin(
            2 * np.pi * t * np.arange(6, 14)[None, None, :] + phase[:, 0, 0, 0, None, None]
        )
        ecog = (12 * sinusoid + rng.normal(0, 2, (n, 250, 8))).astype("<f4")
        if day == 4:
            ecog[3] = 0
            pose[7, :, 3:] = np.nan
        data.update(
            electrode_id=CONTACTS.copy(),
            region_table_row=CONTACTS.copy(),
            prior_pose_px=pose,
            ecog_uv=ecog,
        )
    if stage != "inputs":
        future = positions([8, 15])[:, :, :, 0, :].copy()
        if day == 4:
            future[9, 1, 0] = np.nan
        data["future_wrist_px"] = future
    return data
