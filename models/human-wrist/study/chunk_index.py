"""Read the HDF5 v1 chunk tree used by these two immutable NWB assets."""

import bisect
import struct
import h5py


def require(condition, message):
    if not condition:
        raise ValueError(message)


def root_address(io_file, d):
    # HDF5 v1 object header, version 3 chunked data layout message and
    # default v1 chunk index. See The HDF Group file-format specification.
    parent = d.parent
    link = parent.id.links.get_info(b"data")
    require(link.type == h5py.h5l.TYPE_HARD, "Expected native hard link to named data")
    obj = link.u
    head = io_file.header(obj, 16)
    require(head[0] == 1, "Unsupported HDF5 object header")
    nbytes = struct.unpack_from("<I", head, 8)[0]
    require(0 < nbytes <= 4096, "Unexpected HDF5 object header size")
    messages = io_file.header(obj + 16, nbytes)
    i = 0
    while i + 8 <= len(messages):
        kind, size = struct.unpack_from("<HH", messages, i)
        require(i + 8 + size <= len(messages), "Truncated object-header message")
        payload = messages[i + 8 : i + 8 + size]
        if kind == 8:
            require(payload[:3] == bytes((3, 2, 3)), "Unsupported chunk layout")
            address = struct.unpack_from("<Q", payload, 3)[0]
            dims = struct.unpack_from("<III", payload, 11)
            require(
                dims == (*d.chunks, d.dtype.itemsize),
                "Encoded chunk dimension mismatch",
            )
            return address
        i += 8 + size
    raise ValueError("Missing chunk layout in supported object header")


def lookup(io_file, root, first, col):
    wanted = (first, col, 0)
    addr = root
    for _depth in range(8):
        # Fixed v1 2-D chunk B-tree node with 8-byte addresses, K=32.
        raw = io_file.header(addr, 2616)
        require(raw[:5] == b"TREE\x01", "Unexpected HDF5 chunk index signature")
        level = raw[5]
        used = struct.unpack_from("<H", raw, 6)[0]
        require(0 < used <= 64, "Invalid B-tree node width")
        entries = [struct.unpack_from("<IIQQQ", raw, 24 + 40 * i) for i in range(used + 1)]
        coords = [x[2:] for x in entries[:used]]
        require(coords == sorted(set(coords)), "Unordered B-tree keys")
        j = bisect.bisect_right(coords, wanted) - 1
        require(0 <= j < used, "No lower bound for requested chunk")
        addr = struct.unpack_from("<Q", raw, 24 + 40 * j + 32)[0]
        if level == 0:
            size, mask = entries[j][:2]
            require(coords[j] == wanted and mask == 0, "No exact unmasked chunk")
            return addr, size
    raise ValueError("Unexpected chunk-tree depth")
