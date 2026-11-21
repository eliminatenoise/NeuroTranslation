/** A two-target NeuroTranslate forecast from prepared camera and optional floor readings. */
export const TARGETS = Object.freeze([
  "four_marker_centre",
  "back_pair_centre",
]);
export const MARKERS = Object.freeze(["Left front", "Right front", "Left back", "Right back"]);
export const TIMES = Object.freeze([-200, -150, -100, -50, 0]);

const WIDTH = 32;
const HEADS = 4;
const INPUT = 19;
const MODEL_VARIANTS = ["mixed", "complete"];
const SEEDS = [11, 23, 37];

const SHAPES = {
  position: [5, 32],
  readout: [32],
  "input.weight": [32, 19],
  "input.bias": [32],
  "norm_attention.weight": [32],
  "norm_attention.bias": [32],
  "attention.in_proj_weight": [96, 32],
  "attention.in_proj_bias": [96],
  "attention.out_proj.weight": [32, 32],
  "attention.out_proj.bias": [32],
  "norm_features.weight": [32],
  "norm_features.bias": [32],
  "features.0.weight": [64, 32],
  "features.0.bias": [64],
  "features.2.weight": [32, 64],
  "features.2.bias": [32],
  "finish.weight": [32],
  "finish.bias": [32],
  "forecast.weight": [2, 32],
  "forecast.bias": [2],
};

function numbers(values, count, positive = false) {
  return Array.isArray(values) && values.length === count &&
    Array.from(values).every(value => Number.isFinite(value) && (!positive || value > 0));
}

function same(values, expected) {
  return Array.isArray(values) && values.length === expected.length &&
    expected.every((value, index) => value === values[index]);
}

function modelError() {
  return new Error("The model files failed their integrity check.");
}

function product(shape) {
  return shape.reduce((total, count) => total * count, 1);
}

export async function decodeModel(manifest, payload) {
  const u = manifest?.scaling;
  if (manifest?.format !== "pelvis-f32-le-1" ||
      !same(manifest.targets, TARGETS) ||
      manifest.horizon_ms !== 100 ||
      !/^[0-9a-f]{40}$/.test(manifest.source_revision) ||
      !same(u?.seeds, SEEDS) ||
      !Array.isArray(u.center) || u.center.length !== 4 ||
      !u.center.every(values => numbers(values, 10)) ||
      !Array.isArray(u.scale) || u.scale.length !== 4 ||
      !u.scale.every(values => numbers(values, 10, true)) ||
      !numbers(u.target_average, 2) || !numbers(u.target_spread, 2, true) ||
      !(payload instanceof ArrayBuffer) || payload.byteLength !== manifest.weights_bytes) {
    throw modelError();
  }

  const digest = await crypto.subtle.digest("SHA-256", payload);
  const hex = [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, "0")).join("");
  if (hex !== manifest.weights_sha256) throw modelError();

  const expected = new Map();
  for (const model of MODEL_VARIANTS) {
    for (const seed of SEEDS) {
      for (const [name, dimensions] of Object.entries(SHAPES)) {
        expected.set(model + "/" + seed + "/" + name, dimensions);
      }
    }
  }

  if (!Array.isArray(manifest.arrays) || manifest.arrays.length !== expected.size) throw modelError();
  const arrays = new Map();
  const data = new DataView(payload);
  let cursor = 0;
  for (const entry of manifest.arrays) {
    const shape = expected.get(entry.name);
    if (shape === undefined || arrays.has(entry.name) || !same(entry.shape, shape) ||
        entry.start !== cursor || entry.bytes !== product(shape) * 4 || cursor + entry.bytes > data.byteLength) {
      throw modelError();
    }
    const output = new Float32Array(entry.bytes / 4);
    for (let i = 0; i < output.length; i++) {
      output[i] = data.getFloat32(cursor + i * 4, true);
      if (!Number.isFinite(output[i])) throw modelError();
    }
    arrays.set(entry.name, output);
    cursor += entry.bytes;
  }
  if (cursor !== data.byteLength) throw modelError();
  const groups = Object.fromEntries(MODEL_VARIANTS.map(variant => [variant, SEEDS.map(seed => {
    return Object.fromEntries(Object.keys(SHAPES).map(name => [
      name, arrays.get(variant + "/" + seed + "/" + name),
    ]));
  })]));

  // Retain only the parsed values and exact source identity in the public API.
  const scaling = structuredClone(u);
  const revision = manifest.source_revision;
  return Object.freeze({
    sourceRevision: revision,
    predict(history, training = "mixed") {
      if (!MODEL_VARIANTS.includes(training)) throw new RangeError("Choose complete or mixed training.");
      const prepared = encodeHistory(history, scaling);
      const sum = [0, 0];
      for (const weights of groups[training]) {
        const normalized = runCheckpoint(prepared, weights);
        for (let i = 0; i < TARGETS.length; i++) {
          sum[i] += normalized[i] * scaling.target_spread[i] + scaling.target_average[i];
        }
      }
      const estimates = sum.map(value => value / SEEDS.length);
      if (!estimates.every(Number.isFinite)) throw new RangeError("Those readings are outside the numeric range.");
      return Object.freeze({
        horizonMs: 100,
        unit: "mm",
        estimates: Object.freeze(Object.fromEntries(TARGETS.map((name, i) => [name, estimates[i]]))),
      });
    },
  });
}

export function validateHistory(history) {
  if (history === null || typeof history !== "object" || Array.isArray(history) ||
      (history.unit !== undefined && history.unit !== "mm") ||
      !Array.isArray(history.heights_mm) || history.heights_mm.length !== TIMES.length ||
      !Array.from(history.heights_mm).every(row => Array.isArray(row) && row.length === MARKERS.length &&
        Array.from(row).every(value => value === null || Number.isFinite(value)))) {
    throw new TypeError("Use five rows of four marker heights in millimetres. Enter null for a missing reading.");
  }
  if (history.heights_mm.at(-1).filter(value => value !== null).length < 2) {
    throw new RangeError("Supply at least two marker heights at 0 ms to make a forecast.");
  }
  if (history.force_log_change !== undefined && !numbers(history.force_log_change, 4)) {
    throw new TypeError("Floor force requires four prepared log-change values.");
  }
  if (history.force_log_change !== undefined && history.force_log_change[0] !== 0) {
    throw new RangeError("The first floor force log change must be zero.");
  }
  return history;
}

export function encodeHistory(history, scale) {
  const {heights_mm: heights, force_log_change: force} = validateHistory(history);
  const issue = heights.at(-1).filter(value => value !== null);
  const origin = issue.reduce((sum, value) => sum + value, 0) / issue.length;
  return heights.slice(1).map((row, i) => {
    const encoded = new Float32Array(INPUT);
    const previous = heights[i];
    for (let j = 0; j < MARKERS.length; j++) {
      const value = row[j];
      if (value === null) continue;
      encoded[j] = (value - origin - scale.center[i][j]) / scale.scale[i][j];
      encoded[10 + j] = 1;
      if (previous[j] !== null) {
        encoded[4 + j] = (value - previous[j] - scale.center[i][4 + j]) / scale.scale[i][4 + j];
        encoded[14 + j] = 1;
      }
    }
    encoded[8] = (origin - scale.center[i][8]) / scale.scale[i][8];
    if (force !== undefined) {
      encoded[9] = (force[i] - scale.center[i][9]) / scale.scale[i][9];
      encoded[18] = 1;
    }
    if (!encoded.every(Number.isFinite)) throw new RangeError("Those readings are outside the numeric range.");
    return encoded;
  });
}

function dense(input, weights, bias) {
  const result = new Float32Array(bias.length);
  for (let i = 0; i < result.length; i++) {
    let total = bias[i];
    const offset = i * input.length;
    for (let j = 0; j < input.length; j++) total += input[j] * weights[offset + j];
    result[i] = total;
  }
  return result;
}

function normalized(row, gain, bias) {
  const mean = row.reduce((sum, value) => sum + value, 0) / row.length;
  const variance = row.reduce((sum, value) => sum + (value - mean) ** 2, 0) / row.length;
  const denominator = Math.sqrt(variance + 1e-5);
  return Float32Array.from(row, (value, i) => (value - mean) / denominator * gain[i] + bias[i]);
}

function add(first, second) {
  return Float32Array.from(first, (value, i) => value + second[i]);
}

function gelu(value) {
  const argument = value / Math.SQRT2;
  const t = 1 / (1 + .3275911 * Math.abs(argument));
  // Five-term erf approximation, verified against the exact GELU in the source forecaster.
  const tail = ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - .284496736) * t + .254829592) * t;
  const erf = Math.sign(argument) * (1 - tail * Math.exp(-argument * argument));
  return .5 * value * (1 + erf);
}

function runCheckpoint(tokens, arrays) {
  const linear = (input, name) => dense(input, arrays[name + ".weight"], arrays[name + ".bias"]);
  const norm = (input, name) => normalized(input, arrays[name + ".weight"], arrays[name + ".bias"]);
  const projected = tokens.map(row => linear(row, "input"));
  const stored = [...projected, arrays.readout].map((row, i) =>
    add(row, arrays.position.subarray(i * WIDTH, (i + 1) * WIDTH)));
  const vectors = stored.map(row => dense(norm(row, "norm_attention"),
    arrays["attention.in_proj_weight"], arrays["attention.in_proj_bias"]));

  // The final token can attend to every earlier token and to itself.
  const query = vectors.at(-1);
  const output = new Float32Array(WIDTH);
  const bits = WIDTH / HEADS;
  for (let head = 0; head < HEADS; head++) {
    const offset = head * bits;
    const scores = vectors.map(row => {
      let product = 0;
      for (let i = offset; i < offset + bits; i++) product += query[i] * row[WIDTH + i];
      return product / Math.sqrt(bits);
    });
    const peak = Math.max(...scores);
    const exponential = scores.map(score => Math.exp(score - peak));
    const total = exponential.reduce((sum, value) => sum + value, 0);
    for (let i = offset; i < offset + bits; i++) {
      output[i] = vectors.reduce((sum, row, j) => sum + exponential[j] * row[2 * WIDTH + i], 0) / total;
    }
  }
  const state = add(stored.at(-1), linear(output, "attention.out_proj"));
  const feature = linear(norm(state, "norm_features"), "features.0").map(gelu);
  const combined = add(state, linear(feature, "features.2"));
  return linear(norm(combined, "finish"), "forecast");
}

export async function loadPelvisModel(directory = new URL(".", import.meta.url)) {
  const fetchAsset = async file => {
    const r = await fetch(new URL(file, directory));
    if (!r.ok) throw new Error("The model files could not be loaded.");
    return r;
  };
  const [spec, data] = await Promise.all([fetchAsset("model.json"), fetchAsset("weights.bin")]);
  return decodeModel(await spec.json(), await data.arrayBuffer());
}
