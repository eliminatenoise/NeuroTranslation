/* Primary seed-17 time-series Transformers. Positions retain native units. */
const ReachForecast = (() => {
  function linear(input, weights, layer) {
    const matrix = weights[layer + ".weight"], bias = weights[layer + ".bias"];
    return matrix.map((row, i) => {
      let sum = bias[i];
      for (let j = 0; j < row.length; j++) sum += row[j] * input[j];
      return sum;
    });
  }

  function normalize(input, weights, layer) {
    const average = input.reduce((sum, x) => sum + x, 0) / input.length;
    const variance = input.reduce((sum, x) => sum + (x - average) ** 2, 0) / input.length;
    const denominator = Math.sqrt(variance + 1e-5);
    return input.map((x, i) => (x - average) / denominator * weights[layer + ".weight"][i] + weights[layer + ".bias"][i]);
  }

  const add = (left, right) => left.map((v, i) => v + right[i]);
  const difference = (left, right) => left.map((v, i) => v - right[i]);
  const relu = input => input.map(v => Math.max(v, 0));
  const standardize = (row, mean, scale) => row.map((v, i) => (v - mean[i]) / scale[i]);

  function chunks(values, size) {
    const result = [];
    for (let i = 0; i < values.length; i += size) result.push(values.slice(i, i + size));
    return result;
  }

  // A single attention block feeds one readout. Compute that token's query
  // against every history key and value. Other output tokens are unused.
  function attend(rows, token, heads, weights) {
    const width = heads * 8, qkv = rows.map(row => linear(row, weights, "qkv"));
    const selected = qkv[token];
    const mixed = [];
    for (let head = 0; head < heads; head++) {
      const offset = head * 8;
      const logits = qkv.map(row => {
        let product = 0;
        for (let j = 0; j < 8; j++) product += selected[offset + j] * row[width + offset + j];
        return product / Math.sqrt(8);
      });
      const max = Math.max(...logits);
      const exponents = logits.map(value => Math.exp(value - max));
      const total = exponents.reduce((a, b) => a + b, 0);
      for (let j = 0; j < 8; j++) {
        mixed.push(qkv.reduce((sum, row, i) => sum + exponents[i] / total * row[2 * width + offset + j], 0));
      }
    }
    return linear(mixed, weights, "project");
  }

  function movement(weights, history) {
    const rows = history.pose.map((pose, i) => {
      const features = [...pose, ...difference(pose, history.pose[Math.max(0, i - 1)]),
                        ...history.spikes[i].map(Math.sqrt), ...history.cue[i]];
      return add(linear(standardize(features, weights.x_mean, weights.x_scale), weights, "embed"), weights.position[i]);
    });
    const attended = normalize(add(rows[19], attend(rows, 19, 3, weights)), weights, "attention_norm");
    const readout = normalize(add(attended, linear(relu(linear(attended, weights, "expand")), weights, "reduce")), weights, "final_norm");
    return chunks(linear(readout, weights, "out"), 8)
      .map((row, t) => row.map((v, j) => v * weights.y_scale[j] + weights.y_mean[t][j]));
  }

  function counts(weights, history, predicted) {
    const past = history.pose.flatMap((pose, i) => [
      ...standardize([...pose, ...difference(pose, history.pose[19])], weights.pose_mean, weights.pose_scale),
      ...standardize(history.spikes[i], weights.spikes_mean, weights.spikes_scale),
      ...standardize(history.cue[i], weights.cue_mean, weights.cue_scale)
    ]);
    const path = weights.arm === "direct" ? new Array(80).fill(0) :
      predicted.flatMap(row => standardize(row, weights.movement_mean, weights.movement_scale));
    const tokens = [new Array(16).fill(0), ...chunks(past, 210).map(row => linear(row, weights, "hist")),
                    ...chunks(path, 40).map(row => linear(row, weights, "path"))];
    const rows = tokens.map((r, i) => add(r, weights.position[0][i]));
    const context = add(rows[0], attend(rows.map(r => normalize(r, weights, "norm1")), 0, 2, weights));
    const hidden = add(context, linear(relu(linear(normalize(context, weights, "norm2"), weights, "ff1")), weights, "ff2"));
    const logits = linear(normalize(hidden, weights, "read_norm"), weights, "read");
    return chunks(logits.map(v => Math.max(v, 0) + Math.log1p(Math.exp(-Math.abs(v))) + 1e-6), 23);
  }

  function run(weights, history, countSupported) {
    const path = movement(weights.motor, history);
    return {movement: path, full: countSupported ? counts(weights.full, history, path) : null,
            direct: countSupported ? counts(weights.direct, history, path) : null};
  }
  return {run};
})();
