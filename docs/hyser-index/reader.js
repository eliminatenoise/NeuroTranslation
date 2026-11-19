"use strict";
(() => {
  const el = (id) => document.getElementById(id);
  const model = globalThis.HyserForecast,
    wfdb = globalThis.HyserWFDB,
    weights = globalThis.HYSER_WEIGHTS;
  const files = el("files"),
    folder = el("folder"),
    example = el("example"),
    selector = el("trial");
  const slider = el("cutoff"),
    reveal = el("reveal"),
    plot = el("plot"),
    status = el("record-status");
  let generation = 0,
    choices = [],
    record = null,
    row = null,
    predictions = null,
    inputName = "";
  const volts = (v) =>
    Math.abs(v) >= 1e5 || (v !== 0 && Math.abs(v) < 1e-6)
      ? v.toExponential(5)
      : v.toFixed(6);
  function clearForecast(message) {
    record = null;
    row = null;
    predictions = null;
    el("controls").hidden = true;
    el("window").hidden = true;
    el("unavailable").hidden = false;
    el("unavailable").textContent = message;
    el("outcome").textContent = "";
    el("predictions").replaceChildren();
    plot.removeAttribute("aria-label");
    plot.width = plot.width;
    el("history").querySelector("tbody").replaceChildren();
    el("muscle").querySelector("tbody").replaceChildren();
  }
  function tables() {
    for (const name of ["history", "muscle"]) {
      const details = el(name),
        body = details.querySelector("tbody");
      body.replaceChildren();
      if (!row || !details.open || (name === "muscle" && !row.emg)) continue;
      const rows =
        name === "history"
          ? row.force.map((v, i) => [(i - 40) * 10, volts(v)])
          : Array.from({ length: 4 }, (_, i) => [
              -420 + 100 * i,
              ...row.emg
                .slice(i * 5, i * 5 + 4)
                .map((v) => (1000 * Math.exp(v)).toFixed(4)),
            ]);
      for (const values of rows) {
        const tr = body.insertRow();
        for (const value of values) tr.insertCell().textContent = String(value);
      }
    }
  }
  function renderPlot() {
    if (!row || !predictions) return;
    const target = reveal.checked ? row.observed : null;
    plot.setAttribute(
      "aria-label",
      inputName +
        ". History runs from 400 ms before cutoff to cutoff. Force-history forecast at +120 ms is " +
        volts(predictions.force) +
        " V." +
        (predictions.aligned === undefined
          ? ""
          : " With EMG it is " + volts(predictions.aligned) + " V.") +
        (target === null
          ? ""
          : " Later sensor reading " + volts(target) + " V."),
    );
    const width = plot.clientWidth,
      height = plot.clientHeight;
    if (!width || !height) return;
    const ctx = plot.getContext("2d");
    if (!ctx) {
      plot.hidden = true;
      return;
    }
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    plot.width = Math.round(width * dpr);
    plot.height = Math.round(height * dpr);
    ctx.scale(plot.width / width, plot.height / height);
    ctx.font = "12px " + getComputedStyle(plot).fontFamily;
    const all = [...row.force, predictions.force];
    if (predictions.aligned !== undefined) all.push(predictions.aligned);
    if (target !== null) all.push(target);
    const amplitude = Math.max(...all.map(Math.abs)) || 1;
    let low = Math.min(...all.map((v) => v / amplitude)),
      high = Math.max(...all.map((v) => v / amplitude));
    if (low === high) {
      low -= 0.02;
      high += 0.02;
    }
    const ticks = [low, (low + high) * 0.5, high];
    const labels = ticks.map((v) => volts(v * amplitude));
    const left = Math.max(...labels.map((t) => ctx.measureText(t).width)) + 11,
      right = width - 28,
      top = 24,
      bottom = height - 27;
    if (right <= left) return;
    const x = (ms) => left + ((ms + 400) * (right - left)) / 520,
      y = (n) => bottom - 8 - ((n - low) * (bottom - top - 16)) / (high - low);
    function line(x0, y0, x1, y1, stroke, dash = []) {
      ctx.beginPath();
      ctx.strokeStyle = stroke;
      ctx.setLineDash(dash);
      ctx.lineWidth = 1;
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.fillStyle = "#e7edf7";
    ctx.fillRect(x(0), top, right - x(0) + 10, bottom - top);
    ctx.fillStyle = "#263f38";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText("Sensor voltage (V)", 3, 12);
    ticks.forEach((t, i) => {
      line(left, y(t), right, y(t), "#c6d4ca");
      ctx.fillText(labels[i], 3, y(t));
    });
    line(x(0), top, x(0), bottom, "#5a7069", [3, 3]);
    ctx.textAlign = "center";
    const cutoffText = x(120) - x(0) > 45 ? "Cutoff" : "0";
    for (const k of right - left > 140
      ? [-400, -200, 0, 120]
      : [-400, 0, 120]) {
      ctx.fillText(
        k === 120 ? "+120 ms" : k === 0 ? cutoffText : "−" + Math.abs(k),
        x(k),
        bottom + 14,
      );
    }
    ctx.beginPath();
    row.force.forEach((v, i) => {
      const px = x((i - 40) * 10),
        py = y(v / amplitude);
      if (i) ctx.lineTo(px, py);
      else ctx.moveTo(px, py);
    });
    ctx.lineWidth = 2.4;
    ctx.strokeStyle = "#15594e";
    ctx.stroke();
    const fx = x(120),
      fy = y(predictions.force / amplitude);
    ctx.fillStyle = "#31549b";
    ctx.beginPath();
    ctx.moveTo(fx, fy - 6);
    ctx.lineTo(fx + 6, fy);
    ctx.lineTo(fx, fy + 6);
    ctx.lineTo(fx - 6, fy);
    ctx.closePath();
    ctx.fill();
    if (predictions.aligned !== undefined) {
      ctx.fillStyle = "#8f4811";
      ctx.fillRect(fx - 3, y(predictions.aligned / amplitude) - 3, 6, 6);
    }
    if (target !== null) {
      ctx.beginPath();
      ctx.arc(fx, y(target / amplitude), 8, 0, Math.PI * 2);
      ctx.strokeStyle = "#46374f";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }
  function showOutcome() {
    if (!row) return;
    el("outcome").textContent = !reveal.checked
      ? ""
      : row.observed === null
        ? "The later voltage is missing at this cutoff."
        : (inputName === "Invented trial"
            ? "Invented later reading "
            : "Supplied later reading ") +
          volts(row.observed) +
          " V. Force-history forecast minus that reading " +
          volts(predictions.force - row.observed) +
          " V." +
          (predictions.aligned === undefined
            ? ""
            : " With EMG, " +
              volts(predictions.aligned - row.observed) +
              " V.");
    el("target-key").hidden = !reveal.checked || row.observed === null;
    renderPlot();
  }
  function render() {
    if (!record) return;
    const issue = Number(slider.value);
    const t =
      (issue / 100).toFixed(2) +
      " s · cutoff " +
      ((issue - model.first) / model.step + 1) +
      " of 450";
    el("moment").textContent = t;
    slider.setAttribute("aria-valuetext", t);
    try {
      row = model.windowAt(record, issue);
      predictions = model.predict(row, weights);
      const cards = el("predictions");
      cards.replaceChildren();
      for (const [id, label] of [
        ["force", "Force history"],
        ["aligned", "Force history + EMG"],
        ["persistence", "Last voltage"],
      ]) {
        if (!(id in predictions)) continue;
        const card = document.createElement("div"),
          title = document.createElement("dt"),
          value = document.createElement("dd");
        title.textContent = label;
        value.textContent = volts(predictions[id]) + " V";
        card.append(title, value);
        cards.append(card);
      }
      el("emg-key").hidden = !row.emg;
      el("muscle").hidden = !row.emg;
      const msg =
        record.raw && !row.emg
          ? "The muscle window contains missing samples. The force forecast is available."
          : "";
      el("unavailable").textContent = msg;
      el("unavailable").hidden = !msg;
      el("window").hidden = false;
      showOutcome();
      tables();
    } catch (e) {
      row = null;
      predictions = null;
      el("window").hidden = true;
      el("unavailable").hidden = false;
      el("unavailable").textContent = e.message;
      el("outcome").textContent = "";
      el("predictions").replaceChildren();
      plot.removeAttribute("aria-label");
      plot.width = plot.width;
      tables();
    }
  }
  function show(rec, name) {
    record = rec;
    inputName = name;
    slider.value = String(model.first);
    reveal.checked = false;
    el("controls").hidden = false;
    status.textContent =
      name + (rec.raw ? " · force and raw forearm EMG" : " · force only");
    render();
  }
  async function openTrial() {
    const token = ++generation,
      entry = choices[Number(selector.value)];
    if (!entry) return;
    const valid = () => token === generation;
    clearForecast("Checking the original WFDB files on this device…");
    status.textContent = "Opening trial " + entry.trial + "…";
    try {
      const force = await wfdb.loadPair(entry, "force", valid);
      if (!valid()) return;
      const raw = entry.files["raw.hea"]
        ? await wfdb.loadPair(entry, "raw", valid)
        : null;
      if (!valid()) return;
      show({ force, raw }, "Trial " + entry.trial + " from your files");
    } catch (e) {
      if (valid()) {
        status.textContent = "Trial could not be opened.";
        clearForecast(e.message);
      }
    }
  }
  function choose(input) {
    if (!input.files.length) return;
    ++generation;
    choices = [];
    selector.replaceChildren();
    el("trial-label").hidden = true;
    try {
      choices = wfdb.catalogue([...input.files]);
      for (const [i, ent] of choices.entries())
        selector.add(new Option("Trial " + ent.trial, String(i)));
      el("trial-label").hidden = choices.length < 2;
      selector.value = "0";
      openTrial();
    } catch (e) {
      status.textContent = "No recording selected.";
      clearForecast(e.message);
    }
  }
  function invented() {
    ++generation;
    files.value = "";
    folder.value = "";
    choices = [];
    selector.replaceChildren();
    el("trial-label").hidden = true;
    show(model.invented(), "Invented trial");
  }
  if (!wfdb || !model?.validFit(weights)) {
    clearForecast(
      "The reader requires the matching model and scripts. Extract the complete package and reopen it.",
    );
    status.textContent = "Model unavailable.";
    return;
  }
  files.addEventListener("change", () => {
    folder.value = "";
    choose(files);
  });
  folder.addEventListener("change", () => {
    files.value = "";
    choose(folder);
  });
  selector.addEventListener("change", openTrial);
  example.addEventListener("click", invented);
  slider.addEventListener("input", render);
  reveal.addEventListener("change", showOutcome);
  for (const name of ["muscle", "history"])
    el(name).addEventListener("toggle", tables);
  if (typeof ResizeObserver === "function")
    new ResizeObserver(renderPlot).observe(plot);
  else window.addEventListener("resize", renderPlot);
  for (const control of [files, folder, example]) control.disabled = false;
  invented();
})();
