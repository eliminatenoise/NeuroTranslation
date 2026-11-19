"use strict";
(() => {
  const el = (id) => document.getElementById(id);
  const model = globalThis.HyserForecast,
    wfdb = globalThis.HyserWFDB,
    personal = globalThis.HyserPersonalize,
    weights = globalThis.HYSER_WEIGHTS,
    fingers = globalThis.HyserFingerContext,
    fingerWeights = globalThis.HYSER_FINGER_CONTEXT_WEIGHTS;
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
    fingerScoreAction = el("finger-score-action"),
    plot = el("plot"),
    status = el("record-status");
  let generation = 0,
    fitGeneration = 0,
    scoreGeneration = 0,
    choices = [],
    record = null,
    row = null,
    predictions = null,
    fingerHistory = null,
    inputName = "",
    dayOne = null,
    dayTwo = null,
    calibration = null,
    fitting = false,
    workedExample = false;
  const crossDay = () => mode.value === "crossday";
  const handContext = () => mode.value === "finger-context";
  const hasFingerWeights = fingers?.validWeights(fingerWeights);
  const models = [
    ["force", "Force history"],
    ["aligned", "Force history + EMG"],
  ];
  const fingerModels = [
    ["index_only", "Index history"],
    ["aligned_five", "Five finger histories"],
    ["aligned_summary", "Index + two values per other finger"],
  ];
  const prescribedModels = [["persistence", "Last index reading"], ...fingerModels];
  const digitNames = { thumb: "Thumb", middle: "Middle", ring: "Ring", little: "Little" };
  const digitPlots = (fingers?.extraDigits ?? []).map((digit) => {
    const figure = document.createElement("figure");
    const caption = document.createElement("figcaption");
    const canvas = document.createElement("canvas");
    const latest = document.createElement("div");
    caption.textContent = digitNames[digit];
    canvas.setAttribute("role", "img");
    latest.className = "digit-latest";
    figure.append(caption, canvas, latest);
    el("digit-traces").append(figure);
    return { name: caption.textContent, canvas, latest };
  });
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
    fingerScoreAction.disabled = true;
    fingerScoreAction.removeAttribute("aria-disabled");
    el("finger-score-status").textContent = "";
    el("finger-score-table").hidden = true;
    el("finger-score-rows").replaceChildren();
  }
  function clearForecast(message) {
    clearScores();
    record = null;
    row = null;
    predictions = null;
    clearFingerHistory();
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
  function clearFingerHistory() {
    fingerHistory = null;
    el("finger-status").textContent = "";
    el("finger-samples").querySelector("tbody").replaceChildren();
    for (const { canvas, latest } of digitPlots) {
      canvas.removeAttribute("aria-label");
      canvas.width = canvas.width;
      latest.textContent = "";
    }
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
    const fingerSamples = el("finger-samples");
    const body = fingerSamples.querySelector("tbody");
    body.replaceChildren();
    if (!fingerSamples.open || !fingerHistory) return;
    for (let i = 0; i < 41; i++) {
      const tr = body.insertRow();
      const time = document.createElement("th");
      time.scope = "row";
      time.textContent = (i - 40) * 10;
      tr.append(time);
      for (const digit of fingerHistory) {
        tr.insertCell().textContent = Number.isFinite(digit[i]) ? volts(digit[i]) : "Missing";
      }
    }
  }
  function renderFingerPlots() {
    if (!fingerHistory) return;
    const values = fingerHistory.flat().filter(Number.isFinite);
    const amplitude = Math.max(...values.map(Math.abs)) || 1;
    const normalized = values.map((v) => v / amplitude);
    const min = Math.min(0, ...normalized), max = Math.max(0, ...normalized);
    const lower = min === max ? -0.02 : min, upper = min === max ? 0.02 : max;
    const ticks = [upper, (upper + lower) / 2, lower];
    const labels = ticks.map((n) => volts(n * amplitude) + " V");
    for (const [index, { name, canvas, latest }] of digitPlots.entries()) {
      const history = fingerHistory[index];
      const samples = history.filter(Number.isFinite).length;
      const last = history.at(-1);
      latest.textContent = "At cutoff · " + (Number.isFinite(last) ? volts(last) + " V" : "Missing");
      canvas.setAttribute("aria-label", name + " sensor history from −400 ms through cutoff. " +
        samples + " of 41 voltage samples. " + latest.textContent + ".");
      const width = canvas.clientWidth, height = canvas.clientHeight;
      const ctx = canvas.getContext("2d");
      if (!width || !height || !ctx) continue;
      const ratio = Math.min(window.devicePixelRatio || 1, 3);
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      ctx.scale(canvas.width / width, canvas.height / height);
      ctx.font = "11px " + getComputedStyle(canvas).fontFamily;
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#263f38";
      const left = 11 + Math.max(...labels.map((s) => ctx.measureText(s).width));
      const right = width - 12, top = 12, bottom = height - 26;
      if (right <= left) continue;
      const x = (i) => left + i * (right - left) / 40;
      const y = (n) => bottom - (n - lower) * (bottom - top) / (upper - lower);
      ctx.strokeStyle = "#c6d4ca";
      ctx.beginPath();
      for (const [i, tick] of ticks.entries()) {
        ctx.fillText(labels[i], 5, y(tick));
        ctx.moveTo(left, y(tick));
        ctx.lineTo(right, y(tick));
      }
      ctx.stroke();
      ctx.fillText("−400 ms", left, bottom + 16);
      ctx.textAlign = "right";
      ctx.fillText("Cutoff", right, bottom + 16);
      ctx.strokeStyle = "#15594e";
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.beginPath();
      let connected = false;
      for (const [i, value] of history.entries()) {
        if (!Number.isFinite(value)) {
          connected = false;
          continue;
        }
        const h = y(value / amplitude);
        if (!connected) ctx.moveTo(x(i), h);
        ctx.lineTo(x(i), h);
        connected = true;
      }
      ctx.stroke();
    }
  }
  function renderPlot() {
    if (!row || !predictions) return;
    const target = row.observed;
    const fittedIndex = predictions.index_only !== undefined;
    const indexForecast = fittedIndex ? predictions.index_only : predictions.force;
    plot.setAttribute(
      "aria-label",
      inputName +
        ". History runs from 400 ms before cutoff to cutoff. " +
        (fittedIndex ? "Index-history" : "Force-history") + " forecast at +120 ms is " +
        volts(indexForecast) +
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
        fingerModels.slice(1).filter(([key]) => predictions[key] !== undefined)
          .map(([key, label]) => " " + label + " forecast " + volts(predictions[key]) + " V.")
          .join("") +
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
    const all = [...row.force, indexForecast];
    for (const key of ["aligned", "forceOwn", "alignedOwn", "aligned_five", "aligned_summary"]) {
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
      fy = y(indexForecast / amplitude);
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
    if (predictions.aligned_five !== undefined) {
      const py = y(predictions.aligned_five / amplitude);
      ctx.beginPath();
      ctx.moveTo(fx, py - 6);
      ctx.lineTo(fx + 6, py + 5);
      ctx.lineTo(fx - 6, py + 5);
      ctx.fillStyle = "#1d6353";
      ctx.fill();
    }
    if (predictions.aligned_summary !== undefined) {
      ctx.beginPath();
      ctx.arc(fx, y(predictions.aligned_summary / amplitude), 4, 0, Math.PI * 2);
      ctx.strokeStyle = "#a75212";
      ctx.lineWidth = 2;
      ctx.stroke();
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
          [...models, ...(record.prescribed ? prescribedModels : fingerModels), ["forceOwn", "Personalized force"], ["alignedOwn", "Personalized with EMG"]]
            .filter(([key]) => predictions[key] !== undefined)
            .map(([key, label]) => label + " error " + volts(predictions[key] - row.observed) + " V.")
            .join(" ");
    el("target-key").hidden = !reveal.checked || row.observed === null;
    renderPlot();
  }
  const millivolts = (v) => (v * 1000).toFixed(3);
  async function evaluateTrial() {
    if (!crossDay()) return;
    clearScores();
    if (!reveal.checked || !calibration || !record) return;
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
  async function evaluateFingerTrial() {
    if (!handContext() || !hasFingerWeights || !record || fingerScoreAction.disabled ||
        fingerScoreAction.getAttribute("aria-disabled") === "true") return;
    const token = ++scoreGeneration;
    const valid = () => token === scoreGeneration;
    const scoreStatus = el("finger-score-status");
    const table = el("finger-score-table");
    const rows = el("finger-score-rows");
    const source = inputName;
    fingerScoreAction.setAttribute("aria-disabled", "true");
    table.hidden = true;
    rows.replaceChildren();
    scoreStatus.textContent = "Scoring the trial…";
    try {
      const prescribed = Boolean(record.prescribed);
      const score = await fingers.scoreTrial(record.force, fingerWeights, valid, { includePersistence: prescribed });
      if (!valid()) return;
      const counts = score.count + " / " + score.scheduled;
      if (!score.models) {
        scoreStatus.textContent = counts + " cutoffs have all five histories and a later index reading. " +
          "Missing history at " + score.missingHistories + " of " + score.scheduled + " cutoffs. " +
          "Missing later reading at " + score.missingTargets + " of " + score.scheduled + " cutoffs. " +
          "Scoring requires every scheduled cutoff.";
        return;
      }
      const baseline = score.models.index_only.maeV;
      for (const [arm, label] of prescribed ? prescribedModels : fingerModels) {
        const tr = rows.insertRow();
        const th = document.createElement("th");
        th.scope = "row";
        th.textContent = label;
        tr.append(th);
        const { maeV, rmseV } = score.models[arm];
        tr.insertCell().textContent = millivolts(maeV);
        tr.insertCell().textContent = millivolts(rmseV);
        const gain = baseline - maeV;
        const magnitude = millivolts(Math.abs(gain));
        tr.insertCell().textContent = arm === "index_only" ? "Baseline" :
          magnitude === "0.000" ? magnitude : (gain < 0 ? "−" : "+") + magnitude;
      }
      scoreStatus.textContent = source + " · " + counts + " matched cutoffs.";
      table.hidden = false;
    } catch (error) {
      if (valid()) scoreStatus.textContent = error.message;
    } finally {
      if (valid()) fingerScoreAction.removeAttribute("aria-disabled");
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
      fingerHistory = handContext() ? fingers.extraHistory(record.force, issue) : null;
      predictions = handContext() && hasFingerWeights
        ? { ...fingers.predict(row.force, fingerHistory, fingerWeights), persistence: row.force.at(-1) }
        : model.predict(row, weights);
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
        ...fingerModels,
        ["persistence", record.prescribed ? "Last index reading" : "Last voltage"],
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
      el("force-key-label").textContent = predictions.index_only === undefined ? "Force history forecast" : "Index history forecast";
      el("five-key").hidden = predictions.aligned_five === undefined;
      el("summary-key").hidden = predictions.aligned_summary === undefined;
      el("muscle").hidden = !row.emg;
      if (handContext()) {
        el("finger-status").textContent = !hasFingerWeights
          ? "This copy includes the earlier force-history model. Fitted finger-context models are unavailable."
          : predictions.aligned_five === undefined
            ? "The five-finger forecasts need all 41 readings from each sensor. The index-history forecast is available."
            : "";
      }
      const msg =
        record.raw && !row.emg
          ? "The muscle window contains missing samples. The force forecast is available."
          : "";
      el("unavailable").textContent = msg;
      el("unavailable").hidden = !msg;
      el("window").hidden = false;
      showOutcome();
      tables();
      renderFingerPlots();
    } catch (e) {
      row = null;
      predictions = null;
      clearFingerHistory();
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
    clearScores();
    record = rec;
    inputName = name;
    slider.value = String(model.first);
    reveal.checked = false;
    reveal.disabled = crossDay() && !calibration;
    el("controls").hidden = false;
    el("finger-score-help").textContent = rec.prescribed
      ? "Compare the three forecasts and the last index reading with the later index voltage at all 450 cutoffs."
      : "Compare the three forecasts with the later index reading at all 450 cutoffs in this trial.";
    fingerScoreAction.disabled = !handContext() || !hasFingerWeights;
    if (handContext() && !hasFingerWeights) {
      el("finger-score-status").textContent = "Fitted finger-context models are unavailable in this copy.";
    }
    status.textContent =
      name + (rec.raw ? " · force and raw forearm EMG" : " · force only");
    render();
  }
  async function loadTrialFiles(entry, valid, readRaw = true) {
    const force = await wfdb.loadPair(entry, "force", valid);
    if (!valid()) return null;
    const raw = readRaw && !entry.prescribedStem && entry.files["raw.hea"]
      ? await wfdb.loadPair(entry, "raw", valid)
      : null;
    return valid() ? { force, raw, prescribed: Boolean(entry.prescribedStem) } : null;
  }
  function trialLabel(entry) {
    if (!entry.prescribedStem) return "Trial " + entry.trial;
    return "Combination " + entry.combination + " · repetition " + entry.repetition + " · " +
      (entry.indexCued ? "index cued" : "index uncued");
  }
  async function openTrial() {
    const token = ++generation,
      entry = choices[Number(selector.value)];
    if (!entry) return;
    const valid = () => token === generation;
    clearForecast("Checking the original WFDB files on this device…");
    const trial = trialLabel(entry);
    const label = crossDay()
      ? "Day 2 · " + dayTwo.folder + " · trial " + entry.trial
      : entry.prescribedStem
        ? "Prescribed N-DoF · " + trial + " · " + (entry.folder.split("/").at(-1) || "session unknown")
        : trial + " from your files";
    status.textContent = "Opening " + label + "…";
    try {
      const rec = await loadTrialFiles(entry, valid, !handContext());
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
      choices = wfdb.catalogue([...input.files], { includeRaw: !handContext(), includePrescribed: handContext() });
      if (crossDay()) {
        const session = personal.identifySession(choices);
        if (session?.day !== 2) {
          throw new Error("The Day 2 picker needs one original subjectNN_session2 folder.");
        }
        dayTwo = session;
      }
      for (const [i, ent] of choices.entries())
        selector.add(new Option(trialLabel(ent), String(i)));
      el("trial-caption").textContent = choices[0].prescribedStem ? "Combination and repetition" : "Trial";
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
    const demo = handContext() ? { force: fingers.inventedForce() } : model.invented();
    show(demo, "Invented trial");
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
    clearForecast(crossDay() ? "Choose a Day 2 folder to open a forecast." : "Choose a folder, matching files or the invented trial.");
    discardCalibration();
    for (const input of [files, folder, dayOnePicker]) input.value = "";
    slider.value = String(model.first);
    slider.removeAttribute("aria-valuetext");
    el("moment").textContent = "";
    el("history").open = false;
    el("muscle").open = false;
    el("finger-samples").open = false;
    el("day-one-source").textContent = "";
    status.textContent = message;
    if (crossDay()) refreshFit();
  }
  function setMode(next) {
    mode.value = next;
    resetRecordings("");
    const isCrossDay = crossDay();
    for (const id of ["day-one-panel", "day-two-heading", "day-two-hint", "fit", "fit-status"]) {
      el(id).hidden = !isCrossDay;
    }
    clearRecordings.hidden = !isCrossDay && !handContext();
    for (const id of ["loose-pairs", "example", "population-hint"]) {
      el(id).hidden = isCrossDay;
    }
    el("folder-caption").textContent = isCrossDay ? "Original Day 2 session folder" : "Original session folder";
    el("reveal-caption").textContent = isCrossDay ? "Reveal Day 2 reading and trial errors" : "Reveal the later sensor reading";
    el("population-hint").hidden = isCrossDay || handContext();
    for (const id of ["finger-context", "finger-hint", "finger-evidence", "finger-score", "prescribed-evidence"]) el(id).hidden = !handContext();
    el("finger-fit-evidence").hidden = !handContext() || !hasFingerWeights;
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
  clearRecordings.addEventListener("click", () => resetRecordings(crossDay() ? "Recordings and Day 1 fit cleared." : "Recordings cleared."));
  mode.addEventListener("change", () => setMode(mode.value));
  dayOnePicker.addEventListener("change", chooseDayOne);
  fitButton.addEventListener("click", fitSelected);
  slider.addEventListener("input", render);
  fingerScoreAction.addEventListener("click", evaluateFingerTrial);
  reveal.addEventListener("change", () => {
    showOutcome();
    evaluateTrial();
  });
  for (const name of ["muscle", "history", "finger-samples"])
    el(name).addEventListener("toggle", tables);
  if (typeof ResizeObserver === "function") {
    const resize = new ResizeObserver((entries) => {
      if (entries.some(({ target }) => target === plot)) renderPlot();
      if (entries.some(({ target }) => target !== plot)) renderFingerPlots();
    });
    for (const canvas of [plot, ...digitPlots.map(({ canvas }) => canvas)]) resize.observe(canvas);
  } else {
    window.addEventListener("resize", () => {
      renderPlot();
      renderFingerPlots();
    });
  }
  mode.querySelector('option[value="finger-context"]').disabled = !fingers;
  for (const control of [files, folder, example, mode, dayOnePicker, crossExample, clearRecordings]) control.disabled = false;
  setMode("population");
})();
