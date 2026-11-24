const SEEDS = [104, 211, 389];
const GRU_METHODS = ["walking_gru_residual", "mixed_gru_residual", "mixed_gru_direct"];
const STATE_SIZE = 24;

export function decodeWeights(records) {
  const tensors = new Map();
  for (const [name, record] of Object.entries(records)) {
    const buffer = Uint8Array.from(atob(record.little_endian_base64), value => value.charCodeAt(0));
    const size = record.shape.reduce((a, b) => a * b, 1);
    const words = new DataView(buffer.buffer);
    const single = record.dtype === "float32";
    const bytes = single ? 4 : 8;
    if ((!single && record.dtype !== "float64") || size * bytes !== buffer.byteLength) {
      throw new Error("A stored weight has an invalid shape or data type.");
    }
    const values = single ? new Float32Array(size) : new Float64Array(size);
    for (let i = 0; i < size; i++) {
      values[i] = single ? words.getFloat32(i * bytes, true) : words.getFloat64(i * bytes, true);
    }
    tensors.set(name, values);
  }
  return tensors;
}

function dot(weights, offset, state) {
  let total = 0;
  for (let i = 0; i < state.length; i++) total += weights[offset + i] * state[i];
  return total;
}

function sigmoid(value) {
  return 0.5 * (1 + Math.tanh(value * 0.5));
}

function recurrentMember(readings, tensors, name, seed) {
  const prefix = `${name}/${seed}/`;
  const input = tensors.get(prefix + "history.weight_ih_l0");
  const hidden = tensors.get(prefix + "history.weight_hh_l0");
  const inputBias = tensors.get(prefix + "history.bias_ih_l0");
  const hiddenBias = tensors.get(prefix + "history.bias_hh_l0");
  let state = new Float32Array(STATE_SIZE);
  let next = new Float32Array(STATE_SIZE);
  const fromInput = new Float32Array(3 * STATE_SIZE);
  const fromState = new Float32Array(3 * STATE_SIZE);
  for (const reading of readings) {
    for (let j = 0; j < fromInput.length; j++) {
      fromInput[j] = Math.fround(reading * input[j]) + inputBias[j];
      fromState[j] = Math.fround(dot(hidden, j * STATE_SIZE, state)) + hiddenBias[j];
    }
    for (let j = 0; j < STATE_SIZE; j++) {
      const z = j + STATE_SIZE;
      const n = z + STATE_SIZE;
      const reset = sigmoid(Math.fround(fromInput[j] + fromState[j]));
      const retain = sigmoid(Math.fround(fromInput[z] + fromState[z]));
      const proposed = Math.tanh(Math.fround(fromInput[n] + Math.fround(reset * fromState[n])));
      next[j] = (1 - retain) * proposed + retain * state[j];
    }
    [state, next] = [next, state];
  }
  const head = tensors.get(prefix + "head.weight");
  const bias = tensors.get(prefix + "head.bias")[0];
  const output = Math.fround(Math.fround(dot(head, 0, state)) + bias);
  return 100 * (name.endsWith("_residual") ? Math.fround(output + readings.at(-1)) : output);
}

// Each learned recurrent method returns its three forecasts in training-seed order.
// The page averages these forecasts. The two physical rules and ridge methods have one value.
export function forecastMembers(values, weights) {
  if (values.length !== 10 || !Array.from(values).every(Number.isFinite)) {
    throw new RangeError("Enter ten finite force values in newtons.");
  }
  const normalized = Array.from(values, value => value / 1000);
  const single = Float32Array.from(normalized);
  if (!single.every(Number.isFinite)) throw new RangeError("A force value exceeds the model’s numeric range.");
  const latest = values[9], previous = values[8];
  const methods = {
    persistence: [latest * 0.1],
    recent_trend: [(latest + 3 * (latest - previous)) * 0.1],
  };
  for (const name of ["walking_ridge", "mixed_ridge"]) {
    const coefficients = weights.get(name);
    methods[name] = [(normalized[9] + dot(coefficients, 0, normalized) + coefficients[10]) * 100];
  }
  for (const name of GRU_METHODS) {
    methods[name] = SEEDS.map(seed => recurrentMember(single, weights, name, seed));
  }
  if (!Object.values(methods).every(row => row.every(Number.isFinite))) {
    throw new RangeError("A force value exceeds the model’s numeric range.");
  }
  return methods;
}
