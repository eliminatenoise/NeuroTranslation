"use strict";

window.WristPointing = (() => {
  const offsets = [384, 512, 640, 768, 896, 1024];
  const binCount = 16;
  const channelCount = 14;
  const headWidths = {
    motion_ridge: 2,
    motion_emg_ridge: 6,
    motion_emg_eeg_ridge: 14,
  };
  const shapes = {
    bins_center: [channelCount],
    bins_scale: [channelCount],
    anchor_center: [2],
    anchor_scale: [2],
    residual_center: [2],
    residual_scale: [2],
    training_timing: [offsets.length, 2],
  };
  for (const [head, width] of Object.entries(headWidths)) {
    shapes[head] = [binCount * width + 2 + offsets.length, 2];
  }

  const caseKeys = ["artificial_start", "artificial_emg_change", "artificial_scalp_change"];
  const assets = {
    "MODEL-STATE.json": {
      length: 30765,
      digest: "507249ad6fd25c87cc55100175cc2e750d03f89fc25e92542a9dc8ab3844bf0e",
    },
    "SYNTHETIC-CASES.json": {
      length: 16016,
      digest: "47fc4a4f4343b158074a0f99c323917f00d5cd12a19149139f218bc09557c082",
    },
  };

  function hasKeys(value, keys) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
      && Object.keys(value).length === keys.length
      && keys.every((key) => Object.hasOwn(value, key));
  }

  function hasShape(value, [length, ...remaining]) {
    if (!Array.isArray(value) || value.length !== length) return false;
    return remaining.length
      ? value.every((item) => hasShape(item, remaining))
      : value.every(Number.isFinite);
  }

  function validateParameters(document) {
    if (document?.schema !== "WristMotion cohort-wide ridge state, format 1"
      || !hasKeys(document.arrays, Object.keys(shapes))) {
      throw new Error("Unexpected WristMotion model format");
    }
    for (const [name, shape] of Object.entries(shapes)) {
      const array = document.arrays[name];
      if (!hasShape(array, shape) || (name.endsWith("_scale") && array.some((value) => value <= 0))) {
        throw new Error(`Invalid model array: ${name}`);
      }
    }
    return document.arrays;
  }

  function validateExample(example) {
    if (!hasKeys(example, ["bins", "anchor_deg", "cue_offset_ticks"])
      || !hasShape(example.bins, [binCount, channelCount])
      || !hasShape(example.anchor_deg, [2])
      || !offsets.includes(example.cue_offset_ticks)
      || example.bins.some((bin) => bin.slice(2, 6).some((value) => value < 0))) {
      throw new Error("Invalid invented wrist example");
    }
  }

  async function verifyAsset(name, bytes) {
    const { length, digest } = assets[name];
    if (bytes.byteLength !== length) throw new Error(`Unexpected asset length: ${name}`);
    const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
    const hex = Array.from(hash, (byte) => byte.toString(16).padStart(2, "0")).join("");
    if (hex !== digest) throw new Error(`Unexpected SHA-256: ${name}`);
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  }

  async function load(readBytes) {
    const [model, cases] = await Promise.all(Object.keys(assets).map(async (name) => (
      verifyAsset(name, await readBytes(name))
    )));
    const parameters = validateParameters(model);
    if (!hasKeys(cases, caseKeys)) throw new Error("Unexpected invented examples");
    Object.values(cases).forEach(validateExample);
    return { parameters, cases };
  }

  function estimate(parameters, example, emgOffset = 0) {
    validateExample(example);
    if (!Number.isInteger(emgOffset) || emgOffset < 0 || emgOffset > 30) {
      throw new Error("M1 RMS adjustment must be an integer from 0 to 30");
    }

    const { bins, anchor_deg: anchor, cue_offset_ticks: tick } = example;
    const normalized = bins.map((bin) => bin.map((value, channel) => {
      const adjusted = channel === 2 ? value + emgOffset : value;
      return (adjusted - parameters.bins_center[channel]) / parameters.bins_scale[channel];
    }));
    const normalizedAnchor = anchor.map((value, axis) => (
      (value - parameters.anchor_center[axis]) / parameters.anchor_scale[axis]
    ));
    const timing = offsets.map((offset) => Number(offset === tick));
    const predictions = {};

    for (const [head, width] of Object.entries(headWidths)) {
      const features = [...normalized.flatMap((bin) => bin.slice(0, width)), ...normalizedAnchor, ...timing];
      const residual = [0, 0];
      for (let index = 0; index < features.length; index += 1) {
        for (let axis = 0; axis < 2; axis += 1) {
          residual[axis] += features[index] * parameters[head][index][axis];
        }
      }
      predictions[head] = residual.map((value, axis) => (
        value * parameters.residual_scale[axis] + parameters.residual_center[axis] + anchor[axis]
      ));
      if (!predictions[head].every(Number.isFinite)) throw new Error("Nonfinite wrist forecast");
    }
    return predictions;
  }

  return Object.freeze({ load, estimate });
})();
