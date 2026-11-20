"""Read 26 prespecified Ofner et al. right-arm execution runs on their original two sample grids.

Dataset DOI 10.5281/zenodo.834976, CC BY 4.0; paper DOI 10.1371/journal.pone.0182578.
Authors: Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz.
Tables 1 and 2 in the authors' dataset description supply cue and channel meanings.
"""
import hashlib
import mmap
from pathlib import Path
import struct

API = "https://zenodo.org/api/records/834976"
DOI = "10.5281/zenodo.834976"
# Fixed size in bytes and publisher MD5, keyed by (person, execution run).
FILES = {
    (1, 1): (89712620, "472832e8ade2f5005f95431d606c65b3"),
    (1, 2): (90269676, "be3dbb79203ea1ff4fd7ab24af512989"),
    (1, 3): (90269676, "3d00aee429811fed0c7dc24961f15dc0"),
    (2, 1): (89712620, "7cb4d2efdac2504468540f6edbe3ce35"),
    (2, 2): (90269676, "d974e040d77ba60fb035ac69b9c24a30"),
    (2, 3): (90269676, "3924b22bf8f4f8b72fc3f1a6005c7784"),
    (3, 1): (91662316, "5cd86d70317c65257a56de358fa54716"),
    (3, 2): (90269676, "b39c4c829bc705261baae78acbdb7e52"),
    (3, 3): (90826732, "05e1338d1bcddb8d06499de6ed42a91f"),
    (4, 1): (90269676, "3ff4eec69e922f392d4b8529b5ae246a"),
    (4, 2): (90269676, "669f27db8369804fb08f2d5c011fce53"),
    (4, 3): (89991148, "2e7bdbcb72390299409b47337b74aff4"),
    (5, 1): (90269676, "56420e18715c367f3d057bc0ac82d2ae"),
    (5, 2): (90269676, "c995ab49a3af49b0855bf499c0b5944c"),
    (5, 3): (89991148, "b09504c23f8f268db6791bfea3e7250e"),
    (6, 1): (89712620, "54664049250b6b1ac703cee5985d04f5"),
    (6, 2): (90269676, "36402c36909eae7432b0c7d33f567076"),
    (6, 3): (90269676, "03924595dd270e322ff21c16686769b6"),
    (7, 1): (89712620, "b9c05d8c47a531bfb9b4ff4b85627399"),
    (7, 2): (90269676, "99fa1adbf1f6da25bff95f0d3d1421a9"),
    (7, 3): (90269676, "62fcb583c341f0b2fccf3852511cfbd1"),
    (8, 4): (89991148, "8e608eef687f7b2765b6c9ace57a807c"),
    (9, 4): (89991148, "2c754aba472bb91b2b4c9fdb4e697183"),
    (10, 4): (90269676, "e1dbc90f185df7f8eda9db29715df0eb"),
    (11, 4): (90269676, "cdec3861b5dab06016002fe325b36a0d"),
    (12, 4): (89991148, "3d574d7996c2316ebc9016f7e94e1a18"),
}
FITTING = tuple((p, r) for p in range(1, 8) for r in (1, 2, 3))
ASSESSMENT = tuple((p, 4) for p in range(8, 13))
CUES = dict(enumerate(("elbow flexion", "elbow extension", "supination", "pronation",
                       "hand close", "hand open", "rest"), 0x600))
EEG_SITES = tuple("""
F3 F1 Fz F2 F4 FFC5h FFC3h FFC1h FFC2h FFC4h FFC6h FC5 FC3 FC1 FCz FC2 FC4 FC6
FTT7h FCC5h FCC3h FCC1h FCC2h FCC4h FCC6h FTT8h C5 C3 C1 Cz C2 C4 C6 TTP7h CCP5h
CCP3h CCP1h CCP2h CCP4h CCP6h TTP8h CP5 CP3 CP1 CPz CP2 CP4 CP6 CPP5h CPP3h CPP1h
CPP2h CPP4h CPP6h P3 P1 Pz P2 P4 PPO1h PPO2h
""".split())
CODEBOOK_LABELS = EEG_SITES + (
    "EOG left", "EOG middle", "EOG right", "thumb near", "thumb far", "thumb index",
    "index near", "index far", "index middle", "middle near", "middle far", "middle ring",
    "ring near", "ring far", "ring little", "little near", "little far", "thumb palm",
    "-", "-", "-", "-", "hand X", "hand Y", "hand Z", "elbow X", "elbow Y", "elbow Z",
    "shoulder adduction", "shoulder flexion/extension", "shoulder rotation", "elbow",
    "pro/supination", "wrist flexion/extension", "-",
)
HEADER_LABELS = ("eeg",) * 61 + tuple("""
eog-r eog-m eog-l thumb_near thumb_far thumb_index index_near index_far index_middle
middle_near middle_far middle_ring ring_near ring_far ring_little litte_near litte_far
thumb_palm wrist_bend roll pitch gesture handPosX handPosY handPosZ elbowPosX elbowPosY
elbowPosZ ShoulderAdductio ShoulderFlexionE ShoulderRotation Elbow ProSupination Wrist GripPressure
""".split())
RATES = (512,) * 64 + (64,) * 32
HEADER_BYTES = 256 * 97
RECORD_BYTES = sum(RATES) * 8
CHANNEL_OFFSETS = tuple(sum(RATES[:i]) * 8 for i in range(96))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def filename(person, run):
    require(type(person) is int and type(run) is int, "Person and run must be integers")
    require((person, run) in FILES, "Allowed: S1–S7 runs 1–3 or S8–S12 run 4")
    return f"motorexecution_subject{person}_run{run}.gdf"


def digests(stream, destination=None):
    md5 = hashlib.md5(usedforsecurity=False)
    sha = hashlib.sha256()
    length = 0
    while block := stream.read(1024 * 1024):
        if destination is not None:
            destination.write(block)
        md5.update(block)
        sha.update(block)
        length += len(block)
    return length, md5.hexdigest(), sha.hexdigest()


class Run:
    """One verified recording. Channel numbers are one-based. Window bounds are [first, stop)."""

    def __init__(self, cache, person, run):
        self.person = person
        self.channels = CODEBOOK_LABELS
        self.run_number = run
        self.path = Path(cache) / filename(person, run)
        self._data = None
        with self.path.open("rb") as stream:
            size, self.md5, self.sha256 = digests(stream)
            require((size, self.md5) == FILES[person, run], f"Wrong size or MD5 for {self.path.name}")
            self._data = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            self._read_layout()
        except Exception:
            self.close()
            raise

    def _read_layout(self):
        data = self._data
        require(data[:8] == b"GDF 2.10", "Expected GDF 2.10")
        self.header_bytes = struct.unpack_from("<H", data, 184)[0] * 256
        self.records, numerator, denominator, count = struct.unpack_from("<qIIH", data, 236)
        require(count == 96 and self.header_bytes == HEADER_BYTES and numerator == denominator != 0,
                "Expected 96 channels and one-second records")

        def column(offset, kind):
            return struct.unpack_from(f"<{count}{kind}", data, 256 + count * offset)

        labels = tuple(data[256 + 16*i:272 + 16*i].decode("ascii").strip() for i in range(count))
        require(labels[:61] in (("eeg",)*61, EEG_SITES), "Scalp electrode order differs from the codebook")
        require(labels[61:64] in (("eog-r", "eog-m", "eog-l"), ("eog-l", "eog-m", "eog-r")),
                "Unexpected eye-channel layout")
        require(labels[64:] == HEADER_LABELS[64:] and len(CODEBOOK_LABELS) == count,
                "Mechanical channel order differs from reviewed layout")
        self.header_labels = labels
        require(column(216, "i") == RATES and column(220, "i") == (17,)*count,
                "Expected 512/64 Hz, little-endian float64")
        require(column(104, "d") == column(120, "d") == (-250000.,)*count and
                column(112, "d") == column(128, "d") == (250000.,)*count,
                "Expected exact identity physical calibration on all channels")
        require(column(102, "H") == (0,)*count and data[256+96*count:256+102*count] == b" "*(6*count),
                "Expected unspecified physical dimensions and blank old units")

        self.event_offset = self.header_bytes + self.records * RECORD_BYTES
        raw = data[self.event_offset:]
        count_events = int.from_bytes(raw[1:4], "little")
        require(raw[0] == 1 and struct.unpack_from("<f", raw, 4)[0] == 512.
                and len(raw) == 8 + 6*count_events, "Unexpected event header")
        positions = struct.unpack_from(f"<{count_events}I", raw, 8)
        codes = struct.unpack_from(f"<{count_events}H", raw, 8 + 4*count_events)
        require(all(1 <= p <= self.records*512 for p in positions), "Event outside recorded grid")
        self.events = tuple((p-1, code) for p, code in zip(positions, codes))

    def window(self, channel_1based, first_native_index, stop_native_index):
        """Return stored samples with identity physical scaling and no interpolation."""
        if self._data is None:
            raise ValueError("Recording is closed")
        require(type(channel_1based) is int and 1 <= channel_1based <= 96, "Expected channel 1 through 96")
        channel = channel_1based - 1
        rate = RATES[channel]
        require(type(first_native_index) is int and type(stop_native_index) is int and
                0 <= first_native_index <= stop_native_index <= self.records*rate, "Invalid native window")
        result = []
        current = first_native_index
        while current < stop_native_index:
            record, within = divmod(current, rate)
            count = min(stop_native_index - current, rate - within)
            offset = self.header_bytes + record*RECORD_BYTES + CHANNEL_OFFSETS[channel] + 8*within
            result.extend(struct.unpack_from(f"<{count}d", self._data, offset))
            current += count
        return result

    def close(self):
        if self._data is not None:
            self._data.close()
            self._data = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
