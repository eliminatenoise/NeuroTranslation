"""CPU slots shared by every track that trains on this machine (admission review, minor 9).

One slot = one CPU in 16-31 = one single-thread worker. A worker holds an exclusive advisory lock
(flock) on the slot file of its CPU for its whole life and pins itself to that CPU. Any process of any
track that takes its CPUs through these slot files therefore cannot push the total past 16 threads on
CPUs 16-31, whatever the other tracks run. Locks vanish when a process ends, so a crash frees its slot.
The slot directory comes from the environment variable NS_CPU_SLOTS (a private path, never committed).

Lanes use CPUs 20-31 (at most 12); control and short single-thread steps use CPUs 16-19.
Standard library only.
"""
import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path

ALL_CPUS = tuple(range(16, 32))
LANE_CPUS = tuple(range(20, 32))
CONTROL_CPUS = tuple(range(16, 20))
MAX_LANES = 12


def slot_dir():
    path = os.environ.get('NS_CPU_SLOTS')
    if not path:
        raise SystemExit('lanes: set NS_CPU_SLOTS to the shared slot directory')
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def try_slot(cpu):
    handle = open(slot_dir() / f'cpu-{cpu:02d}.lock', 'a+')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(f'{os.getpid()} {time.time():.0f}\n')
    handle.flush()
    return handle


def acquire(cpus=LANE_CPUS, wait_seconds=None, poll=2.0):
    """Take the first free slot among cpus; wait (polling, bounded) if all are taken. Returns (cpu, handle)."""
    deadline = None if wait_seconds is None else time.monotonic() + wait_seconds
    while True:
        for cpu in cpus:
            handle = try_slot(cpu)
            if handle is not None:
                os.sched_setaffinity(0, {cpu})
                return cpu, handle
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError('no free CPU slot')
        time.sleep(poll)


def release(handle):
    try:
        fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        handle.close()


@contextmanager
def slot(cpus=LANE_CPUS, wait_seconds=None):
    cpu, handle = acquire(cpus, wait_seconds)
    try:
        yield cpu
    finally:
        release(handle)


def held():
    """CPUs whose slot is currently locked by some process (for logs and checks)."""
    busy = []
    for cpu in ALL_CPUS:
        handle = try_slot(cpu)
        if handle is None:
            busy.append(cpu)
        else:
            release(handle)
    return busy


def worker_init():
    """ProcessPoolExecutor initializer: hold one lane slot for the worker's life."""
    global _WORKER_SLOT
    _cpu, _WORKER_SLOT = acquire(LANE_CPUS)
