"use strict";

(async () => {
  const status = document.querySelector("#model-status");
  const controls = document.querySelector("#model-controls");
  const recovery = document.querySelector("#model-recovery");
  const examplePicker = document.querySelector("#example");
  const slider = document.querySelector("#emg-offset");
  const offsetOutput = document.querySelector("#emg-offset-value");
  const inputSummary = document.querySelector("#input-summary");
  const rows = Array.from(document.querySelectorAll("#predictions tr[data-head]"), (row) => ({
    head: row.dataset.head,
    axes: row.querySelectorAll("output[data-axis]"),
  }));

  async function fetchBytes(name) {
    const response = await fetch(name, { mode: "same-origin", redirect: "error" });
    if (!response.ok) throw new Error(`Cannot read ${name}`);
    return response.arrayBuffer();
  }

  async function offlineReader() {
    // A file: page cannot fetch neighboring JSON in common desktop browsers.
    // The local script supplies exact bytes, which undergo the same SHA-256 check.
    const script = document.createElement("script");
    script.src = "offline-assets.js";
    await new Promise((resolve, reject) => {
      script.onload = resolve;
      script.onerror = reject;
      document.head.append(script);
    });
    const local = window.WristPointingOffline;
    return (name) => Uint8Array.from(atob(local[name]), (character) => character.charCodeAt(0));
  }

  function showUnavailable() {
    status.dataset.state = "unavailable";
    status.textContent = "The model files couldn’t be read or verified in this browser. The archived scores below are still available.";
    controls.hidden = true;
    recovery.hidden = false;
  }

  function update({ cases, parameters }) {
    const example = cases[examplePicker.value];
    const offset = slider.valueAsNumber;
    const estimates = window.WristPointing.estimate(parameters, example, offset);
    const target = example.cue_offset_ticks / 512;
    const anchorTime = (example.cue_offset_ticks - 128) / 512;
    const m1 = example.bins.map((bin) => bin[2] + offset);

    offsetOutput.value = `+${offset} µV`;
    slider.setAttribute("aria-valuetext", `${offset} nominal archive microvolts added to each M1 bin`);
    inputSummary.textContent = `Target ${target.toFixed(3)} s after cue. Last-known angles at ${anchorTime.toFixed(3)} s were ${example.anchor_deg[0].toFixed(2)}° on the extension axis and ${example.anchor_deg[1].toFixed(2)}° on the radial axis. M1 RMS spans ${Math.min(...m1).toFixed(1)}–${Math.max(...m1).toFixed(1)} nominal archive µV across the bins.`;

    for (const { head, axes } of rows) {
      axes.forEach((output, axis) => {
        const value = estimates[head][axis];
        output.value = `${value.toFixed(3)}°`;
        output.dataset.value = String(value);
      });
    }
  }

  try {
    if (!window.crypto?.subtle) throw new Error("This browser has no secure digest API here");
    status.textContent = "Verifying the model and invented features…";
    const readBytes = location.protocol === "file:" ? await offlineReader() : fetchBytes;
    const model = await window.WristPointing.load(readBytes);
    update(model);
    controls.hidden = false;
    recovery.hidden = true;
    status.dataset.state = "ready";
    status.textContent = "Released weights verified. Forecasts use the invented features below.";

    function onInput() {
      try {
        update(model);
      } catch {
        showUnavailable();
      }
    }

    examplePicker.addEventListener("change", onInput);
    slider.addEventListener("input", onInput);
  } catch {
    showUnavailable();
  }
})();
