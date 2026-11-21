// SPDX-License-Identifier: CC0-1.0
// See CONTRACT.json for the recording frame, units and public inference API.
(function () {
  "use strict";

  const WIDTH = 32;
  const HEAD_WIDTH = 8;
  const COORDINATES = 6;
  const TIMES = [20, 50, 70, 100];
  const CHANNELS = 45;
  const MOTION = 8;
  const F32 = Math.fround;
  const model = globalThis.ReachForecastModel;
  if (!model || model.schema !== "motion-reach-ar-v1" || model.byteOrder !== "little") {
    throw new Error("Load the matching reach-model.js before reach-engine.js.");
  }

  function unpack(entry) {
    const [shape, dtype, encoded] = entry;
    const type = {float32: Float32Array, float64: Float64Array}[dtype];
    const count = shape.reduce((a, b) => a * b, 1);
    const bytes = Uint8Array.from(atob(encoded), char => char.charCodeAt(0));
    if (!type || bytes.length !== count * type.BYTES_PER_ELEMENT) {
      throw new Error("Invalid reach model parameter.");
    }
    const view = new DataView(bytes.buffer);
    const tensor = new type(count);
    for (let i = 0; i < count; i++) {
      tensor[i] = type === Float32Array ? view.getFloat32(i * 4, true) : view.getFloat64(i * 8, true);
    }
    return tensor;
  }

  const weights = Object.fromEntries(Object.entries(model.tensors).map(([name, value]) => [name, unpack(value)]));

  function matrix(value, rows, columns, label) {
    if (!Array.isArray(value) || value.length !== rows) {
      throw new TypeError(label + " must have " + rows + " rows.");
    }
    return Array.from(value, row => {
      if (!(Array.isArray(row) || ArrayBuffer.isView(row)) || row.length !== columns) {
        throw new TypeError(label + " rows must contain " + columns + " numbers.");
      }
      const result = new Float32Array(columns);
      for (let i = 0; i < columns; i++) {
        if (!Number.isFinite(row[i]) || !Number.isFinite(F32(row[i]))) {
          throw new TypeError(label + " entries must be finite numbers representable in float32.");
        }
        result[i] = row[i];
      }
      return result;
    });
  }

  function project(x, coefficients, bias, first = 0, count = bias.length) {
    const out = new Float32Array(count);
    for (let r = 0; r < count; r++) {
      const start = (first + r) * x.length;
      let sum = bias[first + r];
      for (let i = 0; i < x.length; i++) sum += x[i] * coefficients[start + i];
      out[r] = sum;
    }
    return out;
  }

  function linear(x, layer) {
    return project(x, weights[layer + ".weight"], weights[layer + ".bias"]);
  }

  function add(x, y, offset = 0) {
    const out = new Float32Array(x.length);
    for (let i = 0; i < x.length; i++) out[i] = x[i] + y[offset + i];
    return out;
  }

  function normalize(x, layer) {
    let sum = 0;
    for (const value of x) sum += value;
    const mean = sum / x.length;
    let squared = 0;
    for (const value of x) squared += (value - mean) ** 2;
    const inverse = 1 / Math.sqrt(squared / x.length + 1e-5);
    const scale = weights[layer + ".weight"];
    const shift = weights[layer + ".bias"];
    const out = new Float32Array(x.length);
    for (let i = 0; i < x.length; i++) out[i] = (x[i] - mean) * inverse * scale[i] + shift[i];
    return out;
  }

  // GELU(x) = x * Phi(x). The odd-power series below integrates the normal
  // density. Stop when the next term can no longer change the binary64 sum.
  function gelu(x) {
    if (!Number.isFinite(x)) throw new RangeError("This input exceeds the numerical range of the fitted model.");
    if (x <= -9) return 0;
    if (x >= 9) return x;
    const square = x * x;
    let term = x;
    let sum = x;
    for (let denominator = 3; ; denominator += 2) {
      term *= square / denominator;
      const next = sum + term;
      if (next === sum) break;
      sum = next;
    }
    return x * (0.5 + sum * Math.exp(-square / 2) / Math.sqrt(2 * Math.PI));
  }

  function feedForward(x, layer) {
    const hidden = linear(x, layer + ".linear1");
    for (let i = 0; i < hidden.length; i++) hidden[i] = gelu(hidden[i]);
    return linear(hidden, layer + ".linear2");
  }

  function attentionProjection(x, layer, slot) {
    return project(x, weights[layer + ".in_proj_weight"], weights[layer + ".in_proj_bias"], slot * WIDTH, WIDTH);
  }

  function keyValues(rows, layer) {
    return {
      keys: rows.map(x => attentionProjection(x, layer, 1)),
      values: rows.map(x => attentionProjection(x, layer, 2))
    };
  }

  function attention(x, stored, layer) {
    const q = attentionProjection(x, layer, 0);
    const mixed = new Float32Array(WIDTH);
    const scores = new Float64Array(stored.keys.length);
    for (let head = 0; head < WIDTH; head += HEAD_WIDTH) {
      let max = -Infinity;
      for (let t = 0; t < scores.length; t++) {
        const key = stored.keys[t];
        let dot = 0;
        for (let j = head; j < head + HEAD_WIDTH; j++) dot += q[j] * key[j];
        scores[t] = dot / Math.sqrt(HEAD_WIDTH);
        max = Math.max(max, scores[t]);
      }
      let total = 0;
      for (let t = 0; t < scores.length; t++) {
        scores[t] = Math.exp(scores[t] - max);
        total += scores[t];
      }
      for (let j = head; j < head + HEAD_WIDTH; j++) {
        let sum = 0;
        for (let t = 0; t < scores.length; t++) sum += stored.values[t][j] * scores[t];
        mixed[j] = sum / total;
      }
    }
    return linear(mixed, layer + ".out_proj");
  }

  function ridgePath(rows) {
    const latest = rows[19];
    const design = Array.from(latest);
    for (const lag of [2, 5, 10]) {
      for (let i = 0; i < MOTION; i++) design.push(F32(latest[i] - rows[19 - lag][i]));
    }
    for (let i = 0; i < design.length; i++) {
      design[i] = (design[i] - weights.ridge_input_mean[i]) / weights.ridge_input_scale[i];
    }
    design.push(1);
    const count = TIMES.length * COORDINATES;
    const flat = new Float64Array(count);
    for (let i = 0; i < design.length; i++) {
      for (let j = 0; j < count; j++) flat[j] += design[i] * weights.ridge_weights[i * count + j];
    }
    return TIMES.map((_, t) => Array.from(flat.subarray(t * COORDINATES, (t + 1) * COORDINATES)));
  }

  function encode(rows, ridge) {
    const tokens = rows.map((row, t) => {
      const features = new Float32Array(2 * CHANNELS);
      for (let i = 0; i < MOTION; i++) {
        features[i] = (row[i] - weights.history_mean[i]) / weights.history_scale[i];
        features[CHANNELS + i] = 1;
      }
      return add(linear(features, "observed"), weights.history_pos, t * WIDTH);
    });
    const normalized = tokens.map(x => normalize(x, "encoder.norm1"));
    const projected = keyValues(normalized, "encoder.self_attn");
    const memory = tokens.map((x, t) => {
      const attended = add(x, attention(normalized[t], projected, "encoder.self_attn"));
      const mixed = add(attended, feedForward(normalize(attended, "encoder.norm2"), "encoder"));
      return normalize(mixed, "encoder_norm");
    });
    for (let t = 0; t < TIMES.length; t++) {
      const anchor = Float32Array.from(ridge[t], (value, i) => {
        const j = t * COORDINATES + i;
        return (value - weights.anchor_mean[j]) / weights.anchor_scale[j];
      });
      memory.push(add(linear(anchor, "anchor"), weights.knot_pos, t * WIDTH));
    }
    return keyValues(memory, "decoder.multihead_attn");
  }

  function decodeStep(previous, knot, prefix, memory) {
    const token = add(linear(previous, "future"), weights.knot_pos, knot * WIDTH);
    const normalized = normalize(token, "decoder.norm1");
    // Only the last query is needed. This prefix contains its current and past tokens.
    prefix.keys.push(attentionProjection(normalized, "decoder.self_attn", 1));
    prefix.values.push(attentionProjection(normalized, "decoder.self_attn", 2));
    const causal = add(token, attention(normalized, prefix, "decoder.self_attn"));
    const cross = add(causal, attention(normalize(causal, "decoder.norm2"), memory, "decoder.multihead_attn"));
    const hidden = add(cross, feedForward(normalize(cross, "decoder.norm3"), "decoder"));
    return linear(normalize(hidden, "decoder_norm"), "output");
  }

  function sampleResidual(params, noise) {
    const sample = new Float32Array(COORDINATES);
    let off = 2 * COORDINATES;
    for (let i = 0; i < COORDINATES; i++) {
      const logit = params[COORDINATES + i];
      const diagonal = F32(F32(logit > 20 ? logit : Math.log1p(Math.exp(logit))) + 0.03);
      let value = 0;
      for (let j = 0; j < i; j++) {
        const lower = F32(F32(Math.tanh(params[off++])) * diagonal);
        value += lower * noise[j];
      }
      value += diagonal * noise[i];
      sample[i] = params[i] + F32(value);
    }
    return sample;
  }

  // PCG-XSH-RR 64/32, followed by Box-Muller. Identical explicit Gaussian
  // input can be supplied across runtimes without relying on their RNGs.
  function normals(seed) {
    let state = 0n;
    const increment = 1442695040888963407n;
    function word() {
      const old = state;
      state = BigInt.asUintN(64, old * 6364136223846793005n + increment);
      const shifted = Number(BigInt.asUintN(32, ((old >> 18n) ^ old) >> 27n));
      const rotation = Number(old >> 59n);
      return ((shifted >>> rotation) | (shifted << ((32 - rotation) & 31))) >>> 0;
    }
    word();
    state = BigInt.asUintN(64, state + BigInt(seed));
    word();
    let spare = null;
    return function () {
      if (spare !== null) {
        const value = spare;
        spare = null;
        return value;
      }
      const radius = Math.sqrt(-2 * Math.log((word() + 0.5) / 4294967296));
      const angle = 2 * Math.PI * ((word() + 0.5) / 4294967296);
      spare = radius * Math.sin(angle);
      return radius * Math.cos(angle);
    };
  }

  function predict(historyMm, options = {}) {
    const rows = matrix(historyMm, 20, MOTION, "Motion history");
    if (options === null || typeof options !== "object" || Array.isArray(options)) {
      throw new TypeError("Forecast options must be an object.");
    }
    const {noise, seed = 1117, draws = noise === undefined ? 32 : noise?.length} = options;
    if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) {
      throw new RangeError("The sampling seed must be an unsigned 32-bit integer.");
    }
    if (!Number.isInteger(draws) || draws < 1 || draws > 128) {
      throw new RangeError("Choose between 1 and 128 paths.");
    }
    if (noise !== undefined && (!Array.isArray(noise) || noise.length !== draws)) {
      throw new TypeError("Supply one noise matrix per path.");
    }
    const given = noise === undefined ? null : Array.from(noise, path => matrix(path, TIMES.length, COORDINATES, "Noise"));
    const normal = normals(seed);
    const ridgeMm = ridgePath(rows);
    const memory = encode(rows, ridgeMm);
    const velocity20Mm = TIMES.map(time => Array.from({length: COORDINATES}, (_, i) => {
      const rate = F32(F32(rows[19][i] - rows[17][i]) / 20);
      return F32(rate * time);
    }));
    const meanMm = TIMES.map(() => Array(COORDINATES).fill(0));
    const pathsMm = [];
    for (let d = 0; d < draws; d++) {
      const prefix = {keys: [], values: []};
      const cumulative = new Float64Array(COORDINATES);
      const path = [];
      let previous = new Float32Array(COORDINATES);
      for (let t = 0; t < TIMES.length; t++) {
        const z = given ? given[d][t] : Float32Array.from({length: COORDINATES}, normal);
        previous = sampleResidual(decodeStep(previous, t, prefix, memory), z);
        const displacement = [];
        for (let i = 0; i < COORDINATES; i++) {
          const j = t * COORDINATES + i;
          cumulative[i] += previous[i] * weights.residual_scale[j] + weights.residual_mean[j];
          const mm = F32(ridgeMm[t][i] + cumulative[i]);
          if (!Number.isFinite(mm)) {
            throw new RangeError("This input exceeds the numerical range of the fitted model.");
          }
          displacement.push(mm);
          meanMm[t][i] += mm;
        }
        path.push(displacement);
      }
      pathsMm.push(path);
    }
    for (const row of meanMm) {
      for (let i = 0; i < COORDINATES; i++) row[i] /= draws;
    }
    return {timesMs: TIMES.slice(), pathsMm, meanMm, velocity20Mm, ridgeMm};
  }

  globalThis.ReachForecast = Object.freeze({predict});
})();
