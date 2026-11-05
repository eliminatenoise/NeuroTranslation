import test from 'node:test';
import assert from 'node:assert/strict';
import { LIMITS, validatePacket, parsePacket, parseCsv, combinePackets, summarizePackets,
  assessCompatibility, alignPackets, examplePacket } from '../src/core.mjs';

const copy = value => structuredClone(value);
function stream(overrides = {}) {
  return { id: 'brain', label: 'Recorded brain signal', modality: 'neural', region: 'brain',
    unit: 'mV', origin: 'measured', t: [0, 1, 2], values: [0, 2, 4], ...overrides };
}
function packet(overrides = {}, streams = [stream()]) {
  return { schemaVersion: 1, dataset: { id: 'dataset-a', name: 'Constructed test input',
    sourceUrl: null, license: 'CC0-1.0', organism: 'constructed-test-organism', subjectId: 'test-subject', recordingId: 'test-recording',
    task: 'Test movement', timebase: 'test-clock', split: 'test', ...overrides }, streams };
}
const options = { stepSeconds: 0.5, maxGapSeconds: 2, method: 'linear' };
const metadata = () => ({ dataset: packet().dataset, stream: { id: 'csv', label: 'CSV force', modality: 'mechanics', unit: 'N', frame: 'local x', origin: 'measured' } });

test('valid multi-rate streams align on overlap and retain separate units and provenance', () => {
  const a = packet({}, [stream()]);
  const b = packet({ id: 'dataset-b', sourceUrl: 'https://example.org/source' }, [stream({ id: 'force',
    label: 'Force', modality: 'mechanics', region: undefined, unit: 'N', frame: 'local x',
    t: [0.5, 1, 1.5, 2.5], values: [10, 20, 30, 50] })]);
  const result = alignPackets([a, b], options);
  assert.deepEqual(result.t, [0.5, 1, 1.5, 2]);
  assert.deepEqual(result.streams[0].values, [1, 2, 3, 4]);
  assert.deepEqual(result.streams[1].values, [10, 20, 30, 40]);
  assert.deepEqual(result.streams.map(s => s.unit), ['mV', 'N']);
  assert.equal(result.streams[1].dataset.sourceUrl, 'https://example.org/source');
  assert.equal(result.streams[1].dataset.split, 'test');
  assert.equal(result.pairing.hardwareSynchronizationVerified, false);
  assert.equal(result.pairing.biologicalValidationEstablished, false);
  assert.equal(result.diagnostics.unitConversionPerformed, false);
  assert.equal(result.diagnostics.gridSampleCount, 4);
  assert.equal(result.diagnostics.input.rowCount, 7);
  assert.equal(result.streams[0].counts.resampledSamples, 2);
  assert.deepEqual(a.streams[0].values, [0, 2, 4]);
});

test('unknown pairing remains inspectable and is refused for alignment', () => {
  for (const field of ['organism', 'subjectId', 'recordingId', 'timebase']) {
    const input = packet(); delete input.dataset[field];
    const assessment = assessCompatibility([input]);
    assert.equal(assessment.compatible, false);
    assert.equal(assessment.status, 'unpaired');
    assert.match(assessment.reason, new RegExp(field));
    assert.equal(combinePackets([input]).synchronized, false);
    assert.throws(() => alignPackets([input], options), /Alignment refused/);
  }
});

test('different organism, subject, recording, clock, task and split each block cross-dataset alignment', () => {
  for (const [field, value] of [['organism', 'other'], ['subjectId', 'other'], ['recordingId', 'other'], ['timebase', 'other'], ['task', 'other'], ['split', 'train']]) {
    const inputs = [packet(), packet({ id: 'dataset-b', [field]: value })];
    assert.equal(assessCompatibility(inputs).compatible, false, field);
    assert.throws(() => alignPackets(inputs, options), /Alignment refused/, field);
  }
});

test('null samples and long gaps stay missing with explicit masks for both methods', () => {
  const input = packet({}, [stream({ t: [0, 1, 2, 6, 7], values: [0, null, 2, 6, 7] })]);
  for (const method of ['nearest', 'linear']) {
    const result = alignPackets([input], { stepSeconds: 0.5, maxGapSeconds: 1, method });
    const s = result.streams[0];
    assert.equal(s.values[0], 0);
    assert.equal(s.values[1], null);
    assert.equal(s.values[2], null);
    assert.equal(s.values[3], null);
    assert.equal(s.values[4], 2);
    assert.equal(s.values[5], null);
    assert.equal(s.status[5], 'long_gap');
    assert.equal(s.values[12], 6);
    assert.equal(s.mask[12], true);
    assert.equal(s.mask[5], false);
    assert.equal(s.counts.missingInputSamples, 3);
    assert.equal(s.counts.longGapSamples, 7);
  }
});

test('nearest uses earlier ties and never skips explicit missing samples', () => {
  const result = alignPackets([packet()], { ...options, method: 'nearest' });
  assert.deepEqual(result.streams[0].values, [0, 0, 2, 2, 4]);
  assert.equal(result.streams[0].status[1], 'nearest');
});

test('alignment never extrapolates and rejects non-overlapping streams', () => {
  const input = packet({}, [stream({ t: [0, 1, 2], values: [0, 1, 2] }), stream({ id: 'second', t: [0.25, 1.25, 1.75], values: [1, 2, 3] })]);
  const result = alignPackets([input], options);
  assert.deepEqual(result.t, [0.25, 0.75, 1.25, 1.75]);
  for (const s of result.streams) assert.equal(s.counts.outsideRangeSamples, 0);
  assert.equal(result.diagnostics.noExtrapolation, true);
  input.streams[1].t = [3, 4, 5];
  assert.equal(assessCompatibility([input]).overlap, null);
  assert.throws(() => alignPackets([input], options), /no common time interval/);
});

test('a single shared timestamp forms one original sample and no extrapolation', () => {
  const input = packet({}, [stream({ t: [1], values: [3] }), stream({ id: 'second', t: [0, 1], values: [2, 4] })]);
  const result = alignPackets([input], options);
  assert.deepEqual(result.t, [1]);
  assert.deepEqual(result.streams.map(s => s.values), [[3], [4]]);
});

test('constructed example is deterministic, four-modality and explicitly invented', () => {
  const fixture = examplePacket();
  assert.deepEqual(fixture, examplePacket());
  validatePacket(fixture);
  const assessment = assessCompatibility([fixture]);
  assert.equal(assessment.status, 'constructed_example');
  assert.match(assessment.limitation, /invented/);
  assert.deepEqual(assessment.coverage.modalities.missing, []);
  assert.deepEqual(assessment.coverage.neural.presentRegions, ['brain']);
  assert.deepEqual(assessment.coverage.neural.missingRegions, ['spinal', 'peripheral', 'autonomic', 'visceral']);
  assert.equal(assessment.coverage.neural.completeBodyCoverageEstablished, false);
  const aligned = alignPackets([fixture], options);
  assert.equal(aligned.diagnostics.modelInferencePerformed, false);
  assert.ok(aligned.streams.every(s => s.origin === 'simulated'));
  assert.equal(summarizePackets([fixture]).missingValueCount, 1);
});

test('simulated streams cannot be smuggled into biological pairs or fixtures', () => {
  const mixed = packet({}, [stream(), stream({ id: 'sim', origin: 'simulated' })]);
  assert.equal(assessCompatibility([mixed]).compatible, false);
  assert.throws(() => alignPackets([mixed], options), /Simulated streams cannot form biological pairs/);
  const fake = examplePacket(); fake.streams[0].origin = 'measured';
  assert.throws(() => validatePacket(fake), /only simulated/);
  const undeclared = examplePacket(); delete undeclared.dataset.origin;
  assert.equal(assessCompatibility([undeclared]).compatible, false);
});

test('inferred imported values remain labelled and never become measured predictions', () => {
  const input = packet({}, [stream({ origin: 'inferred' })]);
  const result = alignPackets([input], options);
  assert.equal(result.streams[0].origin, 'inferred');
  assert.equal(result.pairing.containsInferredValues, true);
  assert.equal(result.diagnostics.modelInferencePerformed, false);
});

test('valid CSV supports CRLF, BOM, quotes, missing values and exact counts', () => {
  const input = '\uFEFF"time","value",modality,unit\r\n0,1,mechanics,N\r\n0.5,,mechanics,N\r\n1,null,mechanics,N\r\n1.5,2e1,mechanics,N\r\n';
  const result = parseCsv(input, metadata());
  assert.deepEqual(result.streams[0].t, [0, 0.5, 1, 1.5]);
  assert.deepEqual(result.streams[0].values, [1, null, null, 20]);
  assert.deepEqual(result.importInfo, { format: 'csv', byteLength: new TextEncoder().encode(input).length,
    streamCount: 1, rowCount: 4, nonMissingValueCount: 2, missingValueCount: 2 });
  const fromColumns = metadata(); delete fromColumns.stream.modality; delete fromColumns.stream.unit;
  assert.equal(parseCsv('time,value,modality,unit\n0,1,mechanics,N', fromColumns).streams[0].unit, 'N');
});

test('CSV refuses malformed structure, numeric coercion and metadata conflicts', () => {
  for (const bad of ['time,value\n0,1,2', 'time,value\n"0,1', 'time,value\n0,"1"oops',
    'time,value\n0,1"', 'time,time,value\n0,0,1', 'time,other\n0,1', 'time,value,other\n0,1,2',
    'time,value\n,2', 'time,value\n0,NaN', 'time,value\n0,Infinity', 'time,value\n0,0x10',
    'time,value\n0,1\n0,2', 'time,value,unit\n0,1,mV', 'time,value,unit\n0,1,', 'time,value']) {
    assert.throws(() => parseCsv(bad, metadata()), Error, bad);
  }
  assert.throws(() => parseCsv('time,value\n0,1', {}), /metadata/);
});

test('JSON parser validates schema, reports counts and refuses malformed JSON', () => {
  const original = packet({}, [stream({ values: [1, null, 3] })]);
  const result = parsePacket(JSON.stringify(original));
  assert.equal(result.importInfo.rowCount, 3);
  assert.equal(result.importInfo.missingValueCount, 1);
  assert.equal(result.importInfo.streamCount, 1);
  assert.throws(() => parsePacket('{"schemaVersion":1,'), /JSON could not be read/);
  assert.throws(() => parsePacket('[]'), /schemaVersion/);
  assert.throws(() => parsePacket('{"schemaVersion":2}'), /schemaVersion/);
  assert.throws(() => parsePacket('null'), /schemaVersion/);
});

test('validation refuses bad values, clocks, units, ids, rates, regions and markup', () => {
  for (const change of [
    p => { p.streams[0].values[1] = Infinity; },
    p => { p.streams[0].values[1] = NaN; },
    p => { p.streams[0].values[1] = '2'; },
    p => { p.streams[0].t[1] = null; },
    p => { p.streams[0].t[1] = NaN; },
    p => { p.streams[0].t[1] = '1'; },
    p => { p.streams[0].t = [0, 0, 2]; },
    p => { p.streams[0].t = [2, 1, 0]; },
    p => { p.streams[0].values.pop(); },
    p => { p.streams[0].unit = ''; },
    p => { p.streams.push(copy(p.streams[0])); },
    p => { p.streams[0].rateHz = -1; },
    p => { p.streams[0].region = 'whole-body'; },
    p => { p.streams[0].label = '<img src=x onerror=alert(1)>'; },
    p => { p.dataset.provenance = { notes: '<script>alert(1)</script>' }; },
    p => { p.dataset.provenance = { uncertainty: Infinity }; },
    p => { p.dataset.provenance = new Date(); },
    p => { p.dataset.sourceUrl = 'javascript:alert(1)'; },
    p => { p.dataset.sourceUrl = 'https://user:password@example.org'; },
    p => { p.dataset.split = 'anything'; },
    p => { delete p.dataset.license; },
    p => { p.streams[0].origin = 'observed'; }
  ]) {
    const input = packet(); change(input); assert.throws(() => validatePacket(input), Error);
  }
  const emg = packet({}, [stream({ label: 'Surface EMG' })]);
  assert.throws(() => validatePacket(emg), /belongs in the muscle modality/);
  const muscle = packet({}, [stream({ modality: 'muscle', region: undefined, label: 'Surface EMG' })]);
  assert.equal(validatePacket(muscle), muscle);
});

test('missing neural regions, frames, rights and split labels remain visible', () => {
  const input = packet({ license: 'unknown', split: 'unknown' }, [stream({ region: undefined }),
    stream({ id: 'motion', label: 'Displacement', modality: 'displacement', region: undefined, unit: 'mm' })]);
  const summary = summarizePackets([input]);
  assert.equal(summary.coverage.neural.unspecifiedStreamCount, 1);
  assert.equal(summary.coverage.neural.missingRegions.length, 5);
  assert.ok(summary.warnings.some(w => w.includes('rights are unknown')));
  assert.ok(summary.warnings.some(w => w.includes('split is unknown')));
  assert.ok(summary.warnings.some(w => w.includes('coordinate frame')));
});

test('duplicate selections and conflicting dataset metadata are errors', () => {
  assert.throws(() => combinePackets([packet(), packet()]), /selected twice/);
  assert.throws(() => combinePackets([packet(), packet({ name: 'Different' }, [stream({ id: 'second' })])]), /conflicting metadata/);
  const combined = combinePackets([packet(), packet({}, [stream({ id: 'second' })])]);
  assert.equal(combined.counts.datasetCount, 1);
  assert.equal(combined.counts.streamCount, 2);
  combined.streams[0].dataset.name = 'Changed copy';
  assert.equal(combined.datasets[0].name, 'Constructed test input');
});

test('file and row limits apply before import or expensive alignment', () => {
  const oversized = ' '.repeat(LIMITS.maxBytes + 1);
  assert.throws(() => parsePacket(oversized), /5 MiB/);
  assert.throws(() => parseCsv(oversized, metadata()), /5 MiB/);
  const overRows = packet({}, [stream({ t: Array.from({ length: LIMITS.maxRows + 1 }, (_, i) => i), values: Array(LIMITS.maxRows + 1).fill(0) })]);
  assert.throws(() => validatePacket(overRows), /sample rows/);
  const csvRows = 'time,value\n' + '0,1\n'.repeat(LIMITS.maxRows + 1);
  assert.throws(() => parseCsv(csvRows, metadata()), /exceeds 50000/);
  assert.throws(() => alignPackets([packet()], { ...options, stepSeconds: 0.0001 }), /limit is 5000/);
  const many = packet({}, Array.from({ length: 101 }, (_, i) => stream({ id: `s${i}` })));
  assert.throws(() => alignPackets([many], { ...options, stepSeconds: 2 / 4999 }), /stream values/);
  const half = packet({}, [stream({ t: Array.from({ length: 25001 }, (_, i) => i), values: Array(25001).fill(0) })]);
  assert.throws(() => combinePackets([half, { ...copy(half), dataset: { ...half.dataset, id: 'second' } }]), /combined limit/);
});

test('alignment controls refuse invalid options and preserve floating-clock range', () => {
  for (const bad of [{}, { ...options, stepSeconds: '0.5' }, { ...options, stepSeconds: 0 },
    { ...options, stepSeconds: NaN }, { ...options, maxGapSeconds: 0 }, { ...options, method: 'cubic' }]) {
    assert.throws(() => alignPackets([packet()], bad), Error);
  }
  const input = packet({}, [stream({ t: [0, 0.3], values: [0, 3] })]);
  const result = alignPackets([input], { stepSeconds: 0.1, maxGapSeconds: 1, method: 'linear' });
  assert.ok(result.t.every(t => t >= 0 && t <= 0.3));
  assert.ok(result.streams[0].values.every(Number.isFinite));
  const extreme = packet({}, [stream({ t: [1e15, 1e15 + 1], values: [0, 1] })]);
  assert.throws(() => alignPackets([extreme], { ...options, stepSeconds: 0.01 }), /clock precision/);
});

test('opposite finite extremes interpolate without subtraction overflow', () => {
  const input = packet({}, [stream({ t: [0, 1], values: [-Number.MAX_VALUE, Number.MAX_VALUE] })]);
  const result = alignPackets([input], options);
  assert.deepEqual(result.streams[0].values, [-Number.MAX_VALUE, 0, Number.MAX_VALUE]);
});

test('provenance, rights and uncertainty metadata survive import and alignment', () => {
  const input = packet({ rights: { permission: 'Local inspection only', redistributable: false },
    provenance: { acquisition: 'Constructed unit-test arrays', originalId: 'source-123' },
    organism: 'No organism; software test', environment: 'No physical environment' }, [stream({
      uncertainty: { standardDeviation: 0.25, unit: 'mV' }, missingness: 'An explicit null means no supplied sample.' })]);
  const imported = parsePacket(JSON.stringify(input));
  const aligned = alignPackets([imported], options);
  assert.deepEqual(aligned.streams[0].dataset.rights, input.dataset.rights);
  assert.deepEqual(aligned.streams[0].dataset.provenance, input.dataset.provenance);
  assert.deepEqual(aligned.streams[0].uncertainty, input.streams[0].uncertainty);
  assert.equal(aligned.streams[0].dataset.split, 'test');
});

test('wide malformed CSV is bounded before allocating arbitrary columns', () => {
  assert.throws(() => parseCsv('time,value,unit,modality,extra\n0,1,N,mechanics,x', metadata()), /at most four columns/);
  assert.throws(() => parseCsv('time,value\n' + ','.repeat(50000), metadata()), /at most four columns/);
});

test('a valid 50000-row import is accepted and can use a bounded alignment grid', () => {
  const n = LIMITS.maxRows / 2;
  const t = Array.from({ length: n }, (_, i) => i / 1000);
  const values = Array.from({ length: n }, (_, i) => (i % 100) / 100);
  const input = packet({}, [stream({ t, values }), stream({ id: 'second', t: [...t], values: [...values] })]);
  const imported = parsePacket(JSON.stringify(input));
  assert.equal(imported.importInfo.rowCount, 50000);
  const result = alignPackets([imported], { stepSeconds: 0.01, maxGapSeconds: 0.01, method: 'nearest' });
  assert.equal(result.t.length, 2500);
  assert.equal(result.diagnostics.outputValueCount, 5000);
  assert.equal(result.diagnostics.missingValueCount, 0);
});

test('unknown identity placeholders cannot establish pairing; fixtures still need invented organism', () => {
  for (const field of ['organism', 'subjectId', 'recordingId', 'timebase']) {
    const input = packet({ [field]: 'unknown' });
    assert.equal(validatePacket(input), input);
    assert.equal(assessCompatibility([input]).compatible, false);
    assert.throws(() => alignPackets([input], options), /known/);
  }
  const fixture = examplePacket();
  assert.equal(fixture.dataset.organism, 'invented');
  assert.equal(assessCompatibility([fixture]).compatible, true);
  fixture.dataset.organism = 'Homo sapiens';
  assert.throws(() => alignPackets([fixture], options), /organism: invented/);
});

test('unknown partitions are visible and never silently mixed with held-out or training splits', () => {
  const unknown = packet({ split: 'unknown' });
  const aligned = alignPackets([unknown], options);
  assert.equal(aligned.streams[0].dataset.split, 'unknown');
  assert.ok(aligned.diagnostics.warnings.some(w => w.includes('split is unknown')));
  assert.equal(aligned.pairing.biologicalValidationEstablished, false);
  for (const split of ['train', 'validation', 'test', 'held_out', 'heldout']) {
    assert.throws(() => alignPackets([unknown, packet({ id: 'other', split })], options), /different split labels/);
  }
});
