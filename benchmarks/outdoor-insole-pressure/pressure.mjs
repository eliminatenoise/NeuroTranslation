const CHANNELS = 16;
const FOOT_CHANNELS = 8;
const FRAMES = 13;

function checkedHistory(history, channels) {
  if (!Array.isArray(history) || history.length !== FRAMES ||
      history.some(row => !Array.isArray(row) || row.length !== channels ||
        row.some(reading => !Number.isFinite(reading)))) {
    throw new TypeError(`Expected ${FRAMES} rows of ${channels} finite pressure readings in mbar.`);
  }
}

function dot(weights, values, offset) {
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += weights[offset + i] * values[i];
  }
  return sum;
}

function sigmoid(value) {
  return 1 / (1 + Math.exp(-value));
}

function recurrent(history, model) {
  const width = model.outputWeights.length / CHANNELS;
  let state = new Float64Array(width);
  let next = new Float64Array(width);
  for (const input of history) {
    for (let i = 0; i < width; i++) {
      const reset = sigmoid(
        dot(model.inputWeights, input, i * CHANNELS) + model.inputBias[i] +
        dot(model.hiddenWeights, state, i * width) + model.hiddenBias[i]
      );
      const updateRow = i + width;
      const update = sigmoid(
        dot(model.inputWeights, input, updateRow * CHANNELS) + model.inputBias[updateRow] +
        dot(model.hiddenWeights, state, updateRow * width) + model.hiddenBias[updateRow]
      );
      const candidateRow = i + 2 * width;
      const candidate = Math.tanh(
        dot(model.inputWeights, input, candidateRow * CHANNELS) + model.inputBias[candidateRow] +
        reset * (dot(model.hiddenWeights, state, candidateRow * width) + model.hiddenBias[candidateRow])
      );
      next[i] = (1 - update) * candidate + update * state[i];
    }
    [state, next] = [next, state];
  }
  return state;
}

function output(model, normalized, last, firstChannel) {
  const hidden = recurrent(normalized, model);
  return last.map((reading, index) => {
    const channel = firstChannel + index;
    const estimate = dot(model.outputWeights, hidden, channel * hidden.length) + model.outputBias[channel];
    return reading + estimate * model.changeScale[channel] + model.changeMean[channel];
  });
}

/** Inputs are 13 regularly spaced 60 Hz frames, oldest to newest, for one foot. */
export function forecastFoot(history, side, weights) {
  checkedHistory(history, FOOT_CHANNELS);
  if (side !== "left" && side !== "right") {
    throw new TypeError("Choose left or right foot.");
  }
  const firstChannel = side === "left" ? 0 : FOOT_CHANNELS;
  const model = weights.sameFoot;
  const normalized = history.map(row => {
    const full = new Float64Array(CHANNELS);
    row.forEach((reading, index) => {
      const channel = firstChannel + index;
      full[channel] = (reading - model.mean[channel]) / model.scale[channel];
    });
    return full;
  });
  return output(model, normalized, history[FRAMES - 1], firstChannel);
}

/** Inputs use all 16 sensors, with the left foot first in each frame. */
export function forecastBothFeet(history, weights) {
  checkedHistory(history, CHANNELS);
  const model = weights.bothFeet;
  const normalized = history.map(row => row.map((reading, i) => (reading - model.mean[i]) / model.scale[i]));
  return output(model, normalized, history[FRAMES - 1], 0);
}
