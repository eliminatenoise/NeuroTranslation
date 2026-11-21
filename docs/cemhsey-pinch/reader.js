"use strict";
(() => {
  const byId = (id) => document.getElementById(id),
    api = globalThis.PinchForecast;
  const bundledFit = globalThis.CEMHSEY_PINCH_FIT;
  let fit = bundledFit,
    fitGeneration = 0;
  const bundledLabel =
    globalThis.CEMHSEY_BUNDLED_FIT_KIND === "local_study"
      ? "Private study model fitted on three participants"
      : "Demonstration model fitted on invented signals";
  let modelLabel = bundledLabel;
  const status = byId("status"),
    cutoff = byId("cutoff"),
    reveal = byId("reveal");
  let trial = null,
    generation = 0,
    inventedTrial = false;
  const fmt = (x) => Number(x).toFixed(4);
  function cells(section, rows) {
    const body = document.createDocumentFragment();
    for (const [label, ...values] of rows) {
      const row = document.createElement("tr"),
        th = document.createElement("th");
      th.scope = "row";
      th.textContent = label;
      row.append(th);
      for (const s of values) {
        const td = row.insertCell();
        td.textContent = s;
      }
      body.append(row);
    }
    section.replaceChildren(body);
  }
  function resetScores() {
    byId("scores").hidden = true;
    byId("scores").tBodies[0].replaceChildren();
    byId("score-status").textContent = "";
  }
  function resetSelection() {
    generation++;
    trial = null;
    inventedTrial = false;
    byId("viewer").hidden = true;
    reveal.checked = false;
    byId("answer").hidden = true;
    byId("answer").textContent = "";
    byId("estimates").replaceChildren();
    byId("input-values").replaceChildren();
    byId("inputs").open = false;
    resetScores();
    return generation;
  }
  function draw(index, pred) {
    const canvas = byId("trace"),
      rect = canvas.getBoundingClientRect(),
      w = rect.width,
      h = rect.height;
    if (w < 10 || h < 10) return;
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    const ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    const shown = trial.rows.slice(Math.max(0, index - 60), index + 1);
    const row = shown[shown.length - 1],
      start = Math.max(0, Math.min(row.issue_tick - 120, shown[0].issue_tick)),
      stop = row.issue_tick + 48;
    const futureTick = row.issue_tick + 24;
    const selected = Object.hasOwn(pred, "history_phase_paired_emg")
      ? "history_phase_paired_emg"
      : "history_phase";
    const targetVisible = reveal.checked && Number.isFinite(row.measured_target);
    const values = [
      ...shown.map((r) => r.force_now),
      pred[selected],
      ...(targetVisible ? [row.measured_target] : []),
    ];
    const low = Math.min(...values),
      high = Math.max(...values),
      pad = Math.max(0.005, (high - low) * 0.17);
    if (
      !Number.isFinite(high - low + 2 * pad) ||
      !Number.isFinite(low - pad) ||
      !Number.isFinite(high + pad)
    )
      throw Error("The force scale in this packet exceeds the chart’s numerical range.");
    const left = 58,
      right = w - 13,
      top = 25,
      bottom = h - 30;
    const x = (t) => left + ((right - left) * (t - start)) / (stop - start);
    const y = (v) => bottom - ((bottom - top) * (v - (low - pad))) / (high - low + 2 * pad);
    ctx.font = "12px sans-serif";
    ctx.lineWidth = 1;
    for (let k = 0; k < 4; k++) {
      const n = low - pad + ((high - low + 2 * pad) * k) / 3;
      ctx.strokeStyle = "#e0e7e1";
      ctx.beginPath();
      ctx.moveTo(left, y(n));
      ctx.lineTo(right, y(n));
      ctx.stroke();
      ctx.fillStyle = "#41534d";
      ctx.fillText(n.toFixed(3), 4, y(n) + 4);
    }
    ctx.strokeStyle = "#496b60";
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(x(row.issue_tick), top);
    ctx.lineTo(x(row.issue_tick), bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.strokeStyle = "#205d53";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    shown.forEach((r, i) =>
      i ? ctx.lineTo(x(r.issue_tick), y(r.force_now)) : ctx.moveTo(x(r.issue_tick), y(r.force_now)),
    );
    ctx.stroke();
    ctx.fillStyle = "#205d53";
    ctx.beginPath();
    ctx.arc(x(row.issue_tick), y(row.force_now), 3, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = "#ad581d";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x(row.issue_tick), y(row.force_now));
    ctx.lineTo(x(futureTick), y(pred[selected]));
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#a94c14";
    ctx.beginPath();
    ctx.arc(x(futureTick), y(pred[selected]), 4, 0, 2 * Math.PI);
    ctx.fill();
    if (targetVisible) {
      ctx.strokeStyle = "#222c29";
      ctx.lineWidth = 2;
      ctx.strokeRect(x(futureTick) - 4, y(row.measured_target) - 4, 8, 8);
    }
    ctx.fillStyle = "#40564d";
    ctx.fillText((start / 200).toFixed(2) + " s", left, bottom + 20);
    const label = "cutoff";
    ctx.fillText(label, Math.max(left, x(row.issue_tick) - ctx.measureText(label).width), top - 7);
    const futureLabel = (futureTick / 200).toFixed(2) + " s";
    const futureX = x(futureTick);
    ctx.textAlign = "center";
    ctx.fillText(futureLabel, futureX, bottom + 20);
    ctx.textAlign = "left";
    ctx.strokeStyle = "#526759";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(futureX, bottom);
    ctx.lineTo(futureX, bottom + 5);
    ctx.stroke();
    canvas.setAttribute(
      "aria-label",
      (inventedTrial ? "Invented force" : "Measured force") +
        " through the cutoff and the " +
        api.labels[selected] +
        " forecast at " +
        (futureTick / 200).toFixed(2) +
        " seconds (+24 ticks). Current " +
        fmt(row.force_now) +
        ", forecast " +
        fmt(pred[selected]) +
        (targetVisible
          ? (inventedTrial ? ", invented later force " : ", measured later force ") +
            fmt(row.measured_target)
          : "") +
        ".",
    );
  }
  function fillInputs(row) {
    const box = byId("input-values");
    box.replaceChildren();
    if (!byId("inputs").open) return;
    const table = document.createElement("table"),
      caption = table.createCaption();
    caption.textContent = "Inputs through this cutoff";
    const rows = [
      ["Current force", fmt(row.force_now)],
      ...[5, 10, 20, 40].map((t, i) => ["Force change over " + t * 5 + " ms", fmt(row.force_deltas[i])]),
    ];
    if (row.emg_summaries) {
      [
        "−300 to −200 ms · median",
        "−300 to −200 ms · 90th percentile",
        "−200 to −100 ms · median",
        "−200 to −100 ms · 90th percentile",
      ].forEach((label, i) => rows.push([label, fmt(row.emg_summaries[i])]));
    }
    cells(table.createTBody(), rows);
    box.append(table);
    if (row.emg_summaries) {
      const p = document.createElement("p");
      p.textContent =
        "Each window gives 320 channel RMS values in mV. Take their median and 90th percentile first, then compute log(1 + summary / 1 mV) for each.";
      box.append(p);
    }
  }
  function display() {
    if (!trial) return;
    const index = Number(cutoff.value),
      row = trial.rows[index],
      pred = api.forecast(fit, row);
    cutoff.setAttribute(
      "aria-valuetext",
      (row.issue_tick / 200).toFixed(2) + " seconds from trial start",
    );
    byId("time").textContent =
      (row.issue_tick / 200).toFixed(2) + " s → " + ((row.issue_tick + 24) / 200).toFixed(2) + " s";
    byId("phase").textContent =
      api.phaseAt(row.issue_tick).name +
      " · " +
      (index + 1) +
      " of " +
      trial.rows.length +
      " cutoffs. The orange point is the " +
      (pred.history_phase_paired_emg === undefined
        ? "force-history and cue-phase"
        : "force, cue-phase and EMG") +
      " forecast.";
    byId("model-in-use").textContent = modelLabel + ".";
    cells(
      byId("estimates"),
      Object.entries(pred).map(([key, v]) => [api.labels[key], fmt(v)]),
    );
    reveal.disabled = !Number.isFinite(row.measured_target);
    if (reveal.disabled) reveal.checked = false;
    byId("answer").hidden = !reveal.checked;
    byId("answer").textContent = reveal.checked
      ? (inventedTrial ? "Invented later force is " : "Measured normalized force is ") +
        fmt(row.measured_target)
      : "";
    fillInputs(row);
    draw(index, pred);
  }
  function show(packet, source) {
    trial = api.checkTrial(packet, fit);
    inventedTrial = source === "Invented example";
    cutoff.value = "160";
    reveal.checked = false;
    byId("viewer").hidden = false;
    resetScores();
    status.textContent =
      source +
      " · " +
      (trial.timing_mode === "force_only"
        ? "Force data only."
        : fit.models.history_phase_paired_emg
          ? "Force and forearm summaries available."
          : "The packet contains forearm summaries. This fit uses only force and cue phase.");
    byId("score-help").textContent =
      "Scoring reveals aggregate errors against all 592 " +
      (inventedTrial ? "invented later values" : "later force readings") +
      " in this trial. Smaller errors are better. Moving the cutoff hides these scores again.";
    display();
  }
  function clearError(message) {
    resetSelection();
    status.textContent = message;
  }
  byId("example").addEventListener("click", () => {
    resetSelection();
    byId("file").value = "";
    try {
      show(api.invented(fit), "Invented example");
    } catch (e) {
      clearError(e.message);
    }
  });
  byId("file").addEventListener("change", async (event) => {
    const file = event.currentTarget.files[0];
    if (!file) return;
    const token = resetSelection();
    status.textContent = "Reading the local packet…";
    try {
      if (file.size > 2 * 1024 * 1024)
        throw Error(
          "Choose a compact JSON packet under 2 MiB. Convert an original MAT file locally first.",
        );
      const packet = JSON.parse(await file.text());
      if (token !== generation) return;
      show(packet, "Local trial packet");
    } catch (e) {
      if (token === generation)
        clearError(
          e instanceof SyntaxError
            ? "The selected file is not a readable JSON trial packet."
            : e.message,
        );
    }
  });
  function safeDisplay() {
    try {
      display();
    } catch (e) {
      clearError(e.message);
    }
  }
  cutoff.addEventListener("input", () => {
    reveal.checked = false;
    resetScores();
    safeDisplay();
  });
  reveal.addEventListener("change", safeDisplay);
  byId("inputs").addEventListener("toggle", safeDisplay);
  byId("score").addEventListener("click", () => {
    try {
      const scores = api.score(fit, trial.rows);
      cells(
        byId("scores").tBodies[0],
        Object.entries(scores).map(([key, v]) => [api.labels[key], fmt(v.mae), fmt(v.rmse)]),
      );
      byId("scores").hidden = false;
      const demo = fit === bundledFit && globalThis.CEMHSEY_BUNDLED_FIT_KIND !== "local_study";
      byId("score-status").textContent =
        (inventedTrial ? "Invented example · " : "") +
        "592 matched cutoffs." +
        (inventedTrial || demo
          ? " " +
            (demo ? "The model was fitted on invented signals" : "The trial is invented") +
            ", so these errors are illustrative and say nothing about the study result. On real recordings from four test people, forearm EMG moved the average miss from 0.4634% to 0.4632% of the hardest pinch."
          : "");
    } catch (e) {
      resetScores();
      byId("score-status").textContent = e.message;
    }
  });
  function useFit(next, label) {
    // Cancel pending trial reads before changing the model used to interpret them.
    generation++;
    fit = next;
    modelLabel = label;
    reveal.checked = false;
    resetScores();
    byId("model-status").textContent = label + ".";
    byId("reset-model").disabled = next === bundledFit;
    if (trial) {
      const note =
        trial.timing_mode === "nominal_release_index" && !fit.models.history_phase_paired_emg
          ? " Forearm summaries are present; this model uses force and cue phase only."
          : "";
      status.textContent = (inventedTrial ? "Invented example" : "Local trial packet") + note;
      safeDisplay();
    } else {
      status.textContent = "Choose a local packet or try the invented example.";
    }
  }
  byId("reset-model").addEventListener("click", () => {
    fitGeneration++;
    byId("model-file").value = "";
    useFit(bundledFit, bundledLabel);
  });
  byId("model-file").addEventListener("change", async (event) => {
    const file = event.currentTarget.files[0];
    if (!file) return;
    const token = ++fitGeneration;
    byId("reset-model").disabled = false;
    byId("model-status").textContent = "Checking the local model…";
    try {
      if (file.size > 128 * 1024) throw Error("Choose a compact fitted model under 128 KiB.");
      const next = api.checkFit(JSON.parse(await file.text()));
      if (token !== fitGeneration) return;
      if (next.protocol_sha256 !== bundledFit.protocol_sha256)
        throw Error("This model belongs to a different protocol.");
      useFit(next, "Locally supplied model");
    } catch (e) {
      if (token !== fitGeneration) return;
      byId("model-status").textContent =
        "Could not load this model. " +
        (e instanceof SyntaxError ? "Invalid JSON." : e.message) +
        " Active model: " +
        modelLabel +
        ".";
      byId("reset-model").disabled = fit === bundledFit;
    }
  });
  window.addEventListener("resize", safeDisplay);
  try {
    api.checkFit(fit);
    byId("model-file").disabled = false;
    byId("model-status").textContent = bundledLabel + ".";
    byId("example").disabled = false;
    byId("file").disabled = false;
    status.textContent = "Ready. Choose a local packet or try the invented example.";
  } catch (e) {
    status.textContent = "The fitted weights could not be loaded. Open the complete reader folder.";
  }
})();
