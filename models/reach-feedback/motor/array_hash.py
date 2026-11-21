"""Hash named numeric arrays independently of ZIP compression and host byte order."""
import hashlib
import json
import numpy as np


def content_hash(path):
    members = {}
    with np.load(path, allow_pickle=False) as archive:
        for name in sorted(archive.files):
            array = archive[name]
            dtype = array.dtype.newbyteorder("<")
            little_endian = np.ascontiguousarray(array, dtype=dtype)
            members[name] = [dtype.str, list(array.shape), hashlib.sha256(little_endian.tobytes()).hexdigest()]
    return hashlib.sha256(json.dumps(members, separators=(",", ":")).encode()).hexdigest()
