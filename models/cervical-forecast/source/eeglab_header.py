"""Read selected fields from this publisher's uncompressed, little-endian MATLAB 5 EEG struct."""
import struct
from collections import namedtuple

Element = namedtuple("Element", "kind payload size following")


def element(data, at):
    tag, length = struct.unpack_from("<II", data, at)
    if tag >> 16:  # MATLAB small data element: its payload occupies the next four bytes.
        return Element(tag & 65535, at + 4, tag >> 16, at + 8)
    return Element(tag, at + 8, length, at + 8 + (length + 7) // 8 * 8)


def matrix_info(data, matrix):
    if matrix.kind != 14:
        raise ValueError("Expected an uncompressed miMATRIX")
    flags = element(data, matrix.payload)
    dimensions = element(data, flags.following)
    name = element(data, dimensions.following)
    return name.following


def field_names(data, matrix):
    width_field = element(data, matrix_info(data, matrix))
    width = struct.unpack_from("<i", data, width_field.payload)[0]
    field_table = element(data, width_field.following)
    table = data[field_table.payload:field_table.payload + field_table.size]
    names = [table[i:i + width].rstrip(b"\0").decode("ascii") for i in range(0, len(table), width)]
    return names, field_table.following


def scalar(data, matrix):
    value = element(data, matrix_info(data, matrix))
    fmt = {1: "b", 2: "B", 3: "h", 4: "H", 5: "i", 6: "I", 7: "f", 9: "d"}.get(value.kind)
    if not fmt or value.size != struct.calcsize("<" + fmt):
        raise ValueError("Unexpected MATLAB scalar")
    return struct.unpack_from("<" + fmt, data, value.payload)[0]


def chars(data, matrix):
    value = element(data, matrix_info(data, matrix))
    codec = {1: "ascii", 2: "ascii", 4: "utf-16-le", 16: "utf-8", 17: "utf-16-le"}[value.kind]
    return data[value.payload:value.payload + value.size].decode(codec)


def struct_rows(data, matrix, readers, max_rows=None):
    fields, at = field_names(data, matrix)
    rows = []
    while at < matrix.payload + matrix.size and (max_rows is None or len(rows) < max_rows):
        row = {}
        for field in fields:
            value = element(data, at)
            if field in readers:
                row[field] = readers[field](data, value)
            at = value.following
        rows.append(row)
    return rows


def selected_header(fetch, total_bytes, n_events):
    head = fetch(0, 4095)
    if head[126:128] != b"IM" or not head.startswith(b"MATLAB 5.0 MAT-file"):
        raise ValueError("Unsupported MATLAB header")
    root = element(head, 128)
    if root.following != total_bytes:
        raise ValueError("Unexpected .set container length")
    fields, at = field_names(head, root)
    data = head
    result = {}
    for field in fields:
        value = element(data, at)
        if field == "times":
            # Skip the 31 MB regular sample-time vector. No physiological trace is stored in this vector.
            tail_start = value.following
            data = fetch(tail_start, total_bytes - 1)
            at = 0
            continue
        if field in {"nbchan", "pnts", "srate", "trials", "xmin"}:
            result[field] = scalar(data, value)
        elif field == "data":
            result["external_data_file"] = chars(data, value)
        elif field == "chanlocs":
            result["channel_order"] = [row["labels"] for row in struct_rows(data, value, {"labels": chars})]
        elif field == "event":
            result["first_events"] = struct_rows(data, value, {"type": chars, "latency": scalar}, n_events)
            return result
        at = value.following
    raise ValueError("Publisher event structure unavailable")
