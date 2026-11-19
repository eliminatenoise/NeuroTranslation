"use strict";

(() => {
  const grids = ["ED", "EP", "FD", "FP"];
  const digits = ["thumb", "index", "middle", "ring", "little"];
  const gridNames = grids.flatMap((grid) =>
    Array.from(
      { length: 64 },
      (_, i) => grid + "-" + (8 - Math.floor(i / 8)) + "-" + (8 - (i % 8)),
    ),
  );
  const assert = (ok, message) => {
    if (!ok) throw new Error(message);
  };

  function parseHeader(text, name, kind, trial) {
    const rows = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"));
    const first = (rows.shift() || "").split(/\s+/);
    const record = "random_" + kind + "_sample" + trial;
    const names = kind === "force" ? digits : gridNames;
    const rate = kind === "force" ? 100 : 2048;
    const samples = rate * 25;
    assert(
      name === record + ".hea" &&
        first[0] === record &&
        Number(first[1]) === names.length &&
        Number(first[2]) === rate &&
        Number(first[3]) === samples &&
        rows.length === names.length,
      "Expected the original 25-second Hyser " + kind + " header.",
    );
    const channels = rows.map((row, i) => {
      const f = row.split(/\s+/);
      assert(
        f.length === 9 &&
          f[0] === record + ".dat" &&
          f[1] === "16" &&
          f[8] === names[i],
        "Unexpected WFDB file, encoding or channel order in " + name + ".",
      );
      const m = /^([\d.eE+-]+)(?:\((-?\d+)\))?\/V$/.exec(f[2]);
      assert(m, "Expected a voltage gain in the WFDB header.");
      const gain = Number(m[1]),
        baseline = Number(m[2] ?? f[4]);
      const initial = Number(f[5]),
        checksum = Number(f[6]);
      assert(
        Number.isFinite(gain) &&
          gain > 0 &&
          [baseline, initial, checksum].every(Number.isSafeInteger),
        "Invalid WFDB gain, baseline, initial sample or checksum.",
      );
      return { name: f[8], gain, baseline, initial, checksum };
    });
    return { channels, rate, samples, record };
  }

  function catalogue(files, { includeRaw = true } = {}) {
    const trials = new Map(),
      parents = new Set();
    for (const file of files) {
      const m = /^random_(force|raw)_sample([1-5])\.(hea|dat)$/.exec(file.name);
      if (!m) continue;
      if (!includeRaw && m[1] === "raw") continue;
      const trial = Number(m[2]);
      const folder = (file.webkitRelativePath || "")
        .split("/")
        .slice(0, -1)
        .join("/");
      parents.add(folder);
      const record = trials.get(trial) || { trial, files: {} };
      const key = m[1] + "." + m[3];
      assert(
        !record.files[key],
        "Choose files from one session only. Two files have the same trial and modality.",
      );
      record.files[key] = file;
      trials.set(trial, record);
    }
    assert(parents.size <= 1, "Choose a single Hyser session folder.");
    const complete = [...trials.values()].sort((a, b) => a.trial - b.trial);
    assert(
      complete.length,
      "No random-task files found. Choose random_force_sample1.hea and its matching .dat file.",
    );
    for (const r of complete) {
      assert(
        r.files["force.hea"] && r.files["force.dat"],
        "Trial " + r.trial + " needs its force header and data file.",
      );
      assert(
        Boolean(r.files["raw.hea"]) === Boolean(r.files["raw.dat"]),
        "Trial " + r.trial + " has an incomplete raw EMG pair.",
      );
    }
    return complete;
  }

  async function loadPair(entry, kind, stillCurrent = () => true) {
    const header = entry.files[kind + ".hea"],
      file = entry.files[kind + ".dat"];
    assert(header.size < 65536, "Header is too large for this record.");
    const meta = parseHeader(
      await header.text(),
      header.name,
      kind,
      entry.trial,
    );
    const count = meta.channels.length;
    assert(
      file.size === meta.samples * count * 2 &&
        file.name === meta.record + ".dat",
      "Data length or filename differs from the WFDB header.",
    );
    if (!stillCurrent()) return null;
    const bytes = await file.arrayBuffer();
    if (!stillCurrent()) return null;
    // WFDB format 16 is interleaved little-endian signed int16. Preserve this
    // meaning even if a browser uses big-endian native typed arrays.
    const littleEndian = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;
    const signal = littleEndian
      ? new Int16Array(bytes)
      : Int16Array.from({ length: bytes.byteLength / 2 }, (_, i) =>
          new DataView(bytes).getInt16(i * 2, true),
        );
    const sums = new Int32Array(count);
    for (let i = 0; i < count; i++)
      assert(
        signal[i] === meta.channels[i].initial,
        "The first samples differ from the header. Check that these files are a pair.",
      );
    for (let frame = 0; frame < meta.samples; frame++) {
      const pos = frame * count;
      for (let c = 0; c < count; c++) sums[c] += signal[pos + c];
      if ((frame + 1) % 8192 === 0) {
        await new Promise((resolve) => setTimeout(resolve, 0));
        if (!stillCurrent()) return null;
      }
    }
    assert(
      meta.channels.every((c, i) => (sums[i] & 65535) === (c.checksum & 65535)),
      "WFDB checksum mismatch. Reopen the original header and data from the same session.",
    );
    return {
      voltage(frame, channel) {
        const adc = signal[frame * count + channel],
          c = meta.channels[channel];
        return adc === -32768 ? NaN : (adc - c.baseline) / c.gain;
      },
    };
  }
  globalThis.HyserWFDB = { catalogue, loadPair, parseHeader, grids };
})();
