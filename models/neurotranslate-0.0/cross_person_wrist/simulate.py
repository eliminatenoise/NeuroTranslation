"""Two planar chains rotating about moving shoulders. All parameters are invented."""
import numpy as np

from .reference import ROLES, role_names


def make_event(rng, event, implant="L"):
    annotation = "r_wrist" if implant == "L" else "l_wrist"
    names = role_names(implant, annotation)
    t = np.arange(-14, 16, dtype=float)
    phase, frequency = rng.uniform(-np.pi, np.pi), rng.uniform(.035, .11)
    phase_offset = rng.uniform(-.9, .9)
    translation = rng.uniform([200, 130], [440, 250])
    width = rng.uniform(76, 116)
    origin = translation + np.column_stack((2.2*np.sin(phase+t*.03), 2*np.cos(phase*.6+t*.04)))
    xy_by_name, targets = {}, {}
    mirror = -1 if implant == "R" else 1
    for s, (group, role) in enumerate(zip(names, ROLES)):
        sign = 1 if s == 0 else -1
        a = phase + s * phase_offset + t * frequency
        shoulder = origin + np.array([sign*width/2, sign*2])
        upper = rng.uniform(42, 55)
        fore = rng.uniform(42, 62)
        theta = sign*(.2+.43*np.sin(a))
        phi = sign*(1.0+.48*np.sin(a+.7)+.21*np.cos(.6*a))
        elbow = shoulder + upper*np.column_stack((np.sin(theta), np.cos(theta)))
        wrist = elbow + fore*np.column_stack((np.sin(phi), -np.cos(phi)))
        for name, track in zip(group, (wrist, elbow, shoulder)):
            track[:, 0] = translation[0] + mirror*(track[:, 0]-translation[0])
            xy_by_name[name] = track[:15].tolist()
        targets[role] = wrist[[14+8, 14+15]].copy()
    last = (event+1) * 3600 + 120
    return dict(domain="cross_person_wrist", implant_side=implant, annotated_wrist=annotation,
                frame_indices=list(range(last-14,last+1)), prior_by_name=xy_by_name), targets


def stream(seed, count, implant="L"):
    rng = np.random.default_rng(seed)
    return [make_event(rng, i, implant) for i in range(count)]


def example():
    (earlier, _), (case, targets) = stream(819, 2, "R")
    case["earlier_donor"] = {k: earlier[k] for k in ("frame_indices", "prior_by_name")}
    return case, targets
