"use strict";

(() => {
  const api = globalThis.HygripTrial;
  const weights = globalThis.HYGRIP_TRAIN_WEIGHTS;
  const get = id => document.getElementById(id);
  const status = get("trial-status"), inspect = get("trial-inspect"), slider = get("cutoff");
  const load = get("trial-file"), demo = get("trial-demo"), reveal = get("reveal-target");
  const labels = {force_history: "Force history", aligned: "Force history + EEG", timing: "Cue timing",
    persistence: "Last reading", backward_slope: "Recent slope"};
  const units = value => value.toFixed(6) + " V";
  const plot = globalThis.HygripVoltagePlot?.mount(get("trial-plot"));
  let current, source, request = 0;

  function render() {
    const row = api.replay(current, Number(slider.value), weights);
    const position = row.seconds.toFixed(3) + " s · cutoff " + (Number(slider.value) + 1) + " of " + current.issues.length;
    get("cutoff-value").textContent = position;
    slider.setAttribute("aria-valuetext", position);
    const cards = get("trial-readings");
    cards.replaceChildren();
    for (const [id,label] of Object.entries(labels)) {
      if (!(id in row.predictions)) continue;
      const box=document.createElement("div"), title=document.createElement("dt"), value=document.createElement("dd");
      title.textContent=label; value.textContent=units(row.predictions[id]);
      box.append(title,value); cards.append(box);
    }
    const errors = ["force_history","aligned","timing"].filter(id => id in row.predictions)
      .map(id => labels[id] + " minus later reading " + units(row.predictions[id] - row.observed));
    plot?.show(row.history, row.predictions, status.textContent, reveal.checked ? row.observed : undefined);
    get("trial-outcome").textContent = reveal.checked
      ? source + " at +120 ms: " + units(row.observed) + ". " + errors.join(". ") + "." : "";
  }

  function show(trial, name, kind) {
    current = api.prepare(trial, weights); source = kind;
    slider.max = String(current.issues.length - 1); slider.value = "0"; reveal.checked = false;
    status.textContent = name + " · " + (trial.eeg ? "Force and scalp EEG" : "Force only");
    inspect.hidden = false;
    render();
  }

  function fail(message) {
    plot?.clear();
    current = null; inspect.hidden = true; get("trial-outcome").textContent = ""; status.textContent = message;
  }

  if (!api || !weights || !globalThis.HygripForecast) {
    fail("Trial replay is unavailable. Open the complete browser package."); return;
  }
  demo.disabled = load.disabled = false;
  status.textContent = "Choose a recording or load the invented trial.";
  demo.addEventListener("click", () => {
    ++request; load.value = ""; show(api.invented(), "Invented right-hand trial", "Invented reading");
  });
  load.addEventListener("change", async () => {
    const file = load.files[0]; if (!file) return;
    const token = ++request; fail("Reading trial on this device…");
    try {
      if (file.size > 24*1024*1024) throw new Error("Choose a trial JSON up to 24 MiB.");
      const data = await file.text(); if (token !== request) return;
      show(JSON.parse(data), "Trial from your file", "Supplied reading");
    } catch (error) { if (token === request) fail(error instanceof SyntaxError ? "The file is not valid JSON." : error.message); }
  });
  for (const [element,event] of [[slider,"input"],[reveal,"change"]]) {
    element.addEventListener(event, () => { if (current) try { render(); } catch (e) { fail(e.message); } });
  }
})();
