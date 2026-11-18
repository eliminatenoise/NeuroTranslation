(function () {
  "use strict";

  const spec = /* UJI_AXIS_BLEND_SPEC */ null;
  const axes = Object.freeze(spec.axes);
  const weights = Object.freeze(Object.fromEntries(axes.map((axis, index) => [axis, spec.alpha[index]])));
  const source = Object.freeze({
    config_sha256: spec.config_sha256,
    base_model_sha256: spec.base_model_sha256,
    base_archive_sha256: spec.base_archive_sha256,
    design_sha256: spec.design_sha256,
    glossary_revision: spec.glossary_revision,
    glossary_sha256: spec.glossary_sha256,
    target_offset_ms: spec.target_offset_ms,
    output_units: spec.output_units
  });
  const base = globalThis.UJIEngine;

  function requireBlend(condition, message) {
    if (!condition) throw new Error(message);
  }

  function checkBase() {
    const contract = base?.contract;
    requireBlend(typeof base?.infer === "function" &&
      contract?.source?.model_sha256 === source.base_model_sha256 &&
      contract.source.model_archive_sha256 === source.base_archive_sha256 &&
      contract.amplitude_scale === spec.amplitude_scale &&
      contract.output_offset_from_anchor_ms === source.target_offset_ms &&
      Array.isArray(contract.axes) && contract.axes.length === axes.length &&
      axes.every((axis, index) => axis === contract.axes[index]),
    "Load the matching UJI estimator before the blend.");
  }

  function checkAngles(row) {
    requireBlend(row && Object.keys(row).length === axes.length &&
      axes.every(axis => Object.hasOwn(row, axis) && Number.isFinite(row[axis])),
    "The blend needs two finite angles from each UJI model.");
  }

  function interpolate(baseline, augmented, alpha) {
    if (alpha === 0) return baseline;
    if (alpha === 1) return augmented;
    return baseline + alpha * (augmented - baseline);
  }

  function infer(input) {
    checkBase();
    const result = base.infer(input);
    const estimates = result.predictions;
    requireBlend(result.amplitude_scale === spec.amplitude_scale &&
      result.output_offset_from_anchor_ms === source.target_offset_ms &&
      estimates && Object.keys(estimates).length === 2 &&
      Object.hasOwn(estimates, "task_time") && Object.hasOwn(estimates, "task_time_emg"),
    "The blend needs the two estimates from the matching UJI model.");
    const baseline = estimates.task_time;
    const augmented = estimates.task_time_emg;
    checkAngles(baseline);
    checkAngles(augmented);
    const blended = Object.fromEntries(axes.map(axis => [
      axis, interpolate(baseline[axis], augmented[axis], weights[axis])
    ]));
    requireBlend(axes.every(axis => Number.isFinite(blended[axis])),
      "This input falls outside the blend’s finite numerical range.");
    return {
      ...result,
      estimator: "KIN-MUS UJI wrist angle with a separate EMG blend for each axis",
      predictions: { ...estimates, axis_blend: blended },
      emg_blend_weight_by_axis: weights
    };
  }

  checkBase();
  globalThis.UJIAxisBlend = Object.freeze({ infer, weights, source });
})();
