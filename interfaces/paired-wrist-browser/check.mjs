// Use the same acceptance test for both Chromium and Node. No observations come from participants.
const MODES = ['motion', 'emg', 'full'];
const MODALITY_REQUIRED = {motion: [], emg: ['emg_rms_uv'], full: ['emg_rms_uv', 'eeg_mean_uv']};
const ANGLE_ATOL = 5e-5, VAR_ATOL = 5e-5, VAR_RTOL = 8e-6;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertRejected(fn, label) {
  let rejected = false;
  try { fn(); } catch { rejected = true; }
  assert(rejected, 'Accepted invalid ' + label);
}

function summary(times) {
  const sorted = times.slice().sort((a, b) => a - b);
  return { count: times.length, median_ms: sorted[Math.floor(sorted.length / 2)],
    p95_ms: sorted[Math.ceil(sorted.length * .95) - 1], max_ms: sorted.at(-1) };
}

export async function verify(load, cases) {
  const reports = {};
  for (const mode of MODES) {
    const start = performance.now();
    const [model, duplicate] = await Promise.all([load(mode), load(mode)]);
    const loadMs = performance.now() - start;
    assert(model === duplicate, 'Concurrent loads did not coalesce');
    let maxAngle = 0, maxVariance = 0, maxVarianceRatio = 0;
    const outputs = new Map(), times = [];
    for (const row of cases) {
      const start = performance.now();
      const actual = model.predict(row.payload), expected = row.expected[mode];
      times.push(performance.now() - start);
      outputs.set(row.name, actual);
      for (let i = 0; i < 2; i++) {
        const angleError = Math.abs(actual.angle_deg[i] - expected.angle_deg[i]);
        const varianceError = Math.abs(actual.variance_deg2[i] - expected.variance_deg2[i]);
        const label = row.name + ' / ' + mode + ' / axis ' + i;
        assert(angleError <= ANGLE_ATOL, 'Angle disagreement ' + label + ' by ' + angleError);
        assert(varianceError <= VAR_ATOL + VAR_RTOL * expected.variance_deg2[i] && actual.variance_deg2[i] > 0,
          'Variance disagreement ' + label + ' by ' + varianceError);
        maxAngle = Math.max(maxAngle, angleError);
        maxVariance = Math.max(maxVariance, varianceError);
        maxVarianceRatio = Math.max(maxVarianceRatio, varianceError / expected.variance_deg2[i]);
      }
    }

    for (const slot of [384, 512, 640, 768, 896, 1024]) {
      const base = JSON.stringify(outputs.get('wave-' + slot));
      for (const [name, expectedChange] of [
        ['motion-pulse', true], ['emg-pulse', mode !== 'motion'], ['eeg-pulse', mode === 'full'],
      ]) {
        assert((JSON.stringify(outputs.get(name + '-' + slot)) !== base) === expectedChange,
          'Unexpected response to ' + name + ' in ' + mode + ' at ' + slot);
      }
    }

    const valid = structuredClone(cases.find(row => row.name === 'wave-384').payload);
    const minimum = {anchor_deg: valid.anchor_deg, mean_angles_deg: valid.mean_angles_deg,
      target_offset_after_cue_ticks: 384};
    for (const field of MODALITY_REQUIRED[mode]) minimum[field] = valid[field];
    assert(JSON.stringify(model.predict(minimum)) === JSON.stringify(model.predict(valid)), 'Optional fields affect mode');
    for (const field of ['anchor_deg', 'mean_angles_deg', ...MODALITY_REQUIRED[mode]]) {
      for (const value of [null, [], undefined]) {
        assertRejected(() => model.predict({...valid, [field]: value}), field);
      }
      const bad = structuredClone(valid);
      if (field === 'anchor_deg') bad[field][1] = NaN; else bad[field][2][0] = '3';
      assertRejected(() => model.predict(bad), field + ' scalar');
    }
    for (const bad of [-1, 383, 384.1, '384', null, true]) {
      assertRejected(() => model.predict({...valid, target_offset_after_cue_ticks: bad}), 'offset');
    }
    if (mode !== 'motion') {
      const negative = structuredClone(valid);
      negative.emg_rms_uv[1][2] = -0.1;
      assertRejected(() => model.predict(negative), 'negative muscle RMS');
    }

    // Warm repetitions cover every fixture twice; cold load and first prediction remain separate.
    const warm = [];
    for (let rep = 0; rep < 2; rep++) {
      for (const {payload} of cases) {
        const t = performance.now();
        model.predict(payload);
        warm.push(performance.now() - t);
      }
    }
    reports[mode] = {fit_load_ms: loadMs, first_prediction_ms: times[0], warm: summary(warm),
      cases: cases.length, max_angle_abs_deg: maxAngle, max_variance_abs_deg2: maxVariance,
      max_variance_relative: maxVarianceRatio, channel_perturbation_checks: 18};
  }
  return {angle_atol_deg: ANGLE_ATOL, variance_atol_deg2: VAR_ATOL, variance_rtol: VAR_RTOL, modes: reports};
}
