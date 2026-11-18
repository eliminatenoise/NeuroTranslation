  const SAMPLE_RATE = 512;
  const FRAME_TICKS = 8;
  const CHANNELS = 23;
  const FRAME_BYTES = CHANNELS * FRAME_TICKS * 2;
  const HEADER_BYTES = 6144;
  const TRIALS = 40;
  const OFFSETS = [384, 512, 640, 768, 896, 1024];
  const EEG = ["C3", "C1", "Cz", "C2", "C4", "CP3", "CPz", "CP4"];
  const EMG = ["M1L", "M1R", "M2L", "M2R", "M3L", "M3R", "M4L", "M4R"];
  const MARKERS = ["TrialInitStamp", "AllTargetShowSta", "TrialInitMovStam", "CurrentTarget",
    "TrialEndMovStamp", "XCoordinates", "YCoordinates"];
  const AXES = ["extension", "radial_deviation"];
  const PACKET_CHANNELS = ["extension_relative_to_anchor", "radial_deviation_relative_to_anchor", ...EEG];
  const FORMAT = "wrist-recorded-trial.v1";
  const DEPOSIT = "10.6084/m9.figshare.29666735.v3";
  const RECIPE_SHA = "a0b4db26cd12926aa57a2797f766d0d7da27976cfa773168c56b6516755e1725";
  const CATALOGUE_SHA = "2f6422705881398013b3245fb0d5fb4b0c5bb0528160c2325be8bdbc0286ff30";
  const ROLE_SHA = "eb957afdefd86ede0072a327292ca7b51a123bf4c46d7ed295914d9d5097b92b";
  const ARCHIVES_SHA = "ca9193680afe9d0eabd578acbd1684f91699a6d2d94cef4e731cd9f767194862";
  const FIT_SHA = "e888a96ddfa14e5ee3ec8788bdedede89da3b9646ca201ea9e99e21542788e8a";
  const DESIGN_SHA = "69518d134127f762d7199f1fb64b28c471655f158d63bf8592199388af03ec35";
  const textDecoder = new TextDecoder("utf-8", {fatal: true});
  const textEncoder = new TextEncoder();
  let verification;

  function requireValue(condition, message) {
    if (!condition) throw new Error(message);
  }

  async function sha256(data) {
    const result = await globalThis.crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(result), value => value.toString(16).padStart(2, "0")).join("");
  }

  async function checkReference() {
    const recipeHash = await sha256(textEncoder.encode(RECIPE_TEXT));
    const catalogueHash = await sha256(textEncoder.encode(CATALOGUE_TEXT));
    requireValue(recipeHash === RECIPE_SHA && catalogueHash === CATALOGUE_SHA,
      "The packaged WristMotion source pins changed. Open a fresh copy of the reader.");
    const archives = JSON.parse(RECIPE_TEXT).archives;
    const digests = CATALOGUE_TEXT.slice(0, -1).split("\n");
    const catalogue = new Set(digests);
    requireValue(archives.length === 3 && archives.every(archive => archive.blocks.length === 8)
      && digests.length === 960 && catalogue.size === 960, "Invalid development reference inventory.");
    return {archives, catalogue};
  }

  // This ZIP subset covers the verified deposits. No anonymous entry is inflated.
  function zipEntries(bytes) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const u16 = offset => view.getUint16(offset, true);
    const u32 = offset => view.getUint32(offset, true);
    const end = bytes.length - 22;
    const message = "The verified ZIP member directory is inconsistent.";
    requireValue(u32(end) === 0x06054b50 && u16(end + 4) === 0 && u16(end + 6) === 0
      && u16(end + 20) === 0, message);
    const count = u16(end + 10);
    const central = u32(end + 16);
    requireValue(count === u16(end + 8) && count > 0 && count <= 64 && central < end
      && central + u32(end + 12) === end, message);
    const entries = new Map();
    let position = central;
    for (let index = 0; index < count; index++) {
      requireValue(position + 46 <= end && u32(position) === 0x02014b50, message);
      const nameLength = u16(position + 28);
      const next = position + 46 + nameLength + u16(position + 30) + u16(position + 32);
      requireValue(next <= end && nameLength > 0 && u16(position + 34) === 0, message);
      const name = textDecoder.decode(bytes.subarray(position + 46, position + 46 + nameLength));
      requireValue(!entries.has(name), message);
      entries.set(name, {
        flags: u16(position + 8), method: u16(position + 10), compressed: u32(position + 20),
        size: u32(position + 24), header: u32(position + 42),
      });
      position = next;
    }
    requireValue(position === end, message);
    return {bytes, entries, central, u16, u32};
  }

  async function member(zip, name, maxBytes, exactBytes) {
    const message = "The selected paired recording members cannot be read.";
    const entry = zip.entries.get(name);
    requireValue(entry && entry.flags === 0 && entry.method === 8 && entry.compressed > 0
      && entry.size > 0 && entry.size <= maxBytes && (exactBytes === undefined || entry.size === exactBytes), message);
    const {header, compressed, size} = entry;
    const {bytes, central, u16, u32} = zip;
    requireValue(header + 30 <= central && u32(header) === 0x04034b50
      && u16(header + 6) === 0 && u16(header + 8) === 8
      && u32(header + 18) === compressed && u32(header + 22) === size, message);
    const nameEnd = header + 30 + u16(header + 26);
    const start = nameEnd + u16(header + 28);
    requireValue(start + compressed <= central
      && textDecoder.decode(bytes.subarray(header + 30, nameEnd)) === name, message);
    const input = new ReadableStream({
      start(controller) {
        controller.enqueue(bytes.subarray(start, start + compressed));
        controller.close();
      },
    });
    const reader = input.pipeThrough(new DecompressionStream("deflate-raw")).getReader();
    const output = new Uint8Array(size);
    let position = 0;
    try {
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        if (position + value.length > size) {
          await reader.cancel();
          throw new Error(message);
        }
        output.set(value, position);
        position += value.length;
      }
    } catch {
      throw new Error(message);
    } finally {
      reader.releaseLock();
    }
    requireValue(position === size, message);
    return output;
  }

  function dictionaryRows(data, columns, expected) {
    const [header, ...lines] = textDecoder.decode(data).trimEnd().split(/\r?\n/);
    const labels = header.split("\t");
    const indices = columns.map(label => labels.indexOf(label));
    return indices.every(index => index >= 0) && lines.length === expected.length && lines.every((line, row) => {
      const fields = line.split("\t");
      return fields.length === labels.length && indices.every((index, field) => fields[index] === expected[row][field]);
    });
  }

  async function verifyDictionaries(zip, eegPath, motionPath) {
    const eeg = await member(zip, eegPath, 4096);
    const motion = await member(zip, motionPath, 4096);
    const signals = [...EEG.map(label => [label, "EEG", "microV"]), ...EMG.map(label => [label, "EMG", "microV"])];
    requireValue(dictionaryRows(eeg, ["name", "type", "units"], signals),
      "Unexpected EEG or EMG channel names, order or units.");
    requireValue(dictionaryRows(motion, ["name", "tracked_point", "units"],
      [["X", "RightWrist", "rad"], ["Y", "RightWrist", "rad"]]), "Unexpected motion channels or units.");
  }

  function verifyHeader(header, memberSize, storedRows) {
    const field = (start, width) => textDecoder.decode(header.subarray(start, start + width));
    const records = Number(field(236, 8));
    requireValue(field(0, 8) === "0       " && Number(field(184, 8)) === HEADER_BYTES
      && Number(field(244, 8)) === FRAME_TICKS / SAMPLE_RATE && Number(field(252, 4)) === CHANNELS
      && Number.isInteger(records) && records >= 25000 && records <= 26000
      && records * FRAME_TICKS === storedRows && HEADER_BYTES + records * FRAME_BYTES === memberSize,
    "Unexpected EDF signature, clock or record dimensions.");
    const labels = [...Array.from({length: 16}, (_, index) => `Ch${index + 1}`), ...MARKERS];
    const channelField = (section, width, channel) => field(256 + section * CHANNELS + width * channel, width).trim();
    for (let channel = 0; channel < CHANNELS; channel++) {
      const signal = channel < 16;
      const min = signal ? "-32768" : "0";
      const max = signal || channel >= 21 ? "32767" : "255";
      requireValue(channelField(0, 16, channel) === labels[channel]
        && channelField(96, 8, channel) === (signal ? "uV" : "")
        && channelField(104, 8, channel) === min && channelField(112, 8, channel) === max
        && channelField(120, 8, channel) === min && channelField(128, 8, channel) === max
        && (!signal || channelField(136, 80, channel) === "HP:0.1LP:200N:60")
        && /^ *8 *$/.test(field(256 + 216 * CHANNELS + 8 * channel, 8)),
      "Unexpected EDF channel identity, calibration or samples per record.");
    }
  }

  // A shared byte offset locates the first channel at a given tick. Other channels
  // are stored in planes of eight signed little-endian samples per frame.
  function edfOffset(tick) {
    return HEADER_BYTES + Math.floor(tick / FRAME_TICKS) * FRAME_BYTES + (tick % FRAME_TICKS) * 2;
  }

  function markerTicks(edf, storedRows) {
    const previous = [0, 0, 0, 0];
    const markers = [[], [], [], []];
    for (let tick = 0; tick < storedRows; tick++) {
      const base = edfOffset(tick);
      for (let index = 0; index < 4; index++) {
        const channel = index === 3 ? 20 : 16 + index;
        const value = edf.getInt16(base + channel * 16, true);
        requireValue(value === 0 || value === 1, "Nonbinary EDF trial or movement marker.");
        if (value && !previous[index]) {
          requireValue(markers[index].length < TRIALS + 1, "Unexpected stored source marker count.");
          markers[index].push(tick);
        }
        previous[index] = value;
      }
    }
    const [starts, allTargets, cues, returns] = markers;
    requireValue((starts.length === TRIALS || starts.length === TRIALS + 1)
      && [allTargets, cues, returns].every(series => series.length === TRIALS), "Unexpected stored source marker count.");
    for (let trial = 0; trial < TRIALS; trial++) {
      requireValue(starts[trial] < allTargets[trial] && allTargets[trial] < cues[trial]
        && cues[trial] + OFFSETS[OFFSETS.length - 1] < returns[trial]
        && returns[trial] < (starts[trial + 1] ?? storedRows), "Stored source trial or movement markers are out of order.");
    }
    return {cues, returns};
  }

  function verifyMotion(tsv, edf, storedRows) {
    const message = "Motion TSV and EDF auxiliary states disagree at a stored tick.";
    let position = 0;
    function word(delimiter) {
      const start = position;
      let value = 0;
      while (tsv[position] >= 48 && tsv[position] <= 57 && position - start < 5) {
        value = 10 * value + tsv[position++] - 48;
      }
      requireValue(position > start && tsv[position++] === delimiter && value <= 65535, message);
      return value;
    }
    for (let tick = 0; tick < storedRows; tick++) {
      const base = edfOffset(tick);
      const x = word(9);
      const y = word(13);
      requireValue(tsv[position++] === 10 && x === edf.getUint16(base + 21 * 16, true)
        && y === edf.getUint16(base + 22 * 16, true), message);
    }
    requireValue(position === tsv.length, "Unexpected motion TSV row count.");
  }

  async function readBlock(zip, pin, block) {
    const run = String(block + 2).padStart(2, "0");
    const pattern = new RegExp(`^(sub-[0-9]{2})/eeg/\\1_task-WristPointingTask_run-${run}_eeg\\.edf$`);
    const names = Array.from(zip.entries.keys()).filter(name => pattern.test(name));
    requireValue(names.length === 1, "Expected one EDF for the selected task block.");
    const name = names[0];
    const alias = pattern.exec(name)[1];
    const stem = `${alias}_task-WristPointingTask`;
    const motion = `${alias}/motion/${stem}_tracksys-BiomechWrist`;
    await verifyDictionaries(zip, `${alias}/eeg/${stem}_channels.tsv`, `${motion}_channels.tsv`);
    const edfBytes = HEADER_BYTES + pin.storedRows * CHANNELS * 2;
    const raw = await member(zip, name, edfBytes, edfBytes);
    const header = raw.subarray(0, HEADER_BYTES);
    const rawDigest = await sha256(raw);
    const headerDigest = await sha256(header);
    requireValue(rawDigest === pin.edfSha256 && headerDigest === pin.edfHeaderSha256,
      "The selected EDF or its header changed.");
    verifyHeader(header, raw.length, pin.storedRows);
    const edf = new DataView(raw.buffer);
    const tsv = await member(zip, `${motion}_run-${run}_motion.tsv`, pin.storedRows * 13);
    requireValue(await sha256(tsv) === pin.tsvSha256, "The selected motion TSV changed.");
    verifyMotion(tsv, edf, pin.storedRows);
    return {edf, ...markerTicks(edf, pin.storedRows)};
  }

  function angleAt(edf, base, axis) {
    const word = edf.getUint16(base + (21 + axis) * 16, true);
    const angle = (word * (25 / 65535) - 12.5) * (180 / Math.PI);
    requireValue(word !== 0 && Math.abs(angle) <= 180, "That trial lacks six complete eligible motion windows.");
    return axis === 0 ? angle : -angle;
  }

  async function extractTrial(block, pin, trial, catalogue) {
    const {edf, cues, returns} = block;
    const cue = cues[trial - 1];
    const returned = returns[trial - 1];
    const targets = OFFSETS.map(offset => cue + offset);
    const prefix = textEncoder.encode([
      FORMAT, "development", SAMPLE_RATE, AXES.join(","), PACKET_CHANNELS.join(","), DEPOSIT, ROLE_SHA, ARCHIVES_SHA,
      pin.sourceRunSha256, FIT_SHA, DESIGN_SHA, cue, returned, targets.join(","), OFFSETS.join(","), "",
    ].join("\n"));
    const packet = new Uint8Array(prefix.length + OFFSETS.length * (2 + 16 * 10 + 2) * 8);
    packet.set(prefix);
    const binary = new DataView(packet.buffer);
    let position = prefix.length;
    function put(value) {
      binary.setFloat64(position, value === 0 ? 0 : value, true);
      position += 8;
    }
    const measured = [];
    const windows = targets.map((target, row) => {
      const firstTick = target - 383;
      requireValue(firstTick >= cue && target < returned && target < pin.storedRows,
        "That trial falls outside the recorded movement interval.");
      const anchorBase = edfOffset(target - 128);
      const anchor = [angleAt(edf, anchorBase, 0), angleAt(edf, anchorBase, 1)];
      anchor.forEach(put);
      const motion = [];
      const emg = [];
      for (let bin = 0; bin < 16; bin++) {
        const angleSum = [0, 0];
        const eegSum = new Array(8).fill(0);
        const emgSquares = new Array(4).fill(0);
        for (let sample = 0; sample < 16; sample++) {
          const base = edfOffset(firstTick + bin * 16 + sample);
          angleSum[0] += angleAt(edf, base, 0);
          angleSum[1] += angleAt(edf, base, 1);
          for (let channel = 0; channel < 8; channel++) {
            eegSum[channel] += edf.getInt16(base + channel * 16, true);
          }
          for (let pair = 0; pair < 4; pair++) {
            const left = base + (8 + pair * 2) * 16;
            const diff = edf.getInt16(left, true) - edf.getInt16(left + 16, true);
            emgSquares[pair] += diff * diff;
          }
        }
        const motionBin = angleSum.map((value, axis) => value / 16 - anchor[axis]);
        motionBin.forEach(put);
        eegSum.forEach(value => put(value / 16));
        motion.push(motionBin);
        emg.push(emgSquares.map(value => Math.sqrt(value / 16)));
      }
      const targetBase = edfOffset(target);
      measured.push([angleAt(edf, targetBase, 0), angleAt(edf, targetBase, 1)]);
      return {
        target_offset_ticks: OFFSETS[row],
        anchor_deg: anchor,
        motion_bins_deg_relative_to_anchor: motion,
        emg_differential_rms_uv: emg,
      };
    });
    for (const pair of measured) pair.forEach(put);
    requireValue(position === packet.length && catalogue.has(await sha256(packet)),
      "This trial does not match the released development fingerprint catalogue.");
    return {windows, measured};
  }

  async function open(file) {
    requireValue(file instanceof Blob, "Choose one original development ZIP.");
    requireValue(globalThis.crypto?.subtle && typeof DecompressionStream === "function",
      "This browser needs local SHA-256 and raw ZIP support. Try a recent browser or use the Python reader.");
    try {
      new DecompressionStream("deflate-raw");
    } catch {
      throw new Error("This browser needs raw ZIP support. Try a recent browser or use the Python reader.");
    }
    verification ??= checkReference();
    const {archives, catalogue} = await verification;
    const allowed = archives.find(entry => entry.bytes === file.size);
    requireValue(allowed, "File size does not match an approved public development ZIP.");
    let bytes;
    try {
      bytes = new Uint8Array(await Blob.prototype.arrayBuffer.call(file));
    } catch {
      throw new Error("The selected development ZIP could not be read. Choose it again.");
    }
    requireValue(bytes.length === allowed.bytes && await sha256(bytes) === allowed.sha256,
      "ZIP bytes do not match an approved public development archive.");
    const zip = zipEntries(bytes);
    let cachedBlock;
    let tail = Promise.resolve();
    async function readTrial(block, trial) {
      requireValue(Number.isInteger(block) && block >= 1 && block <= 8
        && Number.isInteger(trial) && trial >= 1 && trial <= TRIALS,
      "Choose a task block from 1 to 8 and a trial from 1 to 40.");
      const pin = allowed.blocks[block - 1];
      const result = tail.then(async () => {
        if (cachedBlock?.ordinal !== block) {
          cachedBlock = undefined;
          cachedBlock = {ordinal: block, data: await readBlock(zip, pin, block)};
        }
        return extractTrial(cachedBlock.data, pin, trial, catalogue);
      });
      tail = result.then(() => undefined, () => undefined);
      return result;
    }
    return Object.freeze({readTrial});
  }

  globalThis.WristArchive = Object.freeze({open});
