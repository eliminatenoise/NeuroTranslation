"""Define a two-dimensional coordinate frame using the fifteen earlier shoulder pairs."""
from dataclasses import dataclass

import numpy as np

ROLES = ("contralateral", "ipsilateral")
JOINTS = ("Wrist", "Elbow", "Shoulder")
TRACKS = tuple(f"{s}_{j}" for s in ("R", "L") for j in JOINTS)


def role_names(implant, wrist):
    if not isinstance(implant, str) or not isinstance(wrist, str):
        raise ValueError("Identify the implant side and the annotated wrist.")
    if (implant, wrist) not in (("L", "r_wrist"), ("R", "l_wrist")):
        raise ValueError("The annotated wrist must be on the side opposite the implant.")
    sides = ("R", "L") if implant == "L" else ("L", "R")
    return tuple(tuple(f"{side}_{joint}" for joint in JOINTS) for side in sides)


@dataclass
class Frame:
    origin: np.ndarray
    basis: np.ndarray
    width: float

    def encode(self, points):
        return (points - self.origin) @ self.basis.T / self.width

    def decode(self, points):
        return points @ self.basis * self.width + self.origin


@dataclass
class History:
    indices: list
    frame: Frame | None
    arms: dict
    reason: str

    def pose(self):
        if self.frame is None or len(self.arms) != 2:
            return None
        return np.concatenate([self.arms[r] for r in ROLES], axis=1)[None] * self.frame.width


def checked_track(raw):
    if not isinstance(raw, list) or len(raw) != 15:
        raise ValueError("Each landmark requires fifteen consecutive earlier image positions.")
    for point in raw:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("Each landmark frame needs an [x,y] pair.")
        for value in point:
            if value is not None and (type(value) not in (int, float) or abs(value) > 1e8
                                      or not np.isfinite(float(value))):
                raise ValueError("Use finite detector pixel coordinates within +/-1e8, or null for a gap.")
    return np.asarray(raw, dtype=np.float64)


def history(indices, named, groups):
    if (not isinstance(indices, list) or len(indices) != 15
            or any(type(i) is not int or i < 0 or i > 2**53-1 for i in indices)):
        raise ValueError("Supply fifteen nonnegative, exactly representable integer camera indices.")
    if not isinstance(named, dict) or set(named) - set(TRACKS):
        raise ValueError("Use the six named native wrist, elbow and shoulder tracks.")
    tracks = {name: checked_track(data) for name, data in named.items()}
    if any(b != a + 1 for a, b in zip(indices, indices[1:])):
        return History(indices, None, {}, "nonconsecutive_prior_frames")
    shoulders = [tracks.get(group[2]) for group in groups]
    if any(x is None or not np.isfinite(x).all() for x in shoulders):
        return History(indices, None, {}, "missing_prior_shoulder")
    contra, ipsi = shoulders
    separation = contra - ipsi
    width = float(np.median(np.linalg.norm(separation, axis=1)))
    if width < 1:
        return History(indices, None, {}, "shoulder_width_below_floor")
    direction = np.mean(separation, axis=0)
    length = np.linalg.norm(direction)
    if length < 0.5 * width:
        return History(indices, None, {}, "unstable_shoulder_direction")
    lateral = direction / length
    up = np.array([lateral[1], -lateral[0]])
    if abs(up[1]) < 0.10:
        return History(indices, None, {}, "ambiguous_image_up_axis")
    if up[1] > 0:
        up *= -1
    frame = Frame((contra[-1] + ipsi[-1]) / 2, np.stack([lateral, up]), width)
    arms = {}
    for name, group in zip(ROLES, groups):
        if all(k in tracks and np.isfinite(tracks[k]).all() for k in group):
            arms[name] = frame.encode(np.stack([tracks[k] for k in group], axis=1))
    return History(indices, frame, arms, "available")
