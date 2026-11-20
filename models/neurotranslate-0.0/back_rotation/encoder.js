// The released NeuroTranslate browser encoder, shared by the motion studies.
const width=24, heads=4, headWidth=6;
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
    // Spatial and wrist-angle heads need only the last query. The population
    // readout also uses each earlier query's state at its own firing interval.
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

