/** Offline replay of the frozen ds006840 right-hand conditional palm regression. */
const MODEL_KIND = 'offline_scalp_eeg_palm_ridge';
const MODEL_ID = 'iackd-r1-conditional-palm-availability-grid-v1';
const ANALYSIS = 'iackd_r1_conditional_palm_availability_grid';
const DESIGN_SHA256 = 'ccaff2ccda3a32ba182c78c0a111fd36295f5bb8b2b400acc46faa1436433fc9';
const SOURCE_URL = 'https://doi.org/10.18112/openneuro.ds006840.v1.0.0';
const RELEASE_COMMIT = '0c701aadfa562b8662e76ca0dd6831788e02e8b6';
const TIMEBASE = 'IACKD event 14 · cue disappearance';
const FRAME = 'Leap Motion device frame, right positive';
const CHANNELS = ['C3', 'Cz', 'C4'];
const RELEASE_CHANNEL_COLUMNS = [11, 12, 13];
const PALM_ANCHOR = 'first_finite_palm_at_or_after_native_cue';
const OFFSETS = Object.freeze([200, 250, 300, 350, 400, 450, 500, 550, 600]);
const STEP_MS = 10;
const TOLERANCE_MS = 0.01;
const NOMINAL_LEAD_MS = 100;
const PALM_LAGS = [100, 150];
const EEG_BINS = [[-190, -140], [-140, -90]];
const FEATURE_ORDER = ['palm_position_mm', 'palm_velocity_mm_s',
  'eeg_older_C3_uv', 'eeg_older_Cz_uv', 'eeg_older_C4_uv',
  'eeg_newer_C3_uv', 'eeg_newer_Cz_uv', 'eeg_newer_C4_uv'];
const MODEL_FEATURES = {
  time: [],
  time_eeg: [2, 3, 4, 5, 6, 7],
  time_palm: [0, 1],
  time_palm_eeg: [0, 1, 2, 3, 4, 5, 6, 7],
};
const TRAIN = ['sub-07', 'sub-08', 'sub-09'];
const DEV = ['sub-10', 'sub-11', 'sub-12'];
const SCOPE = 'offline_recorded_regression';
const MAX_PACKETS = 64;
const LIMITATIONS = Object.freeze([
  'The 100 ms lead comes from the archived sample clock. The released EEG and palm recordings were processed retrospectively.',
  'Palm position comes from optical tracking on the released device axis. It is an estimate of recorded movement.',
  'These errors describe the matched rows in the selected files. The study reports the participant-balanced comparison separately.',
]);

class ReplayInputError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

function requireInput(condition, code, message) {
  if (!condition) throw new ReplayInputError(code, message);
}

const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const isSha256 = value => typeof value === 'string' && /^[0-9a-f]{64}$/u.test(value);
const nonnegativeInteger = value => Number.isSafeInteger(value) && value >= 0;
const sameArray = (actual, expected) => Array.isArray(actual) && actual.length === expected.length
  && expected.every((value, index) => actual[index] === value);
const finiteArray = (actual, expectedLength) => Array.isArray(actual) && actual.length === expectedLength
  && Array.from(actual).every(Number.isFinite);
const assetMapMatches = (map, participants) => isObject(map)
  && Object.keys(map).length === participants.length && participants.every(id => isSha256(map[id]));

/** Validate the precise exported model contract and return the state unchanged. */
export function validateEegReplayModel(state) {
  requireInput(isObject(state) && state.schema_version === 1 && state.kind === MODEL_KIND
    && state.design_sha256 === DESIGN_SHA256 && state.analysis === ANALYSIS && state.model_id === MODEL_ID
    && isSha256(state.source_sha256) && sameArray(state.train_participants, TRAIN),
  'model_identity', 'The model state must identify the frozen ds006840 conditional palm study.');
  requireInput(assetMapMatches(state.train_asset_sha256, TRAIN) && assetMapMatches(state.dev_asset_sha256, DEV),
    'model_asset_identity', 'The model state needs the study’s original participant file hashes.');
  const { clock, features, target, models } = state;
  requireInput(clock?.step_ms === STEP_MS && clock.tolerance_ms === TOLERANCE_MS
    && sameArray(clock.score_offsets_ms, OFFSETS) && clock.anchor === PALM_ANCHOR,
  'model_clock', 'The model state must use the frozen 10 ms grid and nine target offsets.');
  requireInput(sameArray(features?.channels, CHANNELS) && sameArray(features.palm_lags_ms, PALM_LAGS)
    && Array.isArray(features.eeg_bins_ms) && features.eeg_bins_ms.length === EEG_BINS.length
    && EEG_BINS.every((bin, index) => sameArray(features.eeg_bins_ms[index], bin))
    && sameArray(features.order, FEATURE_ORDER),
  'model_features', 'The model state has a different feature order or sample window.');
  requireInput(target?.field === 'x_mm' && target.units === 'mm'
    && target.axis === 'device_horizontal_positive_right',
  'model_target', 'The model state must estimate the horizontal palm coordinate in millimetres.');
  requireInput(isObject(models) && Number.isFinite(state.global_mean_mm),
    'model_parameters', 'The model state needs the frozen regression parameters.');
  for (const [name, indices] of Object.entries(MODEL_FEATURES)) {
    const model = models[name];
    requireInput(sameArray(model?.feature_indices, indices)
      && finiteArray(model.center, indices.length) && finiteArray(model.scale, indices.length)
      && model.scale.every(value => value > 0) && finiteArray(model.coefficients, indices.length)
      && finiteArray(model.intercepts_mm, OFFSETS.length),
    'model_parameters', `The ${name} regression has an invalid feature index, scale or parameter.`);
  }
  return state;
}

function readTrialIdentity(packet, archiveRun = '01') {
  requireInput(packet?.schemaVersion === 1 && isObject(packet.dataset)
    && Array.isArray(packet.streams),
  'packet_format', 'Open a recording in the companion’s packet format.');
  const { dataset, streams } = packet;
  const { provenance, subjectId, recordingId } = dataset;
  requireInput(typeof subjectId === 'string' && /^sub-[0-9]{2}$/u.test(subjectId),
    'subject_identity', 'The recording needs its ds006840 participant ID.');
  const parentId = `${subjectId}_task-ihc_acq-right_run-${archiveRun}`;
  const sourcePath = `derivatives/movement-execution/${subjectId}/ihc/${subjectId}_task-ihc_run-${archiveRun}_eeg_leap_R${Number(archiveRun)}.mat`;
  requireInput(dataset.sourceUrl === SOURCE_URL && dataset.organism === 'Homo sapiens'
    && dataset.origin === 'derived' && provenance?.datasetVersion === '1.0.0'
    && provenance.releaseCommit === RELEASE_COMMIT && provenance.derivativePath === sourcePath
    && isSha256(provenance.derivativeSha256) && provenance.archiveHand === 'right'
    && provenance.archiveRun === archiveRun && provenance.parentRecordingId === parentId,
  'release_identity', 'Use the released ds006840 v1.0.0 right-hand movement-execution derivative for this run.');
  const trial = provenance.trial;
  requireInput(nonnegativeInteger(trial?.outIndexZeroBased) && trial.outIndexZeroBased < Number.MAX_SAFE_INTEGER
    && nonnegativeInteger(trial.eeg_seg_idx) && trial.eeg_seg_idx > 0 && nonnegativeInteger(trial.lm_trial),
  'trial_identity', 'The packet needs its OUT row, EEG segment and Leap Motion trial IDs.');
  const trialRecordingId = `${parentId} · derivative trial ${trial.outIndexZeroBased + 1} (EEG segment ${trial.eeg_seg_idx}, Leap trial ${trial.lm_trial})`;
  requireInput(recordingId === trialRecordingId, 'trial_identity',
    'The recording ID must agree with its declared source trial.');
  requireInput(dataset.timebase === TIMEBASE, 'timebase',
    'Use time relative to ds006840 EEG event 14, when the preparation cue disappears.');
  return { streams, subjectId, recordingId, provenance, trial: {
    outIndexZeroBased: trial.outIndexZeroBased, eeg_seg_idx: trial.eeg_seg_idx, lm_trial: trial.lm_trial,
  } };
}

function readSourceStreams(streams, {columns = RELEASE_CHANNEL_COLUMNS, requireNamedChannel = false} = {}) {
  const eeg = CHANNELS.map((channel, index) => {
    const id = `eeg-${channel.toLowerCase()}`;
    const bindings = streams.filter(stream => stream?.id === id || stream?.provenance?.channel === channel);
    const stream = bindings[0];
    requireInput(bindings.length === 1 && stream?.provenance?.sourceField === 'OUT.EEG'
      && (stream.provenance.channel === channel || (!requireNamedChannel && stream.provenance.channel === undefined))
      && stream.provenance.sourceColumnZeroBased === columns[index]
      && stream.modality === 'neural' && stream.region === 'brain' && stream.signalType === 'EEG'
      && stream.origin === 'derived' && stream.unit === 'µV' && stream.rateHz === 100,
    'eeg_mapping', `${channel} needs its named 100 Hz OUT.EEG scalp channel in µV.`);
    return stream;
  });
  const palms = streams.filter(stream => stream?.provenance?.sourceField === 'OUT.x_mm');
  const palm = palms[0];
  requireInput(palms.length === 1 && palm.modality === 'displacement' && palm.origin === 'derived'
    && palm.unit === 'mm' && palm.rateHz === 100 && palm.frame === FRAME,
  'palm_mapping', 'Use the optical palm coordinate OUT.x_mm in millimetres, with right positive on the Leap Motion device axis.');
  requireInput(new Set([...eeg, palm]).size === 4, 'stream_mapping',
    'Use a separate stream for each EEG channel and the palm coordinate.');
  return { eeg, palm };
}

function readSourceSamples(provenance, streams) {
  const { clock, selection } = provenance;
  const times = clock?.timestampMilliseconds;
  requireInput(clock?.sourceField === 'OUT.t_ms' && clock.sourceUnit === 'ms'
    && clock.packetUnit === 's' && clock.sourceStepMs === STEP_MS
    && Array.isArray(times) && times.length > 0 && finiteArray(times, times.length),
  'source_clock', 'The packet needs the original OUT.t_ms timestamps on the 10 ms source grid.');
  const start = selection?.rowStartZeroBased;
  const end = selection?.rowEndExclusive;
  const sourceCount = selection?.sourceTrialRowCount;
  requireInput(nonnegativeInteger(start) && nonnegativeInteger(end)
    && nonnegativeInteger(sourceCount) && end <= sourceCount && end - start === times.length,
  'source_selection', 'The packet’s row range must agree with the declared source trial and sample count.');
  for (const stream of streams) {
    requireInput(Array.isArray(stream.t) && Array.isArray(stream.values)
      && stream.t.length === times.length && stream.values.length === times.length
      && times.every((time, index) => stream.t[index] === time / 1000)
      && Array.from(stream.values).every(value => value === null || Number.isFinite(value)),
    'stream_clock', 'Every EEG and palm stream needs the same original sample times, with missing values marked null.');
  }
  const coverage = start === 0 && end === sourceCount ? 'full_source_trial' : 'source_window';
  return { times, start, coverage };
}

function readSourceClock(provenance, streams) {
  const source = readSourceSamples(provenance, streams);
  const { times, start, coverage } = source;
  const { clock } = provenance;
  requireInput(times.every((time, index) => index === 0 || (time > times[index - 1]
    && Math.abs(time - times[index - 1] - STEP_MS) <= 2 * TOLERANCE_MS + 1e-10)),
  'off_lattice', 'The original sample timestamps must advance by one native step per row.');
  const anchorIndex = times.findIndex(time => time >= 0);
  if (anchorIndex < 0) return { coverage, code: 'anchor_outside_window',
    message: 'This window ends before the first native row at or after the cue.' };
  const anchorMs = times[anchorIndex];
  if (anchorIndex === 0 && anchorMs >= STEP_MS && start > 0 && clock.previousTimestampMilliseconds === undefined) {
    return { coverage, code: 'anchor_outside_window',
      message: 'This window starts after the native cue row. Include the cue and the preceding source timestamp.' };
  }
  requireInput(anchorMs < STEP_MS, 'anchor_phase',
    'The first native row at or after the cue must fall within the next 10 ms.');
  if (anchorIndex === 0 && clock.previousTimestampMilliseconds === undefined) {
    return { coverage, code: 'anchor_predecessor_missing',
      message: 'This window starts at or after the cue. Include the preceding source timestamp to verify the first native row.' };
  }
  const previous = anchorIndex > 0 ? times[anchorIndex - 1] : clock.previousTimestampMilliseconds;
  requireInput(Number.isFinite(previous) && previous < 0 && (anchorIndex > 0 || start > 0)
    && Math.abs(previous - (anchorMs - STEP_MS)) <= TOLERANCE_MS,
  'anchor_predecessor', 'The preceding native row must be before the cue and on the same 10 ms lattice.');
  for (const [index, time] of times.entries()) {
    requireInput(Math.abs(time - (anchorMs + (index - anchorIndex) * STEP_MS)) <= TOLERANCE_MS,
    'off_lattice', 'A recorded grid row is missing, out of order or outside the allowed timestamp tolerance.');
  }
  return { times, start, coverage, anchorIndex, anchorMs };
}

function missing(code, signal, relativeOffsetMs, message) {
  return { code, signal, relativeOffsetMs, message };
}

function emptyRow(offsetMs, nominalTimeMs, missingReasons) {
  return { offsetMs, nominalTimeMs, timeMs: null, sourceRowIndex: null, estimateMm: null,
    baselineMm: null, targetMm: null, errorMm: null, baselineErrorMm: null,
    inputThroughMs: null, sampleLeadMs: null, predictionsMm: null, missingReasons };
}

function sampleAt(stream, signal, clock, offsetMs, missingReasons) {
  const index = clock.referenceIndex + offsetMs / STEP_MS;
  if (index < 0 || index >= clock.times.length) {
    missingReasons.push(missing('outside_source_window', signal, offsetMs,
      `${signal} is outside the selected source rows at ${offsetMs} ms.`));
    return null;
  }
  const value = stream.values[index];
  if (value === null) missingReasons.push(missing('source_value_missing', signal, offsetMs,
    `${signal} has a missing source value at ${offsetMs} ms.`));
  return value;
}

function standardisedFeature(model, value, index) {
  return (value - model.center[index]) / model.scale[index];
}

function fitPrediction(model, features, offsetIndex) {
  let predicted = model.intercepts_mm[offsetIndex];
  for (const [index, featureIndex] of model.feature_indices.entries()) {
    const standardised = standardisedFeature(model, features[featureIndex], index);
    predicted += model.coefficients[index] * standardised;
  }
  return predicted;
}

function extractReplayRow(clock, eeg, palm, offsetMs) {
  const row = emptyRow(offsetMs, clock.referenceMs + offsetMs, []);
  const targetIndex = clock.referenceIndex + offsetMs / STEP_MS;
  if (targetIndex < clock.times.length) {
    row.timeMs = clock.times[targetIndex];
    row.sourceRowIndex = clock.start + targetIndex;
  }
  row.targetMm = sampleAt(palm, 'Palm target', clock, offsetMs, row.missingReasons);
  const inputIssues = [];
  const [position, olderPosition] = PALM_LAGS.map(lag =>
    sampleAt(palm, 'Past palm', clock, offsetMs - lag, inputIssues));
  const eegMeans = [];
  for (const [from, to] of EEG_BINS) {
    for (const [index, stream] of eeg.entries()) {
      let sum = 0;
      for (let lag = from; lag < to; lag += STEP_MS) {
        sum += sampleAt(stream, CHANNELS[index], clock, offsetMs + lag, inputIssues) ?? 0;
      }
      eegMeans.push(sum / ((to - from) / STEP_MS));
    }
  }
  row.missingReasons.push(...inputIssues);
  if (inputIssues.length > 0) return { row, features: null };
  row.inputThroughMs = clock.times[clock.referenceIndex + (offsetMs - NOMINAL_LEAD_MS) / STEP_MS];
  if (row.timeMs !== null) row.sampleLeadMs = row.timeMs - row.inputThroughMs;

  const velocity = (position - olderPosition) / 0.05;
  return { row, features: [position, velocity, ...eegMeans] };
}

function scoreRow(state, clock, eeg, palm, offsetIndex) {
  const { row, features } = extractReplayRow(clock, eeg, palm, state.clock.score_offsets_ms[offsetIndex]);
  if (features === null) return row;
  const [position, velocity] = features;
  const predictions = Object.fromEntries(Object.keys(MODEL_FEATURES).map(name =>
    [name, fitPrediction(state.models[name], features, offsetIndex)]));
  predictions.global_mean = state.global_mean_mm;
  predictions.persistence = position;
  predictions.velocity_extrapolation = position + velocity * 0.1;
  if (!Object.values(predictions).every(Number.isFinite)) {
    row.missingReasons.push(missing('nonfinite_estimate', 'Regression', row.offsetMs,
      'These source values exceed the numeric range of the regression.'));
    return row;
  }
  row.predictionsMm = predictions;
  row.estimateMm = predictions.time_palm_eeg;
  row.baselineMm = predictions.time_palm;
  if (row.targetMm !== null) {
    const error = row.estimateMm - row.targetMm;
    const baselineError = row.baselineMm - row.targetMm;
    if (Number.isFinite(error) && Number.isFinite(baselineError)) {
      row.errorMm = error;
      row.baselineErrorMm = baselineError;
    } else {
      row.missingReasons.push(missing('nonfinite_error', 'Regression', row.offsetMs,
        'The estimated and recorded positions exceed the numeric range of the error calculation.'));
    }
  }
  return row;
}

function roleOf(subjectId) {
  if (TRAIN.includes(subjectId)) return 'TRAIN';
  if (DEV.includes(subjectId)) return 'DEV';
  return 'outside_cohort';
}

function inspectTrial(state, packet) {
  const identity = readTrialIdentity(packet);
  const { subjectId, provenance } = identity;
  const assetSha256 = state.train_asset_sha256?.[subjectId] ?? state.dev_asset_sha256?.[subjectId];
  requireInput(assetSha256 === undefined || assetSha256 === provenance.derivativeSha256,
    'study_asset_identity', 'This run’s source file hash does not match the file in the frozen study.');
  const { eeg, palm } = readSourceStreams(identity.streams);
  const clock = readSourceClock(provenance, [...eeg, palm]);
  return { identity, eeg, palm, clock, sourceAssetMatchesStudy: assetSha256 !== undefined };
}

function trialKey(identity, field) {
  return `${identity.subjectId}/${identity.trial[field]}`;
}

function useReplayReference(clock, palm) {
  if (clock.code !== undefined) return clock;
  const referenceIndex = palm.values.findIndex((value, index) => index >= clock.anchorIndex && value !== null);
  if (referenceIndex < 0) return { ...clock, code: 'palm_timing_origin_missing',
    message: 'The model needs a recorded palm position at or after the cue to start its clock.' };
  return { ...clock, referenceIndex, referenceMs: clock.times[referenceIndex] };
}

function replayTrial(state, { identity, eeg, palm, clock, sourceAssetMatchesStudy }) {
  const { subjectId, recordingId, trial } = identity;
  const reference = useReplayReference(clock, palm);
  const offsets = state.clock.score_offsets_ms;
  const rows = reference.code === undefined
    ? offsets.map((_, index) => scoreRow(state, reference, eeg, palm, index))
    : offsets.map(offsetMs => emptyRow(offsetMs, null,
      [missing(reference.code, 'Task clock', null, reference.message)]));
  const matched = rows.filter(row => row.errorMm !== null).length;
  return { subjectId, recordingId, trial, cohortRole: roleOf(subjectId), anchorMs: clock.anchorMs ?? null,
    timeReferenceMs: reference.referenceMs ?? null, sourceAssetMatchesStudy, coverage: clock.coverage, rows, matched,
    completeForProtocol: clock.coverage === 'full_source_trial' && matched === offsets.length,
    issues: reference.code === undefined ? [] : [{ code: reference.code, message: reference.message }] };
}

function localErrors(errors) {
  const count = errors.length;
  if (count === 0) return null;
  const denominator = Math.sqrt(count);
  return { rmseMm: Math.hypot(...errors.map(value => value / denominator)),
    maeMm: errors.reduce((sum, value) => sum + Math.abs(value) / count, 0),
    meanSignedErrorMm: errors.reduce((sum, value) => sum + value / count, 0) };
}

// Shared math and packet checks. Run-specific eligibility stays in each scorer.
export const eegReplaySupport = Object.freeze({
  OFFSETS, STEP_MS, TOLERANCE_MS, NOMINAL_LEAD_MS, FRAME, ReplayInputError, requireInput,
  sameArray, finiteArray, readTrialIdentity, readSourceStreams, readSourceSamples,
  useReplayReference, extractReplayRow, fitPrediction, standardisedFeature, localErrors,
});

/**
 * Pass one packet or a list of separate trial packets from the companion's parsePacket.
 * Model identity and source provenance are checked for compatibility, not authenticated.
 */
export function scoreEegReplay(modelState, packetOrPackets, { modelStateSha256 = null } = {}) {
  const result = { status: 'rejected', scope: SCOPE, modelId: null, modelKind: null,
    modelStateSha256: null, modelDesignSha256: null, modelSourceSha256: null,
    clockReference: null,
    unit: 'mm', targetFrame: FRAME, nominalLeadMs: NOMINAL_LEAD_MS,
    measurementsAuthenticated: false, officialCohortScore: null, trials: [],
    summary: null, diagnostics: [], limitations: LIMITATIONS };
  try {
    const state = validateEegReplayModel(modelState);
    requireInput(modelStateSha256 === null || isSha256(modelStateSha256), 'model_digest',
      'Supply the model file’s SHA-256 as 64 lowercase hexadecimal characters.');
    result.modelId = state.model_id;
    result.modelKind = state.kind;
    result.modelStateSha256 = modelStateSha256;
    result.modelDesignSha256 = state.design_sha256;
    result.modelSourceSha256 = state.source_sha256;
    result.clockReference = state.clock.anchor;
    const packets = Array.isArray(packetOrPackets) ? packetOrPackets : [packetOrPackets];
    requireInput(packets.length > 0 && packets.length <= MAX_PACKETS,
      'packet_count', `Open between 1 and ${MAX_PACKETS} trial packets to score this replay.`);
    const sourceTrials = Array.from(packets, packet => inspectTrial(state, packet));
    const bySubject = new Map();
    for (const { identity } of sourceTrials) {
      const sha256 = identity.provenance.derivativeSha256;
      requireInput(!bySubject.has(identity.subjectId) || bySubject.get(identity.subjectId) === sha256,
        'conflicting_run_identity', 'Trial packets for the same subject and run must identify the same source file.');
      bySubject.set(identity.subjectId, sha256);
    }
    for (const field of ['outIndexZeroBased', 'eeg_seg_idx', 'lm_trial']) {
      const keys = sourceTrials.map(({ identity }) => trialKey(identity, field));
      requireInput(new Set(keys).size === keys.length, 'duplicate_trial',
        'Each source trial, EEG segment and Leap trial can appear only once in a replay.');
    }
    result.trials = sourceTrials.map(trial => replayTrial(state, trial));
    const matched = result.trials.flatMap(trial => trial.rows).filter(row => row.errorMm !== null);
    result.summary = { scope: 'local_matched_rows', requestedRows: result.trials.length * state.clock.score_offsets_ms.length,
      matchedRows: matched.length, estimate: localErrors(matched.map(row => row.errorMm)),
      baseline: localErrors(matched.map(row => row.baselineErrorMm)) };
    if (matched.length === 0) result.status = 'no_matched_rows';
    else result.status = result.trials.every(trial => trial.completeForProtocol) ? 'scored' : 'partial';
  } catch (error) {
    if (!(error instanceof ReplayInputError)) throw error;
    result.diagnostics.push({ code: error.code, message: error.message });
  }
  return result;
}
