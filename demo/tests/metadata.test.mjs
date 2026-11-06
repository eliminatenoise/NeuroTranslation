import { test } from 'node:test';
import assert from 'node:assert/strict';
import { toPolicyDescriptor, toPolicyEnvelope } from '../src/packet-policy-bridge.mjs';
import { summarizeObservations, evaluate } from '../src/compat-policy.mjs';
import { examplePacket, validatePacket } from '../src/core.mjs';

const dataset = (patch = {}) => ({ id: 'source dataset', name: 'Example observations', sourceUrl: null, license: 'CC0-1.0', task: 'reach', split: 'held_out', organism: 'human', subjectId: 'S1', recordingId: 'R1', timebase: 'clock-A', ...patch });
const stream = (patch = {}) => ({ id: 'observed stream', modality: 'neural', region: 'brain', label: 'Signal', measurement: 'eeg', unit: 'uV', origin: 'measured', t: [0, 1, 2], values: [1, null, -0], ...patch });
const packet = (d = dataset(), s = stream()) => ({ schemaVersion: 1, dataset: d, streams: [s] });
const codes = r => r.diagnostics.map(x => x.code);
const policyCodes = r => r.policyValidation.reasons.map(x => x.code);

test('the four modality mappings and five region mappings are explicit; unknown region stays absent', () => {
  for (const [from, to] of [['neural', 'neural'], ['muscle', 'myographic'], ['displacement', 'motion'], ['mechanics', 'mechanics']]) {
    const r = toPolicyDescriptor(stream({ modality: from, region: from === 'neural' ? 'brain' : undefined, measurement: undefined }), dataset());
    assert.equal(r.descriptor.modality, to);
    assert.equal(r.descriptor.measurement, undefined);
  }
  for (const [from, to] of [['brain', 'brain'], ['spinal', 'spinal'], ['peripheral', 'peripheral'], ['autonomic', 'autonomic_visceral'], ['visceral', 'autonomic_visceral']]) assert.equal(toPolicyDescriptor(stream({ region: from }), dataset()).descriptor.neural.division, to);
  for (const region of [undefined, null, 'unknown', 'cortex']) {
    const r = toPolicyDescriptor(stream({ region }), dataset());
    assert.equal(r.descriptor.neural, undefined);
    assert.ok(codes(r).includes('REGION_UNMAPPED'));
    assert.ok(policyCodes(r).includes('NEURAL_DIVISION_MISSING'));
  }
});

test('labels, units and generic EMG never create a controlled measurement or an EMG subtype', () => {
  const r = toPolicyDescriptor(stream({ modality: 'muscle', region: undefined, label: 'Surface EMG of biceps', measurement: 'EMG', unit: 'mV', signalType: 'emg_surface' }), dataset());
  assert.equal(r.descriptor.measurement, 'EMG');
  assert.ok(codes(r).includes('MEASUREMENT_UNCONTROLLED'));
  assert.ok(policyCodes(r).includes('MEASUREMENT_UNKNOWN'));
  const missing = toPolicyDescriptor(stream({ measurement: undefined, label: 'EEG', signalType: 'eeg' }), dataset());
  assert.equal(missing.descriptor.measurement, undefined);
  assert.ok(codes(missing).includes('MEASUREMENT_MISSING'));
});

test('caller measurement binding requires provenance and stays distinguishable from native declarations', () => {
  const s = stream({ modality: 'muscle', region: undefined, measurement: 'EMG', unit: 'mV' });
  assert.equal(toPolicyDescriptor(s, dataset(), { measurementBinding: { value: 'emg_surface' } }).descriptor, null);
  const r = toPolicyDescriptor(s, dataset(), { measurementBinding: { value: 'emg_surface', provenance: { source: 'curator declaration', ref: 'record-42' } } });
  assert.equal(r.descriptor.measurement, 'emg_surface');
  assert.equal(s.measurement, 'EMG');
  assert.equal(r.appliedBindings[0].origin, 'explicit_caller_binding');
  assert.equal(r.appliedBindings[0].nativeValue, 'EMG');
  assert.equal(r.appliedBindings[0].provenance.ref, 'record-42');
  assert.equal(r.appliedBindings[0].scientificVerification, false);
  assert.ok(r.declarationOrigins.some(x => x.basis === 'explicit_caller_binding'));
  const conflict = toPolicyDescriptor(stream(), dataset(), { measurementBinding: { value: 'lfp', provenance: { source: 'curator declaration', ref: 'record-43' } } });
  assert.equal(conflict.descriptor, null);
  assert.ok(codes(conflict).includes('BINDING_CONFLICT'));
});

test('controlled native measurement passes exactly and its metadata is not curator-labelled', () => {
  const r = toPolicyDescriptor(stream(), dataset());
  assert.equal(r.descriptor.measurement, 'eeg');
  assert.equal(r.appliedBindings.length, 0);
  assert.ok(r.declarationOrigins.some(x => x.target === 'measurement' && x.basis === 'native_packet'));
});

test('unit strings remain byte-for-byte exact, including ambiguous, whitespace and case spellings', () => {
  for (const unit of ['uV', 'µV', 'μV', ' uV ', 'UV', 'g', 'a.u.']) {
    const r = toPolicyDescriptor(stream({ unit }), dataset());
    assert.equal(r.descriptor.quantity.unit, unit);
  }
  assert.ok(policyCodes(toPolicyDescriptor(stream({ unit: 'g' }), dataset())).includes('UNIT_AMBIGUOUS'));
  assert.ok(policyCodes(toPolicyDescriptor(stream({ unit: ' uV ' }), dataset())).includes('UNIT_UNRECOGNISED'));
});

test('samples, nulls and signed zero are untouched; whole observation summary is passed', () => {
  const t = Object.freeze([-1, 0, 0.5, 2]);
  const values = Object.freeze([Number.MAX_VALUE, null, -0, -Number.MAX_VALUE]);
  const s = Object.freeze(stream({ t, values }));
  const beforeT = [...t], beforeValues = [...values];
  const r = toPolicyDescriptor(s, Object.freeze(dataset()));
  assert.deepEqual(r.descriptor.observations, summarizeObservations(t, values));
  assert.deepEqual(t, beforeT); assert.deepEqual(values, beforeValues);
  assert.ok(Object.is(values[2], -0));
  assert.equal(r.descriptor.missingness.missingCount, 1);
  assert.equal(r.descriptor.missingness.gaps, undefined);
  assert.equal(r.descriptor.interval.start, -1); assert.equal(r.descriptor.interval.end, 2);
  assert.equal(r.descriptor.clock.unit, 's');
});

test('safe IDs encode the complete two-part identity without delimiter, normalization or truncation collisions', () => {
  const pairs = [['a:b', 'c'], ['a', 'b:c'], ['a b', 'x'], ['a_b', 'x'], ['é', 'x'], ['e\u0301', 'x'], ['x'.repeat(2000), 'y'.repeat(2000)], ['x'.repeat(1999) + 'z', 'y'.repeat(2000)]];
  const results = pairs.map(([d, s]) => toPolicyDescriptor(stream({ id: s }), dataset({ id: d })));
  assert.equal(new Set(results.map(r => r.descriptor.streamId)).size, pairs.length);
  results.forEach((r, i) => {
    assert.match(r.descriptor.streamId, /^s\.[0-9a-f]{64}$/u);
    assert.match(r.descriptor.dataset.id, /^d\.[0-9a-f]{64}$/u);
    assert.deepEqual(r.identityMap.original, { datasetId: pairs[i][0], streamId: pairs[i][1] });
    assert.equal(toPolicyDescriptor(stream({ id: pairs[i][1] }), dataset({ id: pairs[i][0] })).descriptor.streamId, r.descriptor.streamId);
  });
});

test('duplicate source identity or conflicting dataset declarations block the whole envelope', () => {
  const duplicate = toPolicyEnvelope([packet(), packet()]);
  assert.equal(duplicate.policyInput, null);
  assert.ok(codes(duplicate).includes('DUPLICATE_SOURCE_IDENTITY'));
  const conflict = toPolicyEnvelope([packet(), packet(dataset({ license: 'restricted' }), stream({ id: 'second' }))]);
  assert.equal(conflict.policyInput, null);
  assert.ok(codes(conflict).includes('DATASET_ID_CONFLICT'));
});

test('measured, inferred and simulated origins and held-out roles survive projection', () => {
  for (const origin of ['measured', 'inferred', 'simulated']) for (const [from, to] of [['train', 'train'], ['validation', 'validation'], ['test', 'test'], ['held_out', 'heldout'], ['heldout', 'heldout'], ['unspecified', 'unknown']]) {
    const r = toPolicyDescriptor(stream({ origin }), dataset({ split: from, origin: 'constructed_example' }));
    assert.equal(r.descriptor.origin, origin);
    assert.equal(r.descriptor.role.split, to);
  }
  const fixture = toPolicyDescriptor(stream({ origin: 'simulated' }), dataset({ split: 'fixture', origin: 'constructed_example' }));
  assert.equal(fixture.descriptor.role, undefined);
  assert.ok(codes(fixture).includes('SPLIT_UNMAPPED'));
  assert.ok(policyCodes(fixture).includes('SPLIT_UNKNOWN'));
  const promotion = toPolicyDescriptor(stream({ policyMetadata: { origin: 'measured' } }), dataset());
  assert.equal(promotion.descriptor, null);
  assert.ok(codes(promotion).includes('RICH_FIELD_UNSUPPORTED'));
});

test('matching subject/session, URL and clocks generate no pairing or scientific or rights claim', () => {
  const d1 = dataset({ id: 'A', sourceUrl: 'https://example.org/source' });
  const d2 = dataset({ id: 'B', sourceUrl: 'https://example.org/source' });
  const r = toPolicyEnvelope([validatePacket(packet(d1)), validatePacket(packet(d2))]);
  assert.equal(r.status, 'mapped'); assert.deepEqual(r.policyInput.links, []);
  assert.deepEqual(r.pairing, { proposedLinks: 0, automaticPairing: false, biologicalInference: false, modelInference: false, grantsRights: false });
  for (const d of r.policyInput.descriptors) {
    assert.equal(d.subject.namespace, undefined); assert.equal(d.session.namespace, undefined);
    assert.equal(d.dataset.sourceId, undefined); assert.equal(d.dataset.sourceFamily, undefined);
    assert.equal(d.rights.status, undefined); assert.equal(d.rights.redistribution, undefined);
    assert.equal(d.clock.offsetUncertaintyS, undefined); assert.equal(d.clock.driftPpm, undefined); assert.equal(d.clock.syncTime, undefined);
    assert.equal(d.subject.taxonId, undefined);
  }
  const report = evaluate(r.policyInput);
  assert.equal(report.nonInference.establishesSameSubject, false);
  assert.equal(report.nonInference.authorizesTraining, false);
});

test('free-text frame does not become 3D; explicit richer fields copy only their declarations', () => {
  const s = stream({ modality: 'displacement', region: undefined, measurement: 'simulated_kinematics', origin: 'simulated', unit: 'mm', frame: 'declared x axis' });
  const r = toPolicyDescriptor(s, dataset());
  assert.deepEqual(r.descriptor.frame, { id: 'declared x axis' });
  assert.equal(r.descriptor.provenance, undefined);
  assert.ok(policyCodes(r).includes('FRAME_UNDECLARED'));
  assert.ok(policyCodes(r).includes('SIMULATION_PROVENANCE_INCOMPLETE'));
  const declared = toPolicyDescriptor({ ...s, policyMetadata: { frame: { id: 'declared x axis', kind: 'cartesian_3d', handedness: 'right' }, interval: { uncertaintyS: 0.02 }, provenance: { generator: { engine: 'declared engine', version: '1', model: 'declared body', controller: 'declared controller', actuation: 'kinematic_playback', deterministic: true } } } }, dataset({ policyMetadata: { sourceId: 'declared-source', subject: { namespace: 'declared-subject-scope', taxonId: 'NCBITaxon:9606' }, session: { namespace: 'declared-session-scope' }, rights: { status: 'declared_restricted', redistribution: 'not_allowed' } } }));
  assert.equal(declared.descriptor.frame.kind, 'cartesian_3d');
  assert.equal(declared.descriptor.interval.uncertaintyS, 0.02);
  assert.equal(declared.descriptor.subject.namespace, 'declared-subject-scope');
  assert.equal(declared.descriptor.subject.taxonId, 'NCBITaxon:9606');
  assert.equal(declared.descriptor.rights.status, 'declared_restricted');
  assert.equal(declared.descriptor.provenance.generator.actuation, 'kinematic_playback');
  assert.ok(declared.declarationOrigins.some(x => x.target === 'frame.kind' && x.basis === 'native_policyMetadata'));
});

test('rich declarations cannot silently override exact native units, frames, clocks or split', () => {
  for (const policyMetadata of [{ quantity: { unit: 'mV' } }, { clock: { unit: 'ms' } }, { clock: { domain: 'different-clock' } }, { frame: { id: 'different-frame' } }, { role: { split: 'train' } }]) {
    const r = toPolicyDescriptor(stream({ frame: 'native-frame', policyMetadata }), dataset());
    assert.equal(r.descriptor, null);
    assert.ok(codes(r).some(x => ['DECLARATION_CONFLICT', 'RICH_FIELD_UNSUPPORTED'].includes(x)));
  }
});

test('declared lineage is not derived from raw ID strings and remains exactly supplied', () => {
  const r = toPolicyDescriptor(stream({ origin: 'inferred', policyMetadata: { provenance: { derivedFrom: ['raw-label'] }, role: { negativeControl: { kind: 'shuffled', of: 'raw-label' } } } }), dataset());
  assert.deepEqual(r.descriptor.provenance.derivedFrom, ['raw-label']);
  assert.equal(r.descriptor.role.negativeControl.of, 'raw-label');
  assert.equal(r.descriptor.origin, 'inferred'); assert.equal(r.descriptor.role.split, 'heldout');
});

test('the actual constructed example exposes missing measurement, generator, frame and split declarations', () => {
  const p = validatePacket(examplePacket());
  const before = JSON.stringify(p);
  const r = toPolicyEnvelope([p]);
  assert.equal(r.status, 'mapped'); assert.equal(r.policyInput.descriptors.length, 4);
  assert.equal(JSON.stringify(p), before);
  assert.ok(r.policyInput.descriptors.every(d => d.origin === 'simulated' && d.provenance === undefined && d.role === undefined));
  assert.equal(r.policyInput.descriptors[1].measurement, 'EMG');
  assert.ok(r.streamResults.every(x => codes(x).includes('SPLIT_UNMAPPED') && policyCodes(x).includes('SIMULATION_PROVENANCE_INCOMPLETE')));
  assert.ok(r.streamResults.some(x => policyCodes(x).includes('MEASUREMENT_UNKNOWN')));
  assert.deepEqual(r.identityMap.map(x => x.original.streamId), p.streams.map(x => x.id));
});

test('overlimit metadata is rejected with diagnostics instead of truncating or dropping it silently', () => {
  const s = stream({ label: 'x'.repeat(513) });
  const r = toPolicyDescriptor(s, dataset());
  assert.equal(r.descriptor, null);
  assert.ok(codes(r).includes('MAPPING_LIMIT_EXCEEDED'));
  assert.equal(s.label.length, 513);
  assert.equal(toPolicyDescriptor(stream({ id: 'x'.repeat(2001) }), dataset()).descriptor, null);
});

test('accessors and malformed samples are refused without invoking getters or repairing values', () => {
  let calls = 0;
  const s = stream(); Object.defineProperty(s, 'label', { enumerable: true, get() { calls++; return 'eeg'; } });
  assert.equal(toPolicyDescriptor(s, dataset()).descriptor, null); assert.equal(calls, 0);
  const values = [1, null, 2]; Object.defineProperty(values, '0', { enumerable: true, get() { calls++; return 1; } });
  assert.equal(toPolicyDescriptor(stream({ values }), dataset()).descriptor, null); assert.equal(calls, 0);
  for (const invalid of [[1, NaN, 2], [1, Infinity, 2], [1, '2', 3]]) assert.equal(toPolicyDescriptor(stream({ values: invalid }), dataset()).descriptor, null);
  assert.equal(toPolicyDescriptor(stream({ t: [0, 0, 2] }), dataset()).descriptor, null);
});

test('valid sample arrays above the policy metadata-array limit retain the complete observation count', () => {
  const t = Array.from({ length: 5000 }, (_, i) => i / 1000), values = t.map((v, i) => i === 4097 ? null : v);
  const r = toPolicyDescriptor(stream({ t, values }), dataset());
  assert.equal(r.status, 'mapped'); assert.equal(r.descriptor.observations.sampleCount, 5000);
  assert.equal(r.descriptor.observations.nullCount, 1); assert.equal(r.descriptor.observations.truncated, false);
  assert.equal(values[4097], null); assert.equal(t.at(-1), 4.999);
});
