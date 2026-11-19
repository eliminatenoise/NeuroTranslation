"use strict";

(() => {
  const weights = globalThis.HYGRIP_TRAIN_WEIGHTS;
  const model = globalThis.HygripForecast;
  const values = document.getElementById("readings");
  const detail = document.getElementById("detail");
  const description = document.getElementById("input-description");
  const error = document.getElementById("error");
  const fileInput = document.getElementById("input-window");
  const exampleButton = document.getElementById("example");
  const downloadButton = document.getElementById("download");
  const plot = globalThis.HygripVoltagePlot?.mount(document.getElementById("window-plot"));
  let importGeneration = 0;
  const labels = {
    timing: "Cue timing",
    force_history: "Force history",
    aligned: "Force history + EEG",
    persistence: "Last force reading",
    backward_slope: "Recent force slope",
  };

  function showError(message, name, instructions) {
    plot?.clear();
    values.replaceChildren();
    description.textContent = name;
    detail.textContent = instructions;
    error.textContent = message;
  }

  function show(input, name) {
    try {
      const predictions = model.predict(input, weights);
      const cards = Object.entries(labels)
        .filter(([branch]) => predictions[branch] !== undefined)
        .map(([branch, label]) => {
          const group = document.createElement("div");
          const title = document.createElement("dt");
          const reading = document.createElement("dd");
          title.textContent = label;
          reading.textContent = predictions[branch].toFixed(8) + " V";
          group.append(title, reading);
          return group;
        });
      description.textContent = name;
      values.replaceChildren(...cards);
      detail.textContent = "Target is force sample " + (input.issueForceIndex + 6) + "."
        + (input.eeg ? " EEG window ends at device sample " + input.eeg.endIndex + "." : "");
      error.textContent = "";
      plot?.show(input.forceV, predictions, name);
      return true;
    } catch (problem) {
      showError(problem.message, name, "Choose a valid window to get a forecast.");
      return false;
    }
  }

  if (!weights || typeof model?.invented !== "function" || typeof model?.predict !== "function") {
    showError("The forecast could not load a required model file.", "Forecast unavailable",
      "Extract the complete package, keep the files together, and reopen this page.");
    return;
  }

  let example;
  try {
    example = model.invented(weights);
  } catch {
    showError("The forecast could not read the packaged model.", "Forecast unavailable",
      "Extract the complete package and reopen this page.");
    return;
  }

  function showExample() {
    importGeneration += 1;
    fileInput.value = "";
    return show(example, "Invented right-hand example");
  }

  if (!showExample()) return;
  for (const control of [fileInput, exampleButton, downloadButton]) control.disabled = false;

  exampleButton.addEventListener("click", showExample);
  fileInput.addEventListener("change", async event => {
    const request = ++importGeneration;
    const file = event.target.files[0];
    if (!file) return;
    const name = "Window from your computer";
    const instructions = "Choose a valid window to get a forecast.";
    if (file.size > 1024 * 1024) {
      showError("Supply one JSON window no larger than 1 MiB.", name, instructions);
      return;
    }
    plot?.clear();
    values.replaceChildren();
    description.textContent = name;
    detail.textContent = "Reading the window…";
    error.textContent = "";
    try {
      const text = await file.text();
      if (request === importGeneration) show(JSON.parse(text), name);
    } catch {
      if (request === importGeneration) {
        showError("The file could not be read as JSON.", name, instructions);
      }
    }
  });
  downloadButton.addEventListener("click", () => {
    const contents = JSON.stringify(example);
    const url = URL.createObjectURL(new Blob([contents], {type: "application/json"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "invented-hygrip-window.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
})();
