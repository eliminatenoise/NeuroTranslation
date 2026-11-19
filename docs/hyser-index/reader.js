"use strict";
(() => {
  const el = (id) => document.getElementById(id);
  const model = globalThis.HyserForecast,
    wfdb = globalThis.HyserWFDB,
    personal = globalThis.HyserPersonalize,
    weights = globalThis.HYSER_WEIGHTS;
  const files = el("files"),
    folder = el("folder"),
    example = el("example"),
    selector = el("trial");
  const mode = el("mode"),
    dayOnePicker = el("day-one"),
    fitButton = el("fit"),
    crossExample = el("cross-example"),
    clearRecordings = el("clear-recordings"),
    fitStatus = el("fit-status");
  const slider = el("cutoff"),
    reveal = el("reveal"),
    plot = el("plot"),
    status = el("record-status");
  let generation = 0,
    fitGeneration = 0,
    scoreGeneration = 0,
    choices = [],
    record = null,
    row = null,
    predictions = null,
    inputName = "",
    dayOne = null,
    dayTwo = null,
    calibration = null,
    fitting = false,
    workedExample = false;
  const crossDay = () => mode.value === "crossday";
  const models = [
    ["force", "Force history"],
    ["aligned", "Force history + EMG"],
  ];
  const volts = (v) =>
    Math.abs(v) >= 1e5 || (v !== 0 && Math.abs(v) < 1e-6)
      ? v.toExponential(5)
      : v.toFixed(6);
  function clearScores() {
    scoreGeneration++;
    el("score").hidden = true;
    el("score-table").hidden = true;
    el("score-status").textContent = "";
    el("score-rows").replaceChildren();
    el("score-changes").hidden = true;
    el("score-changes").replaceChildren();
  }
  function clearForecast(message) {
    clearScores();
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
    const target = row.observed;
    plot.setAttribute(
      "aria-label",
      inputName +
        ". History runs from 400 ms before cutoff to cutoff. Force-history forecast at +120 ms is " +
        volts(predictions.force) +
        " V." +
        (predictions.aligned === undefined
          ? ""
          : " With EMG it is " + volts(predictions.aligned) + " V.") +
        (predictions.forceOwn === undefined
          ? ""
          : " Personalized force-history forecast " + volts(predictions.forceOwn) + " V.") +
        (predictions.alignedOwn === undefined
          ? ""
          : " Personalized with EMG " + volts(predictions.alignedOwn) + " V.") +
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
    for (const key of ["aligned", "forceOwn", "alignedOwn"]) {
      if (predictions[key] !== undefined) all.push(predictions[key]);
    }
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
    if (predictions.forceOwn !== undefined) {
      const py = y(predictions.forceOwn / amplitude);
      ctx.beginPath();
      ctx.moveTo(fx, py - 8);
      ctx.lineTo(fx + 8, py);
      ctx.lineTo(fx, py + 8);
      ctx.lineTo(fx - 8, py);
      ctx.closePath();
      ctx.strokeStyle = "#31549b";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    if (predictions.alignedOwn !== undefined) {
      ctx.strokeStyle = "#8f4811";
      ctx.lineWidth = 2;
      ctx.strokeRect(fx - 5, y(predictions.alignedOwn / amplitude) - 5, 10, 10);
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
    if (!row || !record || !predictions) return;
    row.observed = reveal.checked ? model.observationAt(record, row.issue) : null;
    el("outcome").textContent = !reveal.checked
      ? ""
      : row.observed === null
        ? "The later voltage is missing at this cutoff."
        : (workedExample
            ? "Invented Day 2 reading "
            : inputName === "Invented trial"
              ? "Invented later reading "
              : crossDay() ? "Observed Day 2 reading " : "Supplied later reading ") +
          volts(row.observed) +
          " V. " +
          [...models, ["forceOwn", "Personalized force"], ["alignedOwn", "Personalized with EMG"]]
            .filter(([key]) => predictions[key] !== undefined)
            .map(([key, label]) => label + " error " + volts(predictions[key] - row.observed) + " V.")
            .join(" ");
    el("target-key").hidden = !reveal.checked || row.observed === null;
    renderPlot();
  }
  const millivolts = (v) => (v * 1000).toFixed(3);
  async function evaluateTrial() {
    clearScores();
    if (!crossDay() || !reveal.checked || !calibration || !record) return;
    const token = scoreGeneration;
    const valid = () => token === scoreGeneration;
    el("score").hidden = false;
    el("score-status").textContent = "Comparing Day 2 forecasts with the recorded later values…";
    try {
      await model.yieldFrame();
      if (!valid()) return;
      const scores = await personal.scoreTrial(record, calibration, weights, valid);
      if (!valid()) return;
      for (const [arm, label] of models) {
        const score = scores[arm];
        if (!score?.count) continue;
        const tr = el("score-rows").insertRow();
        const th = document.createElement("th");
        th.scope = "row";
        th.textContent = label;
        tr.append(th);
        const values = [
          score.count + " / " + personal.windowsPerTrial,
          millivolts(score.baseMae), millivolts(score.ownMae),
          millivolts(score.baseRmse), millivolts(score.ownRmse),
        ];
        for (const value of values) tr.insertCell().textContent = value;
        const difference = millivolts(Math.abs(score.baseMae - score.ownMae));
        const direction = difference === "0.000"
          ? "matched the population MAE to 0.001 mV."
          : (score.ownMae < score.baseMae ? "reduced" : "raised") + " MAE by " + difference + " mV.";
        const li = document.createElement("li");
        li.textContent = label + " · Day 1 calibration " + direction;
        el("score-changes").append(li);
      }
      const any = el("score-rows").rows.length > 0;
      el("score-status").textContent = any
        ? "Each row compares both forecasts on the same available cutoffs. " +
          (workedExample ? "These two days were invented." : "These errors cover this Day 2 trial.")
        : "No Day 2 cutoff in this trial has both a forecast and its later reading.";
      el("score-table").hidden = !any;
      el("score-changes").hidden = !any;
    } catch (error) {
      if (valid()) el("score-status").textContent = error.message;
    }
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
      row = model.windowAt(record, issue, { observe: false });
      predictions = model.predict(row, weights);
      if (calibration) {
        for (const [key] of models) {
          if (key in predictions && calibration.fits[key]) {
            predictions[key + "Own"] = personal.apply(predictions.persistence, predictions[key], calibration.fits[key]);
          }
        }
      }
      const cards = el("predictions");
      cards.replaceChildren();
      for (const [id, label] of [
        ["force", crossDay() ? "Population · force history" : "Force history"],
        ["forceOwn", "Personalized · force history"],
        ["aligned", crossDay() ? "Population · force history + EMG" : "Force history + EMG"],
        ["alignedOwn", "Personalized · force history + EMG"],
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
      el("personal-force-key").hidden = predictions.forceOwn === undefined;
      el("personal-emg-key").hidden = predictions.alignedOwn === undefined;
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
    reveal.disabled = crossDay() && !calibration;
    el("controls").hidden = false;
    status.textContent =
      name + (rec.raw ? " · force and raw forearm EMG" : " · force only");
    render();
  }
  async function loadTrialFiles(entry, valid, readRaw = true) {
    const force = await wfdb.loadPair(entry, "force", valid);
    if (!valid()) return null;
    const raw = readRaw && entry.files["raw.hea"]
      ? await wfdb.loadPair(entry, "raw", valid)
      : null;
    return valid() ? { force, raw } : null;
  }
  async function openTrial() {
    const token = ++generation,
      entry = choices[Number(selector.value)];
    if (!entry) return;
    const valid = () => token === generation;
    clearForecast("Checking the original WFDB files on this device…");
    const label = crossDay()
      ? "Day 2 · " + dayTwo.folder + " · trial " + entry.trial
      : "Trial " + entry.trial + " from your files";
    status.textContent = crossDay() ? "Opening " + label + "…" : "Opening trial " + entry.trial + "…";
    try {
      const rec = await loadTrialFiles(entry, valid);
      if (valid()) show(rec, label);
    } catch (e) {
      if (valid()) {
        status.textContent = "Trial could not be opened.";
        clearForecast(e.message);
      }
    }
  }
  function clearChoices() {
    choices = [];
    selector.replaceChildren();
    el("trial-label").hidden = true;
  }
  function choose(input) {
    ++generation;
    clearChoices();
    if (crossDay()) {
      endExample();
      dayTwo = null;
      discardCalibration();
    }
    if (!input.files.length) {
      status.textContent = "No recording selected.";
      clearForecast(crossDay() ? "Choose a Day 2 folder to open a forecast." : "Choose a folder or matching files.");
      if (crossDay()) refreshFit();
      return;
    }
    try {
      choices = wfdb.catalogue([...input.files]);
      if (crossDay()) {
        const session = personal.identifySession(choices);
        if (session?.day !== 2) {
          throw new Error("The Day 2 picker needs one original subjectNN_session2 folder.");
        }
        dayTwo = session;
      }
      for (const [i, ent] of choices.entries())
        selector.add(new Option("Trial " + ent.trial, String(i)));
      el("trial-label").hidden = choices.length < 2;
      selector.value = "0";
      openTrial();
    } catch (e) {
      clearChoices();
      status.textContent = "No recording selected.";
      clearForecast(e.message);
    }
    if (crossDay()) refreshFit();
  }
  function invented() {
    ++generation;
    files.value = "";
    folder.value = "";
    clearChoices();
    show(model.invented(), "Invented trial");
  }
  function discardCalibration() {
    fitGeneration++;
    calibration = null;
    fitting = false;
    reveal.checked = false;
    reveal.disabled = crossDay();
    clearScores();
    if (record) render();
  }
  function endExample() {
    if (!workedExample) return;
    workedExample = false;
    dayOne = null;
    dayTwo = null;
    el("day-one-source").textContent = "";
    clearChoices();
    clearForecast("Choose a Day 2 folder to open a forecast.");
    status.textContent = "";
  }
  function refreshFit(message) {
    const problem = personal.pairProblem(dayOne?.session, dayTwo);
    fitButton.disabled = Boolean(problem) || fitting || workedExample;
    fitStatus.textContent = message ?? problem;
  }
  function chooseDayOne() {
    endExample();
    discardCalibration();
    dayOne = null;
    const source = el("day-one-source");
    if (!dayOnePicker.files.length) {
      source.textContent = "";
      refreshFit();
      return;
    }
    try {
      const entries = wfdb.catalogue([...dayOnePicker.files]);
      const session = personal.identifySession(entries);
      if (session?.day !== 1) {
        throw new Error("The Day 1 picker needs one original subjectNN_session1 folder.");
      }
      if (entries.length !== personal.dayOneTrialCount) {
        throw new Error("Day 1 needs all five original force trials.");
      }
      const useEmg = entries.every((entry) => entry.files["raw.hea"]);
      dayOne = { entries, session, useEmg };
      source.textContent = session.folder + " · five force pairs" + (useEmg ? " and five raw EMG pairs." : ".");
    } catch (error) {
      source.textContent = error.message;
    }
    refreshFit();
  }
  async function fitFromDayOne(loadDayOneTrial, useEmg) {
    discardCalibration();
    fitting = true;
    const token = fitGeneration;
    const valid = () => token === fitGeneration;
    try {
      const fitResult = await personal.calibrate(loadDayOneTrial, useEmg, weights, valid, (trial) => {
        refreshFit("Fitting " + (workedExample ? "invented " : "") + "Day 1 · trial " + trial + " of 5…");
      });
      if (!valid()) return;
      fitting = false;
      calibration = fitResult;
      reveal.disabled = false;
      const source = workedExample ? "Invented Day 1" : "Day 1";
      refreshFit(
        "Fitted on " + fitResult.count.toLocaleString("en-US") + " " + source + " windows." +
        (workedExample || !fitResult.emgIssue ? "" : " " + fitResult.emgIssue),
      );
      if (record) render();
    } catch (error) {
      if (!valid()) return;
      fitting = false;
      refreshFit("Calibration stopped. " + error.message);
    }
  }
  function fitSelected() {
    if (fitButton.disabled) return;
    const { entries, useEmg } = dayOne;
    fitFromDayOne(async (trial, valid) => {
      try {
        return await loadTrialFiles(entries[trial - 1], valid, useEmg);
      } catch (error) {
        throw new Error("Day 1 trial " + trial + " · " + error.message);
      }
    }, useEmg);
  }
  function resetRecordings(message) {
    ++generation;
    dayOne = null;
    dayTwo = null;
    workedExample = false;
    inputName = "";
    clearChoices();
    clearForecast("Choose a Day 2 folder to open a forecast.");
    discardCalibration();
    for (const input of [files, folder, dayOnePicker]) input.value = "";
    slider.value = String(model.first);
    slider.removeAttribute("aria-valuetext");
    el("moment").textContent = "";
    el("history").open = false;
    el("muscle").open = false;
    el("day-one-source").textContent = "";
    status.textContent = message;
    if (crossDay()) refreshFit();
  }
  function setMode(next) {
    mode.value = next;
    resetRecordings("");
    const isCrossDay = crossDay();
    for (const id of ["day-one-panel", "day-two-heading", "day-two-hint", "fit", "fit-status", "clear-recordings"]) {
      el(id).hidden = !isCrossDay;
    }
    for (const id of ["loose-pairs", "example", "population-hint"]) {
      el(id).hidden = isCrossDay;
    }
    el("folder-caption").textContent = isCrossDay ? "Original Day 2 session folder" : "Original session folder";
    el("reveal-caption").textContent = isCrossDay ? "Reveal Day 2 reading and trial errors" : "Reveal the later sensor reading";
    if (!isCrossDay) invented();
  }
  function inventedDays() {
    setMode("crossday");
    workedExample = true;
    el("day-one-source").textContent = "Invented Day 1 · five force trials.";
    show({ force: model.invented(2.5).force }, "Invented Day 2 · trial 1");
    fitFromDayOne(async (trial) => ({ force: model.invented(trial / 6).force }), false);
  }
  if (!wfdb || !personal || !model?.validFit(weights)) {
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
  crossExample.addEventListener("click", inventedDays);
  clearRecordings.addEventListener("click", () => resetRecordings("Recordings and Day 1 fit cleared."));
  mode.addEventListener("change", () => setMode(mode.value));
  dayOnePicker.addEventListener("change", chooseDayOne);
  fitButton.addEventListener("click", fitSelected);
  slider.addEventListener("input", render);
  reveal.addEventListener("change", () => {
    showOutcome();
    evaluateTrial();
  });
  for (const name of ["muscle", "history"])
    el(name).addEventListener("toggle", tables);
  if (typeof ResizeObserver === "function")
    new ResizeObserver(renderPlot).observe(plot);
  else window.addEventListener("resize", renderPlot);
  for (const control of [files, folder, example, mode, dayOnePicker, crossExample, clearRecordings]) control.disabled = false;
  setMode("population");
})();
