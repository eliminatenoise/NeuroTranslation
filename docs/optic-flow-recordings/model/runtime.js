/* Frozen optic-flow forecast. JavaScript Number and Float64Array arithmetic. */
(function (root) {
  "use strict";

  const MODES = ["camera_only", "command", "earlier_command"];
  const LINEAR_NAMES = ["camera_only", "camera_and_command", "camera_and_earlier_command_control"];
  const METHODS = Object.freeze([
    "recent_variation", "linear_camera", "linear_command", "linear_earlier_command",
    "transformer_camera", "transformer_command", "transformer_earlier_command"
  ]);
  const D = 24;
  const HEADS = 4;
  const HEAD_DIM = D / HEADS;
  const FF = 48;
  const LAYERS = 2;
  const TOKENS = 15;
  const EPS = 1e-5;
  const BIN_BOUNDS = [-0.20, -0.15, -0.10, -0.05, 0];
  const BIN_AGES = [0.175, 0.125, 0.075, 0.025];
  const LAGS = [5, 4, 3, 2, 1, 0.5, 0.2, 0.1, 0.05, 0];
  const CASE_FIELDS = [
    "valid", "case_id", "issue_s", "camera_stats_rad", "recent_spread_rad", "camera_first_s", "camera_last_s",
    "camera_closed_s", "command_codes", "command_sample_s", "command_closed_s", "earlier_command_codes",
    "earlier_command_sample_s", "earlier_command_closed_s", "command_max_age_s", "clock_tolerance_s"
  ];

  function require(ok, text) {
    if (!ok) throw new Error(text);
  }

  function keysAre(object, keys) {
    return object !== null && typeof object === "object" && !Array.isArray(object)
      && Object.keys(object).length === keys.length && keys.every(key => Object.hasOwn(object, key));
  }

  function vector(value, size, isValid = Number.isFinite) {
    return Array.isArray(value) && value.length === size && Array.from(value).every(isValid);
  }

  function validateCase(input) {
    require(input !== null && typeof input === "object" && !Array.isArray(input)
      && typeof input.valid === "boolean" && Object.hasOwn(input, "valid"), "A case needs an explicit boolean valid flag.");
    if (!input.valid) {
      require(Object.keys(input).every(key => CASE_FIELDS.includes(key)), "Unexpected masked case field.");
      return false;
    }
    require(keysAre(input, CASE_FIELDS), "A valid case needs exactly the documented earlier input fields.");
    const issue = input.issue_s;
    const tolerance = input.clock_tolerance_s;
    require(Number.isSafeInteger(input.case_id) && input.case_id >= 0 && Number.isFinite(issue)
      && issue === input.case_id * 0.32, "The issue time must be the exact case ID times 0.32 seconds.");
    require(Number.isFinite(tolerance) && tolerance >= 0 && tolerance <= 1e-11
      && Number.isFinite(input.command_max_age_s) && input.command_max_age_s > 0, "The clock tolerance or display age limit is invalid.");
    require(Number.isFinite(input.recent_spread_rad) && input.recent_spread_rad >= 0
      && vector(input.camera_stats_rad, 4, row => vector(row, 2) && row[1] >= 0), "Camera means and spreads must be finite, and spreads must be nonnegative.");
    const first = input.camera_first_s;
    const last = input.camera_last_s;
    const closed = input.camera_closed_s;
    require([first, last, closed].every(v => vector(v, 4)), "Four finite camera timestamp sets are required.");
    for (let i = 0; i < 4; i++) {
      require(first[i] >= (issue + BIN_BOUNDS[i]) - tolerance && first[i] < last[i]
        && last[i] < (issue + BIN_BOUNDS[i + 1]) - tolerance && closed[i] > last[i]
        && closed[i] <= issue + tolerance, "A camera bin or closing timestamp crosses its earlier time bounds.");
    }
    for (const [name, offset] of [["command", 0], ["earlier_command", 6]]) {
      const values = input[name + "_codes"];
      const times = input[name + "_sample_s"];
      const closes = input[name + "_closed_s"];
      require([values, times, closes].every(v => vector(v, 10)), "Each display history requires ten finite values and timestamp pairs.");
      for (let i = 0; i < 10; i++) {
        const cutoff = issue - LAGS[i] - offset;
        require(times[i] <= cutoff + tolerance && cutoff - times[i] <= input.command_max_age_s + tolerance
          && times[i] < closes[i] && closes[i] <= issue + tolerance, "A display sample or its closing timestamp is late or stale.");
      }
    }
    return true;
  }

  function expectedTensors() {
    const schema = {
      "camera_value.weight": [D, 2], "camera_value.bias": [D],
      "command_value.weight": [D, 1], "command_value.bias": [D],
      "issue_value.weight": [D, 1], "issue_value.bias": [D],
      "time_value.weight": [D, 3], "token_type.weight": [3, D], "unit_type.weight": [2, D]
    };
    for (let i = 0; i < LAYERS; i++) {
      const name = "context.layers." + i + ".";
      for (const [key, shape] of Object.entries({
        "self_attn.in_proj_weight": [3 * D, D], "self_attn.in_proj_bias": [3 * D],
        "self_attn.out_proj.weight": [D, D], "self_attn.out_proj.bias": [D],
        "linear1.weight": [FF, D], "linear1.bias": [FF], "linear2.weight": [D, FF], "linear2.bias": [D],
        "norm1.weight": [D], "norm1.bias": [D], "norm2.weight": [D], "norm2.bias": [D]
      })) schema[name + key] = shape;
    }
    schema["readout.weight"] = [1, D];
    schema["readout.bias"] = [1];
    return schema;
  }

  function readWeights(arm) {
    const schema = expectedTensors();
    require(keysAre(arm, ["tensors", "little_endian_float64_base64"]) && Array.isArray(arm.tensors)
      && arm.tensors.length === Object.keys(schema).length, "Invalid Transformer weight directory.");
    require(typeof arm.little_endian_float64_base64 === "string" && arm.little_endian_float64_base64.length === 108044,
      "Invalid encoded weight size.");
    const raw = atob(arm.little_endian_float64_base64);
    require(raw.length === 10129 * 8, "Invalid decoded weight size.");
    const byteArray = Uint8Array.from(raw, c => c.charCodeAt(0));
    const bits = new DataView(byteArray.buffer);
    let offset = 0;
    const tensors = Object.create(null);
    let i = 0;
    for (const [key, shape] of Object.entries(schema)) {
      const row = arm.tensors[i++];
      require(keysAre(row, ["key", "shape"]) && row.key === key && vector(row.shape, shape.length)
        && row.shape.every((value, axis) => value === shape[axis]), "Unexpected Transformer tensor scalar shape.");
      const size = shape.reduce((a, b) => a * b, 1);
      const values = new Float64Array(size);
      for (let j = 0; j < size; j++, offset += 8) {
        values[j] = bits.getFloat64(offset, true);
        require(Number.isFinite(values[j]), "Nonfinite Transformer coefficient.");
      }
      tensors[key] = values;
    }
    require(offset === raw.length, "Incomplete Transformer weight byte readback.");
    return tensors;
  }

  function linear(x, weight, bias, width) {
    const output = new Float64Array(width);
    for (let row = 0; row < width; row++) {
      let sum = 0;
      for (let col = 0, base = row * x.length; col < x.length; col++) sum += x[col] * weight[base + col];
      output[row] = sum + (bias === undefined ? 0 : bias[row]);
    }
    return output;
  }

  function projected(weights, name, x, width) {
    return linear(x, weights[name + ".weight"], weights[name + ".bias"], width);
  }

  function layerNorm(x, scale, offset) {
    let mean = 0;
    for (const value of x) mean += value;
    mean /= x.length;
    let variance = 0;
    for (const value of x) variance += (value - mean) ** 2;
    const inv = 1 / Math.sqrt(variance / x.length + EPS);
    return x.map((value, i) => (value - mean) * inv * scale[i] + offset[i]);
  }

  // Erf power series near zero and the regularized upper incomplete gamma
  // continued fraction for its positive tail. GELU uses the exact CDF form.
  function gelu(x) {
    const z = Math.abs(x) / Math.SQRT2;
    let lowerTail;
    if (z <= 2) {
      let sum = z;
      let term = z;
      for (let n = 1; n <= 80; n++) {
        term *= -(z * z) / n;
        const add = term / (2 * n + 1);
        sum += add;
        if (Math.abs(add) <= 2e-17) break;
      }
      lowerTail = 0.5 - sum / Math.sqrt(Math.PI);
    } else if (z > 28) {
      lowerTail = 0;
    } else {
      const y = z * z;
      let b = y + 0.5;
      let c = 1e300;
      let d = 1 / b;
      let h = d;
      for (let i = 1; i <= 200; i++) {
        const a = -i * (i - 0.5);
        b += 2;
        c = b + a / c;
        d = 1 / (b + a * d);
        const ratio = c * d;
        h *= ratio;
        if (Math.abs(ratio - 1) <= 2e-16) break;
      }
      lowerTail = 0.5 * Math.exp(-y + 0.5 * Math.log(y) - 0.5 * Math.log(Math.PI)) * h;
    }
    return x * (x < 0 ? lowerTail : 1 - lowerTail);
  }

  function attention(qkv, active, query) {
    const context = new Float64Array(D);
    for (let h = 0; h < HEADS; h++) {
      const start = h * HEAD_DIM;
      const logits = new Float64Array(active.length);
      let max = -Infinity;
      for (let k = 0; k < active.length; k++) {
        const key = qkv[active[k]];
        let dot = 0;
        for (let d = start; d < start + HEAD_DIM; d++) dot += qkv[query][d] * key[D + d];
        logits[k] = dot / Math.sqrt(HEAD_DIM);
        max = Math.max(logits[k], max);
      }
      let total = 0;
      for (let k = 0; k < active.length; k++) {
        logits[k] = Math.exp(logits[k] - max);
        total += logits[k];
      }
      for (let k = 0; k < active.length; k++) {
        const probability = logits[k] / total;
        const values = qkv[active[k]];
        for (let d = start; d < start + HEAD_DIM; d++) context[d] += probability * values[2 * D + d];
      }
    }
    return context;
  }

  function encoderLayer(weights, name, tokens, active) {
    const qkv = tokens.map(token => {
      const norm = layerNorm(token, weights[name + "norm1.weight"], weights[name + "norm1.bias"]);
      return linear(norm, weights[name + "self_attn.in_proj_weight"], weights[name + "self_attn.in_proj_bias"], 3 * D);
    });
    return tokens.map((token, i) => {
      const attended = projected(weights, name + "self_attn.out_proj", attention(qkv, active, i), D);
      const afterAttention = token.map((v, j) => v + attended[j]);
      const norm = layerNorm(afterAttention, weights[name + "norm2.weight"], weights[name + "norm2.bias"]);
      const hidden = projected(weights, name + "linear1", norm, FF).map(gelu);
      const feedforward = projected(weights, name + "linear2", hidden, D);
      return afterAttention.map((v, j) => v + feedforward[j]);
    });
  }

  function token(weights, valueName, type, unit, value, times) {
    const data = projected(weights, valueName, value, D);
    const time = projected(weights, "time_value", times.map(v => v / 11), D);
    return data.map((v, i) => v + time[i] + weights["token_type.weight"][type * D + i] + weights["unit_type.weight"][unit * D + i]);
  }

  function transformer(input, mode, weights) {
    const issue = input.issue_s;
    const shift = mode === "earlier_command" ? 6 : 0;
    const prefix = shift ? "earlier_command" : "command";
    const maskCommands = mode === "camera_only";
    const tokens = input.camera_stats_rad.map((summary, i) => token(weights, "camera_value", 0, 0, summary,
      [BIN_AGES[i], issue - input.camera_last_s[i], input.camera_last_s[i] - input.camera_first_s[i]]));
    for (let i = 0; i < 10; i++) {
      const lag = LAGS[i] + shift;
      const age = issue - input[prefix + "_sample_s"][i];
      tokens.push(token(weights, "command_value", 1, 1, [maskCommands ? 0 : input[prefix + "_codes"][i]],
        maskCommands ? [0, 0, 0] : [lag, age, age - lag]));
    }
    tokens.push(token(weights, "issue_value", 2, 0, [input.recent_spread_rad], [0, 0, 0]));
    const active = maskCommands ? [0, 1, 2, 3, 14] : Array.from({ length: TOKENS }, (_, i) => i);
    let context = tokens;
    for (let layer = 0; layer < LAYERS; layer++) context = encoderLayer(weights, "context.layers." + layer + ".", context, active);
    const correction = projected(weights, "readout", context[14], 1)[0];
    return Math.max(input.recent_spread_rad + correction, 0);
  }

  function residual(input, model) {
    let total = 0;
    for (let i = 0; i < input.length; i++) {
      if (model.varying[i]) total += ((input[i] - model.average[i]) / model.scale[i]) * model.weight[i + 1];
    }
    return model.weight[0] + total;
  }

  function prepare(bundle) {
    require(keysAre(bundle, ["format", "transformers", "linear"]) && bundle.format === "zebrafish-optic-flow-fp64-v1"
      && keysAre(bundle.transformers, MODES) && keysAre(bundle.linear, LINEAR_NAMES), "Unexpected frozen weight bundle.");
    const decoded = MODES.map(mode => readWeights(bundle.transformers[mode]));
    const models = LINEAR_NAMES.map((key, index) => {
      const model = bundle.linear[key];
      const size = index === 0 ? 8 : 18;
      require(keysAre(model, ["average", "scale", "varying", "weight"]) && vector(model.average, size)
        && vector(model.scale, size, value => Number.isFinite(value) && value > 0)
        && vector(model.varying, size, flag => typeof flag === "boolean") && vector(model.weight, size + 1), "Invalid linear coefficients.");
      return Object.fromEntries(Object.entries(model).map(([name, values]) => [name, values.slice()]));
    });
    return { decoded, models };
  }

  const provided = root.ZebrafishModelWeights || (typeof module === "object" && module.exports ? requireWeights() : null);
  function requireWeights() {
    return module.require("./weights.js");
  }
  const { decoded, models } = prepare(provided);

  function predict(input) {
    if (!validateCase(input)) return null;
    const base = input.recent_spread_rad;
    const camera = input.camera_stats_rad.flat();
    const regressors = [camera, camera.concat(input.command_codes), camera.concat(input.earlier_command_codes)];
    const predictions = [base, ...models.map((model, i) => Math.max(base + residual(regressors[i], model), 0)),
      ...MODES.map((mode, i) => transformer(input, mode, decoded[i]))];
    require(predictions.every(v => Number.isFinite(v) && v >= 0), "The supplied values did not produce finite nonnegative spreads.");
    return Object.fromEntries(METHODS.map((method, index) => [method, predictions[index]]));
  }

  function predictCases(inputs) {
    require(Array.isArray(inputs), "Expected an ordered case array.");
    return Array.from(inputs, predict);
  }

  const api = Object.freeze({ methodNames: METHODS, predict, predictCases, validateCase });
  root.ZebrafishForecast = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(globalThis);
