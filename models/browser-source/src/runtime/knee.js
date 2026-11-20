// The one-block attention calculation is shared with the population-motion reader.
const sharedKneeForecast = (() => {
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


  return function sharedKneeForecast(history, payload) {
    if (payload?.format !== 1 || !Array.isArray(history) || history.length !== 240 ||
        !Array.from(history).every(row => Array.isArray(row) && row.length === 2 &&
          Number.isFinite(row[0]) && Number.isFinite(row[1]))) {
      throw new RangeError('A verified shared knee model and 240 right/left angle pairs are required.');
    }
    let best = Infinity, period = 45;
    for (let lag = 45; lag <= 180; lag++) {
      let cost = 0;
      for (let t = 180; t < 240; t++) {
        cost += (history[t][0] - history[t-lag][0])**2 + (history[t][1] - history[t-lag][1])**2;
      }
      if (!Number.isFinite(cost)) throw new RangeError('The angles exceed the stride calculation range.');
      if (cost < best) { best = cost; period = lag; }
    }
    const stride = history[239 + 15 - period].slice();
    const readouts = payload.readouts;
    const z = [];
    for (let stop = 60; stop <= 240; stop += 60) {
      const mean = [0, 0];
      for (let t = stop - 60; t < stop; t++) {
        mean[0] += history[t][0]; mean[1] += history[t][1];
      }
      const last = history[stop-1], prior = history[stop-6];
      const token = [mean[0]/60, mean[1]/60, ...last, last[0]-prior[0], last[1]-prior[1]];
      z.push(token.map((v,k) => (v-readouts.token_center[k])/readouts.token_scale[k]));
    }
    const phase = history[239].map((v,i) => v-history[239-period][i]);
    const raw = [...z.flat(), ...stride, ...phase, period];
    const result = {period_frames:period, stride};
    for (const mode of ['raw', 'shared', 'scrambled']) {
      let features = raw;
      if (mode !== 'raw') {
        const encoder = mode === 'shared' ? payload.encoder : payload.scrambled_encoder;
        const hidden = encode(encoder, z.map(token => linear(encoder, 'project', token)), true);
        features = raw.concat(hidden.flatMap(row => Array.from(row)));
      }
      result[mode] = stride.map((angle, side) => {
        let correction = readouts[mode+'.intercept'][side];
        for (let j = 0; j < features.length; j++) {
          const scaled = (features[j] - readouts[mode+'.center'][j]) / readouts[mode+'.scale'][j];
          correction += scaled * readouts[mode+'.coef'][2*j+side];
        }
        return angle + correction;
      });
      if (!result[mode].every(Number.isFinite)) throw new RangeError('This history exceeds the forecast calculation range.');
    }
    return result;
  };
})();
