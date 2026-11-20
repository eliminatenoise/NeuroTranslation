// Float64 one-block attention from the NeuroTranslate shared-knee reader.
const kneeMoment = (() => {
  const width = 24, heads = 4, headWidth = width / heads;
  function linear(state, key, input) {
    const weight = state[key+'.weight'], bias = state[key+'.bias'];
    const output = new Float64Array(bias.length);
    for (let row = 0; row < bias.length; row++) {
      let sum = 0;
      const offset = row * input.length;
      for (let i = 0; i < input.length; i++) sum += weight[offset+i] * input[i];
      output[row] = sum + bias[row];
    }
    return output;
  }

  function normalize(state, name, input) {
    let mean = 0, variance = 0;
    for (const value of input) mean += value;
    mean /= width;
    for (const value of input) variance += (value - mean) ** 2;
    const sd = Math.sqrt(variance / width + 1e-5);
    const weight = state[name+'.weight'], bias = state[name+'.bias'];
    return input.map((v,i) => (v - mean) / sd * weight[i] + bias[i]);
  }

  function encode(state, projected, allTokens = false) {
    const tokens = projected.map((row, t) => row.map((v, i) => v + state.position[t*width+i]));
    const block = 'blocks.0.';
    const packed = tokens.map(z => linear(state, block+'qkv', normalize(state, block+'attention_norm', z)));
    function attentionRow(query) {
      const mixed = new Float64Array(width);
      for (let h = 0; h < heads; h++) {
        const start = h * headWidth;
        const scores = packed.map(row => {
          let score = 0;
          for (let i = start; i < start + headWidth; i++) score += packed[query][i] * row[width+i];
          return score / Math.sqrt(headWidth);
        });
        const max = Math.max(...scores);
        const exps = scores.map(score => Math.exp(score-max));
        const total = exps.reduce((sum, v) => sum+v, 0);
        for (let t = 0; t < 4; t++) {
          const attention = exps[t]/total;
          for (let i = start; i < start + headWidth; i++) mixed[i] += attention * packed[t][2*width+i];
        }
      }
      const residual = linear(state, block+'attention_out', mixed).map((v,i) => v + tokens[query][i]);
      const hidden = linear(state, block+'ff_in', normalize(state, block+'ff_norm', residual));
      const update = linear(state, block+'ff_out', hidden.map(v => Math.max(0, v)));
      return normalize(state, 'last_norm', update.map((v,i) => v + residual[i]));
    }
    return allTokens ? tokens.map((_, t) => attentionRow(t)) : attentionRow(3);
  }

  const modes = ['mean', 'ridge', 'shared', 'scrambled', 'trained'];

  function validateWindow(frames, history) {
    if (!Array.isArray(frames) || frames.length !== 400 || !Array.isArray(history) || history.length !== 400)
      throw new RangeError('Each history needs 400 consecutive frames and 400 rows of six angles.');
    for (let t = 0; t < 400; t++) {
      if (!Number.isSafeInteger(frames[t]) || frames[t] < 0 || (t && frames[t] !== frames[t - 1] + 1))
        throw new RangeError('Frame numbers must be nonnegative, consecutive safe integers.');
      const row = history[t];
      if (!Array.isArray(row) || row.length !== 6 || !Array.from(row).every(v => Number.isFinite(v) && v !== 0))
        throw new RangeError('Each row needs six finite, nonzero angles in degrees.');
    }
  }

  function choosePeriod(history) {
    let lowest = Infinity, period = 75;
    for (let lag = 75; lag <= 300; lag++) {
      let cost = 0;
      for (let t = 300; t < 400; t++) {
        cost += (history[t][0] - history[t-lag][0]) ** 2 + (history[t][1] - history[t-lag][1]) ** 2;
      }
      if (!Number.isFinite(cost)) throw new RangeError('Angles exceed the stride comparison range.');
      if (cost < lowest) { lowest = cost; period = lag; }
    }
    return period;
  }

  function readout(stats, mode, values) {
    const bias = stats[mode + '.bias'], mean = stats[mode + '.mean'];
    const sd = stats[mode + '.sd'], coef = stats[mode + '.coef'];
    const out = [0, 0];
    for (let j = 0; j < values.length; j++) {
      const standardized = (values[j] - mean[j]) / sd[j];
      out[0] += standardized * coef[2*j];
      out[1] += standardized * coef[2*j+1];
    }
    return out.map((v,i) => v + bias[i]);
  }

  function predictWindow(history, period, mode, weights) {
    const stats = weights.stats;
    if (mode === 'mean') return stats.target_mean.slice();
    const bins = [];
    for (let start = 300; start < 400; start += 25) {
      const bin = Array(6).fill(0);
      for (let t = start; t < start + 25; t++)
        for (let j = 0; j < 6; j++) bin[j] += history[t][j];
      bins.push(bin.map(v => v/25));
    }
    const raw = [];
    for (let t = 359; t <= 399; t += 5) raw.push(...history[t]);
    raw.push(...history[424-period], ...history[419-period],
      ...history[399].map((v,j) => v-history[399-period][j]), period, ...bins.flat());
    if (mode === 'ridge') return readout(stats, mode, raw);
    const state = weights[mode];
    const tokens = bins.map(row => linear(state, 'project', row.map((v,j) => (v-stats.bin_mean[j])/stats.bin_sd[j])));
    if (mode === 'trained') {
      const correction = linear(state, 'readout', encode(state, tokens));
      return readout(stats, 'ridge', raw).map((v,j) => v + correction[j] * stats.target_sd[j]);
    }
    const hidden = encode(state, tokens, true);
    return readout(stats, mode, raw.concat(hidden.flatMap(row => Array.from(row))));
  }

  function predict(record, weights) {
    if (!record || typeof record !== 'object' || Array.isArray(record) ||
        Object.keys(record).sort().join(',') !== 'angles_deg,domain,frames,mode' ||
        record.domain !== 'knee_moment' || !modes.includes(record.mode))
      throw new RangeError('Expected domain knee_moment, mode, frames and angles_deg.');
    if (!weights || weights.format !== 1) throw new RangeError('Expected a knee moment weight export.');
    if (!Array.isArray(record.frames) || !Array.isArray(record.angles_deg) || !record.frames.length)
      throw new RangeError('Supply a history or a nonempty batch of histories.');
    const batch = Array.isArray(record.frames[0]);
    const frames = batch ? record.frames : [record.frames];
    const histories = batch ? record.angles_deg : [record.angles_deg];
    if (frames.length !== histories.length) throw new RangeError('Frame and angle batch sizes must match.');
    const moments = [], periods = [];
    for (let i = 0; i < frames.length; i++) {
      validateWindow(frames[i], histories[i]);
      const period = choosePeriod(histories[i]);
      const y = predictWindow(histories[i], period, record.mode, weights);
      if (!y.every(Number.isFinite)) throw new RangeError('Angles exceed the forecast calculation range.');
      periods.push(period); moments.push(y);
    }
    return {axes: ['right', 'left'], internal_knee_moment_Nm_per_kg: moments,
      positive: 'flexion', period_frames: periods, horizon_stored_frames: 25, stored_hz: 100};
  }

  return {predict};
})();
if (typeof module === 'object' && module.exports) module.exports = kneeMoment;
