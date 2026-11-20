/** Apply fixed R1 parameters to archived, source-qualified R2 packets. */
import { sha256Hex } from './hash.e857080fae8333b54a69fc8d6427e6f53816c5561698dbaca9af46657094c6cc.mjs';
import { eegReplaySupport, validateEegReplayModel } from './palm-model.e857080fae8333b54a69fc8d6427e6f53816c5561698dbaca9af46657094c6cc.mjs';

const {
  OFFSETS, STEP_MS, TOLERANCE_MS, NOMINAL_LEAD_MS, FRAME, ReplayInputError, requireInput,
  sameArray, finiteArray, readTrialIdentity, readSourceStreams, readSourceSamples,
  useReplayReference, extractReplayRow, fitPrediction, standardisedFeature, localErrors,
} = eegReplaySupport;

const DIGESTS = Object.freeze({
  baseModel: 'c9c9e6a5c357274103e339f69517ae6a11f1d90c39f1d172585ad81a38ee8337',
  calibrationState: '14ab9c33101f7f8eb379b646a61b391557096151d2f75ea235965281e3dd5818',
  source: 'a8068a70b4ae0fe11184d5d49741b38d49cd3f368faff9b96799dc09d0ec719c',
  trialIndex: '729f006faa0880031127777a95369f95a3034fc72c5e4b42e81181c93d511b48',
});
const STUDY = 'iackd-right-hand-cross-run-last-head-v1';
const DESIGN_SHA256 = 'd621ee2859bc8e8e2f16f553e332f63b4fdf890fbc52a38c6684e86839b578cd';
const RUN = '02';
const PARTICIPANTS = ['sub-13', 'sub-14', 'sub-15'];
const METHODS = Object.freeze(['fixedHand', 'fixedEegHand', 'calibratedHand', 'calibratedEegHand']);
const LIMITATIONS = Object.freeze([
  'The two models use the same archived samples. The calibrated versions add corrections fitted on that person’s earlier R1 recording.',
  'The 100 ms input gap comes from the archive clock. The release authors filtered and aligned the recordings retrospectively.',
  'Time zero marks cue disappearance. The first available palm sample sets the model clock. Neither timestamp measures movement onset.',
  'The traces and errors describe the selected packet. The study reports a separate comparison across all three participants.',
]);
const verifiedStates = new WeakSet();

function loadAsset(text, asset) {
  requireInput(typeof text === 'string' && sha256Hex(text) === DIGESTS[asset],
    'state_digest', `The ${asset} file does not match the frozen study release.`);
  return JSON.parse(text, (_, value) => value !== null && typeof value === 'object' ? Object.freeze(value) : value);
}

function sampleFingerprint(series) {
  // Vector-major [t_ms, C3, Cz, C4, palm x]. Each vector begins with a
  // little-endian uint32 length, then tag byte and little-endian float64 pairs.
  // tag 0 records null. Null and either signed zero use the +0 float encoding.
  const bytes = new Uint8Array(series.reduce((size, values) => size + 4 + values.length * 9, 0));
  const view = new DataView(bytes.buffer);
  let at = 0;
  for (const values of series) {
    view.setUint32(at, values.length, true);
    at += 4;
    for (const value of values) {
      view.setUint8(at, value === null ? 0 : 1);
      view.setFloat64(at + 1, value || 0, true);
      at += 9;
    }
  }
  return sha256Hex(bytes);
}

/** Check release asset bytes before loading the state. The returned state is immutable. */
export function loadR2ReplayState({baseModel, calibrationState, source, trialIndex}) {
  const model = validateEegReplayModel(loadAsset(baseModel, 'baseModel'));
  const calibration = loadAsset(calibrationState, 'calibrationState');
  const bindings = loadAsset(source, 'source');
  const index = loadAsset(trialIndex, 'trialIndex');
  requireInput(calibration.study === STUDY && calibration.design_sha256 === DESIGN_SHA256
    && calibration.kind === 'R1_subject_specific_last_head_corrections'
    && calibration.source_sha256 === DIGESTS.source && calibration.frozen_model_sha256 === DIGESTS.baseModel
    && calibration.frozen_model_id === model.model_id && calibration.ridge_lambda === 0.01
    && calibration.release_commit === model.release_commit && bindings.release_commit === model.release_commit
    && index.schemaVersion === 1 && index.sourceSha256 === DIGESTS.source && index.releaseCommit === model.release_commit,
  'state_identity', 'The model weights, calibration and source index must describe the same frozen release.');
  const participants = Object.fromEntries(PARTICIPANTS.map(subjectId => {
    const calibrationSource = bindings.participants.find(row => row.subject === subjectId && row.role === 'CALIBRATION');
    const evaluation = bindings.participants.find(row => row.subject === subjectId && row.role === 'EVALUATION');
    const personal = calibration.participants[subjectId];
    const census = index.participants[subjectId];
    requireInput(calibrationSource?.run === '01' && evaluation?.run === RUN
      && personal?.calibration?.asset_sha256 === calibrationSource.asset_sha256
      && personal.calibration.basename === calibrationSource.basename
      && census?.derivativeSha256 === evaluation.asset_sha256 && census.trials.length === evaluation.released_trials,
    'state_subject_identity', `The frozen R1 calibration and distinct R2 source must agree for ${subjectId}.`);
    for (const name of ['time_palm', 'time_palm_eeg']) {
      const correction = personal.corrections[name];
      requireInput(finiteArray(correction?.ridge_delta_intercepts_mm, OFFSETS.length)
        && finiteArray(correction.ridge_delta_slopes, model.models[name].feature_indices.length),
      'state_parameters', `The personal calibration parameters are incomplete for ${subjectId}.`);
    }
    return [subjectId, Object.freeze({ evaluation, corrections: personal.corrections, trials: census.trials })];
  }));
  const state = Object.freeze({ model, participants: Object.freeze(participants) });
  verifiedStates.add(state);
  return state;
}

function inspectR2Packet(state, packet) {
  const identity = readTrialIdentity(packet, RUN);
  const { subjectId, provenance, trial } = identity;
  const participant = state.participants[subjectId];
  requireInput(participant !== undefined, 'subject_outside_study', 'Held-out R2 replay covers sub-13, sub-14 and sub-15.');
  const { evaluation } = participant;
  requireInput(packet.dataset.split === 'heldout' && provenance.archiveDerivative === 'R2'
    && provenance.derivativeSha256 === evaluation.asset_sha256
    && provenance.derivativePath === evaluation.derivative.release_path
    && provenance.selection?.evaluationRole === 'EVALUATION',
  'r2_source_identity', 'Use the held-out right-hand R2 derivative recorded for this participant.');
  const declaredStudy = provenance.calibrationStudy;
  requireInput(declaredStudy === undefined || (declaredStudy?.id === STUDY && declaredStudy.participantId === subjectId
    && declaredStudy.calibrationRun === '01' && declaredStudy.evaluationRun === RUN
    && declaredStudy.frozenModelId === state.model.model_id && declaredStudy.frozenModelSha256 === DIGESTS.baseModel
    && declaredStudy.calibrationStateSha256 === DIGESTS.calibrationState && declaredStudy.studySourceSha256 === DIGESTS.source),
  'r2_calibration_identity', 'This packet’s calibration details disagree with the frozen R1-to-R2 study.');
  const sourceTrial = participant.trials[trial.outIndexZeroBased];
  requireInput(sourceTrial?.outIndexZeroBased === trial.outIndexZeroBased
    && provenance.trial.outPositionOneBased === trial.outIndexZeroBased + 1
    && sourceTrial.eeg_seg_idx === trial.eeg_seg_idx && sourceTrial.lm_trial === trial.lm_trial,
  'r2_trial_identity', 'The derivative row, EEG segment and Leap trial must agree with the R2 study index.');
  requireInput(provenance.selection.sourceTrialRowCount === sourceTrial.sourceTrialRowCount,
    'r2_source_selection', 'The selected row range must refer to the original R2 trial length.');
  const { montage } = provenance;
  const columns = evaluation.channels.map(channel => channel.index_zero_based);
  requireInput(montage?.acquisitionChannelCount === 31 && montage.derivativeEegColumnCount === evaluation.n_channels
    && montage.sourceOrientation === 'samples × channels in HDF5 storage'
    && sameArray(montage.sourceEegShape, [sourceTrial.sourceTrialRowCount, evaluation.n_channels])
    && montage.acquisitionHeaderSha256 === evaluation.raw_sources.brainvision_header.sha256
    && montage.channelsTsvSha256 === evaluation.raw_sources.channels_tsv.sha256
    && Array.isArray(montage.selectedChannels) && montage.selectedChannels.length === columns.length
    && evaluation.channels.every((channel, index) => montage.selectedChannels[index]?.name === channel.name
      && montage.selectedChannels[index]?.sourceColumnZeroBased === channel.index_zero_based),
  'r2_montage', 'The packet needs the released sample orientation and the same-run C3, Cz and C4 channel mapping.');
  const { eeg, palm } = readSourceStreams(identity.streams, {columns, requireNamedChannel: true});
  const clock = readSourceSamples(provenance, [...eeg, palm]);
  const seconds = provenance.clock.timestampSeconds;
  requireInput(seconds === undefined || (Array.isArray(seconds) && seconds.length === clock.times.length
    && clock.times.every((time, index) => seconds[index] === time / 1000)),
  'r2_absolute_clock', 'The timestamp conversion must preserve the original event-relative sample times.');
  if (clock.coverage === 'full_source_trial') {
    const bytes = new Uint8Array(clock.times.length * Float64Array.BYTES_PER_ELEMENT);
    const view = new DataView(bytes.buffer);
    clock.times.forEach((time, index) => view.setFloat64(index * Float64Array.BYTES_PER_ELEMENT, time, true));
    requireInput(sha256Hex(bytes) === sourceTrial.clockSha256, 'r2_archived_clock_mismatch',
      'This complete trial’s timestamps differ from the released R2 clock.');
    requireInput(sampleFingerprint([clock.times, ...eeg.map(stream => stream.values), palm.values]) === sourceTrial.samplesSha256,
      'r2_archived_samples_mismatch', 'The EEG or palm samples differ from the released R2 trial.');
  }
  return { identity, participant, sourceTrial, eeg, palm, clock };
}

function qualifyClock(clock, palm, provenance) {
  const { times, start, coverage } = clock;
  if (times.some((time, index) => index > 0 && time <= times[index - 1])) {
    return { ...clock, code: 'clock_nonfinite_or_nonincreasing' };
  }
  const anchorIndex = times.findIndex(time => time >= 0);
  const anchorMs = anchorIndex < 0 ? null : times[anchorIndex];
  const hasOutsidePredecessor = anchorIndex === 0 && start > 0 && coverage === 'source_window'
    && Number.isFinite(provenance.clock.previousTimestampMilliseconds)
    && provenance.clock.previousTimestampMilliseconds < 0;
  if (anchorIndex < 0 || anchorMs >= STEP_MS || (anchorIndex === 0 && !hasOutsidePredecessor)) {
    return { ...clock, code: 'no_native_anchor_bracketing_event' };
  }
  const native = { ...clock, anchorIndex, anchorMs };
  if (times.some((time, index) => Math.abs(time - anchorMs - (index - anchorIndex) * STEP_MS) > TOLERANCE_MS)
    || (hasOutsidePredecessor && Math.abs(provenance.clock.previousTimestampMilliseconds - anchorMs + STEP_MS) > TOLERANCE_MS)) {
    return { ...native, code: 'clock_gapped_or_off_lattice' };
  }
  const reference = useReplayReference(native, palm);
  return reference.code === undefined ? reference : { ...reference, code: 'no_finite_palm_at_or_after_native_cue' };
}

function calibratedPrediction(model, correction, features, offsetIndex, fixed) {
  let delta = correction.ridge_delta_intercepts_mm[offsetIndex];
  for (const [index, featureIndex] of model.feature_indices.entries()) {
    delta += correction.ridge_delta_slopes[index] * standardisedFeature(model, features[featureIndex], index);
  }
  return fixed + delta;
}

function predictRow(model, corrections, clock, eeg, palm, offsetIndex) {
  const { row: extracted, features } = extractReplayRow(clock, eeg, palm, OFFSETS[offsetIndex]);
  const { offsetMs, nominalTimeMs, timeMs, sourceRowIndex, targetMm, inputThroughMs, sampleLeadMs, missingReasons } = extracted;
  const row = { offsetMs, nominalTimeMs, timeMs, sourceRowIndex, targetMm, inputThroughMs,
    sampleLeadMs, missingReasons, predictionsMm: null, errorsMm: null };
  if (features === null || targetMm === null) return row;
  const hand = model.models.time_palm;
  const eegHand = model.models.time_palm_eeg;
  const fixedHand = fitPrediction(hand, features, offsetIndex);
  const fixedEegHand = fitPrediction(eegHand, features, offsetIndex);
  const predictionsMm = {
    fixedHand, fixedEegHand,
    calibratedHand: calibratedPrediction(hand, corrections.time_palm, features, offsetIndex, fixedHand),
    calibratedEegHand: calibratedPrediction(eegHand, corrections.time_palm_eeg, features, offsetIndex, fixedEegHand),
  };
  const errorsMm = Object.fromEntries(METHODS.map(name => [name, predictionsMm[name] - targetMm]));
  if (![...Object.values(predictionsMm), ...Object.values(errorsMm)].every(Number.isFinite)) {
    row.missingReasons.push({code: 'nonfinite_regression', signal: 'Regression', relativeOffsetMs: offsetMs,
      message: 'The sample or error is outside the numeric range of this regression.'});
    return row;
  }
  return { ...row, predictionsMm, errorsMm };
}

const ISSUES = Object.freeze({
  clock_nonfinite_or_nonincreasing: 'The stored sample times must increase strictly.',
  no_native_anchor_bracketing_event: 'The selected rows must bracket cue disappearance on the archived clock.',
  clock_gapped_or_off_lattice: 'A stored timestamp falls off the native 10 ms grid or a native row is missing.',
  no_finite_palm_at_or_after_native_cue: 'There is no recorded palm position at or after the cue.',
  required_time_support_unavailable: 'The selected rows do not cover every required target and input time.',
  nonfinite_target: 'A recorded palm target is missing.',
  nonfinite_past_palm: 'A past palm sample is missing.',
  nonfinite_eeg: 'A required EEG sample is missing.',
  nonfinite_regression: 'The regression exceeds the numeric range of this packet.',
  source_window: 'This window covers part of an R2 trial. The study assessed complete trials.',
  indexed_exclusion_requires_complete_trial: 'This window refers to the R2 trial flagged in the study. Use the complete trial to check the archived exclusion.',
});

function supportProblem(rows) {
  const issues = rows.flatMap(row => row.missingReasons);
  if (issues.some(issue => issue.code === 'outside_source_window')) return 'required_time_support_unavailable';
  if (issues.some(issue => issue.signal === 'Palm target')) return 'nonfinite_target';
  if (issues.some(issue => issue.signal === 'Past palm')) return 'nonfinite_past_palm';
  if (issues.some(issue => issue.code === 'source_value_missing')) return 'nonfinite_eeg';
  if (issues.some(issue => issue.code === 'nonfinite_regression')) return 'nonfinite_regression';
  return null;
}

function unavailableRows(code) {
  return OFFSETS.map(offsetMs => ({
    offsetMs, nominalTimeMs: null, timeMs: null, sourceRowIndex: null, targetMm: null,
    inputThroughMs: null, sampleLeadMs: null, predictionsMm: null, errorsMm: null,
    missingReasons: [{code, signal: 'Task clock', relativeOffsetMs: null, message: ISSUES[code]}],
  }));
}

function summarize(rows) {
  const matched = rows.filter(row => row.errorsMm !== null);
  return {
    scope: 'local_matched_rows', requestedRows: OFFSETS.length, matchedRows: matched.length,
    metrics: Object.fromEntries(METHODS.map(name => [name, localErrors(matched.map(row => row.errorsMm[name]))])),
  };
}

/** Score one parsed R2 packet. The source metadata checks cannot authenticate observations. */
export function scoreR2Replay(state, packet) {
  const result = {
    status: 'rejected', scope: 'offline_recorded_r2_trial_replay', study: STUDY, modelId: null,
    modelStateSha256: DIGESTS.baseModel, calibrationStateSha256: DIGESTS.calibrationState,
    sourceSha256: DIGESTS.source, modelDesignSha256: DESIGN_SHA256, trialIndexSha256: DIGESTS.trialIndex,
    unit: 'mm', targetFrame: FRAME, nominalLeadMs: NOMINAL_LEAD_MS, measurementsAuthenticated: false,
    subjectId: null, recordingId: null, trial: null, coverage: null, fullSourceTrial: false,
    eligibleForStudySupport: null, sourceClockVerified: false, selectedSamplesMatchSource: null,
    anchorMs: null, timeReferenceMs: null, officialExclusion: null,
    officialCohortScore: null, rows: [], summary: null, diagnostics: [], limitations: LIMITATIONS,
  };
  try {
    requireInput(verifiedStates.has(state), 'unverified_state', 'Load the frozen cross-run study files before opening an R2 trial.');
    const { identity, participant, sourceTrial, eeg, palm, clock } = inspectR2Packet(state, packet);
    const reference = qualifyClock(clock, palm, identity.provenance);
    const fullSourceTrial = clock.coverage === 'full_source_trial';
    const clockProblem = !fullSourceTrial && sourceTrial.exclusion !== null
      ? 'indexed_exclusion_requires_complete_trial' : reference.code;
    let rows = clockProblem === undefined
      ? OFFSETS.map((_, index) => predictRow(state.model, participant.corrections, reference, eeg, palm, index))
      : unavailableRows(clockProblem);
    const problem = clockProblem ?? supportProblem(rows);
    requireInput(!fullSourceTrial || sourceTrial.exclusion === null || sourceTrial.exclusion === problem,
      'r2_study_exclusion_mismatch', 'The complete R2 packet disagrees with its archived trial’s recorded exclusion.');
    if (fullSourceTrial && problem !== null) {
      rows = rows.map(row => ({ ...row, predictionsMm: null, errorsMm: null }));
    }
    const status = fullSourceTrial ? (problem === null ? 'scored' : 'ineligible') : 'partial';
    const diagnostics = [];
    if (!fullSourceTrial) diagnostics.push({code: 'source_window', message: ISSUES.source_window});
    if (problem !== null) diagnostics.push({code: problem, message: ISSUES[problem]});
    const { subjectId, recordingId, trial } = identity;
    const officialExclusion = fullSourceTrial && problem !== null && problem === sourceTrial.exclusion
      ? { code: problem, subjectId, run: RUN, ...trial } : null;
    return { ...result, status, modelId: state.model.model_id, subjectId, recordingId, trial,
      coverage: clock.coverage, fullSourceTrial, sourceClockVerified: fullSourceTrial,
      selectedSamplesMatchSource: fullSourceTrial ? true : null,
      eligibleForStudySupport: fullSourceTrial ? problem === null : null,
      anchorMs: reference.anchorMs ?? null, timeReferenceMs: reference.referenceMs ?? null, officialExclusion,
      rows, summary: summarize(rows), diagnostics };
  } catch (error) {
    if (!(error instanceof ReplayInputError)) throw error;
    return { ...result,
      selectedSamplesMatchSource: error.code === 'r2_archived_samples_mismatch' ? false : null,
      diagnostics: [{code: error.code, message: error.message}] };
  }
}
