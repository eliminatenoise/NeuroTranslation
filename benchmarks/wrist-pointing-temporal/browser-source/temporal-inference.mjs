import { recordedCommitments } from "./recorded-commitments.mjs";
import { temporalCheckpoint } from "./temporal-weights.mjs";

const schema = "wrist-recorded-trial.v1";
const sampleRateHz = 512;
const offsetSamples = [384, 512, 640, 768, 896, 1024];
const axisOrder = ["extension", "radial_deviation"];
const channelOrder = [
  "extension_relative_to_anchor", "radial_deviation_relative_to_anchor",
  "C3", "C1", "Cz", "C2", "C4", "CP3", "CPz", "CP4",
];
const sourceBinding = {
  depositDoi: "10.6084/m9.figshare.29666735.v3",
  roleManifestSha256: "eb957afdefd86ede0072a327292ca7b51a123bf4c46d7ed295914d9d5097b92b",
  archiveManifestSha256: "ca9193680afe9d0eabd578acbd1684f91699a6d2d94cef4e731cd9f767194862",
};
const sha256Pattern = /^[0-9a-f]{64}$/;
const archiveTickLimit = 2 ** 32;
const seeds = [17, 29, 43];
const methodNames = ["motion", "combined"];
const binCount = 16;
const binWidth = channelOrder.length;
const axisCount = axisOrder.length;
const convWidth = 16;
const kernelWidth = 3;
const denseWidth = 32;
const flattenedSize = convWidth * (binCount - 2 * (kernelWidth - 1));
const auxiliarySize = axisCount + offsetSamples.length;
const acceptedDigests = new Set(recordedCommitments.sha256);
let fittedModels;

function recordWithKeys(value, keys) {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
}

function sameVector(value, expected) {
  return Array.isArray(value) && value.length === expected.length &&
    expected.every((item, index) => value[index] === item);
}

function isDigest(value) {
  return typeof value === "string" && value.length === 64 && sha256Pattern.test(value);
}

function isArchiveTick(value) {
  return Number.isInteger(value) && value >= 0 && value < archiveTickLimit;
}

function numericVector(value, length, minimum, maximum) {
  if (!Array.isArray(value) || value.length !== length) {
    throw new Error("The recorded trial has incomplete angles or signal bins.");
  }
  const copy = new Array(length);
  for (let index = 0; index < length; index++) {
    const number = value[index];
    if (!Number.isFinite(number) || number < minimum(index) || number > maximum(index)) {
      throw new Error("The recorded trial has an invalid angle or signal value.");
    }
    copy[index] = number === 0 ? 0 : number;
  }
  return copy;
}

function copyAngles(value) {
  return numericVector(value, axisCount, () => -180, () => 180);
}

function copyBin(value) {
  // A difference of two eligible encoder angles spans at most 360 degrees.
  // EEG means lie within the verified original signed-word microvolt range.
  return numericVector(value, binWidth,
    channel => channel < axisCount ? -360 : -32768,
    channel => channel < axisCount ? 360 : 32767);
}

function readTrial(packet) {
  const packetKeys = ["schema", "role", "sampleRateHz", "axisOrder", "channelOrder",
    "source", "rows", "measuredDegrees", "contentSha256"];
  if (!recordWithKeys(packet, packetKeys) || packet.schema !== schema ||
      packet.role !== "development" || packet.sampleRateHz !== sampleRateHz ||
      !sameVector(packet.axisOrder, axisOrder) || !sameVector(packet.channelOrder, channelOrder)) {
    throw new Error("Choose a WristMotion v3 development trial from the matching converter.");
  }
  const contentSha256 = packet.contentSha256;
  const source = packet.source;
  const sourceKeys = [...Object.keys(sourceBinding), "sourceRunSha256", "fitSealSha256",
    "designSha256", "cueTick", "returnTick", "targetTicks"];
  if (!isDigest(contentSha256) ||
      !recordWithKeys(source, sourceKeys) ||
      Object.entries(sourceBinding).some(([key, expected]) => source[key] !== expected) ||
      source.fitSealSha256 !== temporalCheckpoint.fitSealSha256 ||
      source.designSha256 !== temporalCheckpoint.designSha256 ||
      !isDigest(source.sourceRunSha256)) {
    throw new Error("The trial belongs to a different study or checkpoint.");
  }
  const { cueTick, returnTick, sourceRunSha256 } = source;
  if (!isArchiveTick(cueTick) || !isArchiveTick(returnTick)) {
    throw new Error("The recorded trial has invalid cue or target timing.");
  }
  const targetTicks = offsetSamples.map(offset => cueTick + offset);
  if (targetTicks.at(-1) >= returnTick || !sameVector(source.targetTicks, targetTicks)) {
    throw new Error("The recorded trial has invalid cue or target timing.");
  }
  if (!Array.isArray(packet.rows) || packet.rows.length !== offsetSamples.length ||
      !Array.isArray(packet.measuredDegrees) || packet.measuredDegrees.length !== offsetSamples.length) {
    throw new Error("The recorded trial must contain all six target times.");
  }
  const rows = offsetSamples.map((offset, index) => {
    const row = packet.rows[index];
    if (!recordWithKeys(row, ["offsetSamples", "anchorDegrees", "bins"]) ||
        row.offsetSamples !== offset || !Array.isArray(row.bins) || row.bins.length !== binCount) {
      throw new Error("The recorded trial has incomplete or out-of-order forecast inputs.");
    }
    const bins = Array.from({ length: binCount }, (_, bin) => copyBin(row.bins[bin]));
    return { bins, anchorDegrees: copyAngles(row.anchorDegrees),
      measuredDegrees: copyAngles(packet.measuredDegrees[index]) };
  });
  return { rows, cueTick, returnTick, targetTicks, sourceRunSha256, contentSha256 };
}

async function verifyTrial(trial) {
  if (!acceptedDigests.has(trial.contentSha256)) {
    throw new Error("This trial does not match the verified development recordings.");
  }
  const text = [schema, "development", sampleRateHz, axisOrder.join(","), channelOrder.join(","),
    sourceBinding.depositDoi, sourceBinding.roleManifestSha256, sourceBinding.archiveManifestSha256,
    trial.sourceRunSha256, temporalCheckpoint.fitSealSha256, temporalCheckpoint.designSha256,
    trial.cueTick, trial.returnTick, trial.targetTicks.join(","), offsetSamples.join(","), ""];
  const prefix = new TextEncoder().encode(text.join("\n"));
  const numbersPerRow = axisCount * 2 + binCount * binWidth;
  const bytes = new Uint8Array(prefix.length + 8 * offsetSamples.length * numbersPerRow);
  bytes.set(prefix);
  const view = new DataView(bytes.buffer);
  let position = prefix.length;
  function writeValues(values) {
    for (const value of values) {
      view.setFloat64(position, value, true);
      position += 8;
    }
  }
  for (const row of trial.rows) {
    writeValues(row.anchorDegrees);
    for (const bin of row.bins) writeValues(bin);
  }
  for (const row of trial.rows) writeValues(row.measuredDegrees);

  if (!globalThis.crypto?.subtle) {
    throw new Error("This browser cannot verify local recordings. Open the HTTPS preview or use a current browser.");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  if (hex !== trial.contentSha256) {
    throw new Error("The recorded trial has changed since it was verified.");
  }
}

function readModel(encoded, channels) {
  const bytes = Uint8Array.from(atob(encoded), byte => byte.charCodeAt(0));
  const view = new DataView(bytes.buffer);
  const parameters = new Float32Array(bytes.length / 4);
  for (let index = 0; index < parameters.length; index++) {
    parameters[index] = view.getFloat32(index * 4, true);
  }
  let position = 0;
  function layer(inputs, outputs, kernel = 1) {
    const weightEnd = position + inputs * outputs * kernel;
    const biasEnd = weightEnd + outputs;
    const weights = parameters.subarray(position, weightEnd);
    const biases = parameters.subarray(weightEnd, biasEnd);
    position = biasEnd;
    return { weights, biases };
  }
  const firstConv = layer(channels, convWidth, kernelWidth);
  const secondConv = layer(convWidth, convWidth, kernelWidth);
  const hidden = layer(flattenedSize + auxiliarySize, denseWidth);
  const output = layer(denseWidth, axisCount);
  if (position * 4 !== bytes.length || !parameters.every(Number.isFinite)) {
    throw new Error("The browser's frozen checkpoint is incomplete.");
  }
  return { channels, firstConv, secondConv, hidden, output };
}

function getFittedModels() {
  fittedModels ??= Object.fromEntries(methodNames.map((method, index) => {
    const channels = index === 0 ? axisCount : binWidth;
    const models = seeds.map(seed => readModel(temporalCheckpoint.models[method][seed], channels));
    return [method, models];
  }));
  return fittedModels;
}

function convRelu(input, channels, length, { weights, biases }) {
  const outputLength = length - kernelWidth + 1;
  const result = new Float32Array(biases.length * outputLength);
  for (let output = 0; output < biases.length; output++) {
    for (let sample = 0; sample < outputLength; sample++) {
      let sum = biases[output];
      for (let channel = 0; channel < channels; channel++) {
        const inputStart = channel * length + sample;
        const weightStart = (output * channels + channel) * kernelWidth;
        for (let tick = 0; tick < kernelWidth; tick++) {
          sum += input[inputStart + tick] * weights[weightStart + tick];
        }
      }
      result[output * outputLength + sample] = Math.max(0, sum);
    }
  }
  return result;
}

function linear(input, { weights, biases }, relu) {
  const result = new Float32Array(biases.length);
  for (let output = 0; output < biases.length; output++) {
    let sum = biases[output];
    const weightStart = output * input.length;
    for (let index = 0; index < input.length; index++) {
      sum += input[index] * weights[weightStart + index];
    }
    result[output] = relu ? Math.max(0, sum) : sum;
  }
  return result;
}

function standardize(row, offsetIndex) {
  const scale = temporalCheckpoint.normalization;
  const bins = new Float32Array(binWidth * binCount);
  const auxiliary = new Float32Array(auxiliarySize);
  for (let channel = 0; channel < binWidth; channel++) {
    for (let bin = 0; bin < binCount; bin++) {
      bins[channel * binCount + bin] =
        (row.bins[bin][channel] - scale.bins_center[channel]) / scale.bins_scale[channel];
    }
  }
  for (let axis = 0; axis < axisCount; axis++) {
    auxiliary[axis] = (row.anchorDegrees[axis] - scale.anchor_center[axis]) / scale.anchor_scale[axis];
  }
  auxiliary[axisCount + offsetIndex] = 1;
  return { bins, auxiliary };
}

function predict(row, { bins, auxiliary }, model) {
  const first = convRelu(bins, model.channels, binCount, model.firstConv);
  const second = convRelu(first, convWidth, binCount - kernelWidth + 1, model.secondConv);
  const denseInput = new Float32Array(flattenedSize + auxiliarySize);
  denseInput.set(second);
  denseInput.set(auxiliary, flattenedSize);
  const hidden = linear(denseInput, model.hidden, true);
  const prediction = linear(hidden, model.output, false);
  const { residual_scale, residual_center } = temporalCheckpoint.normalization;
  const degrees = row.anchorDegrees.map((angle, axis) =>
    angle + prediction[axis] * residual_scale[axis] + residual_center[axis]);
  if (!degrees.every(Number.isFinite)) throw new Error("The frozen model produced an invalid angle.");
  return degrees;
}

function forecastRow(row, index, models) {
  const inputs = standardize(row, index);
  const forecasts = Object.fromEntries(methodNames.map(method => {
    const predictions = models[method].map(model => predict(row, inputs, model));
    const bySeed = Object.fromEntries(seeds.map((seed, position) => [seed, predictions[position]]));
    const meanDegrees = axisOrder.map((_, axis) =>
      predictions.reduce((sum, prediction) => sum + prediction[axis], 0) / seeds.length);
    return [method, { bySeed, meanDegrees }];
  }));
  return { offsetSamples: offsetSamples[index], timeSeconds: offsetSamples[index] / sampleRateHz,
    measuredDegrees: row.measuredDegrees, anchorDegrees: row.anchorDegrees, forecasts };
}

export async function forecastRecordedTrial(packet) {
  // Snapshot the numbers before the asynchronous digest so the authenticated values are
  // the same values used for inference and returned as measured angles.
  const trial = readTrial(packet);
  await verifyTrial(trial);
  const models = getFittedModels();
  return {
    provenance: {
      role: "development",
      depositDoi: sourceBinding.depositDoi,
      sampleRateHz,
      axisOrder: [...axisOrder],
      leadSamples: 128,
      modelEdition: "wrist-pointing-temporal-r1",
      fitSealSha256: temporalCheckpoint.fitSealSha256,
      designSha256: temporalCheckpoint.designSha256,
      publicArchiveSha256: temporalCheckpoint.publicArchiveSha256,
      commitmentCatalogueSha256: recordedCommitments.fileSha256,
      glossaryRevision: 36,
      glossarySha256: "40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406",
      seeds: [...seeds],
    },
    rows: trial.rows.map((row, index) => forecastRow(row, index, models)),
  };
}
