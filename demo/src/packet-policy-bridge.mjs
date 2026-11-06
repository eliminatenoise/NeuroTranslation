/** Packet v1 -> policy descriptor v1. No pairing, conversion or model execution. */
import { summarizeObservations, toPlainSnapshot, validateDescriptor } from './compat-policy.mjs';
import { canonicalJson, fingerprint } from './hash.mjs';
import { MEASUREMENTS } from './vocabulary.mjs';

export const BRIDGE = Object.freeze({ version: '0.1.0-candidate', packetVersion: 1, descriptorVersion: 1 });
export const LIMITS = Object.freeze({ maxIdentityChars: 2000, maxStreams: 64, maxSamples: 50000 });
const MODALITY = Object.freeze({ neural: 'neural', muscle: 'myographic', displacement: 'motion', mechanics: 'mechanics' });
const DIVISION = Object.freeze({ brain: 'brain', spinal: 'spinal', peripheral: 'peripheral', autonomic: 'autonomic_visceral', visceral: 'autonomic_visceral' });
const SPLIT = Object.freeze({ train: 'train', validation: 'validation', test: 'test', held_out: 'heldout', heldout: 'heldout', unassigned: 'unassigned', unknown: 'unknown', unspecified: 'unknown' });
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const plain = o => o !== null && typeof o === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(o));
const absent = v => v === null || v === undefined;
const controlled = v => typeof v === 'string' && own(MEASUREMENTS, v);
const placeholder = v => typeof v === 'string' && ['', 'unknown', 'unspecified', 'unassigned', 'n/a', 'na', '?', 'none', 'null', 'undefined', 'tbd', 'tba'].includes(v.trim().toLowerCase());
const diagnostic = (out, code, severity, path, message, details) => out.push({ code, severity, path, message, ...(details === undefined ? {} : { details }) });

function dataProperty(o, key, path, diagnostics) {
  try {
    const d = Object.getOwnPropertyDescriptor(o, key);
    if (!d) return undefined;
    if (!('value' in d) || !d.enumerable) {
      diagnostic(diagnostics, 'SOURCE_NOT_PLAIN_DATA', 'error', path, 'An own enumerable data property is required.');
      return undefined;
    }
    return d.value;
  } catch {
    diagnostic(diagnostics, 'SOURCE_NOT_PLAIN_DATA', 'error', path, 'The property could not be inspected.');
    return undefined;
  }
}

function metadata(o, omit, path, diagnostics) {
  try {
    if (!plain(o)) throw new TypeError();
    const projected = Object.create(null);
    for (const k of Reflect.ownKeys(o)) {
      if (omit.includes(k)) continue;
      if (typeof k !== 'string') throw new TypeError();
      projected[k] = dataProperty(o, k, `${path}.${k}`, diagnostics);
    }
    const snap = toPlainSnapshot(projected, path);
    for (const p of snap.problems) diagnostic(diagnostics, p.code === 'LIMIT_EXCEEDED' ? 'MAPPING_LIMIT_EXCEEDED' : 'SOURCE_NOT_PLAIN_DATA', 'error', p.path, p.detail ?? p.code);
    return snap.value ?? {};
  } catch {
    diagnostic(diagnostics, 'SOURCE_NOT_PLAIN_DATA', 'error', path, 'Plain JSON metadata is required.');
    return {};
  }
}

function identityText(o, key, path, diagnostics) {
  const v = dataProperty(o, key, path, diagnostics);
  if (typeof v !== 'string' || v.length === 0 || v.length > LIMITS.maxIdentityChars || /[\u0000-\u001f\u007f]/u.test(v)) {
    diagnostic(diagnostics, 'IDENTITY_INVALID', 'error', path, `The exact identity must be nonempty plain text of at most ${LIMITS.maxIdentityChars} characters; it is never shortened.`);
    return null;
  }
  return v;
}

function sampleArray(source, path, nullable, diagnostics) {
  try {
    if (!Array.isArray(source) || Object.getPrototypeOf(source) !== Array.prototype) throw new TypeError();
    const length = Object.getOwnPropertyDescriptor(source, 'length').value;
    if (length < 1 || length > LIMITS.maxSamples) {
      diagnostic(diagnostics, 'SAMPLE_LIMIT_OR_EMPTY', 'error', path, `Expected 1-${LIMITS.maxSamples} packet samples.`);
      return null;
    }
    const out = [];
    for (let i = 0; i < length; i++) {
      const p = Object.getOwnPropertyDescriptor(source, String(i));
      if (!p || !p.enumerable || !('value' in p) || !(typeof p.value === 'number' && Number.isFinite(p.value) || nullable && p.value === null)) {
        diagnostic(diagnostics, 'SAMPLE_INVALID', 'error', `${path}[${i}]`, 'Accepted packet samples must be finite numbers, or null values; no repair or coercion was performed.');
        return null;
      }
      out.push(p.value);
    }
    return out;
  } catch {
    diagnostic(diagnostics, 'SAMPLE_INVALID', 'error', path, 'A plain dense sample array is required.');
    return null;
  }
}

const EXTENSIONS = Object.freeze({
  dataset: { sourceId: true, sourceFamily: true, subject: true, session: true, rights: true, role: true },
  stream: { measurement: true, side: true, neural: true, provenance: true, quantity: true, frame: true, clock: true, interval: true, subject: true, session: true, rights: true, role: true, missingness: true, channels: true },
});
const FIELDS = Object.freeze({
  neural: ['division', 'structure', 'direction'], provenance: ['derivedFrom', 'generator', 'pipeline'],
  quantity: ['unit', 'dimension', 'name'], frame: ['id', 'kind', 'handedness'],
  clock: ['domain', 'unit', 'rateHz', 'offsetUncertaintyS', 'driftPpm', 'syncTime'], interval: ['start', 'end', 'uncertaintyS'],
  subject: ['id', 'namespace', 'species', 'taxonId'], session: ['id', 'namespace'],
  rights: ['dataLicence', 'codeLicence', 'status', 'redistribution'], role: ['negativeControl'],
  missingness: ['encoding', 'missingCount', 'gaps'], channels: ['count', 'order'],
});

/** Result contains the descriptor AND its identity/mapping record. Keep them together. */
export function toPolicyDescriptor(stream, dataset, options = {}) {
  const diagnostics = [], origins = [], appliedBindings = [];
  let identityMap = null, descriptor = null;
  try {
    if (!plain(stream) || !plain(dataset) || !plain(options)) throw new TypeError('Plain stream, dataset and options objects are required.');
    const datasetId = identityText(dataset, 'id', 'dataset.id', diagnostics);
    const streamId = identityText(stream, 'id', 'stream.id', diagnostics);
    const ds = metadata(dataset, ['id'], 'dataset', diagnostics);
    const ss = metadata(stream, ['id', 't', 'values'], 'stream', diagnostics);
    const opts = metadata(options, [], 'options', diagnostics);
    const t = sampleArray(dataProperty(stream, 't', 'stream.t', diagnostics), 'stream.t', false, diagnostics);
    const values = sampleArray(dataProperty(stream, 'values', 'stream.values', diagnostics), 'stream.values', true, diagnostics);
    if (datasetId !== null && streamId !== null) {
      identityMap = { original: { datasetId, streamId }, policy: { datasetId: `d.${fingerprint(['packet-v1-dataset', datasetId])}`, streamId: `s.${fingerprint(['packet-v1-stream', datasetId, streamId])}` },
        encoding: 'full-sha256-of-domain-separated-canonical-json-tuples', collisionResolution: 'refuse-conflicting-original-identities' };
    }
    if (diagnostics.some(d => d.severity === 'error')) return finish();
    if (t.length !== values.length || t.some((v, i) => i > 0 && !(v > t[i - 1]))) {
      diagnostic(diagnostics, 'PACKET_SAMPLE_STRUCTURE_INVALID', 'error', 'stream.t', 'Equal-length arrays and strictly increasing timestamps are required; samples were not changed.');
      return finish();
    }

    descriptor = { descriptorVersion: 1, streamId: identityMap.policy.streamId, dataset: { id: identityMap.policy.datasetId } };
    const put = (path, value, source, basis = 'native_packet') => {
      if (absent(value)) return;
      const keys = path.split('.');
      let obj = descriptor;
      for (const k of keys.slice(0, -1)) {
        if (!own(obj, k)) obj[k] = {};
        if (!plain(obj[k])) { diagnostic(diagnostics, 'DECLARATION_CONFLICT', 'error', path, 'Structured and scalar declarations conflict.', { source }); return; }
        obj = obj[k];
      }
      const key = keys.at(-1);
      if (own(obj, key) && canonicalJson(obj[key]) !== canonicalJson(value)) {
        diagnostic(diagnostics, 'DECLARATION_CONFLICT', 'error', path, 'Two explicit declarations disagree; neither was silently preferred.', { source });
        return;
      }
      obj[key] = value;
      origins.push({ target: path, source, basis });
    };
    origins.push({ target: 'streamId', source: ['dataset.id', 'stream.id'], basis: 'identity_encoding' }, { target: 'dataset.id', source: 'dataset.id', basis: 'identity_encoding' });
    put('label', ss.label, 'stream.label');
    if (own(MODALITY, ss.modality)) put('modality', MODALITY[ss.modality], 'stream.modality', 'explicit_vocabulary_map');
    else { put('modality', ss.modality, 'stream.modality'); diagnostic(diagnostics, 'MODALITY_UNMAPPED', 'warning', 'stream.modality', 'No explicit packet modality mapping exists.'); }
    if (ss.modality === 'neural') {
      if (own(DIVISION, ss.region)) put('neural.division', DIVISION[ss.region], 'stream.region', 'explicit_vocabulary_map');
      else diagnostic(diagnostics, 'REGION_UNMAPPED', 'warning', 'stream.region', 'The neural division remains undeclared; no region was guessed.');
    } else if (!absent(ss.region)) diagnostic(diagnostics, 'REGION_ON_NON_NEURAL', 'error', 'stream.region', 'Packet v1 reserves region for neural streams.');
    put('measurement', ss.measurement, 'stream.measurement');
    put('origin', ss.origin, 'stream.origin');
    put('quantity.unit', ss.unit, 'stream.unit');
    if (!absent(ss.frame)) put('frame.id', ss.frame, 'stream.frame');
    put('clock.domain', ds.timebase, 'dataset.timebase');
    put('clock.unit', 's', 'packet-v1 timestamp contract', 'packet_schema');
    put('clock.rateHz', ss.rateHz, 'stream.rateHz');
    put('interval.start', t[0], 'stream.t[0]', 'observed_from_samples');
    put('interval.end', t.at(-1), 'stream.t[last]', 'observed_from_samples');
    put('subject.id', ds.subjectId, 'dataset.subjectId');
    put('subject.species', ds.organism, 'dataset.organism');
    put('session.id', ds.recordingId, 'dataset.recordingId');
    put('rights.dataLicence', ds.license, 'dataset.license');
    if (own(SPLIT, ds.split)) put('role.split', SPLIT[ds.split], 'dataset.split', 'explicit_vocabulary_map');
    else diagnostic(diagnostics, 'SPLIT_UNMAPPED', 'warning', 'dataset.split', 'No policy split is assigned to this packet split.', { declared: ds.split ?? null });
    put('channels.count', 1, 'packet-v1 scalar values contract', 'packet_schema');
    // Use the WHOLE helper result. Values, timestamps, nulls and signed zero stay untouched.
    const observations = summarizeObservations(t, values);
    put('observations', observations, 'summarizeObservations(stream.t, stream.values)', 'observed_from_samples');
    put('missingness.encoding', 'null', 'packet-v1 nullable values contract', 'packet_schema');
    put('missingness.missingCount', observations.nullCount, 'observations.nullCount', 'observed_from_samples');

    for (const [scope, source] of [['dataset', ds], ['stream', ss]]) {
      const ext = source.policyMetadata;
      if (absent(ext)) continue;
      if (!plain(ext)) { diagnostic(diagnostics, 'RICH_METADATA_INVALID', 'error', `${scope}.policyMetadata`, 'policyMetadata must be a plain object.'); continue; }
      for (const [key, value] of Object.entries(ext)) {
        const sourcePath = `${scope}.policyMetadata.${key}`;
        if (!own(EXTENSIONS[scope], key)) { diagnostic(diagnostics, 'RICH_FIELD_UNSUPPORTED', 'error', sourcePath, 'This field has no admitted mapping; it was not applied.'); continue; }
        if (scope === 'dataset' && ['sourceId', 'sourceFamily'].includes(key)) put(`dataset.${key}`, value, sourcePath, 'native_policyMetadata');
        else if (['measurement', 'side'].includes(key)) put(key, value, sourcePath, 'native_policyMetadata');
        else {
          if (!plain(value)) { diagnostic(diagnostics, 'RICH_METADATA_INVALID', 'error', sourcePath, 'A structured declaration is required.'); continue; }
          for (const [child, v] of Object.entries(value)) {
            if (!FIELDS[key]?.includes(child)) { diagnostic(diagnostics, 'RICH_FIELD_UNSUPPORTED', 'error', `${sourcePath}.${child}`, 'This field has no admitted mapping; it was not applied.'); continue; }
            put(`${key}.${child}`, v, `${sourcePath}.${child}`, 'native_policyMetadata');
          }
        }
      }
    }
    if (own(opts, 'measurementBinding')) {
      const b = opts.measurementBinding;
      if (!plain(b) || Object.keys(b).some(k => !['value', 'provenance'].includes(k)) || !controlled(b.value) || !plain(b.provenance)
        || !['source', 'ref'].every(k => typeof b.provenance[k] === 'string' && !placeholder(b.provenance[k]))) {
        diagnostic(diagnostics, 'BINDING_PROVENANCE_REQUIRED', 'error', 'options.measurementBinding', 'A controlled value and explicit provenance.source and provenance.ref are required.');
      } else if (controlled(descriptor.measurement) && descriptor.measurement !== b.value) {
        diagnostic(diagnostics, 'BINDING_CONFLICT', 'error', 'measurement', 'A caller binding cannot replace a different controlled native measurement.');
      } else {
        appliedBindings.push({ target: 'measurement', value: b.value, nativeValue: descriptor.measurement ?? null, provenance: b.provenance, origin: 'explicit_caller_binding', scientificVerification: false });
        descriptor.measurement = b.value;
        origins.push({ target: 'measurement', source: 'options.measurementBinding', basis: 'explicit_caller_binding' });
        diagnostic(diagnostics, 'CALLER_BINDING_APPLIED', 'info', 'measurement', 'The mapping record identifies this as a provenance-bearing caller binding, not a native declaration.');
      }
    }
    for (const k of Object.keys(opts)) if (k !== 'measurementBinding') diagnostic(diagnostics, 'OPTION_UNSUPPORTED', 'error', `options.${k}`, 'This option is not supported.');
    if (!controlled(descriptor.measurement)) diagnostic(diagnostics, absent(descriptor.measurement) ? 'MEASUREMENT_MISSING' : 'MEASUREMENT_UNCONTROLLED', 'warning', 'measurement', 'No controlled measurement was supplied; neither the label nor the unit is used to guess it.');
    const gaps = ['dataset.sourceId', 'clock.domain', 'clock.offsetUncertaintyS', 'clock.driftPpm', 'clock.syncTime', 'interval.uncertaintyS', 'subject.namespace', 'session.namespace', 'subject.taxonId', 'rights.status', 'rights.redistribution'];
    if (['motion', 'mechanics'].includes(descriptor.modality)) gaps.push('frame.kind', 'frame.handedness');
    if (descriptor.origin === 'simulated') gaps.push('provenance.generator');
    if (descriptor.origin === 'inferred') gaps.push('provenance.derivedFrom');
    for (const path of gaps) {
      const value = path.split('.').reduce((o, k) => plain(o) ? o[k] : undefined, descriptor);
      if (absent(value) || placeholder(value)) diagnostic(diagnostics, 'DECLARATION_ABSENT', 'info', path, 'This declaration is unknown; the bridge supplies no default.');
    }
    return finish();
  } catch (e) {
    diagnostic(diagnostics, 'BRIDGE_INPUT_REJECTED', 'error', '', typeof e?.message === 'string' ? e.message : 'Input could not be mapped.');
    return finish();
  }

  function finish() {
    const rejected = diagnostics.some(d => d.severity === 'error');
    if (rejected) descriptor = null;
    const policyValidation = descriptor ? validateDescriptor(descriptor) : null;
    return { bridgeVersion: BRIDGE.version, status: rejected ? 'input_rejected' : 'mapped', descriptor, identityMap, declarationOrigins: origins, appliedBindings, diagnostics, policyValidation,
      mappingFingerprint: identityMap ? fingerprint({ identityMap, descriptor, appliedBindings, diagnostics }) : null };
  }
}

/** Already parsed/validated packet v1 inputs. Any fatal mapping error blocks the entire envelope. */
export function toPolicyEnvelope(packets) {
  const diagnostics = [], streamResults = [], identities = new Map(), safeIds = new Map(), safeDatasets = new Map();
  try {
    if (!Array.isArray(packets) || packets.length < 1 || packets.length > LIMITS.maxStreams) throw new TypeError('Supply 1-64 already validated packet-v1 objects.');
    let rows = 0, streams = 0;
    const datasetDeclarations = new Map();
    for (const [pi, packet] of packets.entries()) {
      if (!plain(packet) || dataProperty(packet, 'schemaVersion', `packets[${pi}].schemaVersion`, diagnostics) !== 1) throw new TypeError('Only packet schemaVersion 1 is supported.');
      const dataset = dataProperty(packet, 'dataset', `packets[${pi}].dataset`, diagnostics);
      const entries = dataProperty(packet, 'streams', `packets[${pi}].streams`, diagnostics);
      if (!plain(dataset) || !Array.isArray(entries) || entries.length < 1 || streams + entries.length > LIMITS.maxStreams) throw new TypeError('The envelope requires datasets and 1-64 total streams.');
      const datasetId = identityText(dataset, 'id', `packets[${pi}].dataset.id`, diagnostics);
      // Metadata snapshot first, so canonicalJson never invokes a source getter.
      const ds = metadata(dataset, ['id'], `packets[${pi}].dataset`, diagnostics);
      const declaration = canonicalJson(ds);
      if (datasetDeclarations.has(datasetId) && datasetDeclarations.get(datasetId) !== declaration) diagnostic(diagnostics, 'DATASET_ID_CONFLICT', 'error', `packets[${pi}].dataset`, 'The same exact dataset ID has different declarations.');
      datasetDeclarations.set(datasetId, declaration);
      for (let si = 0; si < entries.length; si++) {
        const stream = dataProperty(entries, String(si), `packets[${pi}].streams[${si}]`, diagnostics);
        const result = toPolicyDescriptor(stream, dataset);
        streams++;
        rows += result.descriptor?.observations.sampleCount ?? 0;
        streamResults.push(result);
        if (result.identityMap) {
          const original = canonicalJson(result.identityMap.original);
          const safe = result.identityMap.policy.streamId;
          const safeDataset = result.identityMap.policy.datasetId;
          if (safeDatasets.has(safeDataset) && safeDatasets.get(safeDataset) !== result.identityMap.original.datasetId) diagnostic(diagnostics, 'HASH_COLLISION', 'error', `packets[${pi}].dataset.id`, 'Different exact dataset IDs produced one policy dataset ID; mapping refused.');
          if (identities.has(original)) diagnostic(diagnostics, 'DUPLICATE_SOURCE_IDENTITY', 'error', `packets[${pi}].streams[${si}].id`, 'This complete dataset/stream identity was selected more than once.');
          if (safeIds.has(safe) && safeIds.get(safe) !== original) diagnostic(diagnostics, 'HASH_COLLISION', 'error', `packets[${pi}].streams[${si}].id`, 'Different complete identities produced one policy ID; mapping refused.');
          identities.set(original, safe); safeIds.set(safe, original); safeDatasets.set(safeDataset, result.identityMap.original.datasetId);
        }
      }
    }
    if (rows > LIMITS.maxSamples) diagnostic(diagnostics, 'SAMPLE_LIMIT_EXCEEDED', 'error', 'packets', `The combined sample count exceeds ${LIMITS.maxSamples}.`);
  } catch (e) {
    diagnostic(diagnostics, 'ENVELOPE_INPUT_REJECTED', 'error', 'packets', typeof e?.message === 'string' ? e.message : 'Invalid packet envelope.');
  }
  const blocked = diagnostics.some(d => d.severity === 'error') || streamResults.some(r => r.status === 'input_rejected');
  return { bridgeVersion: BRIDGE.version, status: blocked ? 'input_rejected' : 'mapped',
    policyInput: blocked ? null : { descriptors: streamResults.map(r => r.descriptor), links: [] },
    identityMap: streamResults.map(r => r.identityMap).filter(Boolean), streamResults, diagnostics,
    pairing: { proposedLinks: 0, automaticPairing: false, biologicalInference: false, modelInference: false, grantsRights: false } };
}
