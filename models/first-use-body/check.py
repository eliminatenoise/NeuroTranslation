"""Reproduce first-frame, missing-point and geometric equivariance checks on fictional data."""
import sys
import numpy as np

from first_use import fictional, predict
from forecaster import forecast, read_weights


def check(weights):
    xy,t = fictional()
    first, methods = predict(xy[:1],t[:1],.12,weights)
    np.testing.assert_allclose(first,xy[0],equal_nan=True)
    assert list(methods).count("unobserved") == 1
    future, methods = predict(xy,t,.12,weights)
    assert methods[0] == "last_position" and methods[-1] == "unobserved"
    assert (methods == "learned").sum() == 5
    shuffled = [4,2,6,0,1,5,3]
    angle = .59
    # Reflection plus rotation of a camera and arbitrary coordinate units.
    transform = np.array([[np.cos(angle),np.sin(angle)],[np.sin(angle),-np.cos(angle)]])
    shift = np.array([310.,-23.])
    original = forecast(xy,t,.12,weights,all_methods=True)
    moved = forecast(13.5*xy[:,shuffled] @ transform + shift,t+83.,.12,weights,all_methods=True)
    for method in original:
        expected=13.5*original[method][shuffled] @ transform+shift
        np.testing.assert_allclose(moved[method],expected,equal_nan=True,atol=1e-9,rtol=1e-11)
    one = forecast(xy[:,1:2],t,.12,weights)
    assert one.shape == (1,2) and np.isfinite(one).all()
    missing=forecast(xy*np.nan,t,.12,weights)
    assert np.isnan(missing).all()
    checktime=t.copy(); checktime[-1]=checktime[-2]
    try:
        forecast(xy,checktime,.12,weights)
    except ValueError:
        pass
    else:
        raise AssertionError("Non-increasing timestamps must fail")
    print("Passed. First-frame availability, per-point handoff, single landmark, missing history, elapsed time, translation, rotation, reflection, scale and permutation.")


if __name__=="__main__":
    check(read_weights(sys.argv[1]))
