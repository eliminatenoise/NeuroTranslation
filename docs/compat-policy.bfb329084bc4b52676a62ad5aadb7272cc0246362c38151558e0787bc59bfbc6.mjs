/* NeuroTranslate 0.0 provenance/compatibility policy engine, release r1 (revision 5, version 1.3.0).
 *
 * Input: stream DESCRIPTORS (declared metadata about neural, myographic, motion,
 * mechanics or physiological-context streams) plus proposed LINKS between them.
 * Output: for each link, a decision (compatible | unverified | unsupported | rejected),
 * machine-readable reasons, owners, input fingerprints and fixed non-inference flags.
 *
 * Scope limits (deliberate):
 * - It reads only the declared metadata it is given. It does not parse files, read
 *   recordings, convert or resample values, fit or run models, or infer links.
 * - Declared metadata is self-attested. "compatible" means the declarations are
 *   complete and consistent for the proposed operation. It is not scientific
 *   verification, and it authorizes no data use, training, resampling or publication.
 * - Equal identifiers, labels or timestamps, a shared source family, or equal clock or
 *   frame names in different datasets or sources are never evidence of the same person,
 *   session, time or frame.
 * Pure ES module: no imports beyond this folder, no I/O, no globals, no randomness, no clock.
 * Every external value is copied once into a plain snapshot (no getter is ever invoked);
 * all later logic reads only the snapshot.
 */
import { canonicalJson, sha256Hex } from './hash.bfb329084bc4b52676a62ad5aadb7272cc0246362c38151558e0787bc59bfbc6.mjs';
import {
  MODALITIES, ORIGINS, NEURAL_DIVISIONS, NEURAL_DIRECTIONS, FRAME_KINDS, SPLITS, NEGATIVE_CONTROL_KINDS,
  RIGHTS_STATUSES, REDISTRIBUTION, MISSING_ENCODINGS, PURPOSES, RESAMPLE_METHODS, NON_CAUSAL_METHODS,
  ADMISSIBLE_EVIDENCE, INADMISSIBLE_EVIDENCE, REGISTRY_CLAIMS, MEASUREMENTS, UNITS, DIMENSIONS,
  AMBIGUOUS_UNITS, TIME_UNIT_DIVISORS, UNKNOWN_WORDS, PAIRING_FIELD_NAMES, ADJACENT_KINDS,
  SIMULATION_ACTUATIONS, JOINT_LEVEL_ACTUATIONS, namesSoftwareLicence, isLicencePlaceholder, SIDES, TRANSFORM_TYPES, HANDEDNESS_CHANGING_TRANSFORMS,
} from './vocabulary.bfb329084bc4b52676a62ad5aadb7272cc0246362c38151558e0787bc59bfbc6.mjs';
import { REASONS, SEVERITY_RANK, DECISION_BY_RANK } from './reasons.bfb329084bc4b52676a62ad5aadb7272cc0246362c38151558e0787bc59bfbc6.mjs';

export { REASONS, OWNERS } from './reasons.bfb329084bc4b52676a62ad5aadb7272cc0246362c38151558e0787bc59bfbc6.mjs';
export * as vocabulary from './vocabulary.bfb329084bc4b52676a62ad5aadb7272cc0246362c38151558e0787bc59bfbc6.mjs';

export const POLICY = Object.freeze({ id: 'neurotranslate-0.0-compatibility-policy', release: 'r1', version: '1.3.0', descriptorVersion: 1 });
export const DECISIONS = Object.freeze(['compatible', 'unverified', 'unsupported', 'rejected']);
export const OPS = Object.freeze({
  unpaired_exploration: [2, 16], pairing: [2, 2], unit_conversion: [1, 1], frame_transform: [1, 2],
  clock_mapping: [1, 2], resample_precondition: [1, 1], cross_modal_mapping: [2, 2], relabel: [1, 1], derivation: [2, 2],
});
/** Allowed top-level keys of link.params per op (anything else is PARAMS_INVALID). */
export const OP_PARAMS = Object.freeze({
  unpaired_exploration: [], pairing: ['toleranceS', 'window'], unit_conversion: ['toUnit', 'fromUnit'], frame_transform: ['toFrame', 'transform'],
  clock_mapping: ['toDomain', 'mapping', 'toleranceS'], resample_precondition: ['method', 'stepS', 'maxGapS', 'extrapolate', 'window'],
  cross_modal_mapping: ['mapping', 'model'], relabel: ['toModality', 'toOrigin', 'toMeasurement', 'toDivision', 'toSplit', 'toSide', 'removeNegativeControl', 'toLabel'], derivation: [],
});
export const LIMITS = Object.freeze({
  maxDescriptors: 512, maxLinks: 2048, maxRegistry: 512, maxEvidence: 16, maxString: 512, maxArray: 4096,
  maxKeys: 128, maxDepth: 10, maxNodes: 20000, maxTotalChars: 8000000, maxLineage: 8192, maxLineageEdges: 32768, maxInheritedReasons: 200000, maxListedIds: 16, maxObservationEntries: 1000000, maxDiffEntries: 256, maxProblems: 20,
});

/** Fixed for every result: what this engine never establishes or authorizes. */
export const NON_INFERENCE = Object.freeze({
  basis: 'declared_metadata_only',
  selfAttestedMetadataTreatedAsVerified: false,
  engineVerifiedPairing: false,
  establishesSameSubject: false,
  establishesSameSession: false,
  establishesSameTime: false,
  linksInferredByEngine: false,
  dataRead: false,
  dataTransformed: false,
  authorizesDataUse: false,
  authorizesTraining: false,
  authorizesResampling: false,
  authorizesPublication: false,
  grantsRights: false,
  modelInference: false,
  biologicalInference: false,
  clinicalInference: false,
  wholeBodyCoverageEstablished: false,
  scientificAcceptance: false,
});

const LIMITATIONS = Object.freeze([
  'Decisions describe declared metadata only. Every descriptor and link is self-attested input.',
  'compatible means complete and consistent declarations for the proposed operation. It is not scientific verification or permission to use data.',
  'No links are inferred. Equal identifiers, labels, timestamps, clock or frame names and shared sources are never evidence of the same person, session, time or frame.',
  'Coverage is reported per dataset. Streams from different datasets are never combined into one body, and division presence within a dataset is not one subject\'s whole body.',
  'EMG is myographic, not neural; simulated values are never recorded values; joint angles are never Cartesian positions.',
  'Lineage (simulated, held-out, negative-control status) is followed only through descriptors supplied in the same evaluation.',
]);

// ---------------------------------------------------------------- helpers
const ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/u;
const HEX64_RE = /^[0-9a-f]{64}$/u;
const INDEX_RE = /^(?:0|[1-9][0-9]*)$/u;
const CONTROL_RE = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u;
const UNSAFE_KEYS = new Set(['__proto__', 'constructor', 'prototype']);
/** Signal words, matched against the words of the label or quantity name (see pieces()). */
const EMG_WORD_RE = /^([a-z]{0,3}emgs?|electromyogra\w*|elektromyogra\w*|myogra\w*|mechanomyogra\w*|sonomyogra\w*|mmgs?|myoelectric\w*)$/u;
const CONTEXT_WORD_RE = /^(ecgs?|ekgs?|electrocardiogra\w*|elektrokardiogra\w*|eda|gsr|electrodermal|airflow|pneumotach\w*)$/u;
const CONTEXT_BIGRAMS = [['skin', 'conductance'], ['galvanic', 'skin'], ['respiration', 'belt'], ['respiratory', 'belt']];
/** Words after a signal word (up to two) that mark it as a reference to another signal: an artefact, a cleaning step, an
 * event or alignment marker ('EMG artefact', 'EMG-triggered', 'EMG contaminates'). 'free' counts only right after ('EMG-free'). */
const REFERENCE_AFTER_RE = /^(artefacts?|artifacts?|free|remov(?:e|es|al|als|ed|ing)|reject(?:s|ion|ions|ed|ing)?|onsets?|align(?:s|ed|ment|ments|ing)?|lock(?:s|ed|ing)?|trigger(?:s|ed|ing)?|gat(?:e|es|ed|ing)|contaminat(?:e|es|ion|ions|ed|ing)|suppress(?:es|ion|ions|ed|ing)?|subtract(?:s|ion|ions|ed|ing)?)$/u;
/** A word right before a signal word that negates it or names its removal ('no EMG', 'non-EMG', 'removal ECG'). */
const NEGATOR_RE = /^(no|not|non|without|excluding|minus)$/u;
const REMOVAL_NOUN_RE = /^(removal|rejection|subtraction|suppression)s?$/u;
/** 'contaminated by EMG', 'aligned to the EMG', 'removal of ECG': a reference word, a preposition, an optional article. */
const PREPOSITION_RE = /^(to|by|from|of|with|on|after|for)$/u;
const ARTICLE_RE = /^(the|a|an)$/u;
const SPLIT_PIECES_RE = /(?<=\p{Ll})(?=\p{Lu})|(?<=\p{Lu})(?=\p{Lu}\p{Ll}{2})|(?<=\p{L})(?=\p{N})|(?<=\p{N})(?=\p{L})|(?<=[A-Za-z])(?=[^\x00-\x7F])|(?<=[^\x00-\x7F])(?=[A-Za-z])/u;
/** Pieces of a self-description: compatibility-normalised, accents and invisible format characters removed, split at
 * non-alphanumerics, case changes, letter-digit and Latin/non-Latin boundaries (BicepsEMG -> biceps emg, EMG1 -> emg 1,
 * ECGLead -> ecg lead, EMG信号 -> emg 信号). Each piece keeps an uppercase prefix of its token ('EMGrms' -> emg). */
function pieces(t) {
  const out = [];
  for (const tok of t.normalize('NFKD').replace(/[\p{M}\p{Cf}]/gu, '').split(/[^\p{L}\p{N}]+/u)) {
    if (!tok) continue;
    const up = /^(\p{Lu}{2,})\p{Ll}/u.exec(tok);
    tok.split(SPLIT_PIECES_RE).filter(Boolean).forEach((p, k) => out.push({ w: p.toLowerCase(), prefix: k === 0 && up ? up[1].toLowerCase() : null }));
  }
  return out;
}
/** Spans [first, last] of signal words: one piece, a run of up to three pieces written as one word ('AirFlow', 'myo-electric',
 * 'Electro-dermal', 'HD-EMG'), an uppercase token prefix, or a two-word phrase. */
function signalSpans(ps, wordRe, bigrams) {
  const spans = [];
  const alone = ps.map(p => wordRe.test(p.w) || Boolean(p.prefix && wordRe.test(p.prefix)));
  ps.forEach((p, i) => {
    if (wordRe.test(p.w)) spans.push([i, i]);
    if (p.prefix && wordRe.test(p.prefix)) spans.push([i, i]);
    // a compound counts only when it is needed: none of its pieces is a signal word alone, and every piece has two or more letters
    let joined = p.w;
    for (let j = i + 1; j < Math.min(ps.length, i + 3) && !alone[i] && p.w.length >= 2; j++) {
      if (alone[j] || ps[j].w.length < 2) break;
      joined += ps[j].w;
      if (wordRe.test(joined)) { spans.push([i, j]); break; }
    }
    for (const [a, b] of bigrams) if (p.w === a && ps[i + 1] && ps[i + 1].w === b) spans.push([i, i + 1]);
  });
  return spans;
}
/** Does any of the texts describe itself with a signal word that is not marked as a reference to another signal?
 * A signal word is a reference when one of the next two words matches REFERENCE_AFTER_RE ('free' only right after), when the
 * word right before it negates it or names its removal, or when it follows a reference word and a preposition (with an
 * optional article). The search never crosses another signal word of any kind. */
function selfDescribes(texts, wordRe, bigrams = []) {
  for (const t of texts) {
    const ps = pieces(t), w = ps.map(p => p.w);
    const covered = new Set();
    for (const [re, bi] of [[EMG_WORD_RE, []], [CONTEXT_WORD_RE, CONTEXT_BIGRAMS]]) for (const [a, b] of signalSpans(ps, re, bi)) for (let k = a; k <= b; k++) covered.add(k);
    for (const [s, e] of signalSpans(ps, wordRe, bigrams)) {
      let ref = false;
      for (let j = e + 1; j <= Math.min(w.length - 1, e + 2) && !ref; j++) {
        if (covered.has(j)) break;
        if (w[j] === 'free') { if (j === e + 1) ref = true; } else if (REFERENCE_AFTER_RE.test(w[j])) ref = true;
      }
      if (!ref && s >= 1 && !covered.has(s - 1)) {
        if (NEGATOR_RE.test(w[s - 1]) || REMOVAL_NOUN_RE.test(w[s - 1])) ref = true;
        else {
          const k = ARTICLE_RE.test(w[s - 1]) ? s - 2 : s - 1;
          if (k >= 1 && PREPOSITION_RE.test(w[k]) && !covered.has(k - 1) && w[k - 1] !== 'free' && (REFERENCE_AFTER_RE.test(w[k - 1]) || REMOVAL_NOUN_RE.test(w[k - 1]))) ref = true;
        }
      }
      if (!ref) return true;
    }
  }
  return false;
}
const JOINT_CONTROLLER_RE = /(^|[^a-z])(s?pd|pid)([^a-z]|$)|pd.?control|proportional.?derivative|joint.?(?:position.?|angle.?|velocity.?|rotation.?|pose.?)?(?:targets?|setpoints?)|(?:target|desired|reference).?joint.?(?:angles?|positions?)|joint.?torques?|torque.?(?:control|driven)|joint[\s_-]*(?:level|space)[\s_-]*control|inverse[\s_-]*kinematics|(^|[^a-z])ik([^a-z]|$)|kinematics?.?playback|motion.?playback|mocap.?playback/iu;
const ADD_TOKEN_RE = /(^|[^A-Za-z])ADD([^A-Za-z]|$)/u;
/** Controller text that names a genuine muscle-level stage (for example CMC: PD tracking, then static optimisation to muscle excitations). */
const MUSCLE_STAGE_RE = /muscle[\s_-]*(?:excitations?|activations?|forces?|actuat\w*|driven|models?|dynamics)|static[\s_-]*optimi[sz]\w*|computed[\s_-]*muscle[\s_-]*control|(^|[^a-z])cmc([^a-z]|$)|hill[\s_-]*type/iu;
const MUSCLE_STAGE_G = new RegExp(MUSCLE_STAGE_RE.source, 'giu');
const STAGE_NEGATOR_RE = /^(no|not|non|without|w\/o|excluding|absent|zero|never)$/u;
const STAGE_NEGATED_AFTER_RE = /^[\s:=,()-]*(none|absent|disabled|off|unused|not used|n\/a)(?![a-z])/iu;
/** Does the text name a muscle-level stage that it does not negate ('no muscle model', 'w/o muscle dynamics', 'muscle model: none')? */
function namesMuscleStage(text) {
  for (const m of text.matchAll(MUSCLE_STAGE_G)) {
    const before = text.slice(Math.max(0, m.index - 24), m.index).toLowerCase().split(/[^a-z/]+/u).filter(Boolean).slice(-2);
    const after = text.slice(m.index + m[0].length, m.index + m[0].length + 16);
    if (!before.some(x => STAGE_NEGATOR_RE.test(x)) && !STAGE_NEGATED_AFTER_RE.test(after)) return true;
  }
  return false;
}
/** A key shortened and made printable for a reason path. */
const safeKey = k => (k.length > 64 ? `${k.slice(0, 64)}...` : k).replace(/[\u0000-\u001f\u007f]/gu, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);
const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const own = (o, k) => (isObj(o) && Object.prototype.hasOwnProperty.call(o, k) ? o[k] : undefined);
const absent = v => v === undefined || v === null;
const isFiniteNum = v => typeof v === 'number' && Number.isFinite(v);
const isNonNegInt = v => Number.isInteger(v) && v >= 0;
const isPlaceholder = v => UNKNOWN_WORDS.includes(v.trim().toLowerCase()) || v.trim().toLowerCase() === 'unassigned';
const idOrNull = v => (typeof v === 'string' && v.trim() !== '' && !isPlaceholder(v) ? v : null);
const textOrNull = v => (typeof v === 'string' && v.trim() !== '' ? v : null);
const declaredText = v => (typeof v === 'string' && v.trim() !== '' && !isPlaceholder(v) ? v : null);
const uniqSorted = a => [...new Set(a)].sort();
const pick = (value, list) => (list.includes(value) ? value : null);
const cmp = (x, y) => (x < y ? -1 : x > y ? 1 : 0);

function reason(code, path, detail, extra) {
  const def = REASONS[code];
  if (!def) throw new Error(`internal error: unknown reason code ${code}`);
  const r = { code, severity: def.severity, path: path ?? '', message: detail ? `${def.text} ${detail}` : def.text };
  if (def.owner) r.owner = def.owner;
  if (extra) Object.assign(r, extra);
  return r;
}

function sortReasons(list) {
  const key = r => `${3 - SEVERITY_RANK[r.severity]}\u0000${r.code}\u0000${r.path}\u0000${r.inheritedFrom ?? ''}\u0000${r.message}\u0000${(r.streams ?? []).join(',')}`;
  return list.map(r => ({ r, k: key(r) })).sort((a, b) => cmp(a.k, b.k)).map(x => x.r);
}

function dedupeReasons(list) {
  const seen = new Set();
  return list.filter(r => { const k = canonicalJson(r); if (seen.has(k)) return false; seen.add(k); return true; });
}

function decisionOf(reasons) {
  let rank = 0;
  for (const r of reasons) rank = Math.max(rank, SEVERITY_RANK[r.severity]);
  return DECISION_BY_RANK[rank];
}

function canonicalJsonSafe(v) {
  try { return canonicalJson(v); } catch { return 'unhashable'; }
}

/** Read one own data property without invoking accessors. Returns undefined on any doubt. */
function ownData(o, k) {
  try {
    if (o === null || typeof o !== 'object') return undefined;
    const d = Object.getOwnPropertyDescriptor(o, k);
    return d && 'value' in d ? d.value : undefined;
  } catch { return undefined; }
}

/** Copy an external value into a fresh plain JSON snapshot, reading each property once
 * through its descriptor (no getter runs). Objects may carry undefined-valued properties
 * (dropped as absent); arrays may not. Shared references, cycles, holes, accessors,
 * non-enumerable or symbol keys, unsafe keys, non-plain prototypes, non-finite numbers,
 * control characters and size limits are reported as problems.
 * Returns { value, problems, chars } (chars = an upper bound on the canonical JSON size: string and key
 * characters with quotes, number digits, literals and structure). */
export function toPlainSnapshot(root, rootPath = 'value', budget = null) {
  const problems = [];
  const seen = new Set();
  let nodes = 0, chars = 0;
  const push = (code, path, detail) => { if (problems.length < LIMITS.maxProblems) problems.push({ code, path, detail }); };
  const spend = n => { chars += n; if (budget) { budget.remaining -= n; if (budget.remaining < 0 && !budget.exhausted) { budget.exhausted = true; push('LIMIT_EXCEEDED', rootPath, `The input is larger than ${LIMITS.maxTotalChars} units of JSON (string and key characters, number digits, literals and structure).`); } } };
  const walk = (v, path, depth) => {
    if (problems.length >= LIMITS.maxProblems || (budget && budget.exhausted)) return undefined;
    if (++nodes > LIMITS.maxNodes) { push('LIMIT_EXCEEDED', path, `More than ${LIMITS.maxNodes} values.`); return undefined; }
    if (v === null) { spend(4); return v; }
    if (typeof v === 'boolean') { spend(5); return v; }
    if (typeof v === 'string') {
      if (v.length > LIMITS.maxString) { spend(v.length + 2); push('LIMIT_EXCEEDED', path, `Text is longer than ${LIMITS.maxString} characters.`); return v; }
      // canonical JSON escapes quotes, backslashes, tab, newline and carriage return (2 characters) and lone surrogates (6)
      let extra = 0;
      for (let i = 0; i < v.length; i++) {
        const c = v.charCodeAt(i);
        if (c === 34 || c === 92 || c === 9 || c === 10 || c === 13) extra += 1;
        else if (c >= 0xd800 && c <= 0xdfff) {
          const nx = v.charCodeAt(i + 1);
          if (c <= 0xdbff && nx >= 0xdc00 && nx <= 0xdfff) i++; else extra += 5;
        }
      }
      spend(v.length + 2 + extra);
      if (CONTROL_RE.test(v)) push('INPUT_TEXT_INVALID', path);
      return v;
    }
    if (typeof v === 'number') { if (!Number.isFinite(v)) push('INPUT_NOT_PLAIN_JSON', path, 'Numbers must be finite (JSON has no NaN or Infinity).'); else spend(String(v).length); return v; }
    if (typeof v !== 'object') { push('INPUT_NOT_PLAIN_JSON', path, `A ${typeof v} value is not JSON.`); return undefined; }
    if (depth > LIMITS.maxDepth) { push('LIMIT_EXCEEDED', path, `Nesting is deeper than ${LIMITS.maxDepth} levels.`); return undefined; }
    if (seen.has(v)) { push('INPUT_NOT_PLAIN_JSON', path, 'Shared or circular references are not accepted.'); return undefined; }
    seen.add(v);
    if (Array.isArray(v)) {
      if (Object.getPrototypeOf(v) !== Array.prototype) { push('INPUT_NOT_PLAIN_JSON', path, 'Only plain arrays are accepted.'); return undefined; }
      const len = ownData(v, 'length');
      if (!Number.isInteger(len) || len < 0 || len > LIMITS.maxArray) { push('LIMIT_EXCEEDED', path, `Arrays are limited to ${LIMITS.maxArray} items.`); return undefined; }
      for (const k of Reflect.ownKeys(v)) {
        if (k === 'length') continue;
        if (typeof k === 'symbol' || !INDEX_RE.test(k) || Number(k) >= len) { push('INPUT_NOT_PLAIN_JSON', path, 'Arrays may hold only index entries.'); return undefined; }
      }
      spend(2 + len);
      const out = [];
      for (let i = 0; i < len; i++) {
        const d = Object.getOwnPropertyDescriptor(v, String(i));
        if (!d) { push('INPUT_NOT_PLAIN_JSON', `${path}[${i}]`, 'Arrays cannot contain holes.'); continue; }
        if (!('value' in d)) { push('INPUT_NOT_PLAIN_JSON', `${path}[${i}]`, 'Accessor properties are not JSON.'); continue; }
        if (d.value === undefined) { push('INPUT_NOT_PLAIN_JSON', `${path}[${i}]`, 'Arrays cannot contain undefined.'); continue; }
        out.push(walk(d.value, `${path}[${i}]`, depth + 1));
      }
      return out;
    }
    const proto = Object.getPrototypeOf(v);
    if (proto !== Object.prototype && proto !== null) { push('INPUT_NOT_PLAIN_JSON', path, 'Only plain objects are accepted.'); return undefined; }
    const keys = Reflect.ownKeys(v);
    if (keys.length > LIMITS.maxKeys) { push('LIMIT_EXCEEDED', path, `Objects are limited to ${LIMITS.maxKeys} keys.`); return undefined; }
    spend(2);
    const out = {};
    for (const k of keys) {
      if (typeof k === 'symbol') { push('INPUT_NOT_PLAIN_JSON', path, 'Symbol keys are not JSON.'); continue; }
      spend(k.length + 4);
      if (budget && budget.exhausted) break;
      const p = `${path}.${safeKey(k)}`;
      if (UNSAFE_KEYS.has(k)) { push('UNSAFE_KEY', p); continue; }
      if (k.length > LIMITS.maxString || CONTROL_RE.test(k)) { push('INPUT_TEXT_INVALID', p, 'Keys must be short plain text.'); continue; }
      const d = Object.getOwnPropertyDescriptor(v, k);
      if (!d.enumerable) { push('INPUT_NOT_PLAIN_JSON', p, 'Non-enumerable properties are not JSON.'); continue; }
      if (!('value' in d)) { push('INPUT_NOT_PLAIN_JSON', p, 'Accessor properties are not JSON.'); continue; }
      if (d.value === undefined) continue;
      out[k] = walk(d.value, p, depth + 1);
    }
    return out;
  };
  try {
    const value = walk(root, rootPath, 0);
    return { value: problems.length ? null : value, problems, chars };
  } catch {
    return { value: null, problems: [{ code: 'INPUT_NOT_PLAIN_JSON', path: rootPath, detail: 'The value could not be inspected.' }], chars };
  }
}
const snapshotPlain = toPlainSnapshot;

/** Fingerprint of a link's operation: op, streams (in order for directional ops, sorted otherwise),
 * the sorted true claim keys and the params with null-valued keys dropped. A verifier registry entry
 * must carry this value, so a record covers exactly one declared operation and direction. */
const withoutNulls = v => (Array.isArray(v) ? v.map(withoutNulls) : isObj(v) ? Object.fromEntries(Object.entries(v).filter(([, x]) => x !== null).map(([k, x]) => [k, withoutNulls(x)])) : v);
const DIRECTIONAL_OPS = new Set(['frame_transform', 'clock_mapping', 'derivation', 'cross_modal_mapping', 'unit_conversion', 'resample_precondition', 'relabel']);
export function operationFingerprint(link) {
  try {
    const s = toPlainSnapshot(link, 'link');
    if (s.problems.length || !isObj(s.value)) return null;
    const l = s.value;
    const op = own(l, 'op') ?? null;
    const raw = Array.isArray(l.streams) ? l.streams.filter(x => typeof x === 'string') : [];
    // stream order carries meaning for directional ops (source -> target); claims are normalised to their true keys
    const streams = DIRECTIONAL_OPS.has(op) ? raw : [...raw].sort();
    const c = own(l, 'claims');
    const claims = isObj(c) ? Object.keys(c).filter(k => c[k] === true).sort() : [];
    const p = own(l, 'params');
    return sha256Hex(canonicalJson({ op, streams, claims, params: isObj(p) ? withoutNulls(p) : absent(p) ? {} : p }));
  } catch { return null; }
}

// ------------------------------------------------------- descriptor checks
const DESCRIPTOR_FIELDS = new Set(['descriptorVersion', 'streamId', 'label', 'dataset', 'modality', 'measurement', 'neural', 'origin', 'side',
  'provenance', 'quantity', 'frame', 'clock', 'interval', 'subject', 'session', 'rights', 'role', 'missingness', 'channels', 'observations', 'notes']);
const OBS_COUNTS = ['sampleCount', 'valueCount', 'finiteCount', 'nullCount', 'nonFiniteCount'];
const OBS_QUALITY = ['timeNonFiniteCount', 'timeStrictlyIncreasing', 'lengthMismatch', 'channelCountsConsistent', 'invalidCount', 'truncated', 'channelCount'];
const ANGLE_DIMS = ['angle'];
const CARTESIAN_DIMS = ['length', 'velocity', 'acceleration'];

function unitClass(unit) {
  if (absent(unit)) return 'undeclared';
  if (typeof unit !== 'string') return 'unknown';
  if (Object.prototype.hasOwnProperty.call(AMBIGUOUS_UNITS, unit)) return 'ambiguous';
  if (!Object.prototype.hasOwnProperty.call(UNITS, unit)) return 'unknown';
  return UNITS[unit].dimension === 'arbitrary' ? 'arbitrary' : 'known';
}

/** Validate and normalize one descriptor. Never throws for bad data. */
export function validateDescriptor(raw) {
  return validateSnapshot(snapshotPlain(raw, 'descriptor'), raw);
}

function validateSnapshot(snap, raw) {
  const reasons = [];
  const add = (code, path, detail) => reasons.push(reason(code, path, detail));
  if (snap.problems.length || !isObj(snap.value)) {
    if (!snap.problems.length) add('INPUT_NOT_OBJECT', '', 'A descriptor must be an object.');
    for (const p of snap.problems) add(p.code, p.path, p.detail);
    const sid = ownData(raw, 'streamId');
    return { streamId: typeof sid === 'string' && ID_RE.test(sid) ? sid : null, status: 'invalid', fingerprint: null, normalized: null, reasons: sortReasons(dedupeReasons(reasons)), chars: snap.chars };
  }
  const d = snap.value;
  const fp = sha256Hex(canonicalJson(d));
  const n = { descriptorVersion: POLICY.descriptorVersion };

  if (own(d, 'descriptorVersion') !== POLICY.descriptorVersion) add('DESCRIPTOR_VERSION_UNSUPPORTED', 'descriptorVersion');
  const sid = own(d, 'streamId');
  n.streamId = typeof sid === 'string' && ID_RE.test(sid) ? sid : null;
  if (!n.streamId) add('STREAM_ID_INVALID', 'streamId');
  n.label = textOrNull(own(d, 'label'));
  const unknownKeys = [];
  for (const k of Object.keys(d)) {
    if (DESCRIPTOR_FIELDS.has(k)) continue;
    if (PAIRING_FIELD_NAMES.includes(k)) add('DESCRIPTOR_PAIRING_FIELD_IGNORED', k);
    else unknownKeys.push(k);
  }
  if (unknownKeys.length) add('UNRECOGNISED_FIELD', unknownKeys.length === 1 ? unknownKeys[0] : '', `Fields: ${listIds(unknownKeys.sort())}.`);

  const ds = own(d, 'dataset');
  n.dataset = { id: idOrNull(own(ds, 'id')), sourceId: idOrNull(own(ds, 'sourceId')), sourceFamily: idOrNull(own(ds, 'sourceFamily')) };
  if (!n.dataset.id) add('DATASET_ID_MISSING', 'dataset.id');
  if (isObj(ds)) for (const k of Object.keys(ds)) if (PAIRING_FIELD_NAMES.includes(k)) add('DESCRIPTOR_PAIRING_FIELD_IGNORED', `dataset.${k}`);

  // modality and measurement
  n.modality = pick(own(d, 'modality'), MODALITIES);
  if (!n.modality) add('MODALITY_UNKNOWN', 'modality');
  const meas = own(d, 'measurement');
  const mdef = typeof meas === 'string' && Object.prototype.hasOwnProperty.call(MEASUREMENTS, meas) ? MEASUREMENTS[meas] : null;
  n.measurement = mdef ? meas : null;
  if (!mdef) add('MEASUREMENT_UNKNOWN', 'measurement');
  else if (n.modality && mdef.modality !== n.modality) {
    if (n.modality === 'neural' && mdef.family === 'emg') add('EMG_IS_NOT_NEURAL', 'measurement');
    else if (n.modality === 'neural' && mdef.modality === 'physiological_context') add('CONTEXT_SIGNAL_IS_NOT_NEURAL', 'measurement');
    else add('MEASUREMENT_MODALITY_MISMATCH', 'measurement', `${meas} is ${mdef.modality}.`);
  } else if (mdef.other) add('MEASUREMENT_OTHER', 'measurement');
  const measOk = Boolean(mdef && n.modality && mdef.modality === n.modality);

  // side (hemisphere for neural streams, body side otherwise)
  const side = own(d, 'side');
  n.side = pick(side, SIDES);
  if (!absent(side) && !n.side) add('SIDE_INVALID', 'side');

  // neural division
  const neural = own(d, 'neural');
  if (n.modality === 'neural') {
    const div = own(neural, 'division'), dir = own(neural, 'direction');
    n.neural = { division: pick(div, NEURAL_DIVISIONS), structure: textOrNull(own(neural, 'structure')), direction: pick(dir, NEURAL_DIRECTIONS) };
    if (absent(div) || div === 'unknown') add('NEURAL_DIVISION_MISSING', 'neural.division');
    else if (!n.neural.division) add('NEURAL_DIVISION_INVALID', 'neural.division');
    else if (measOk && !mdef.divisions.includes(div)) add('NEURAL_DIVISION_MEASUREMENT_MISMATCH', 'neural.division', `${meas} records from: ${mdef.divisions.join(', ')}.`);
    if (!absent(dir) && !n.neural.direction) add('NEURAL_DIRECTION_INVALID', 'neural.direction');
  } else {
    n.neural = null;
    if (!absent(neural)) add('DIVISION_ON_NON_NEURAL', 'neural');
  }

  // origin and provenance
  n.origin = pick(own(d, 'origin'), ORIGINS);
  if (!n.origin) add('ORIGIN_INVALID', 'origin');
  else if (n.origin === 'unknown') add('ORIGIN_UNKNOWN', 'origin');
  const prov = own(d, 'provenance');
  const dfrom = own(prov, 'derivedFrom');
  const gen = own(prov, 'generator');
  const act = own(gen, 'actuation');
  const seed = own(gen, 'seed');
  const seedPlaceholder = typeof seed === 'string' && isPlaceholder(seed);
  const seedOk = isFiniteNum(seed) || (typeof seed === 'string' && ID_RE.test(seed) && !seedPlaceholder);
  n.provenance = {
    derivedFrom: Array.isArray(dfrom) ? uniqSorted(dfrom.filter(x => typeof x === 'string' && ID_RE.test(x) && !isPlaceholder(x))) : [],
    generator: isObj(gen) ? {
      engine: declaredText(own(gen, 'engine')), version: declaredText(own(gen, 'version')), model: declaredText(own(gen, 'model')),
      controller: declaredText(own(gen, 'controller')), actuation: pick(act, SIMULATION_ACTUATIONS),
      seed: seedOk ? seed : null, deterministic: own(gen, 'deterministic') === true,
      sourceMotion: idOrNull(own(gen, 'sourceMotion')), parametersRef: declaredText(own(gen, 'parametersRef')),
    } : null,
    pipeline: textOrNull(own(prov, 'pipeline')),
  };
  if (!absent(dfrom) && (!Array.isArray(dfrom) || dfrom.length !== n.provenance.derivedFrom.length)) add('PARAMS_INVALID', 'provenance.derivedFrom', 'derivedFrom must be unique stream identifiers, not placeholders.');
  if (n.streamId && n.provenance.derivedFrom.includes(n.streamId)) { add('PARAMS_INVALID', 'provenance.derivedFrom', 'derivedFrom cannot list the stream itself.'); n.provenance.derivedFrom = n.provenance.derivedFrom.filter(x => x !== n.streamId); }
  if (n.provenance.generator && n.streamId && n.provenance.generator.sourceMotion === n.streamId) { add('PARAMS_INVALID', 'provenance.generator.sourceMotion', 'sourceMotion cannot name the stream itself.'); n.provenance.generator.sourceMotion = null; }
  if (!absent(gen) && !isObj(gen)) add('PARAMS_INVALID', 'provenance.generator', 'generator must be an object.');
  if (isObj(gen) && !absent(seed) && !seedOk && !seedPlaceholder) add('PARAMS_INVALID', 'provenance.generator.seed', 'seed must be a finite number or an identifier string.');
  if (!absent(act) && !n.provenance.generator.actuation) add('SIMULATION_ACTUATION_INVALID', 'provenance.generator.actuation');
  if (measOk && mdef.simulatedOnly && n.origin && n.origin !== 'simulated') add('SIMULATED_MEASUREMENT_DECLARED_MEASURED', 'origin');
  if (measOk && mdef.estimateOnly && n.origin === 'measured') add('ESTIMATE_DECLARED_MEASURED', 'origin');
  if (n.origin === 'measured' && (!absent(gen) || n.provenance.derivedFrom.length > 0)) add('ORIGIN_PROVENANCE_CONFLICT', !absent(gen) ? 'provenance.generator' : 'provenance.derivedFrom');
  // a generator with an actuation, or a controller naming a muscle-model stage, is a simulation whatever the declared origin:
  // its EMG-kind output is simulated activation, and any other output must be declared simulated
  const simGen = n.provenance.generator && (n.provenance.generator.actuation || (n.provenance.generator.controller && namesMuscleStage(n.provenance.generator.controller)));
  if (measOk && mdef.family === 'emg' && n.origin !== 'measured' && simGen) add('SIMULATED_ACTIVATION_IS_NOT_EMG', n.provenance.generator.actuation ? 'provenance.generator.actuation' : 'provenance.generator.controller', 'Declare simulator output as simulated_muscle_activation.');
  else if (['derived', 'inferred', 'unknown'].includes(n.origin) && n.provenance.generator && n.provenance.generator.actuation) add('SIMULATED_LINEAGE_MUST_STAY_SIMULATED', 'provenance.generator.actuation', 'A generator with an actuation is a simulator.');
  const g = n.provenance.generator;
  if (n.origin === 'simulated') {
    const needsActuation = ['myographic', 'motion', 'mechanics'].includes(n.modality);
    const missing = g ? ['engine', 'version', 'model', 'controller', ...(needsActuation ? ['actuation'] : [])].filter(k => !g[k]).concat(g.seed === null && !g.deterministic ? ['seed'] : []) : ['generator'];
    if (missing.length) add('SIMULATION_PROVENANCE_INCOMPLETE', 'provenance.generator', `Missing or placeholder: ${missing.join(', ')}.`);
    if (g && !g.sourceMotion) add('SIMULATION_SOURCE_MOTION_UNDECLARED', 'provenance.generator.sourceMotion');
    if (g && !g.parametersRef) add('SIMULATION_PARAMETERS_UNDECLARED', 'provenance.generator.parametersRef');
  }
  if (g && g.actuation === 'schematic_rules') add('SCHEMATIC_SIMULATION', 'provenance.generator.actuation');
  if (g && n.modality === 'myographic') {
    const jointText = Boolean(g.controller && (JOINT_CONTROLLER_RE.test(g.controller) || ADD_TOKEN_RE.test(g.controller)));
    // joint-control text with no muscle-level stage names a joint-level controller outright
    const muscleStage = Boolean(g.controller && namesMuscleStage(g.controller));
    if (g.actuation && JOINT_LEVEL_ACTUATIONS.includes(g.actuation)) add('PD_JOINT_TARGETS_NOT_MUSCLE_ACTIVATION', 'provenance.generator.actuation');
    else if (jointText && !muscleStage) add('PD_JOINT_TARGETS_NOT_MUSCLE_ACTIVATION', 'provenance.generator.controller');
    else {
      if (g.actuation === 'other') add('SIMULATION_ACTUATION_OTHER', 'provenance.generator.actuation');
      if (jointText) add('CONTROLLER_TEXT_MENTIONS_JOINT_CONTROL', 'provenance.generator.controller');
    }
  }
  if ((n.origin === 'derived' || n.origin === 'inferred') && n.provenance.derivedFrom.length === 0) add('DERIVATION_SOURCE_UNDECLARED', 'provenance.derivedFrom');

  // self-description text on neural streams (label and quantity name only; references to another signal are not flagged)
  if (n.modality === 'neural') {
    const texts = [n.label, textOrNull(own(own(d, 'quantity'), 'name'))].filter(Boolean);
    if (selfDescribes(texts, EMG_WORD_RE)) add('LABEL_MENTIONS_EMG', 'label');
    if (selfDescribes(texts, CONTEXT_WORD_RE, CONTEXT_BIGRAMS)) add('LABEL_MENTIONS_CONTEXT_SIGNAL', 'label');
  }

  // quantity and unit
  const q = own(d, 'quantity');
  const unit = own(q, 'unit');
  const uc = unitClass(unit);
  n.quantity = { name: textOrNull(own(q, 'name')), unit: typeof unit === 'string' ? unit : null, unitClass: uc, dimension: uc === 'known' || uc === 'arbitrary' ? UNITS[unit].dimension : null };
  if (uc === 'undeclared') add('UNIT_UNDECLARED', 'quantity.unit');
  else if (uc === 'ambiguous') add('UNIT_AMBIGUOUS', 'quantity.unit', `"${unit}" could mean ${AMBIGUOUS_UNITS[unit]}.`);
  else if (uc === 'unknown') add('UNIT_UNRECOGNISED', 'quantity.unit', typeof unit === 'string' ? `"${unit}" is not in the table.` : 'The unit must be text.');
  else if (uc === 'arbitrary') add('UNIT_ARBITRARY', 'quantity.unit');
  const qdim = own(q, 'dimension');
  if (!absent(qdim) && (!DIMENSIONS.includes(qdim) || (n.quantity.dimension && qdim !== n.quantity.dimension))) add('QUANTITY_DIMENSION_CONFLICT', 'quantity.dimension');
  // the measurement must be able to produce the declared dimension, whether it comes from the unit or from quantity.dimension
  const dims = uniqSorted([n.quantity.dimension, DIMENSIONS.includes(qdim) ? qdim : null].filter(Boolean));
  n.quantity.declaredDimensions = dims;
  if (n.modality === 'neural' && dims.includes('normalized_activation')) add('EMG_IS_NOT_NEURAL', 'quantity.unit', '%MVC is a normalisation of muscle EMG.');
  if (measOk) {
    for (const dim of dims) {
      if (mdef.dims.includes(dim)) continue;
      if (mdef.jointAngles && dim === 'length') add('GLOVE_ANGLES_NOT_CARTESIAN', 'quantity');
      else if (mdef.image && dim === 'length') add('IMAGE_POSE_NOT_PHYSICAL', 'quantity');
      else if (mdef.eventRate && dim === 'frequency') add('SPIKE_RATE_IN_HZ', 'quantity.unit');
      else add('MEASUREMENT_UNIT_MISMATCH', 'quantity', `${meas} produces: ${mdef.dims.join(', ')}.`);
    }
  }

  // frame
  const fr = own(d, 'frame');
  const spatial = n.modality === 'motion' || n.modality === 'mechanics';
  if (absent(fr)) {
    n.frame = { id: null, kind: null, handedness: null };
    if (spatial) add('FRAME_UNDECLARED', 'frame');
  } else {
    const kind = own(fr, 'kind'), hand = own(fr, 'handedness');
    n.frame = { id: idOrNull(own(fr, 'id')), kind: pick(kind, FRAME_KINDS), handedness: pick(hand, ['right', 'left']) };
    if (!isObj(fr) || (!absent(kind) && !n.frame.kind) || (!absent(hand) && !n.frame.handedness)) add('FRAME_INVALID', 'frame');
    else if (spatial && (!n.frame.kind || n.frame.kind === 'none' || !n.frame.id)) add('FRAME_UNDECLARED', 'frame');
    const k = n.frame.kind;
    if (measOk && k && k !== 'none') {
      if (mdef.jointAngles && k !== 'joint_space') add(/^cartesian/u.test(k) ? 'GLOVE_ANGLES_NOT_CARTESIAN' : 'JOINT_ANGLES_REQUIRE_JOINT_SPACE', 'frame.kind');
      if (mdef.image && k !== 'image_2d') add(/^cartesian/u.test(k) ? 'IMAGE_POSE_NOT_PHYSICAL' : 'IMAGE_POSE_REQUIRES_IMAGE_FRAME', 'frame.kind');
      if (mdef.cartesian && k !== 'cartesian_3d') add('MEASUREMENT_FRAME_MISMATCH', 'frame.kind');
      // quantity against frame: angles are not Cartesian (except IMU orientation), lengths are not joint space
      if (spatial && meas !== 'imu' && /^cartesian/u.test(k) && dims.some(x => ANGLE_DIMS.includes(x))) add('QUANTITY_FRAME_MISMATCH', 'frame.kind', 'Angle values in a Cartesian frame.');
      if (spatial && k === 'joint_space' && dims.some(x => CARTESIAN_DIMS.includes(x))) add('QUANTITY_FRAME_MISMATCH', 'frame.kind', 'Length, velocity or acceleration values in joint space.');
    }
  }

  // clock
  const ck = own(d, 'clock');
  const cu = own(ck, 'unit'), rate = own(ck, 'rateHz'), offU = own(ck, 'offsetUncertaintyS'), drift = own(ck, 'driftPpm'), sync = own(ck, 'syncTime');
  n.clock = {
    domain: idOrNull(own(ck, 'domain')),
    unit: typeof cu === 'string' && Object.prototype.hasOwnProperty.call(TIME_UNIT_DIVISORS, cu) ? cu : null,
    rateHz: isFiniteNum(rate) && rate > 0 ? rate : null,
    offsetUncertaintyS: isFiniteNum(offU) && offU >= 0 ? offU : null,
    driftPpm: isFiniteNum(drift) && drift >= 0 ? drift : null,
    syncTime: isFiniteNum(sync) ? sync : null,
  };
  if (!n.clock.domain) add('CLOCK_DOMAIN_UNDECLARED', 'clock.domain');
  if (absent(cu)) add('CLOCK_UNIT_UNDECLARED', 'clock.unit');
  else if (!n.clock.unit) add('CLOCK_UNIT_INVALID', 'clock.unit');
  if ((!absent(rate) && n.clock.rateHz === null) || (!absent(offU) && n.clock.offsetUncertaintyS === null) || (!absent(drift) && n.clock.driftPpm === null)
    || (!absent(sync) && n.clock.syncTime === null)) add('CLOCK_FIELD_INVALID', 'clock');

  // interval (start/end in clock units on clock.domain; uncertaintyS in seconds)
  const iv = own(d, 'interval');
  if (absent(iv)) {
    n.interval = { start: null, end: null, uncertaintyS: null };
    add('INTERVAL_UNDECLARED', 'interval');
  } else {
    const st = own(iv, 'start'), en = own(iv, 'end'), iu = own(iv, 'uncertaintyS');
    const ok = isFiniteNum(st) && isFiniteNum(en) && st <= en && (absent(iu) || (isFiniteNum(iu) && iu >= 0));
    n.interval = ok ? { start: st, end: en, uncertaintyS: absent(iu) ? null : iu } : { start: null, end: null, uncertaintyS: null };
    if (!ok) add('INTERVAL_INVALID', 'interval');
  }

  // subject and session
  const sj = own(d, 'subject'), se = own(d, 'session');
  n.subject = { id: idOrNull(own(sj, 'id')), namespace: idOrNull(own(sj, 'namespace')), species: idOrNull(own(sj, 'species')), taxonId: idOrNull(own(sj, 'taxonId')) };
  n.session = { id: idOrNull(own(se, 'id')), namespace: idOrNull(own(se, 'namespace')) };
  if (n.origin === 'simulated') {
    if (n.subject.id) add('SIMULATED_SUBJECT_IS_MODEL', 'subject.id');
  } else {
    if (!n.subject.id) add('SUBJECT_UNDECLARED', 'subject.id');
    if (!n.subject.species && !n.subject.taxonId) add('SPECIES_UNDECLARED', 'subject.species');
  }
  if ((n.subject.id && !n.subject.namespace) || (n.session.id && !n.session.namespace)) add('SUBJECT_NAMESPACE_UNDECLARED', n.subject.id && !n.subject.namespace ? 'subject.namespace' : 'session.namespace');
  if (!n.session.id) add('SESSION_UNDECLARED', 'session.id');

  // rights (a software licence or a placeholder word is never a data licence)
  const rt = own(d, 'rights');
  const rs = own(rt, 'status'), rr = own(rt, 'redistribution');
  const licText = v => { const t = declaredText(v); return t && !isLicencePlaceholder(t) ? t : null; };
  let dataLic = licText(own(rt, 'dataLicence'));
  let codeLic = licText(own(rt, 'codeLicence'));
  if (dataLic && namesSoftwareLicence(dataLic)) { add('CODE_LICENCE_IS_NOT_DATA_PERMISSION', 'rights.dataLicence', `"${dataLic}" names a software licence.`); codeLic = codeLic ?? dataLic; dataLic = null; }
  n.rights = { dataLicence: dataLic, codeLicence: codeLic, status: absent(rs) ? 'unknown' : pick(rs, RIGHTS_STATUSES), redistribution: absent(rr) ? 'unknown' : pick(rr, REDISTRIBUTION) };
  if (!n.rights.status || !n.rights.redistribution) {
    add('RIGHTS_INVALID', 'rights');
    n.rights.status = n.rights.status ?? 'unknown';
    n.rights.redistribution = n.rights.redistribution ?? 'unknown';
  }
  if (n.rights.status === 'unknown' || !n.rights.dataLicence) add('RIGHTS_UNKNOWN', 'rights');
  if (!n.rights.dataLicence && n.rights.codeLicence) add('CODE_LICENCE_IS_NOT_DATA_PERMISSION', 'rights.codeLicence');
  if (n.rights.redistribution === 'unknown') add('REDISTRIBUTION_UNKNOWN', 'rights.redistribution');

  // role
  const rl = own(d, 'role');
  const split = own(rl, 'split'), nc = own(rl, 'negativeControl');
  n.role = { split: absent(split) ? 'unknown' : pick(split, SPLITS), negativeControl: null };
  if (!n.role.split) { add('SPLIT_INVALID', 'role.split'); n.role.split = 'unknown'; } else if (n.role.split === 'unknown') add('SPLIT_UNKNOWN', 'role.split');
  if (!absent(nc)) {
    const kind = own(nc, 'kind'), of = own(nc, 'of');
    if (isObj(nc) && NEGATIVE_CONTROL_KINDS.includes(kind) && (absent(of) || (typeof of === 'string' && ID_RE.test(of)))) n.role.negativeControl = { kind, of: absent(of) ? null : of };
    else add('NEGATIVE_CONTROL_INVALID', 'role.negativeControl');
  }

  // missingness (undeclared gaps stay unknown: null, never [])
  const ms = own(d, 'missingness');
  if (absent(ms)) {
    n.missingness = { declared: false, encoding: null, missingCount: null, gaps: null };
    add('MISSINGNESS_UNDECLARED', 'missingness');
  } else {
    const enc = own(ms, 'encoding'), mc = own(ms, 'missingCount'), gaps = own(ms, 'gaps');
    n.missingness = { declared: true, encoding: pick(enc, MISSING_ENCODINGS), missingCount: isNonNegInt(mc) ? mc : null, gaps: null };
    if (enc === 'sentinel') add('MISSING_SENTINEL_NOT_MASKED', 'missingness.encoding');
    else if (!n.missingness.encoding || (!absent(mc) && n.missingness.missingCount === null)) add('MISSINGNESS_INVALID', 'missingness');
    if (!absent(gaps)) {
      const okGaps = Array.isArray(gaps) && gaps.every(x => isObj(x) && isFiniteNum(own(x, 'start')) && isFiniteNum(own(x, 'end')) && own(x, 'start') < own(x, 'end')
        && (n.interval.start === null || (own(x, 'start') >= n.interval.start && own(x, 'end') <= n.interval.end)));
      if (okGaps) n.missingness.gaps = gaps.map(x => ({ start: x.start, end: x.end })).sort((a, b) => a.start - b.start || a.end - b.end);
      else add('GAPS_INVALID', 'missingness.gaps');
    }
    if (n.missingness.encoding === 'none' && ((n.missingness.missingCount ?? 0) > 0 || (n.missingness.gaps ?? []).length > 0)) add('MISSINGNESS_INCONSISTENT', 'missingness', 'Encoding none declares no missing values.');
  }

  // channels
  const ch = own(d, 'channels');
  if (absent(ch)) {
    n.channels = { count: null, order: null };
    add('CHANNELS_UNDECLARED', 'channels');
  } else {
    const count = own(ch, 'count'), order = own(ch, 'order');
    const countOk = Number.isInteger(count) && count >= 1 && count <= LIMITS.maxArray;
    const orderOk = absent(order) || (Array.isArray(order) && order.length === count && order.every(x => typeof x === 'string' && x !== '') && new Set(order).size === order.length);
    n.channels = { count: countOk ? count : null, order: countOk && orderOk && Array.isArray(order) ? [...order] : null };
    if (!countOk || !orderOk) add('CHANNELS_INVALID', 'channels');
    else if (absent(order)) add('CHANNEL_ORDER_UNDECLARED', 'channels.order');
  }

  // observation summary (counts and timestamp-quality flags only; never values)
  const ob = own(d, 'observations');
  if (absent(ob)) {
    n.observations = null;
    add('OBSERVATIONS_UNSUMMARISED', 'observations');
  } else {
    const vals = Object.fromEntries(OBS_COUNTS.map(k => [k, own(ob, k)]));
    const intsOk = OBS_COUNTS.every(k => isNonNegInt(vals[k]));
    const sumOk = intsOk && vals.finiteCount + vals.nullCount + vals.nonFiniteCount === vals.valueCount;
    const shapeOk = intsOk && (n.channels.count === null ? (vals.sampleCount === 0) === (vals.valueCount === 0) : vals.valueCount === vals.sampleCount * n.channels.count);
    const qual = Object.fromEntries(OBS_QUALITY.map(k => [k, own(ob, k)]));
    const qualShapeOk = isObj(ob) && (absent(qual.timeNonFiniteCount) || isNonNegInt(qual.timeNonFiniteCount)) && (absent(qual.invalidCount) || isNonNegInt(qual.invalidCount))
      && ['timeStrictlyIncreasing', 'lengthMismatch', 'channelCountsConsistent', 'truncated'].every(k => absent(qual[k]) || typeof qual[k] === 'boolean')
      && (absent(qual.channelCount) || isNonNegInt(qual.channelCount)) && Object.keys(ob).every(k => OBS_COUNTS.includes(k) || OBS_QUALITY.includes(k));
    const qualBad = (qual.invalidCount ?? 0) > 0 || qual.channelCountsConsistent === false || qual.truncated === true
      || (!absent(qual.channelCount) && n.channels.count !== null && vals.sampleCount > 0 && qual.channelCount !== n.channels.count);
    if (!intsOk || !sumOk || !shapeOk || !qualShapeOk || qualBad) { n.observations = null; add('OBSERVATIONS_INVALID', 'observations'); } else {
      n.observations = { ...vals, timestampQualityDeclared: !absent(qual.timeStrictlyIncreasing) && !absent(qual.timeNonFiniteCount) && !absent(qual.lengthMismatch) };
      if ((qual.timeNonFiniteCount ?? 0) > 0 || qual.timeStrictlyIncreasing === false || qual.lengthMismatch === true) add('OBSERVATIONS_TIMESTAMPS_INVALID', 'observations');
      if (vals.sampleCount === 0) add('OBSERVATIONS_EMPTY', 'observations.sampleCount');
      else if (vals.finiteCount === 0) add('OBSERVATIONS_ALL_MISSING', 'observations.finiteCount');
      if (vals.nonFiniteCount > 0) add('NONFINITE_VALUES_PRESENT', 'observations.nonFiniteCount');
      if (vals.sampleCount > 1 && n.interval.start !== null && n.interval.start === n.interval.end) add('INTERVAL_INCONSISTENT_WITH_OBSERVATIONS', 'interval');
      const m = n.missingness;
      if (m.declared && m.encoding === 'none' && vals.nullCount > 0) add('MISSINGNESS_INCONSISTENT', 'observations.nullCount', 'Encoding none, but null values are counted.');
      if (m.declared && m.missingCount !== null && m.encoding === 'null' && m.missingCount !== vals.nullCount) add('MISSINGNESS_INCONSISTENT', 'missingness.missingCount', 'missingCount differs from observations.nullCount.');
    }
  }

  n.parents = uniqSorted([...n.provenance.derivedFrom, ...(n.provenance.generator && n.provenance.generator.sourceMotion && n.provenance.generator.sourceMotion !== n.streamId ? [n.provenance.generator.sourceMotion] : [])]);
  const sorted = sortReasons(dedupeReasons(reasons));
  return { streamId: n.streamId, status: decisionOf(sorted) === 'rejected' ? 'invalid' : 'valid', fingerprint: fp, normalized: n, reasons: sorted, chars: snap.chars };
}

/** Count samples/values from already-parsed arrays (for example an importer's output).
 * values[i] is a number, null, or an array of numbers/nulls (one per channel).
 * This helper reads values; it is for the importer and is outside evaluate()'s
 * metadata-only scope. Pass its whole result as descriptor.observations. */
export function summarizeObservations(t, values) {
  const out = { sampleCount: 0, valueCount: 0, finiteCount: 0, nullCount: 0, nonFiniteCount: 0, invalidCount: 0, channelCount: null,
    timeNonFiniteCount: 0, timeStrictlyIncreasing: true, lengthMismatch: false, channelCountsConsistent: true, truncated: false };
  try {
    if (!Array.isArray(t) || !Array.isArray(values)) { out.invalidCount = 1; out.timeStrictlyIncreasing = false; return out; }
    out.lengthMismatch = t.length !== values.length;
    const n = Math.min(t.length, values.length);
    let entries = 0, prev = null;
    for (let i = 0; i < n; i++) {
      const ti = t[i];
      if (!isFiniteNum(ti)) { out.timeNonFiniteCount++; out.timeStrictlyIncreasing = false; } else {
        if (prev !== null && !(ti > prev)) out.timeStrictlyIncreasing = false;
        prev = ti;
      }
      const row = Array.isArray(values[i]) ? values[i] : [values[i]];
      if (out.channelCount === null) out.channelCount = row.length;
      else if (row.length !== out.channelCount) out.channelCountsConsistent = false;
      for (const v of row) {
        if (++entries > LIMITS.maxObservationEntries) { out.truncated = true; break; }
        out.valueCount++;
        if (v === null) out.nullCount++;
        else if (typeof v !== 'number') out.invalidCount++;
        else if (Number.isFinite(v)) out.finiteCount++;
        else out.nonFiniteCount++;
      }
      if (out.truncated) break;
      out.sampleCount++;
    }
  } catch {
    out.invalidCount++; out.truncated = true;
  }
  return out;
}

// ------------------------------------------------------------ evidence
const REGISTRY_FIELDS = ['ref', 'sha256', 'verifierId', 'claims', 'streams', 'fingerprints', 'operationFingerprint', 'notes'];
function validRegistryEntry(e) {
  if (!isObj(e) || Object.keys(e).some(k => !REGISTRY_FIELDS.includes(k))) return false;
  const claims = own(e, 'claims'), streams = own(e, 'streams'), fps = own(e, 'fingerprints');
  return typeof own(e, 'ref') === 'string' && ID_RE.test(own(e, 'ref')) && typeof own(e, 'sha256') === 'string' && HEX64_RE.test(own(e, 'sha256'))
    && typeof own(e, 'verifierId') === 'string' && declaredText(own(e, 'verifierId')) !== null
    && typeof own(e, 'operationFingerprint') === 'string' && HEX64_RE.test(own(e, 'operationFingerprint'))
    && Array.isArray(claims) && claims.length > 0 && claims.every(c => REGISTRY_CLAIMS.includes(c))
    && Array.isArray(streams) && streams.length > 0 && streams.every(s => typeof s === 'string' && ID_RE.test(s)) && new Set(streams).size === streams.length
    && isObj(fps) && Object.keys(fps).length === streams.length && streams.every(s => typeof own(fps, s) === 'string' && HEX64_RE.test(own(fps, s)));
}

/** Which of `wanted` claims a link's evidence covers (per claim). A verifier record counts
 * only when a registry entry matches its ref and sha256, the link's stream set, the current
 * descriptor fingerprints, the link's operation fingerprint, and the claim.
 * selfDeclared: a self_attestation or header_field was given. recordGiven: a verifier record was given. */
/** Shape and admissibility of link.evidence. Run for every evidence-bearing link, identity links included. */
function scanEvidence(link, add) {
  const evidence = own(link, 'evidence');
  if (absent(evidence)) return [];
  if (!Array.isArray(evidence) || evidence.length > LIMITS.maxEvidence) { add('EVIDENCE_INVALID', 'evidence', `evidence must be an array of at most ${LIMITS.maxEvidence} items.`); return []; }
  const items = [];
  evidence.forEach((ev, i) => {
    const path = `evidence[${i}]`;
    const kind = own(ev, 'kind');
    if (!isObj(ev) || typeof kind !== 'string') { add('EVIDENCE_INVALID', path); return; }
    if (INADMISSIBLE_EVIDENCE.includes(kind)) { add('INADMISSIBLE_EVIDENCE', path, `Kind: ${kind}.`); return; }
    if (!ADMISSIBLE_EVIDENCE.includes(kind)) { add('EVIDENCE_INVALID', path, `Unknown kind: ${kind}.`); return; }
    if (kind !== 'verifier_record') { items.push({ path, kind }); return; }
    const ref = own(ev, 'ref'), sha = own(ev, 'sha256');
    if (typeof ref !== 'string' || !ID_RE.test(ref) || typeof sha !== 'string' || !HEX64_RE.test(sha)) { add('EVIDENCE_INVALID', path, 'A verifier_record needs ref and a lowercase sha256.'); return; }
    items.push({ path, kind, ref, sha });
  });
  return items;
}

function assessEvidence(link, wanted, recs, ctx, add) {
  const accepted = new Set();
  let selfDeclared = false, recordGiven = false;
  const items = scanEvidence(link, add);
  if (!items.length) return { accepted, selfDeclared, recordGiven };
  const linkSet = uniqSorted(recs.map(r => r.streamId)).join('\u0000');
  const opFp = operationFingerprint(link);
  items.forEach(({ path, kind, ref, sha }) => {
    if (kind !== 'verifier_record') { selfDeclared = true; return; }
    recordGiven = true;
    const entry = ctx.registry.get(ref);
    if (!entry || entry.sha256 !== sha || entry.streams.join('\u0000') !== linkSet) { add('VERIFIER_RECORD_NOT_QUALIFIED', path); return; }
    const stale = recs.filter(r => entry.fingerprints[r.streamId] !== r.fingerprint).map(r => r.streamId);
    if (stale.length) { add('VERIFIER_RECORD_NOT_QUALIFIED', path, `Descriptor changed since verification: ${stale.join(', ')}.`); return; }
    if (entry.operationFingerprint !== opFp) { add('VERIFIER_RECORD_NOT_QUALIFIED', path, 'The record was issued for a different operation (op, stream order, true claims or params).'); return; }
    const hit = wanted.filter(c => entry.claims.includes(c));
    if (hit.length === 0) { add('VERIFIER_RECORD_NOT_QUALIFIED', path, 'The registry entry does not cover these claims.'); return; }
    hit.forEach(c => accepted.add(c));
    add('VERIFIER_RECORD_ACCEPTED', path, `Covers: ${hit.join(', ')}; verifier ${entry.verifierId}.`);
  });
  return { accepted, selfDeclared, recordGiven };
}

// ------------------------------------------------------------- lineage
const parentsOf = n => n.parents;
const listIds = ids => (ids.length > LIMITS.maxListedIds ? `${ids.slice(0, LIMITS.maxListedIds).join(', ')} and ${ids.length - LIMITS.maxListedIds} more` : ids.join(', '));

/** Follow derivedFrom/sourceMotion through supplied descriptors (cycle-safe; each id counted once).
 * simulated: the stream or an ancestor is simulated. heldout: an ancestor is heldout/test.
 * negativeControl: an ancestor is a negative control. unresolved: named sources not supplied.
 * truncated: the walk hit LIMITS.maxLineage, so nothing about the remaining ancestors is known. */
function lineageOf(rec, ctx) {
  const cache = ctx.lineage;
  if (cache.has(rec.streamId)) return cache.get(rec.streamId);
  const out = { ancestors: [], unresolved: [], unknown: [], splitUnknown: [], simulated: rec.normalized.origin === 'simulated', heldout: false, negativeControl: false, truncated: false, cycle: false };
  const visited = new Set([rec.streamId]);
  const queued = new Set();
  const queue = [];
  const enqueue = id => { if (id === rec.streamId) out.cycle = true; else if (!visited.has(id) && !queued.has(id)) { queued.add(id); queue.push(id); } };
  parentsOf(rec.normalized).forEach(enqueue);
  for (let qi = 0; qi < queue.length; qi++) {
    const id = queue[qi];
    if (visited.size > LIMITS.maxLineage) { out.truncated = true; break; }
    visited.add(id);
    const a = ctx.byId.get(id);
    if (!a || !a.normalized) { out.unresolved.push(id); continue; }
    out.ancestors.push(id);
    const n = a.normalized;
    // an ancestor whose origin or control status is unknown, or that failed validation, leaves the lineage unknown
    if (!n.origin || n.origin === 'unknown' || a.validationStatus === 'invalid' || a.reasons.some(r => r.code === 'NEGATIVE_CONTROL_INVALID')) out.unknown.push(id);
    if (n.origin === 'simulated') out.simulated = true;
    if (n.role.split === 'unknown') out.splitUnknown.push(id);
    if (['heldout', 'test'].includes(n.role.split)) out.heldout = true;
    if (n.role.negativeControl) out.negativeControl = true;
    parentsOf(n).forEach(enqueue);
  }
  out.ancestors = uniqSorted(out.ancestors);
  out.unresolved = uniqSorted(out.unresolved);
  out.unknown = uniqSorted(out.unknown);
  out.splitUnknown = uniqSorted(out.splitUnknown);
  cache.set(rec.streamId, out);
  return out;
}

/** Reasons for a lineage that gates a decision: truncated or cyclic (reject), or with sources that are not
 * supplied, or of unknown origin or control status, or caught in a cycle (unverified). */
function lineageGate(r, lin, add, ctx, opts = {}) {
  if (lin.truncated) add('LINEAGE_TRUNCATED', 'provenance', undefined, [r.streamId]);
  if (lin.cycle) add('LINEAGE_CYCLE', 'provenance.derivedFrom', undefined, [r.streamId]);
  if (lin.truncated) return;
  if (lin.unresolved.length && ['derived', 'inferred', 'simulated'].includes(r.normalized.origin)) add('LINEAGE_UNRESOLVED', 'provenance', `Not supplied: ${listIds(lin.unresolved)}.`, [r.streamId]);
  const unclear = uniqSorted([...lin.unknown, ...lin.ancestors.filter(id => ctx.byId.get(id).lineageCycle)]);
  if (unclear.length) add('LINEAGE_UNRESOLVED', 'provenance', `Origin, control status or lineage unknown for: ${listIds(unclear)}.`, [r.streamId]);
  // for held-out rules (training, derivation): an ancestor outside the link whose train/test role is unknown leaves the lineage unknown
  if (opts.split) {
    const su = lin.splitUnknown.filter(id => !(opts.exclude ?? []).includes(id));
    if (su.length) add('LINEAGE_UNRESOLVED', 'role.split', `Train/test role unknown for ancestors: ${listIds(su)}.`, [r.streamId]);
  }
}

// ------------------------------------------------------------- time math
const toSeconds = (value, unit) => value / TIME_UNIT_DIVISORS[unit];
const recordTiming = n => (n.clock.domain && n.clock.unit && n.interval.start !== null ? {
  start: toSeconds(n.interval.start, n.clock.unit), end: toSeconds(n.interval.end, n.clock.unit),
  boundU: n.interval.uncertaintyS,
  gaps: n.missingness.gaps === null ? null : n.missingness.gaps.map(x => ({ start: toSeconds(x.start, n.clock.unit), end: toSeconds(x.end, n.clock.unit) })),
  sync: n.clock.syncTime === null ? null : toSeconds(n.clock.syncTime, n.clock.unit),
} : null);

/** Same declared scope: same dataset id and same declared source (both undeclared counts as same). */
const sameScope = (a, b) => a.dataset.id === b.dataset.id && a.dataset.sourceId === b.dataset.sourceId;
/** Two streams share a clock only if both declare the same domain inside the same dataset and source. */
const sameClock = (a, b) => a.clock.domain !== null && a.clock.domain === b.clock.domain && sameScope(a, b);

function parseWindow(win) {
  if (absent(win)) return { window: null, ok: true };
  const s = own(win, 'start'), e = own(win, 'end'), u = own(win, 'unit'), d = own(win, 'domain');
  if (!isObj(win) || Object.keys(win).some(k => !['start', 'end', 'unit', 'domain'].includes(k)) || !isFiniteNum(s) || !isFiniteNum(e) || !(s < e)
    || typeof u !== 'string' || !Object.prototype.hasOwnProperty.call(TIME_UNIT_DIVISORS, u) || !idOrNull(d)) return { window: null, ok: false };
  return { window: { start: toSeconds(s, u), end: toSeconds(e, u), domain: d }, ok: true };
}

/** Is [a, b] fully covered by the sorted union of gaps? Did any gap touch it? */
function gapCoverage(gaps, a, b) {
  let cursor = a, touched = false;
  for (const x of gaps) {
    if (x.end <= a || x.start >= b) continue;
    touched = true;
    if (x.start > cursor) return { full: false, touched };
    cursor = Math.max(cursor, x.end);
    if (cursor >= b) return { full: true, touched };
  }
  return { full: false, touched };
}

function windowChecks(recs, win, add, outsideCode) {
  for (const r of recs) {
    const tm = recordTiming(r.normalized);
    if (!tm) { add('INTERVAL_UNKNOWN_FOR_OPERATION', 'params.window', undefined, [r.streamId]); continue; }
    if (win.domain !== r.normalized.clock.domain) { add('WINDOW_INVALID', 'params.window.domain', `Stream ${r.streamId} is on ${r.normalized.clock.domain}.`, [r.streamId]); continue; }
    if (win.start < tm.start || win.end > tm.end) { add(outsideCode, 'params.window', undefined, [r.streamId]); continue; }
    if (!tm.gaps) { add('WINDOW_GAPS_UNKNOWN', 'missingness.gaps', undefined, [r.streamId]); continue; }
    const cov = gapCoverage(tm.gaps, win.start, win.end);
    if (cov.full) add('WINDOW_INSIDE_GAP', 'params.window', undefined, [r.streamId]);
    else if (cov.touched) add('WINDOW_OVERLAPS_GAP', 'params.window', undefined, [r.streamId]);
  }
}

/** Timing uncertainty of one stream over a span [a, b] (seconds): offset + drift since the
 * declared sync time. Returns { value, lower }: value null when unknown; lower is a known lower bound. */
function streamTimingUncertainty(n, span) {
  if (n.clock.offsetUncertaintyS === null) return { value: null, lower: 0, why: 'offset uncertainty' };
  if (n.clock.driftPpm === null) return { value: null, lower: n.clock.offsetUncertaintyS, why: 'drift rate' };
  if (n.clock.driftPpm === 0) return { value: n.clock.offsetUncertaintyS, lower: n.clock.offsetUncertaintyS };
  const tm = recordTiming(n);
  if (!span || !tm) return { value: null, lower: n.clock.offsetUncertaintyS, why: 'interval' };
  if (tm.sync === null) return { value: null, lower: n.clock.offsetUncertaintyS, why: 'clock.syncTime' };
  const v = n.clock.offsetUncertaintyS + n.clock.driftPpm * 1e-6 * Math.max(Math.abs(span[0] - tm.sync), Math.abs(span[1] - tm.sync));
  return { value: v, lower: v };
}

/** Compare summed uncertainty parts with a tolerance. Unknown parts count as >= their lower
 * bound, so a declared lower bound above the tolerance still rejects. */
function toleranceCheck(parts, tol, add, path, ids) {
  const lower = parts.reduce((x, p) => x + p.lower, 0);
  if (lower > tol) { add('ALIGNMENT_UNCERTAINTY_EXCEEDS_TOLERANCE', path, `Declared uncertainty of at least ${lower} s > tolerance ${tol} s.`, ids); return; }
  const unknown = parts.filter(p => p.value === null);
  if (unknown.length) add('ALIGNMENT_UNCERTAINTY_UNKNOWN', 'clock', `Undeclared: ${uniqSorted(unknown.map(p => p.why)).join(', ')}.`, ids);
}

function sameTimeChecks(recs, params, add) {
  const ns = recs.map(r => r.normalized);
  const ids = recs.map(r => r.streamId);
  if (ns.some(n => !n.clock.domain || !n.clock.unit)) { add('SAME_TIME_CLOCK_UNKNOWN', 'clock', undefined, ids); return; }
  if (!sameClock(ns[0], ns[1])) {
    if (ns[0].clock.domain === ns[1].clock.domain) add('CLOCK_DOMAIN_NAME_EQUAL_ACROSS_DATASETS', 'clock.domain', undefined, ids);
    add('CLOCK_DOMAINS_DIFFER_NO_MAPPING', 'clock.domain', undefined, ids);
    return;
  }
  const tms = ns.map(recordTiming);
  let span = null;
  if (tms.some(t => t === null)) add('INTERVAL_UNKNOWN_FOR_OPERATION', 'interval', undefined, ids);
  else {
    const s = Math.max(...tms.map(t => t.start)), e = Math.min(...tms.map(t => t.end));
    const overlap = e - s;
    const uB = tms.some(t => t.boundU === null) ? null : tms.reduce((acc, t) => acc + t.boundU, 0);
    if (overlap > 0) {
      if (uB === null) add('INTERVAL_UNCERTAINTY_UNKNOWN', 'interval.uncertaintyS', undefined, ids);
      else if (overlap <= uB) add('OVERLAP_WITHIN_UNCERTAINTY', 'interval', undefined, ids);
      span = [s, e];
    } else if (uB !== null && uB > 0 && -overlap < uB) {
      add('OVERLAP_WITHIN_UNCERTAINTY', 'interval', undefined, ids);
      span = [Math.min(s, e), Math.max(s, e)];
    } else add('NO_TEMPORAL_OVERLAP', 'interval', overlap === 0 ? 'The intervals share only one instant.' : undefined, ids);
  }
  const w = parseWindow(own(params, 'window'));
  if (w.window) span = [w.window.start, w.window.end];
  const tol = own(params, 'toleranceS');
  if (absent(tol)) { add('TOLERANCE_UNDECLARED', 'params.toleranceS', undefined, ids); return; }
  if (!isFiniteNum(tol) || tol <= 0) { add('TOLERANCE_INVALID', 'params.toleranceS', undefined, ids); return; }
  toleranceCheck(ns.map(n => streamTimingUncertainty(n, span)), tol, add, 'params.toleranceS', ids);
}

const hasObservations = n => Boolean(n.observations && n.observations.sampleCount > 0 && n.observations.finiteCount > 0);

function dataPresence(recs, add, timed) {
  for (const r of recs) {
    const o = r.normalized.observations;
    if (o && (o.sampleCount === 0 || o.finiteCount === 0)) add('EMPTY_OBSERVATIONS_FOR_DATA_OPERATION', 'observations', undefined, [r.streamId]);
    if (timed && o && !o.timestampQualityDeclared) add('TIMESTAMP_QUALITY_UNDECLARED', 'observations', undefined, [r.streamId]);
  }
}

/** Brain structures whose expected side of control is not the cerebral contralateral rule (the cerebellum is ipsilateral; the brainstem is mixed). */
const NON_CEREBRAL_RE = /cerebell|vermis|purkinje|dentate[\s_-]*nucle|interpos|fastigi|floccul|brain[\s_-]*stem|medull|pontine|(^|[^a-z])pons([^a-z]|$)|midbrain|mesencephal|red[\s_-]*nucle|olivar|tegment/iu;
/** Laterality of a brain-to-body relation (contralateral cerebral control is the declared expectation). */
function lateralityCheck(a, b, add, ids) {
  const brain = [a, b].find(n => n.modality === 'neural' && n.neural && n.neural.division === 'brain');
  const body = [a, b].find(n => ['myographic', 'motion', 'mechanics'].includes(n.modality));
  if (!brain || !body) return;
  if (brain.neural.structure && NON_CEREBRAL_RE.test(brain.neural.structure)) { add('LATERALITY_EXPECTATION_NOT_ENCODED', 'neural.structure', undefined, ids); return; }
  const lr = s => s === 'left' || s === 'right';
  if ([brain.side, body.side].some(s => s === 'bilateral' || s === 'midline')) add('LATERALITY_NOT_LATERALISED', 'side', undefined, ids);
  else if (!lr(brain.side) || !lr(body.side)) add('LATERALITY_UNDECLARED', 'side', undefined, ids);
  else if (brain.side === body.side) add('LATERALITY_IPSILATERAL', 'side', undefined, ids);
  else add('LATERALITY_CONTRALATERAL', 'side', undefined, ids);
}

// ----------------------------------------------------------------- ops
const IDENTITY_MAPPINGS = ['identity', 'copy', 'relabel', 'rename', 'alias'];
const CLAIM_KEYS = ['sameSubject', 'sameSession', 'sameTime'];
const taxonNumber = t => { const m = /(?:^|[^0-9])([0-9]+)$/u.exec(t); return m ? m[1] : null; };

/** For ops other than pairing: claims must be absent or only false booleans. */
function checkNoClaims(link, add, op) {
  const claims = own(link, 'claims');
  if (absent(claims)) return;
  if (!isObj(claims) || Object.keys(claims).some(k => !CLAIM_KEYS.includes(k)) || Object.values(claims).some(v => typeof v !== 'boolean')) { add('CLAIMS_INVALID', 'claims', 'claims must be booleans named sameSubject, sameSession or sameTime.'); return; }
  if (Object.values(claims).some(v => v === true)) {
    if (op === 'unpaired_exploration') add('CONTRADICTORY_UNPAIRED_CLAIM', 'claims');
    else add('CLAIMS_INVALID', 'claims', `${op} makes no pairing claim; use a pairing link.`);
  }
}

function opPairing(link, recs, ctx, add) {
  const claims = own(link, 'claims');
  const params = own(link, 'params');
  const flags = Object.fromEntries(CLAIM_KEYS.map(k => [k, own(claims, k)]));
  if (!isObj(claims) || Object.values(flags).some(v => !absent(v) && typeof v !== 'boolean') || Object.keys(claims).some(k => !CLAIM_KEYS.includes(k))) { add('CLAIMS_INVALID', 'claims'); return; }
  const wanted = CLAIM_KEYS.filter(k => flags[k] === true);
  if (wanted.length === 0) { add('CLAIMS_INVALID', 'claims'); return; }
  if (flags.sameSession && !flags.sameSubject) add('SESSION_WITHOUT_SUBJECT', 'claims.sameSession');
  const ids = recs.map(r => r.streamId);
  const ev = assessEvidence(link, wanted, recs, ctx, add);
  const uncovered = wanted.filter(c => !ev.accepted.has(c));
  if (uncovered.length) add(ev.selfDeclared ? 'PAIRING_SELF_ATTESTED' : ev.recordGiven ? 'CLAIM_NOT_COVERED_BY_VERIFIER' : 'IMPLICIT_PAIRING_CLAIM', 'claims', `Claims: ${uncovered.join(', ')}.`, ids);
  const [a, b] = recs.map(r => r.normalized);
  const lin = recs.map(r => lineageOf(r, ctx));
  recs.forEach((r, i) => lineageGate(r, lin[i], add, ctx));
  const simLin = lin.map(l => l.simulated);
  if ((simLin[0] || simLin[1]) && (flags.sameSubject || flags.sameSession)) add('SIMULATED_NOT_A_SUBJECT', 'claims', simLin.some((s, i) => s && recs[i].normalized.origin !== 'simulated') ? 'Through derivation lineage.' : undefined, ids.filter((_, i) => simLin[i]));
  if (flags.sameTime && simLin[0] !== simLin[1]) add('SIMULATED_MEASURED_TIME_PAIRING', 'claims.sameTime', undefined, ids);
  if ([a, b].some(n => n.origin === 'inferred')) add('INFERRED_VALUES_IN_PAIRING', 'origin', undefined, ids.filter((_, i) => recs[i].normalized.origin === 'inferred'));
  const controls = recs.filter((r, i) => r.normalized.role.negativeControl || lin[i].negativeControl);
  const cc = own(link, 'controlComparison');
  if (!absent(cc) && typeof cc !== 'boolean') add('PARAMS_INVALID', 'controlComparison', 'controlComparison must be a boolean.');
  if (controls.length) add(cc === true ? 'NEGATIVE_CONTROL_COMPARISON' : 'NEGATIVE_CONTROL_AS_GENUINE_PAIR', 'role.negativeControl', undefined, controls.map(r => r.streamId));
  if (flags.sameSubject) {
    if (!a.subject.id || !b.subject.id || !(a.subject.species || a.subject.taxonId) || !(b.subject.species || b.subject.taxonId)) add('SUBJECT_UNKNOWN_FOR_CLAIM', 'subject', undefined, ids);
    if (a.subject.taxonId && b.subject.taxonId) {
      const [ta, tb] = [taxonNumber(a.subject.taxonId), taxonNumber(b.subject.taxonId)];
      if (ta && tb) { if (ta !== tb) add('SPECIES_CONFLICT', 'subject.taxonId', undefined, ids); }
      else if (a.subject.taxonId !== b.subject.taxonId) add('SPECIES_UNRESOLVED', 'subject.taxonId', undefined, ids);
    } else if (a.subject.species && b.subject.species) {
      if (a.subject.species.trim().toLowerCase() !== b.subject.species.trim().toLowerCase()) add('SPECIES_UNRESOLVED', 'subject.species', undefined, ids);
    } else if ((a.subject.taxonId || a.subject.species) && (b.subject.taxonId || b.subject.species)) add('SPECIES_UNRESOLVED', 'subject', 'One stream declares a taxon id, the other only a species name.', ids);
    if (a.subject.id && b.subject.id) {
      if (!a.subject.namespace || !b.subject.namespace || a.subject.namespace !== b.subject.namespace) add('SUBJECT_NAMESPACES_DIFFER', 'subject.namespace', undefined, ids);
      else if (a.subject.id !== b.subject.id) add('SUBJECT_ID_CONFLICT', 'subject.id', undefined, ids);
      else add('EQUAL_IDENTIFIERS_ARE_NOT_EVIDENCE', 'subject.id', undefined, ids);
    }
  }
  if (flags.sameSession) {
    if (!a.session.id || !b.session.id) add('SESSION_UNKNOWN_FOR_CLAIM', 'session', undefined, ids);
    else if (!a.session.namespace || !b.session.namespace || a.session.namespace !== b.session.namespace) add('SESSION_NAMESPACES_DIFFER', 'session.namespace', undefined, ids);
    else if (a.session.id !== b.session.id) add('SESSION_ID_CONFLICT', 'session.id', undefined, ids);
    else add('EQUAL_IDENTIFIERS_ARE_NOT_EVIDENCE', 'session.id', undefined, ids);
  }
  if (!flags.sameTime && (!absent(own(params, 'window')) || !absent(own(params, 'toleranceS')))) add('PARAMS_INVALID', 'params', 'window and toleranceS apply only to a sameTime claim.');
  if (flags.sameTime) {
    const tol0 = own(params, 'toleranceS');
    if (!absent(tol0) && (!isFiniteNum(tol0) || tol0 <= 0)) add('TOLERANCE_INVALID', 'params.toleranceS', undefined, ids);
    sameTimeChecks(recs, params, add);
    dataPresence(recs, add, true);
    const w = parseWindow(own(params, 'window'));
    if (!w.ok) add('WINDOW_INVALID', 'params.window');
    else if (w.window) windowChecks(recs, w.window, add, 'WINDOW_OUTSIDE_INTERVAL');
  }
}

function opUnpaired(link, recs, ctx, add) {
  add('UNPAIRED_EXPLORATION', '', undefined, recs.map(r => r.streamId));
}

function opUnitConversion(link, recs, ctx, add) {
  const params = own(link, 'params');
  const n = recs[0].normalized;
  const to = own(params, 'toUnit'), from = own(params, 'fromUnit');
  if (typeof to !== 'string' || to === '') { add('CONVERSION_TARGET_UNIT_MISSING', 'params.toUnit'); return null; }
  if (!absent(from) && from !== n.quantity.unit) { add('CONVERSION_FROM_UNIT_MISMATCH', 'params.fromUnit', `Descriptor unit: ${n.quantity.unit === null ? 'undeclared' : `"${n.quantity.unit}"`}.`); return null; }
  const src = n.quantity.unit;
  const classes = [unitClass(src), unitClass(to)];
  if (classes.some(c => c === 'undeclared' || c === 'unknown')) { add('CONVERSION_UNIT_UNKNOWN', 'quantity.unit'); return null; }
  if (classes.includes('ambiguous')) { add('CONVERSION_UNIT_AMBIGUOUS', 'quantity.unit'); return null; }
  if (classes.includes('arbitrary')) { add('CONVERSION_ARBITRARY_UNIT', 'quantity.unit'); return null; }
  const a = UNITS[src], b = UNITS[to];
  if (a.dimension === b.dimension) {
    add('UNIT_CONVERSION_DEFINED', 'params.toUnit', `Factor ${a.factor / b.factor}.`);
    return { fromUnit: src, toUnit: to, factor: a.factor / b.factor, appliedToData: false };
  }
  const dims = new Set([a.dimension, b.dimension]);
  if (dims.has('image_length') && dims.has('length')) add('CAMERA_CALIBRATION_REQUIRED', 'params.toUnit');
  else if (dims.has('angle') && dims.has('length')) add('ANGLE_IS_NOT_DISPLACEMENT', 'params.toUnit');
  else if (ADJACENT_KINDS.some(([x, y]) => dims.has(x) && dims.has(y))) {
    const mdef = n.measurement ? MEASUREMENTS[n.measurement] : null;
    // %MVC is a target only for a measurement that can produce it (the EMG kinds, and other_myographic)
    if (b.dimension === 'normalized_activation' && mdef && mdef.dims && !mdef.dims.includes('normalized_activation')) {
      add(n.modality === 'neural' ? 'EMG_IS_NOT_NEURAL' : 'MEASUREMENT_UNIT_MISMATCH', 'params.toUnit', `${n.measurement} produces: ${mdef.dims.join(', ')}.`);
    } else add('QUANTITY_KIND_DIFFERS', 'params.toUnit', `${a.dimension} vs ${b.dimension}.`);
  }
  else add('UNIT_DIMENSION_MISMATCH', 'params.toUnit', `${a.dimension} vs ${b.dimension}.`);
  return null;
}

function opFrameTransform(link, recs, ctx, add) {
  const params = own(link, 'params');
  const srcN = recs[0].normalized;
  const src = srcN.frame;
  let tgt = null, crossScope = false, tgtN = null;
  const tf = own(params, 'toFrame');
  if (recs[1]) {
    if (!absent(tf)) add('PARAMS_INVALID', 'params.toFrame', 'Give either a second stream or params.toFrame, not both.');
    tgtN = recs[1].normalized;
    tgt = tgtN.frame;
    crossScope = !sameScope(srcN, tgtN);
  } else if (!absent(tf)) {
    const kind = own(tf, 'kind'), hand = own(tf, 'handedness');
    tgt = { id: idOrNull(own(tf, 'id')), kind: pick(kind, FRAME_KINDS), handedness: pick(hand, ['right', 'left']) };
    if (!isObj(tf) || Object.keys(tf).some(k => !['id', 'kind', 'handedness'].includes(k)) || (!absent(kind) && !tgt.kind) || (!absent(hand) && !tgt.handedness)) { add('FRAME_INVALID', 'params.toFrame'); return; }
  }
  if (!src.kind || !src.id) { add('FRAME_SOURCE_UNKNOWN', 'frame'); return; }
  if (src.kind === 'none') { add('FRAME_NOT_SPATIAL', 'frame.kind'); return; }
  if (!tgt) { add('FRAME_TARGET_MISSING', 'params.toFrame'); return; }
  if (!tgt.kind || !tgt.id) { add('FRAME_TARGET_UNKNOWN', 'params.toFrame'); return; }
  if (tgt.kind === 'none') { add('FRAME_NOT_SPATIAL', 'params.toFrame.kind'); return; }
  const srcDef = srcN.measurement ? MEASUREMENTS[srcN.measurement] : null;
  const tgtDef = tgtN && tgtN.measurement ? MEASUREMENTS[tgtN.measurement] : null;
  const cart = k => /^cartesian/u.test(k);
  const handed = k => cart(k) || k === 'sensor_local';
  const transform = own(params, 'transform');
  const type = own(transform, 'type');
  if (!absent(transform)) {
    if (!isObj(transform) || typeof type !== 'string') { add('PARAMS_INVALID', 'params.transform', 'transform must be {type, parameters?, notes?}.'); return; }
    if (!TRANSFORM_TYPES.includes(type)) { add('PARAMS_INVALID', 'params.transform.type', `type must be one of: ${TRANSFORM_TYPES.join(', ')}.`); return; }
    if (Object.keys(transform).some(k => !['type', 'parameters', 'notes'].includes(k))) { add('PARAMS_INVALID', 'params.transform', 'transform accepts type, parameters and notes.'); return; }
  }
  if (src.id === tgt.id && !crossScope) {
    if (!absent(transform)) { add('PARAMS_INVALID', 'params.transform', 'An identity frame link takes no transform.'); return; }
    if (src.kind !== tgt.kind || (src.handedness && tgt.handedness && src.handedness !== tgt.handedness)) add('FRAME_ID_KIND_CONFLICT', 'frame');
    else if (handed(src.kind) && (!src.handedness || !tgt.handedness)) add('FRAME_HANDEDNESS_UNDECLARED', 'frame.handedness');
    else add('FRAME_IDENTITY', 'frame');
    return;
  }
  if (src.id === tgt.id && crossScope) add('FRAME_ID_EQUAL_ACROSS_DATASETS', 'frame.id');
  const kinds = new Set([src.kind, tgt.kind]);
  const angleValued = n => n && n.measurement !== 'imu' && n.quantity.declaredDimensions.some(x => ANGLE_DIMS.includes(x));
  if (src.kind === 'joint_space' && tgt.kind === 'joint_space') { add('JOINT_SPACE_MAPPING_REQUIRES_MODEL', 'frame'); return; }
  if ((srcDef && srcDef.jointAngles) || (tgtDef && tgtDef.jointAngles) || kinds.has('joint_space') || angleValued(srcN) || angleValued(tgtN)) { add('JOINT_ANGLES_NOT_CARTESIAN', 'frame.kind'); return; }
  if ((srcDef && srcDef.image) || (tgtDef && tgtDef.image) || kinds.has('image_2d')) { add('CAMERA_CALIBRATION_REQUIRED', 'frame.kind'); return; }
  if (cart(src.kind) && cart(tgt.kind) && src.kind !== tgt.kind) { add('FRAME_DIMENSION_CHANGE', 'frame.kind'); return; }
  if (absent(transform)) { add('FRAME_TRANSFORM_UNDECLARED', 'params.transform'); return; }
  if ([src, tgt].some(f => handed(f.kind) && !f.handedness)) add('FRAME_HANDEDNESS_UNDECLARED', 'frame.handedness');
  if (src.handedness && tgt.handedness) {
    if (src.handedness !== tgt.handedness && !HANDEDNESS_CHANGING_TRANSFORMS.includes(type)) add('FRAME_HANDEDNESS_CHANGE_NOT_RIGID', 'params.transform.type');
    if (src.handedness === tgt.handedness && type === 'reflection') add('FRAME_REFLECTION_HANDEDNESS_CONFLICT', 'params.transform.type');
  }
  const ev = assessEvidence(link, ['frameTransform'], recs, ctx, add);
  if (!ev.accepted.has('frameTransform')) add('FRAME_TRANSFORM_SELF_DECLARED', 'params.transform');
}

function opClockMapping(link, recs, ctx, add) {
  const params = own(link, 'params');
  const a = recs[0].normalized;
  const from = a.clock.domain;
  const toDomainParam = own(params, 'toDomain');
  let to;
  if (recs[1]) {
    if (!absent(toDomainParam)) add('PARAMS_INVALID', 'params.toDomain', 'Give either a second stream or params.toDomain, not both.');
    to = recs[1].normalized.clock.domain;
  } else to = idOrNull(toDomainParam);
  if (!from) { add('CLOCK_MAPPING_SOURCE_UNKNOWN', 'clock.domain'); return; }
  if (!to) { add(recs[1] ? 'CLOCK_MAPPING_TARGET_UNKNOWN' : 'CLOCK_MAPPING_TARGET_MISSING', recs[1] ? 'clock.domain' : 'params.toDomain'); return; }
  // simulated time and recorded time are never mapped onto each other (both link forms)
  const srcLin = lineageOf(recs[0], ctx);
  lineageGate(recs[0], srcLin, add, ctx);
  // a recorded user of a clock domain: a valid stream of known, non-simulated origin with a fully known lineage
  const recordedUser = o => {
    if (o.status === 'invalid' || !o.normalized || !['measured', 'derived', 'inferred'].includes(o.normalized.origin)) return false;
    const l = lineageOf(o, ctx);
    return !l.simulated && !l.truncated && !l.cycle && l.unresolved.length === 0 && l.unknown.length === 0;
  };
  const usersOf = (domain, scopeOf) => [...ctx.byId.values()].filter(o => o.normalized && !recs.includes(o) && o.normalized.clock.domain === domain && sameScope(o.normalized, scopeOf));
  if (recs[1]) {
    const ol = lineageOf(recs[1], ctx);
    lineageGate(recs[1], ol, add, ctx);
    if (ol.simulated !== srcLin.simulated) { add('SIMULATED_MEASURED_TIME_PAIRING', 'clock.domain', undefined, recs.map(r => r.streamId)); return; }
    // two simulated streams: neither clock domain may be a recorded acquisition clock in its scope
    if (srcLin.simulated) {
      const recorded = uniqSorted(recs.flatMap(r => usersOf(r.normalized.clock.domain, r.normalized).filter(recordedUser).map(o => o.streamId)));
      if (recorded.length) { add('SIMULATED_MEASURED_TIME_PAIRING', 'clock.domain', `Recorded streams use these clock domains: ${listIds(recorded)}.`, recs.map(r => r.streamId)); return; }
    }
  } else {
    // one-stream form: a simulated clock is mapped only with the two-stream form; a recorded clock may not be mapped onto a domain that only simulations use in scope
    if (srcLin.simulated) { add('SIMULATED_MEASURED_TIME_PAIRING', 'clock.domain', 'A simulated stream\'s clock can be mapped only with the two-stream form, so the target\'s lineage can be checked.', [recs[0].streamId]); return; }
    if (to !== from) {
      const users = usersOf(to, a);
      const simOnly = o => Boolean(o.normalized.measurement && MEASUREMENTS[o.normalized.measurement].simulatedOnly);
      const sims = users.filter(o => o.normalized.origin === 'simulated' || simOnly(o) || lineageOf(o, ctx).simulated).map(o => o.streamId).sort();
      if (sims.length && !users.some(recordedUser)) { add('SIMULATED_MEASURED_TIME_PAIRING', 'clock.domain', `Only simulated streams use ${to} in this scope: ${listIds(sims)}.`, [recs[0].streamId, ...sims.slice(0, LIMITS.maxListedIds)]); return; }
    }
  }
  const identity = recs[1] ? sameClock(a, recs[1].normalized) : from === to;
  if (identity) {
    if (!absent(own(params, 'mapping'))) { add('PARAMS_INVALID', 'params.mapping', 'An identity clock link takes no mapping.'); return; }
    const tolI = own(params, 'toleranceS');
    if (!absent(tolI) && (!isFiniteNum(tolI) || tolI <= 0)) { add('TOLERANCE_INVALID', 'params.toleranceS'); return; }
    add('CLOCK_MAPPING_IDENTITY', 'clock.domain'); return;
  }
  if (recs[1] && from === to) add('CLOCK_DOMAIN_NAME_EQUAL_ACROSS_DATASETS', 'clock.domain', undefined, recs.map(r => r.streamId));
  const m = own(params, 'mapping');
  if (absent(m)) { add('CLOCK_MAPPING_UNDECLARED', 'params.mapping'); return; }
  const unc = own(m, 'uncertaintyS'), drift = own(m, 'driftPpm'), refT = own(m, 'referenceTime');
  if (!isObj(m) || Object.keys(m).some(k => !['offsetS', 'driftPpm', 'uncertaintyS', 'referenceTime'].includes(k)) || !isFiniteNum(own(m, 'offsetS')) || !isFiniteNum(drift)
    || !(absent(unc) || (isFiniteNum(unc) && unc >= 0)) || !(absent(refT) || isFiniteNum(refT))) { add('CLOCK_MAPPING_PARAMS_INVALID', 'params.mapping'); return; }
  const ev = assessEvidence(link, ['clockMapping'], recs, ctx, add);
  if (!ev.accepted.has('clockMapping')) add('CLOCK_MAPPING_SELF_DECLARED', 'params.mapping');
  // total uncertainty: mapping + each stream's own offset and drift over its interval
  const parts = [absent(unc) ? { value: null, lower: 0, why: 'mapping.uncertaintyS' } : { value: unc, lower: unc }];
  if (drift !== 0 && absent(refT)) parts.push({ value: null, lower: 0, why: 'mapping.referenceTime' });
  for (const r of recs) {
    const tm = recordTiming(r.normalized);
    parts.push(streamTimingUncertainty(r.normalized, tm ? [tm.start, tm.end] : null));
  }
  const tol = own(params, 'toleranceS');
  if (absent(tol)) {
    const unknown = parts.filter(p => p.value === null);
    if (unknown.length) add('ALIGNMENT_UNCERTAINTY_UNKNOWN', 'params.mapping', `Undeclared: ${uniqSorted(unknown.map(p => p.why)).join(', ')}.`);
  } else if (!isFiniteNum(tol) || tol <= 0) add('TOLERANCE_INVALID', 'params.toleranceS');
  else toleranceCheck(parts, tol, add, 'params.toleranceS', recs.map(r => r.streamId));
}

function opResample(link, recs, ctx, add, purpose) {
  const params = own(link, 'params');
  const n = recs[0].normalized;
  add('RESAMPLE_OWNED_BY_ADAPTER', '');
  const method = own(params, 'method'), step = own(params, 'stepS'), gap = own(params, 'maxGapS'), extra = own(params, 'extrapolate');
  if (absent(method)) add('RESAMPLE_METHOD_UNDECLARED', 'params.method');
  else if (!RESAMPLE_METHODS.includes(method)) add('RESAMPLE_METHOD_UNKNOWN', 'params.method');
  if (!isFiniteNum(step) || step <= 0) add('RESAMPLE_STEP_INVALID', 'params.stepS');
  if (!isFiniteNum(gap) || gap <= 0) add('GAP_RULE_UNDECLARED', 'params.maxGapS');
  if (!absent(extra) && typeof extra !== 'boolean') add('PARAMS_INVALID', 'params.extrapolate', 'extrapolate must be a boolean.');
  if (extra === true) add('EXTRAPOLATION_PROHIBITED', 'params.extrapolate');
  if (purpose === 'causal_analysis' && NON_CAUSAL_METHODS.includes(method)) add('RETROSPECTIVE_INTERPOLATION_NOT_CAUSAL', 'params.method');
  if (!n.clock.domain || !n.clock.unit) add('RESAMPLE_CLOCK_UNKNOWN', 'clock');
  else if (n.interval.start === null) add('RESAMPLE_INTERVAL_UNKNOWN', 'interval');
  if (isFiniteNum(step) && step > 0 && n.clock.rateHz !== null && 1 / step > n.clock.rateHz) add('UPSAMPLING_ADDS_NO_INFORMATION', 'params.stepS');
  dataPresence(recs, add, true);
  const w = parseWindow(own(params, 'window'));
  if (!w.ok) add('WINDOW_INVALID', 'params.window');
  else if (w.window && n.clock.domain && n.clock.unit && n.interval.start !== null) windowChecks(recs, w.window, add, 'EXTRAPOLATION_PROHIBITED');
}

function opCrossModal(link, recs, ctx, add) {
  const mapping = own(own(link, 'params'), 'mapping');
  if (typeof mapping === 'string' && IDENTITY_MAPPINGS.includes(mapping)) add('CROSS_MODAL_IDENTITY_PROHIBITED', 'params.mapping');
  const [a, b] = recs.map(r => r.normalized);
  if (a.modality === b.modality) { add('PARAMS_INVALID', 'streams', `Both streams are ${a.modality}; this is not a cross-modal mapping.`); return; }
  lateralityCheck(a, b, add, recs.map(r => r.streamId));
  add('CROSS_MODAL_MAPPING_REQUIRES_OWNER', '', `${a.modality} (${a.measurement}) to ${b.modality} (${b.measurement}).`, recs.map(r => r.streamId));
}

function opRelabel(link, recs, ctx, add) {
  const params = own(link, 'params');
  const n = recs[0].normalized;
  if (!isObj(params) || Object.keys(params).length === 0) { add('PARAMS_INVALID', 'params'); return; }
  let substantive = false;
  const fam = n.measurement ? MEASUREMENTS[n.measurement].family : undefined;
  const toMod = own(params, 'toModality'), toOrig = own(params, 'toOrigin'), toMeas = own(params, 'toMeasurement');
  if (!absent(toMod) && toMod !== n.modality) {
    substantive = true;
    add(toMod === 'neural' && fam === 'emg' ? 'EMG_IS_NOT_NEURAL' : toMod === 'neural' && n.modality === 'physiological_context' ? 'CONTEXT_SIGNAL_IS_NOT_NEURAL' : 'RELABEL_PROHIBITED', 'params.toModality');
  }
  if (!absent(toOrig) && toOrig !== n.origin) {
    substantive = true;
    add(n.origin === 'simulated' && toOrig === 'measured' ? 'SIMULATED_IS_NOT_RECORDED' : 'RELABEL_PROHIBITED', 'params.toOrigin');
  }
  if (!absent(toMeas) && toMeas !== n.measurement) {
    substantive = true;
    const target = typeof toMeas === 'string' && Object.prototype.hasOwnProperty.call(MEASUREMENTS, toMeas) ? MEASUREMENTS[toMeas] : null;
    const srcDef = n.measurement ? MEASUREMENTS[n.measurement] : null;
    if (n.measurement === 'simulated_muscle_activation' && target && target.family === 'emg') add('SIMULATED_ACTIVATION_IS_NOT_EMG', 'params.toMeasurement');
    else if (srcDef && srcDef.jointAngles && target && target.cartesian) add('GLOVE_ANGLES_NOT_CARTESIAN', 'params.toMeasurement');
    else if (target && target.modality === 'neural' && fam === 'emg') add('EMG_IS_NOT_NEURAL', 'params.toMeasurement');
    else add('RELABEL_PROHIBITED', 'params.toMeasurement');
  }
  if (!absent(own(params, 'toDivision')) && own(params, 'toDivision') !== (n.neural ? n.neural.division : null)) { substantive = true; add('RELABEL_PROHIBITED', 'params.toDivision'); }
  if (!absent(own(params, 'toSplit')) && own(params, 'toSplit') !== n.role.split) { substantive = true; add('RELABEL_PROHIBITED', 'params.toSplit'); }
  if (!absent(own(params, 'toSide')) && own(params, 'toSide') !== n.side) { substantive = true; add('RELABEL_PROHIBITED', 'params.toSide'); }
  const rnc = own(params, 'removeNegativeControl');
  if (!absent(rnc) && typeof rnc !== 'boolean') { substantive = true; add('PARAMS_INVALID', 'params.removeNegativeControl'); }
  if (rnc === true && n.role.negativeControl) { substantive = true; add('RELABEL_PROHIBITED', 'params.removeNegativeControl'); }
  if (!substantive) add('RELABEL_NOT_SUPPORTED', 'params');
}

function opDerivation(link, recs, ctx, add) {
  const [srcR, derR] = recs;
  const src = srcR.normalized, der = derR.normalized;
  if (!['derived', 'inferred', 'simulated'].includes(der.origin)) { add('DERIVATION_TARGET_ORIGIN_INVALID', 'origin', undefined, [der.streamId]); return; }
  if (!parentsOf(der).includes(src.streamId)) { add('DERIVATION_NOT_DECLARED', 'provenance.derivedFrom', undefined, [der.streamId]); return; }
  const srcLin = lineageOf(srcR, ctx), derLin = lineageOf(derR, ctx);
  lineageGate(srcR, srcLin, add, ctx);
  lineageGate(derR, derLin, add, ctx, { split: true, exclude: [srcR.streamId] });
  if (srcLin.simulated && der.origin !== 'simulated') {
    const derDef = der.measurement ? MEASUREMENTS[der.measurement] : null;
    add(derDef && derDef.family === 'emg' ? 'SIMULATED_ACTIVATION_IS_NOT_EMG' : 'SIMULATED_LINEAGE_MUST_STAY_SIMULATED', 'origin', undefined, [der.streamId]);
  }
  // the derived stream's whole lineage counts (its other parents too), not only this link's source
  if ((['heldout', 'test'].includes(src.role.split) || srcLin.heldout || derLin.heldout) && !['heldout', 'test'].includes(der.role.split)) add('HELDOUT_LINEAGE_RELABELLED', 'role.split', undefined, [der.streamId]);
  if ((src.role.negativeControl || srcLin.negativeControl || derLin.negativeControl) && !der.role.negativeControl) add('NEGATIVE_CONTROL_LINEAGE_LOST', 'role.negativeControl', undefined, [der.streamId]);
  // a body-level simulation (muscle, motion or mechanics) driven by measured motion or mechanics is a physics
  // simulation; any other cross-modal derivation, including one to a neural target, is a model claim
  const physicsDriven = der.origin === 'simulated' && ['motion', 'mechanics'].includes(src.modality) && src.origin === 'measured' && !srcLin.simulated
    && ['myographic', 'motion', 'mechanics'].includes(der.modality);
  if (der.modality !== src.modality && !physicsDriven) add('CROSS_MODAL_MAPPING_REQUIRES_OWNER', 'modality', `${src.modality} (${src.measurement}) to ${der.modality} (${der.measurement}).`, recs.map(r => r.streamId));
  lateralityCheck(src, der, add, recs.map(r => r.streamId));
  const ev = assessEvidence(link, ['derivation'], recs, ctx, add);
  if (!ev.accepted.has('derivation')) add('DERIVATION_SELF_DECLARED', 'provenance.derivedFrom', undefined, [der.streamId]);
  if (der.origin === 'simulated' && src.origin === 'measured') add('SIMULATION_DRIVEN_BY_MEASURED', 'origin', undefined, [der.streamId]);
}

const OP_IMPL = { pairing: opPairing, unpaired_exploration: opUnpaired, unit_conversion: opUnitConversion, frame_transform: opFrameTransform,
  clock_mapping: opClockMapping, resample_precondition: opResample, cross_modal_mapping: opCrossModal, relabel: opRelabel, derivation: opDerivation };
const EVIDENCE_OPS = new Set(['pairing', 'frame_transform', 'clock_mapping', 'derivation']);
const LINK_FIELDS = new Set(['linkId', 'op', 'streams', 'purpose', 'claims', 'evidence', 'params', 'controlComparison', 'notes']);

function evaluateLink(link, ctx) {
  const reasons = [];
  const add = (code, path, detail, streams) => reasons.push(reason(code, path, detail, streams && streams.length ? { streams: uniqSorted(streams) } : undefined));
  const linkId = own(link, 'linkId');
  const out = { linkId: typeof linkId === 'string' && ID_RE.test(linkId) ? linkId : null, op: null, streams: [], purpose: null };
  const finish = (extra = {}) => {
    const sorted = sortReasons(dedupeReasons(reasons));
    return { ...out, decision: decisionOf(sorted), reasons: sorted, owners: uniqSorted(sorted.filter(r => r.owner && SEVERITY_RANK[r.severity] > 0).map(r => r.owner)), ...extra, nonInference: NON_INFERENCE };
  };
  if (!out.linkId) add('LINK_ID_INVALID', 'linkId');
  for (const k of Object.keys(link)) if (!LINK_FIELDS.has(k)) add('PARAMS_INVALID', k, 'Unrecognised link field.');
  const op = own(link, 'op');
  if (typeof op !== 'string' || !Object.prototype.hasOwnProperty.call(OPS, op)) { add('LINK_OP_UNKNOWN', 'op'); return finish(); }
  out.op = op;
  const streams = own(link, 'streams');
  const [min, max] = OPS[op];
  if (!Array.isArray(streams) || streams.length < min || streams.length > max || !streams.every(s => typeof s === 'string')) { add('LINK_STREAM_COUNT', 'streams', `${op} takes ${min === max ? min : `${min}-${max}`} stream(s).`); return finish(); }
  out.streams = [...streams];
  if (new Set(streams).size !== streams.length) { add('LINK_SELF_REFERENCE', 'streams'); return finish(); }
  const params = own(link, 'params');
  if (!absent(params) && (!isObj(params) || Object.keys(params).some(k => !OP_PARAMS[op].includes(k)))) add('PARAMS_INVALID', 'params', `${op} accepts params: ${OP_PARAMS[op].join(', ') || 'none'}.`);
  const recs = [];
  for (const sid of streams) {
    const rec = ctx.byId.get(sid);
    if (!rec) { add('LINK_STREAM_UNKNOWN', 'streams', `Unknown: ${sid}.`); continue; }
    recs.push(rec);
  }
  const purpose = own(link, 'purpose');
  out.purpose = typeof purpose === 'string' ? purpose : null;
  if (recs.length !== streams.length) return finish();
  for (const rec of recs) {
    for (const r of rec.reasons) reasons.push({ ...r, inheritedFrom: rec.streamId });
    if (rec.status === 'invalid') add('DESCRIPTOR_INVALID', 'streams', undefined, [rec.streamId]);
  }
  const inputFingerprints = Object.fromEntries(recs.map(r => [r.streamId, r.fingerprint]));
  if (recs.some(r => r.status === 'invalid')) return finish({ inputFingerprints });

  // purpose
  if (absent(purpose)) add('PURPOSE_UNDECLARED', 'purpose');
  else if (!PURPOSES.includes(purpose)) add('PURPOSE_UNKNOWN', 'purpose');
  if (purpose === 'clinical') add('CLINICAL_USE_PROHIBITED', 'purpose');
  if (['training', 'evaluation', 'publication'].includes(purpose)) add('AUTHORIZATION_OUTSIDE_ENGINE', 'purpose');
  if (purpose === 'training') {
    const held = [];
    for (const r of recs) {
      const lin = lineageOf(r, ctx);
      lineageGate(r, lin, add, ctx, { split: true, exclude: recs.map(x => x.streamId) });
      if (['heldout', 'test'].includes(r.normalized.role.split) || lin.heldout) held.push(r.streamId);
    }
    if (held.length) add('HELDOUT_IN_TRAINING', 'role.split', undefined, held);
  }
  if (purpose === 'publication') {
    const bad = recs.filter(r => r.normalized.rights.status !== 'declared_open' || !r.normalized.rights.dataLicence || r.normalized.rights.redistribution !== 'allowed');
    if (bad.length) add('RIGHTS_NOT_ESTABLISHED_FOR_PUBLICATION', 'rights', undefined, bad.map(r => r.streamId));
  }
  if (purpose === 'causal_analysis') add('CAUSAL_CLAIM_REQUIRES_OWNER', 'purpose');
  if (recs.length > 1 && new Set(recs.map(r => r.normalized.role.split)).size > 1) add('SPLIT_ROLES_DIFFER', 'role.split', undefined, recs.map(r => r.streamId));
  if (op !== 'pairing') checkNoClaims(link, add, op);
  if (op !== 'pairing' && !absent(own(link, 'controlComparison'))) add('PARAMS_INVALID', 'controlComparison', 'controlComparison applies only to pairing links.');
  const ev = own(link, 'evidence');
  if (!EVIDENCE_OPS.has(op) && Array.isArray(ev) && ev.length) add('EVIDENCE_NOT_APPLICABLE', 'evidence');
  if (EVIDENCE_OPS.has(op)) scanEvidence(link, add);
  const extra = {};
  const result = OP_IMPL[op](link, recs, ctx, add, purpose);
  if (op === 'unit_conversion' && result) extra.conversion = result;
  extra.inputFingerprints = inputFingerprints;
  return finish(extra);
}

// ------------------------------------------------------------ coverage
const FOUR = ['neural', 'myographic', 'motion', 'mechanics'];
const UNCHECKED_CODES = new Set(['MEASUREMENT_OTHER', 'LABEL_MENTIONS_EMG', 'LABEL_MENTIONS_CONTEXT_SIGNAL']);
const UNDECLARED = '(undeclared)';

/** Per-dataset coverage of the four modalities and the four neural divisions.
 * A division or modality counts as measured only for a valid, measured stream with a
 * non-empty observation summary and no unchecked-measurement warning. Datasets are never
 * merged, and the sources, subjects and species behind each dataset are listed
 * (undeclared values are listed as "(undeclared)"). */
function coverageReport(records) {
  const byDataset = new Map();
  const excludedWithoutDataset = [];
  const get = id => {
    if (!byDataset.has(id)) {
      byDataset.set(id, { datasetId: id,
        neuralDivisions: Object.fromEntries(NEURAL_DIVISIONS.map(d => [d, { measured: false, origins: [], streams: [], uncheckedOrUnsummarisedMeasuredStreams: [] }])),
        neuralUnknownDivisionStreams: [],
        modalities: Object.fromEntries([...FOUR, 'physiological_context'].map(m => [m, { measuredStreamCount: 0, origins: [], measurements: [], streams: [] }])),
        excludedStreams: [], unsummarisedStreams: [], uncheckedStreams: [], sourceIds: [], subjects: [], species: [], taxonIds: [] });
    }
    return byDataset.get(id);
  };
  for (const rec of records) {
    const n = rec.normalized;
    if (!n || !n.dataset.id) { if (rec.streamId) excludedWithoutDataset.push(rec.streamId); continue; }
    const ds = get(n.dataset.id);
    if (rec.status === 'invalid') { ds.excludedStreams.push({ streamId: rec.streamId, why: 'invalid descriptor' }); continue; }
    if (n.observations && !hasObservations(n)) { ds.excludedStreams.push({ streamId: rec.streamId, why: 'no finite observations' }); continue; }
    const unsummarised = !n.observations;
    const unchecked = rec.reasons.some(r => UNCHECKED_CODES.has(r.code));
    if (unsummarised) ds.unsummarisedStreams.push(rec.streamId);
    if (unchecked) ds.uncheckedStreams.push(rec.streamId);
    ds.sourceIds.push(n.dataset.sourceId ?? UNDECLARED);
    if (n.origin !== 'simulated') {
      ds.subjects.push(n.subject.id ? `${n.subject.namespace ?? '?'}:${n.subject.id}` : UNDECLARED);
      ds.species.push(n.subject.species ? n.subject.species.trim().toLowerCase() : UNDECLARED);
      ds.taxonIds.push(n.subject.taxonId ?? UNDECLARED);
    }
    const counts = n.origin === 'measured' && !unsummarised && !unchecked;
    const m = ds.modalities[n.modality];
    m.origins.push(n.origin); m.measurements.push(n.measurement); m.streams.push(rec.streamId);
    if (counts) m.measuredStreamCount++;
    if (n.modality === 'neural') {
      if (!n.neural.division) ds.neuralUnknownDivisionStreams.push(rec.streamId);
      else {
        const d = ds.neuralDivisions[n.neural.division];
        d.origins.push(n.origin); d.streams.push(rec.streamId);
        if (counts) d.measured = true;
        else if (n.origin === 'measured') d.uncheckedOrUnsummarisedMeasuredStreams.push(rec.streamId);
      }
    }
  }
  const gapStatus = (origins, pending) => (pending ? 'only_unchecked_or_unsummarised_measured' : origins.length === 0 ? 'not_declared' : `only_${origins.join('_and_')}`);
  const datasets = [...byDataset.values()].sort((a, b) => cmp(a.datasetId, b.datasetId)).map(ds => {
    for (const d of Object.values(ds.neuralDivisions)) { d.origins = uniqSorted(d.origins); d.streams = uniqSorted(d.streams); d.uncheckedOrUnsummarisedMeasuredStreams = uniqSorted(d.uncheckedOrUnsummarisedMeasuredStreams); }
    for (const m of Object.values(ds.modalities)) { m.origins = uniqSorted(m.origins); m.measurements = uniqSorted(m.measurements); m.streams = uniqSorted(m.streams); }
    for (const k of ['neuralUnknownDivisionStreams', 'unsummarisedStreams', 'uncheckedStreams', 'sourceIds', 'subjects', 'species', 'taxonIds']) ds[k] = uniqSorted(ds[k]);
    ds.excludedStreams.sort((a, b) => cmp(a.streamId, b.streamId) || cmp(a.why, b.why));
    ds.neuralDivisionGaps = NEURAL_DIVISIONS.filter(k => !ds.neuralDivisions[k].measured)
      .map(k => ({ division: k, status: gapStatus(ds.neuralDivisions[k].origins, ds.neuralDivisions[k].uncheckedOrUnsummarisedMeasuredStreams.length > 0) }));
    ds.modalityGaps = FOUR.filter(k => ds.modalities[k].measuredStreamCount === 0)
      .map(k => ({ modality: k, status: gapStatus(ds.modalities[k].origins, ds.modalities[k].origins.includes('measured')) }));
    ds.heterogeneous = { sources: ds.sourceIds.length > 1, subjects: ds.subjects.length > 1, species: ds.species.length > 1 || ds.taxonIds.length > 1 };
    ds.contextSignalsCountedAsNeural = false;
    ds.divisionsFromOneSubjectEstablished = false;
    ds.wholeBodyNeuralCoverageEstablished = false;
    return ds;
  });
  return { datasets, excludedWithoutDataset: uniqSorted(excludedWithoutDataset), crossDatasetUnionComputed: false, wholeBodyNeuralCoverageEstablished: false,
    note: 'Division presence is not whole-body coverage and does not show one subject. Context signals (ECG, respiration) and EMG are not neural. Datasets are not merged.' };
}

// ------------------------------------------------------------- evaluate
/** Sort by an id field; ties (and missing ids, which sort last) are broken by canonical JSON. */
function sortById(list, key) {
  const canon = o => (o.c === null ? (o.c = canonicalJsonSafe(o.x)) : o.c);
  return list.map(x => ({ x, missing: x[key] === null || x[key] === undefined ? 1 : 0, id: x[key] ?? '', c: null }))
    .sort((a, b) => a.missing - b.missing || cmp(a.id, b.id) || cmp(canon(a), canon(b))).map(o => o.x);
}

function rejectedInput(code, path, detail) {
  const reasons = [reason(code, path, detail)];
  return { policy: POLICY, status: 'input_rejected', inputFingerprint: null, inputReasons: reasons, descriptors: [], links: [], registry: [],
    coverage: coverageReport([]), summary: { descriptors: { valid: 0, invalid: 0 }, links: Object.fromEntries(DECISIONS.map(d => [d, 0])) },
    nonInference: NON_INFERENCE, limitations: LIMITATIONS };
}

/** Read the envelope's own data properties without invoking accessors. Each array must be a
 * plain, hole-free array of data entries; the entries themselves are checked one by one later.
 * links and verifierRegistry may be absent or null. */
function readEnvelope(input) {
  if (input === null || typeof input !== 'object' || Array.isArray(input)) return { error: ['INPUT_NOT_OBJECT', '', 'Pass { descriptors, links, verifierRegistry }.'] };
  const proto = Object.getPrototypeOf(input);
  if (proto !== Object.prototype && proto !== null) return { error: ['INPUT_NOT_PLAIN_JSON', 'input', 'Only a plain object is accepted.'] };
  const env = { descriptors: undefined, links: [], verifierRegistry: [], extraKeys: [] };
  for (const k of Reflect.ownKeys(input)) {
    if (typeof k === 'symbol') return { error: ['INPUT_NOT_PLAIN_JSON', 'input', 'Symbol keys are not JSON.'] };
    if (UNSAFE_KEYS.has(k)) return { error: ['UNSAFE_KEY', `input.${k}`] };
    const d = Object.getOwnPropertyDescriptor(input, k);
    if (!('value' in d) || !d.enumerable) return { error: ['INPUT_NOT_PLAIN_JSON', `input.${safeKey(k)}`, 'Accessor or non-enumerable properties are not JSON.'] };
    if (d.value === undefined || (d.value === null && k !== 'descriptors')) continue;
    if (k === 'descriptors' || k === 'links' || k === 'verifierRegistry') env[k] = d.value;
    else env.extraKeys.push(k);
  }
  if (env.extraKeys.length > LIMITS.maxKeys) return { error: ['LIMIT_EXCEEDED', 'input', `The envelope holds more than ${LIMITS.maxKeys} keys.`] };
  if (env.extraKeys.some(k => k.length > LIMITS.maxString || CONTROL_RE.test(k))) return { error: ['INPUT_TEXT_INVALID', 'input', 'Envelope keys must be short plain text.'] };
  const lim = { descriptors: LIMITS.maxDescriptors, links: LIMITS.maxLinks, verifierRegistry: LIMITS.maxRegistry };
  for (const k of ['descriptors', 'links', 'verifierRegistry']) {
    const arr = env[k];
    if (!Array.isArray(arr) || Object.getPrototypeOf(arr) !== Array.prototype) return { error: ['INPUT_NOT_PLAIN_JSON', `input.${k}`, 'descriptors, links and verifierRegistry must be plain arrays.'] };
    const len = ownData(arr, 'length');
    if (!Number.isInteger(len) || len < 0) return { error: ['INPUT_NOT_PLAIN_JSON', `input.${k}`, 'Array length is invalid.'] };
    if (len > lim[k]) return { error: ['LIMIT_EXCEEDED', k, `At most ${lim[k]} ${k}.`] };
    for (const key of Reflect.ownKeys(arr)) {
      if (key === 'length') continue;
      if (typeof key === 'symbol' || !INDEX_RE.test(key) || Number(key) >= len) return { error: ['INPUT_NOT_PLAIN_JSON', `input.${k}`, 'Arrays may hold only index entries.'] };
    }
    const items = [];
    for (let i = 0; i < len; i++) {
      const d = Object.getOwnPropertyDescriptor(arr, String(i));
      if (!d || !('value' in d) || d.value === undefined) return { error: ['INPUT_NOT_PLAIN_JSON', `${k}[${i}]`, 'Arrays cannot contain holes, accessors or undefined.'] };
      items.push(d.value);
    }
    env[k] = items;
  }
  return { env };
}

/** Evaluate descriptors and proposed links. Input: { descriptors: [], links?: [], verifierRegistry?: [] }.
 * Never throws for malformed data; returns status 'input_rejected' when the envelope itself is unusable
 * or exceeds a limit. The result is independent of the order of descriptors, links and registry entries. */
export function evaluate(input) {
  try { return evaluateInner(input); } catch (e) {
    return rejectedInput('ENGINE_INTERNAL_ERROR', 'input', e && typeof e.name === 'string' ? `${e.name}.` : undefined);
  }
}

function evaluateInner(input) {
  let read;
  try { read = readEnvelope(input); } catch { return rejectedInput('INPUT_NOT_PLAIN_JSON', 'input', 'The input could not be inspected.'); }
  if (read.error) return rejectedInput(...read.error);
  const { descriptors, links, verifierRegistry: registryIn, extraKeys } = read.env;
  const inputReasons = extraKeys.length ? [reason('UNRECOGNISED_FIELD', 'input', `Ignored: ${listIds(extraKeys.sort().map(safeKey))}.`)] : [];

  // snapshot everything first under one shared text budget, before any hashing
  const budget = { remaining: LIMITS.maxTotalChars, exhausted: false };
  const descSnaps = [];
  for (const raw of descriptors) { descSnaps.push({ raw, snap: snapshotPlain(raw, 'descriptor', budget) }); if (budget.exhausted) break; }
  const regSnaps = [], linkSnaps = [];
  if (!budget.exhausted) for (const raw of registryIn) { regSnaps.push({ raw, snap: snapshotPlain(raw, 'registry', budget) }); if (budget.exhausted) break; }
  if (!budget.exhausted) for (const raw of links) { linkSnaps.push({ raw, snap: snapshotPlain(raw, 'link', budget) }); if (budget.exhausted) break; }
  if (budget.exhausted) return rejectedInput('LIMIT_EXCEEDED', 'input', `The input is larger than ${LIMITS.maxTotalChars} units of JSON (string and key characters, number digits, literals and structure).`);
  const edges = descSnaps.reduce((acc, { snap }) => { const df = snap.value && isObj(snap.value.provenance) ? snap.value.provenance.derivedFrom : null; return acc + (Array.isArray(df) ? df.length : 0); }, 0);
  if (edges > LIMITS.maxLineageEdges) return rejectedInput('LIMIT_EXCEEDED', 'descriptors', `The descriptors declare ${edges} derivedFrom entries; the limit is ${LIMITS.maxLineageEdges}.`);
  const validated = descSnaps.map(({ raw, snap }) => validateSnapshot(snap, raw));

  // descriptors (dedupe identical, reject conflicting)
  const groups = new Map();
  const orphans = [];
  for (const v of validated) {
    if (!v.streamId) { orphans.push(v); continue; }
    if (!groups.has(v.streamId)) groups.set(v.streamId, []);
    groups.get(v.streamId).push(v);
  }
  const records = [];
  for (const [sid, group] of groups) {
    const fps = new Set(group.map(g => g.fingerprint ?? 'unhashable'));
    if (fps.size > 1 || (fps.has('unhashable') && group.length > 1)) {
      records.push({ streamId: sid, status: 'invalid', fingerprint: null, normalized: null, variants: uniqSorted(group.map(g => g.fingerprint ?? 'unhashable')),
        reasons: [reason('CONFLICTING_DESCRIPTOR', 'streamId', `${group.length} descriptors use ${sid}.`)] });
    } else {
      const rec = { ...group[0], validationStatus: group[0].status };
      if (group.length > 1) rec.reasons = sortReasons([...rec.reasons, reason('DUPLICATE_DESCRIPTOR_IDENTICAL', 'streamId', `${group.length} copies.`)]);
      records.push(rec);
    }
  }
  const byId = new Map(records.map(r => [r.streamId, r]));
  const ctx = { byId, registry: new Map(), lineage: new Map() };
  // cross-descriptor lineage rules: values computed from simulations stay simulated; oversized or cyclic lineage is unknown
  for (const rec of records) {
    if (rec.status === 'invalid' || !rec.normalized) continue;
    const n = rec.normalized;
    if (parentsOf(n).length === 0) continue;
    const lin = lineageOf(rec, ctx);
    const extra = [];
    if (lin.truncated) extra.push(reason('LINEAGE_TRUNCATED', 'provenance'));
    if (lin.cycle) { rec.lineageCycle = true; extra.push(reason('LINEAGE_CYCLE', 'provenance.derivedFrom')); }
    if (lin.simulated && n.origin !== 'simulated') {
      const def = n.measurement ? MEASUREMENTS[n.measurement] : null;
      const sims = lin.ancestors.filter(id => byId.get(id).normalized.origin === 'simulated');
      extra.push(reason(def && def.family === 'emg' ? 'SIMULATED_ACTIVATION_IS_NOT_EMG' : 'SIMULATED_LINEAGE_MUST_STAY_SIMULATED', 'provenance.derivedFrom', `Simulated ancestor: ${listIds(sims)}.`));
    }
    if (extra.length) {
      rec.reasons = sortReasons(dedupeReasons([...rec.reasons, ...extra]));
      rec.status = decisionOf(rec.reasons) === 'rejected' ? 'invalid' : 'valid';
    }
  }

  // registry (caller-supplied; the engine checks shape and bindings, never qualifies verifiers).
  // Entries are grouped by their raw ref first, so a malformed variant invalidates the whole group.
  const registry = ctx.registry;
  const registryReport = [];
  const regGroups = new Map();
  regSnaps.forEach(({ raw, snap }, i) => {
    const refRaw = snap.value ? own(snap.value, 'ref') : ownData(raw, 'ref');
    const key = typeof refRaw === 'string' && ID_RE.test(refRaw) ? refRaw : null;
    if (key === null) {
      const c = snap.value ? canonicalJsonSafe(snap.value) : 'unhashable';
      registryReport.push({ ref: null, status: 'invalid', entryFingerprint: c === 'unhashable' ? null : sha256Hex(c), reasons: [reason('REGISTRY_ENTRY_INVALID', 'verifierRegistry')] });
      return;
    }
    if (!regGroups.has(key)) regGroups.set(key, []);
    regGroups.get(key).push(snap);
  });
  for (const [ref, group] of regGroups) {
    const valid = group.every(s => !s.problems.length && validRegistryEntry(s.value));
    if (!valid || new Set(group.map(s => canonicalJsonSafe(s.value))).size > 1) {
      registryReport.push({ ref, status: 'invalid', reasons: [reason('REGISTRY_ENTRY_INVALID', 'verifierRegistry', group.length > 1 ? `Conflicting or malformed entries for ${ref}.` : undefined)] });
      continue;
    }
    const e = group[0].value;
    registry.set(ref, { ref, sha256: e.sha256, verifierId: e.verifierId, claims: uniqSorted(e.claims), streams: uniqSorted(e.streams), fingerprints: { ...e.fingerprints }, operationFingerprint: e.operationFingerprint });
    registryReport.push({ ref, status: 'loaded', claims: uniqSorted(e.claims), streams: uniqSorted(e.streams), verifierId: e.verifierId, reasons: [] });
  }

  // every link inherits all reasons of every stream it names: bound that product before evaluating
  let inherited = 0;
  for (const { snap } of linkSnaps) {
    const l = snap.value;
    if (!isObj(l)) continue;
    const op = own(l, 'op'), st = own(l, 'streams');
    if (typeof op !== 'string' || !Object.prototype.hasOwnProperty.call(OPS, op) || !Array.isArray(st) || st.length < OPS[op][0] || st.length > OPS[op][1]
      || !st.every(s => typeof s === 'string') || new Set(st).size !== st.length) continue;
    const rs = st.map(s => byId.get(s));
    if (rs.every(Boolean)) for (const r of rs) inherited += r.reasons.length;
  }
  if (inherited > LIMITS.maxInheritedReasons) return rejectedInput('LIMIT_EXCEEDED', 'links', `The links would inherit ${inherited} descriptor reasons; the limit is ${LIMITS.maxInheritedReasons}. Evaluate fewer links or streams at a time.`);

  // links: group by valid linkId first (so a duplicate id rejects every member), then evaluate
  const linkGroups = new Map();
  const singles = [];
  for (const { raw, snap } of linkSnaps) {
    const lidRaw = snap.value ? own(snap.value, 'linkId') : ownData(raw, 'linkId');
    if (typeof lidRaw === 'string' && ID_RE.test(lidRaw)) {
      if (!linkGroups.has(lidRaw)) linkGroups.set(lidRaw, []);
      linkGroups.get(lidRaw).push(snap);
    } else singles.push(snap);
  }
  const linkResults = [];
  const resultFor = (snap, id) => {
    if (snap.problems.length || !isObj(snap.value)) {
      const probs = snap.problems.length ? snap.problems : [{ code: 'INPUT_NOT_OBJECT', path: 'link' }];
      const reasons = sortReasons(dedupeReasons([...(id ? [] : [reason('LINK_ID_INVALID', 'linkId')]), ...probs.map(p => reason(p.code, p.path, p.detail))]));
      return { linkId: id, op: null, streams: [], purpose: null, decision: 'rejected', reasons, owners: [], nonInference: NON_INFERENCE };
    }
    return evaluateLink(snap.value, ctx);
  };
  for (const [key, group] of linkGroups) {
    if (group.length > 1) {
      linkResults.push({ linkId: key, op: null, streams: [], purpose: null, decision: 'rejected', variants: group.length,
        reasons: [reason('DUPLICATE_LINK_ID', 'linkId', `${group.length} links use ${key}.`)], owners: [], nonInference: NON_INFERENCE });
    } else linkResults.push(resultFor(group[0], key));
  }
  for (const snap of singles) linkResults.push(resultFor(snap, null));

  const descriptorOut = sortById([...records, ...orphans], 'streamId').map(r => ({
    streamId: r.streamId, datasetId: r.normalized ? r.normalized.dataset.id : null, status: r.status, fingerprint: r.fingerprint,
    ...(r.variants ? { variants: r.variants } : {}), reasons: r.reasons, normalized: r.normalized,
  }));
  const linksOut = sortById(linkResults, 'linkId');
  const registryOut = sortById(registryReport, 'ref');
  const summary = { descriptors: { valid: descriptorOut.filter(d => d.status === 'valid').length, invalid: descriptorOut.filter(d => d.status === 'invalid').length },
    links: Object.fromEntries(DECISIONS.map(d => [d, linksOut.filter(l => l.decision === d).length])) };
  const itemHash = s => (s.value ? sha256Hex(canonicalJsonSafe(s.value)) : 'unhashable');
  const inputFingerprint = sha256Hex(canonicalJson({ policy: POLICY,
    descriptors: validated.map(v => v.fingerprint ?? 'unhashable').sort(),
    links: linkSnaps.map(x => itemHash(x.snap)).sort(),
    registry: regSnaps.map(x => itemHash(x.snap)).sort() }));
  return { policy: POLICY, status: 'evaluated', inputFingerprint, inputReasons, descriptors: descriptorOut, links: linksOut, registry: registryOut,
    coverage: coverageReport(records), summary, nonInference: NON_INFERENCE, limitations: LIMITATIONS };
}

/** Differences between two descriptors (for example, before and after a metadata
 * update). Any difference changes the fingerprint and invalidates earlier decisions.
 * Each input is snapshotted once; validation and the diff use the same snapshot. */
export function compareDescriptors(before, after) {
  const sa = snapshotPlain(before, 'before'), sb = snapshotPlain(after, 'after');
  const a = validateSnapshot(sa, before), b = validateSnapshot(sb, after);
  const changes = [];
  let truncated = false;
  const diff = (x, y, path) => {
    if (changes.length >= LIMITS.maxDiffEntries) { truncated = true; return; }
    if (isObj(x) && isObj(y)) {
      for (const k of uniqSorted([...Object.keys(x), ...Object.keys(y)])) diff(own(x, k), own(y, k), path ? `${path}.${k}` : k);
      return;
    }
    if (Array.isArray(x) && Array.isArray(y) && x.length === y.length) { x.forEach((v, i) => diff(v, y[i], `${path}[${i}]`)); return; }
    const cx = x === undefined ? undefined : canonicalJsonSafe(x), cy = y === undefined ? undefined : canonicalJsonSafe(y);
    if (cx !== cy) changes.push({ path, before: x === undefined ? null : x, after: y === undefined ? null : y, ...(x === undefined ? { added: true } : y === undefined ? { removed: true } : {}) });
  };
  const comparable = !sa.problems.length && !sb.problems.length && isObj(sa.value) && isObj(sb.value);
  if (comparable) diff(sa.value, sb.value, '');
  const ordA = a.normalized && a.normalized.channels.order, ordB = b.normalized && b.normalized.channels.order;
  const sameSet = Boolean(ordA && ordB && ordA.length === ordB.length && uniqSorted(ordA).join('\u0000') === uniqSorted(ordB).join('\u0000'));
  const identical = comparable && a.fingerprint !== null && a.fingerprint === b.fingerprint;
  return {
    streamIds: [a.streamId, b.streamId], fingerprints: [a.fingerprint, b.fingerprint],
    identical, comparable,
    channelOrderChanged: sameSet && ordA.join('\u0000') !== ordB.join('\u0000'),
    channelSetChanged: Boolean(ordA && ordB && !sameSet),
    decisionsBoundToEarlierFingerprintInvalidated: !identical,
    changes, truncated,
    statusChange: [a.status, b.status],
  };
}
