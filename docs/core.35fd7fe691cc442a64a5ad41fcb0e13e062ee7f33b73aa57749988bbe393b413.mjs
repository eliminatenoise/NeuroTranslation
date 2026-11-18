/** Local data inspection and declared-clock alignment. No model inference or training.
 * Packet v1: {schemaVersion:1, dataset:{id,name,sourceUrl,license,organism?,subjectId?,
 * recordingId?,task,timebase?,split,origin?}, streams:[{id,modality,region?,label,
 * unit,frame?,origin,rateHz?,measurement?,t:number[],values:(number|null)[]}] }.
 * t is seconds on dataset.timebase. Units are retained, never converted or mixed.
 * Optional metadata is retained. Importing a held-out split does not train on it.
 */
export const LIMITS = Object.freeze({ maxBytes: 5 * 1024 * 1024, maxRows: 50000,
  maxGridSamples: 5000, maxAlignedValues: 500000 });
export const MODALITIES = Object.freeze(['neural', 'muscle', 'displacement', 'mechanics']);
export const NEURAL_REGIONS = Object.freeze(['brain', 'spinal', 'peripheral', 'autonomic', 'visceral']);
export const ORIGINS = Object.freeze(['measured', 'inferred', 'simulated']);
const SPLITS = ['train', 'validation', 'test', 'held_out', 'heldout', 'unassigned', 'unknown', 'unspecified', 'fixture'];
const encoder = new TextEncoder();
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const has = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
const present = value => typeof value === 'string' && value.trim().length > 0;
const known = value => present(value) && !['unknown', 'unspecified', 'unassigned', 'n/a', 'na', '?'].includes(value.trim().toLowerCase());
const fail = message => { throw new Error(message); };
const clone = value => JSON.parse(JSON.stringify(value));

function textField(value, path, { optional = false, max = 2000 } = {}) {
  if (optional && (value === undefined || value === null || value === '')) return;
  if (!present(value)) fail(`${path} needs a non-empty text value.`);
  if (value.length > max) fail(`${path} is too long (maximum ${max} characters).`);
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(value) || /<\/?[a-z!][^>]*>/iu.test(value)) {
    fail(`${path} must be plain text.`);
  }
}

function assertTextSize(text, label) {
  if (typeof text !== 'string') fail(`${label} must be text.`);
  const bytes = encoder.encode(text).byteLength;
  if (bytes > LIMITS.maxBytes) fail(`${label} is ${bytes} bytes; the limit is ${LIMITS.maxBytes} bytes (5 MiB).`);
  return bytes;
}

function packetBytes(packet) {
  let text;
  try { text = JSON.stringify(packet); } catch { fail('The packet must contain plain JSON data without circular references.'); }
  return assertTextSize(text, 'The packet');
}

function plainMetadata(value, path, seen = new Set(), depth = 0) {
  if (value === null || value === undefined || typeof value === 'boolean') return;
  if (typeof value === 'string') {
    if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(value) || /<\/?[a-z!][^>]*>/iu.test(value)) fail(`${path} must be plain text.`);
    return;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) fail(`${path} must be finite.`);
    return;
  }
  if (typeof value !== 'object' || (!Array.isArray(value) && ![Object.prototype, null].includes(Object.getPrototypeOf(value)))) fail(`${path} must contain plain JSON metadata.`);
  if (depth > 12 || seen.has(value)) fail(`${path} has nested or circular metadata that cannot be imported.`);
  seen.add(value);
  for (const [key, child] of Object.entries(value)) plainMetadata(child, `${path}.${key}`, seen, depth + 1);
  seen.delete(value);
}

/** Validate without mutation or numeric coercion; return the original packet. */
export function validatePacket(packet) {
  if (!isObject(packet) || packet.schemaVersion !== 1) fail('Use a packet with schemaVersion: 1.');
  for (const [field, value] of Object.entries(packet)) if (field !== 'dataset' && field !== 'streams') plainMetadata(value, field);
  if (!isObject(packet.dataset)) fail('The packet needs a dataset object.');
  const d = packet.dataset;
  plainMetadata(d, 'dataset');
  for (const field of ['id', 'name', 'license', 'task', 'split']) textField(d[field], `dataset.${field}`);
  for (const field of ['organism', 'subjectId', 'recordingId', 'timebase']) textField(d[field], `dataset.${field}`, { optional: true });
  if (!SPLITS.includes(d.split)) fail(`dataset.split must be one of: ${SPLITS.join(', ')}.`);
  if (!has(d, 'sourceUrl')) fail('dataset.sourceUrl is required; use null when the source has no public URL.');
  textField(d.sourceUrl, 'dataset.sourceUrl', { optional: true });
  if (present(d.sourceUrl)) {
    let url;
    try { url = new URL(d.sourceUrl); } catch { fail('dataset.sourceUrl needs a complete http or https URL, or null.'); }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) fail('dataset.sourceUrl needs an http or https URL without login details.');
  }
  if (has(d, 'origin') && ![...ORIGINS, 'constructed_example', 'mixed', 'unknown'].includes(d.origin)) fail('dataset.origin is not recognised.');
  if (!Array.isArray(packet.streams) || packet.streams.length === 0) fail('The packet needs at least one stream.');
  const ids = new Set();
  let rowCount = 0;
  for (const [index, s] of packet.streams.entries()) {
    const path = `streams[${index}]`;
    if (!isObject(s)) fail(`${path} must be a stream object.`);
    for (const [field, value] of Object.entries(s)) if (field !== 't' && field !== 'values') plainMetadata(value, `${path}.${field}`);
    for (const field of ['id', 'label', 'unit']) textField(s[field], `${path}.${field}`);
    if (ids.has(s.id)) fail(`Stream id "${s.id}" is repeated in dataset "${d.id}".`);
    ids.add(s.id);
    if (!MODALITIES.includes(s.modality)) fail(`${path}.modality must be neural, muscle, displacement or mechanics.`);
    if (!ORIGINS.includes(s.origin)) fail(`${path}.origin must be measured, inferred or simulated.`);
    if (s.region !== undefined && s.region !== null && !NEURAL_REGIONS.includes(s.region)) fail(`${path}.region must be brain, spinal, peripheral, autonomic or visceral.`);
    if (s.modality !== 'neural' && s.region != null) fail(`${path}.region is reserved for neural streams; use anatomy for other locations.`);
    for (const field of ['frame', 'measurement', 'signalType', 'anatomy']) textField(s[field], `${path}.${field}`, { optional: true });
    if (s.modality === 'neural' && /\b(?:emg|electromyograph\w*)\b/iu.test(`${s.label} ${s.measurement ?? ''} ${s.signalType ?? ''}`)) {
      fail(`${path} describes EMG. Muscle electrical activity belongs in the muscle modality, not neural.`);
    }
    if (s.rateHz !== undefined && (typeof s.rateHz !== 'number' || !Number.isFinite(s.rateHz) || s.rateHz <= 0)) fail(`${path}.rateHz must be a finite number greater than zero.`);
    if (!Array.isArray(s.t) || !Array.isArray(s.values) || s.t.length === 0 || s.t.length !== s.values.length) fail(`${path}.t and values must be non-empty arrays of equal length.`);
    rowCount += s.t.length;
    if (rowCount > LIMITS.maxRows) fail(`The packet has ${rowCount} sample rows so far; the limit is ${LIMITS.maxRows}.`);
    for (let i = 0; i < s.t.length; i++) {
      if (typeof s.t[i] !== 'number' || !Number.isFinite(s.t[i])) fail(`${path}.t[${i}] must be a finite time in seconds.`);
      if (i && s.t[i] <= s.t[i - 1]) fail(`${path}.t must increase strictly; check sample ${i + 1}.`);
      if (s.values[i] !== null && (typeof s.values[i] !== 'number' || !Number.isFinite(s.values[i]))) fail(`${path}.values[${i}] must be a finite number or null.`);
    }
  }
  if (d.origin === 'constructed_example' && packet.streams.some(s => s.origin !== 'simulated')) fail('A constructed example must contain only simulated streams.');
  packetBytes(packet);
  return packet;
}

/** Parse a local JSON packet. File text is bounded before JSON parsing. */
export function parsePacket(text) {
  const byteLength = assertTextSize(text, 'The JSON file');
  let packet;
  try { packet = JSON.parse(text); } catch { fail('The JSON could not be read. Check commas, quotes and brackets.'); }
  validatePacket(packet);
  return { ...packet, importInfo: { format: 'json', byteLength, ...countsFor(packet.streams) } };
}

function csvRows(text) {
  const rows = [];
  let row = [], cell = '', state = 'start', line = 1, startLine = 1;
  const addRow = () => {
    row.push(cell);
    if (!(row.length === 1 && row[0].trim() === '')) rows.push({ cells: row, line: startLine });
    if (rows.length > LIMITS.maxRows + 1) fail(`The CSV exceeds ${LIMITS.maxRows} data rows.`);
    row = []; cell = ''; state = 'start'; startLine = line + 1;
  };
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (state === 'quoted') {
      if (c === '"') {
        if (text[i + 1] === '"') { cell += '"'; i++; } else state = 'closed';
      } else { cell += c; if (c === '\n') line++; }
      continue;
    }
    if (c === ',') {
      if (row.length >= 3) fail(`CSV line ${line}: at most four columns are supported.`);
      row.push(cell); cell = ''; state = 'start'; continue;
    }
    if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      addRow(); line++; continue;
    }
    if (state === 'closed') fail(`CSV line ${line}: a closing quote must be followed by a comma or line ending.`);
    if (c === '"') {
      if (state !== 'start') fail(`CSV line ${line}: a quote appears inside an unquoted cell.`);
      state = 'quoted';
    } else { cell += c; state = 'plain'; }
  }
  if (state === 'quoted') fail(`CSV line ${startLine}: a quoted cell was never closed.`);
  if (cell !== '' || row.length || state !== 'start') addRow();
  return rows;
}

const numberPattern = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/u;
function csvNumber(value, label, nullable = false) {
  const clean = value.trim();
  if (nullable && (clean === '' || clean === 'null')) return null;
  if (!numberPattern.test(clean) || !Number.isFinite(Number(clean))) fail(`${label} needs a finite number${nullable ? ', an empty cell or null' : ''}.`);
  return Number(clean);
}

/** CSV headers: time,value; optional modality,unit. Metadata is
 * {dataset:{...packet dataset...},stream:{id,label,modality,unit,origin,...}}.
 * A file contains one stream. modality/unit can come from metadata or constant
 * CSV columns; conflicts are errors. Empty or literal null values stay missing.
 */
export function parseCsv(text, metadata) {
  const byteLength = assertTextSize(text, 'The CSV file');
  if (!isObject(metadata) || !isObject(metadata.dataset) || !isObject(metadata.stream)) fail('CSV metadata needs dataset and stream objects.');
  const rows = csvRows(text.replace(/^\uFEFF/u, ''));
  if (rows.length < 2) fail('The CSV needs a header and at least one data row.');
  const header = rows[0].cells.map(cell => cell.trim());
  if (new Set(header).size !== header.length) fail('CSV column names must be unique.');
  if (!header.includes('time') || !header.includes('value')) fail('CSV headers must include time and value.');
  if (header.some(h => !['time', 'value', 'modality', 'unit'].includes(h))) fail('CSV columns may only be time, value, modality and unit.');
  const s = { ...metadata.stream, t: [], values: [] };
  for (const row of rows.slice(1)) {
    if (row.cells.length !== header.length) fail(`CSV line ${row.line}: expected ${header.length} columns, found ${row.cells.length}.`);
    const values = Object.fromEntries(header.map((h, i) => [h, row.cells[i]]));
    for (const field of ['modality', 'unit']) {
      if (has(values, field)) {
        const value = values[field].trim();
        if (!value) fail(`CSV line ${row.line}: ${field} is empty.`);
        if (s[field] !== undefined && s[field] !== value) fail(`CSV line ${row.line}: ${field} conflicts with the stream metadata or an earlier row.`);
        s[field] = value;
      }
    }
    s.t.push(csvNumber(values.time, `CSV line ${row.line}: time`));
    s.values.push(csvNumber(values.value, `CSV line ${row.line}: value`, true));
  }
  const packet = { schemaVersion: 1, dataset: clone(metadata.dataset), streams: [s] };
  validatePacket(packet);
  return { ...packet, importInfo: { format: 'csv', byteLength, ...countsFor(packet.streams) } };
}

function countsFor(streams) {
  let rowCount = 0, missingValueCount = 0;
  for (const s of streams) {
    rowCount += s.t.length;
    for (const value of s.values) if (value === null) missingValueCount++;
  }
  return { streamCount: streams.length, rowCount, nonMissingValueCount: rowCount - missingValueCount, missingValueCount };
}

function validatedPackets(packets) {
  if (!Array.isArray(packets) || packets.length === 0) fail('Choose at least one dataset.');
  let rows = 0, bytes = 0;
  const streams = new Set(), datasets = new Map();
  for (const packet of packets) {
    validatePacket(packet);
    rows += countsFor(packet.streams).rowCount;
    bytes += packetBytes(packet);
    const old = datasets.get(packet.dataset.id);
    const dataset = JSON.stringify(packet.dataset);
    if (old && old !== dataset) fail(`Dataset id "${packet.dataset.id}" has conflicting metadata; use distinct dataset ids.`);
    datasets.set(packet.dataset.id, dataset);
    for (const s of packet.streams) {
      const key = JSON.stringify([packet.dataset.id, s.id]);
      if (streams.has(key)) fail(`Stream "${s.id}" in dataset "${packet.dataset.id}" was selected twice.`);
      streams.add(key);
    }
  }
  if (rows > LIMITS.maxRows) fail(`The selected datasets contain ${rows} sample rows; the combined limit is ${LIMITS.maxRows}.`);
  if (bytes > LIMITS.maxBytes) fail(`The selected packets contain ${bytes} JSON bytes; the combined limit is ${LIMITS.maxBytes} bytes (5 MiB).`);
  return packets;
}

function coverageFor(streams) {
  const counts = Object.fromEntries(MODALITIES.map(modality => [modality, streams.filter(s => s.modality === modality).length]));
  const regions = new Set(streams.filter(s => s.modality === 'neural' && s.region).map(s => s.region));
  return { modalities: { present: MODALITIES.filter(m => counts[m]), missing: MODALITIES.filter(m => !counts[m]), counts },
    neural: { presentRegions: NEURAL_REGIONS.filter(r => regions.has(r)), missingRegions: NEURAL_REGIONS.filter(r => !regions.has(r)),
      unspecifiedStreamCount: streams.filter(s => s.modality === 'neural' && !s.region).length,
      completeBodyCoverageEstablished: false } };
}

/** Collect streams for separate inspection. This never labels them synchronized. */
export function combinePackets(packets) {
  validatedPackets(packets);
  const datasets = [...new Map(packets.map(p => [p.dataset.id, clone(p.dataset)])).values()];
  const streams = packets.flatMap(p => p.streams.map(s => ({ ...clone(s), key: JSON.stringify([p.dataset.id, s.id]), datasetId: p.dataset.id, dataset: clone(p.dataset) })));
  return { schemaVersion: 1, kind: 'separate_inspection', synchronized: false, datasets, streams,
    counts: { datasetCount: datasets.length, packetCount: packets.length, ...countsFor(streams) }, coverage: coverageFor(streams) };
}

export function summarizePackets(packets) {
  const combined = combinePackets(packets);
  const warnings = [];
  for (const d of combined.datasets) {
    if (!present(d.sourceUrl)) warnings.push(`${d.name}: no public source URL is declared.`);
    if (/^(unknown|unspecified|unassigned)$/iu.test(d.license)) warnings.push(`${d.name}: rights are unknown; confirm them before redistribution.`);
    if (['organism', 'subjectId', 'recordingId', 'timebase'].some(field => !known(d[field]))) warnings.push(`${d.name}: incomplete organism, subject, recording or clock metadata; inspect separately.`);
    if (['unknown', 'unspecified', 'unassigned'].includes(d.split)) warnings.push(`${d.name}: the training/held-out split is unknown.`);
  }
  for (const s of combined.streams) if (['displacement', 'mechanics'].includes(s.modality) && !present(s.frame)) warnings.push(`${s.label}: the coordinate frame is not declared.`);
  return { ...combined.counts, coverage: combined.coverage, datasets: combined.datasets, warnings,
    limitation: 'Declared data and timing can be inspected here. They do not establish neural function, causal relationships or whole-body coverage.' };
}

/** Check declared pairing only. No clock offset, drift correction or inferred
 * cross-dataset correspondence is invented. Matching declarations are not proof
 * of hardware synchronization or biological validation. */
export function assessCompatibility(packets) {
  const combined = combinePackets(packets);
  const { datasets, streams } = combined;
  const issues = [];
  for (const field of ['organism', 'subjectId', 'recordingId', 'timebase']) {
    if (datasets.some(d => !known(d[field]))) issues.push(`Every dataset needs a known ${field} before alignment.`);
    else if (new Set(datasets.map(d => d[field])).size !== 1) issues.push(`The datasets have different ${field} values; inspect them separately.`);
  }
  if (new Set(datasets.map(d => d.task)).size !== 1) issues.push('The datasets declare different tasks; inspect them separately.');
  if (new Set(datasets.map(d => d.split)).size !== 1) issues.push('The datasets have different split labels; keep training and evaluation data separate.');
  const constructed = datasets.every(d => d.origin === 'constructed_example') && streams.every(s => s.origin === 'simulated');
  if (constructed && datasets.some(d => d.organism !== 'invented')) issues.push('A constructed example must declare organism: invented.');
  if (streams.some(s => s.origin === 'simulated') && !constructed) issues.push('Simulated streams cannot form biological pairs. Use a declared constructed example containing only simulated streams.');
  const startSeconds = Math.max(...streams.map(s => s.t[0]));
  const endSeconds = Math.min(...streams.map(s => s.t.at(-1)));
  const overlap = startSeconds <= endSeconds ? { startSeconds, endSeconds, durationSeconds: endSeconds - startSeconds } : null;
  if (!overlap) issues.push('The streams have no common time interval.');
  const compatible = issues.length === 0;
  return { compatible, canAlign: compatible, status: compatible ? (constructed ? 'constructed_example' : 'declared_common_recording') : 'unpaired',
    reason: issues[0] ?? (constructed ? 'Invented streams share a declared fixture clock.' : 'The streams declare the same subject, recording and clock.'),
    issues, overlap, counts: combined.counts, coverage: combined.coverage,
    pairing: { kind: compatible ? (constructed ? 'constructed_example' : 'declared_common_recording') : 'unpaired',
      organism: compatible ? datasets[0].organism : null,
      subjectId: compatible ? datasets[0].subjectId : null, recordingId: compatible ? datasets[0].recordingId : null,
      timebase: compatible ? datasets[0].timebase : null, hardwareSynchronizationVerified: false,
      biologicalValidationEstablished: false, containsInferredValues: streams.some(s => s.origin === 'inferred') },
    warnings: summarizePackets(packets).warnings,
    limitation: constructed ? 'All values are invented for a software test. No biological measurements or predictions are shown.' : 'Alignment follows supplied clock metadata. It does not verify acquisition synchronization, train a model or establish biological correspondence.' };
}

function sampleStream(stream, grid, method, maxGapSeconds) {
  const values = [], mask = [], status = [];
  let right = 0;
  for (const time of grid) {
    while (right < stream.t.length && stream.t[right] < time) right++;
    let value = null, state;
    if (right < stream.t.length && stream.t[right] === time) {
      value = stream.values[right]; state = value === null ? 'missing_input' : 'original';
    } else if (right === 0 || right === stream.t.length) state = 'outside_range';
    else if (stream.values[right - 1] === null || stream.values[right] === null) state = 'missing_input';
    else if (stream.t[right] - stream.t[right - 1] > maxGapSeconds) state = 'long_gap';
    else if (method === 'nearest') {
      value = time - stream.t[right - 1] <= stream.t[right] - time ? stream.values[right - 1] : stream.values[right]; state = 'nearest';
    } else {
      const weight = (time - stream.t[right - 1]) / (stream.t[right] - stream.t[right - 1]);
      // Convex weighting avoids overflow from subtracting opposite extreme values.
      value = stream.values[right - 1] * (1 - weight) + stream.values[right] * weight;
      if (!Number.isFinite(value)) fail(`Interpolation overflowed for stream "${stream.id}"; inspect the original values.`);
      state = 'linear';
    }
    values.push(value); mask.push(value !== null); status.push(state);
  }
  return { values, mask, status, counts: { gridSamples: grid.length, validSamples: mask.filter(Boolean).length,
    missingSamples: mask.filter(v => !v).length, originalSamples: status.filter(s => s === 'original').length,
    resampledSamples: status.filter(s => s === 'linear' || s === 'nearest').length,
    longGapSamples: status.filter(s => s === 'long_gap').length, missingInputSamples: status.filter(s => s === 'missing_input').length,
    outsideRangeSamples: status.filter(s => s === 'outside_range').length } };
}

/** Resample only the common interval. stepSeconds and maxGapSeconds are required
 * finite positive numbers. Missing samples and long brackets stay null, with a
 * false mask. There is no extrapolation, unit conversion or prediction. */
export function alignPackets(packets, options = {}) {
  const { stepSeconds, maxGapSeconds, method = 'nearest' } = options;
  if (typeof stepSeconds !== 'number' || !Number.isFinite(stepSeconds) || stepSeconds <= 0) fail('stepSeconds must be a finite number greater than zero.');
  if (typeof maxGapSeconds !== 'number' || !Number.isFinite(maxGapSeconds) || maxGapSeconds <= 0) fail('maxGapSeconds must be a finite number greater than zero.');
  if (!['nearest', 'linear'].includes(method)) fail('Choose nearest or linear sampling.');
  const compatibility = assessCompatibility(packets);
  if (!compatibility.compatible) fail(`Alignment refused: ${compatibility.issues.join(' ')}`);
  const { startSeconds, endSeconds } = compatibility.overlap;
  const count = Math.floor((endSeconds - startSeconds) / stepSeconds) + 1;
  if (!Number.isFinite(count) || count > LIMITS.maxGridSamples) fail(`The grid needs ${Number.isFinite(count) ? count : 'too many'} samples; the limit is ${LIMITS.maxGridSamples}. Increase stepSeconds.`);
  const combined = combinePackets(packets);
  if (count * combined.streams.length > LIMITS.maxAlignedValues) fail(`The grid needs ${count * combined.streams.length} stream values; the limit is ${LIMITS.maxAlignedValues}. Increase stepSeconds or select fewer streams.`);
  const t = Array.from({ length: count }, (_, i) => startSeconds + i * stepSeconds).filter(time => time <= endSeconds);
  if (t.some((time, i) => !Number.isFinite(time) || (i > 0 && time <= t[i - 1]))) fail('The requested step is too small for this clock precision; increase stepSeconds.');
  const streams = combined.streams.map(s => {
    const sampled = sampleStream(s, t, method, maxGapSeconds);
    const { t: originalTimes, values: originalValues, ...metadata } = s;
    return { ...metadata, ...sampled, inputSampleCount: originalTimes.length, inputMissingCount: originalValues.filter(v => v === null).length };
  });
  return { schemaVersion: 1, kind: 'declared_clock_alignment', t, timeUnit: 's', datasets: combined.datasets, streams,
    method, stepSeconds, maxGapSeconds, overlap: compatibility.overlap, pairing: compatibility.pairing,
    diagnostics: { input: combined.counts, gridSampleCount: t.length, outputValueCount: t.length * streams.length,
      validValueCount: streams.reduce((n, s) => n + s.counts.validSamples, 0), missingValueCount: streams.reduce((n, s) => n + s.counts.missingSamples, 0),
      noExtrapolation: true, unitConversionPerformed: false, unitDimensionsVerified: false,
      modelInferencePerformed: false, clockCorrectionPerformed: false,
      sampling: method === 'linear' ? 'Linear interpolation inside supplied brackets only.' : 'Nearest sample inside supplied brackets only; ties choose the earlier sample.',
      gapRule: 'Null samples and brackets longer than maxGapSeconds remain missing.',
      warnings: compatibility.warnings, limitation: compatibility.limitation }, coverage: compatibility.coverage };
}

/** Deterministic four-modality fixture. Every number is invented. */
export function examplePacket() {
  const t = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4];
  return { schemaVersion: 1, dataset: { id: 'constructed-four-modality-example', name: 'Invented four-modality example',
    sourceUrl: null, license: 'CC0-1.0 (invented demo values)', organism: 'invented', subjectId: 'invented-subject', recordingId: 'invented-recording',
    task: 'Invented single-axis movement', timebase: 'fixture-clock-seconds', split: 'fixture', origin: 'constructed_example',
    notes: 'Software fixture only. Every value is invented; no biological recording, trained prediction or whole-body coverage is demonstrated.' },
    streams: [
      { id: 'brain', modality: 'neural', region: 'brain', label: 'Invented brain signal', unit: 'a.u.', origin: 'simulated', rateHz: 2, t: [...t], values: [0, 1, 2, 1, 0, -1, -2, -1, 0] },
      { id: 'muscle', modality: 'muscle', label: 'Invented muscle electrical activity (EMG)', measurement: 'EMG', unit: 'mV', origin: 'simulated', rateHz: 2, t: [...t], values: [0, 0.2, 0.5, 0.3, 0.1, 0.2, 0.4, 0.2, 0] },
      { id: 'displacement', modality: 'displacement', label: 'Invented displacement', unit: 'mm', frame: 'Invented local x axis', origin: 'simulated', rateHz: 1, t: [0, 1, 2, 3, 4], values: [0, 2, 4, 2, 0] },
      { id: 'force', modality: 'mechanics', label: 'Invented force', unit: 'N', frame: 'Invented local x axis', origin: 'simulated', rateHz: 2, t: [...t], values: [0, 1, 2, null, 0, -1, -2, -1, 0] }
    ] };
}
