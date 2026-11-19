"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const math = globalThis.PinchTransfer;
  const identity = globalThis.PinchIntervals;
  const sources = globalThis.TransferSources;
  const enc = new TextEncoder();
  const bundledBytes = enc.encode(globalThis.CEMHSEY_ARRAY_FIT_BYTES);
  const bundled = globalThis.ArrayPinch.checkFit(JSON.parse(globalThis.CEMHSEY_ARRAY_FIT_BYTES));
  const descriptions = {
    invented_signals: "fitted on invented signals",
    user_supplied_local: "fitted on a user-selected 30% set",
    measured_train_local: "fitted on the study’s 30% training recordings"
  };
  const roleMessages = {
    missing: "Choose a comparison repeat. For practice, add the first repeat from the same source group.",
    duplicate: "Both files decode to the same readings. Choose two different repeats.",
    different: "The names indicate different participants or days. Choose two repeats from the same group.",
    confirm: "Check both original sources before using these relabelled trials.",
    ready: "Both repeat roles are available."
  };
  const slots = [null, null];
  const display = value => value === undefined ? "—" : Math.abs(value) < .0000005 ? "0.000000" : value.toFixed(6);
  let q = Number($("target").value);
  let fit = bundled;
  let fitHash;
  let example;
  let adapter = null;
  let job = null;
  let predictSecond = null;
  let scores = null;

  function setRows(body, rows) {
    const fragment = document.createDocumentFragment();
    for (const [label, ...values] of rows) {
      const tr = document.createElement("tr");
      const th = document.createElement("th");
      th.scope = "row";
      th.textContent = label;
      tr.append(th);
      for (const value of values) tr.insertCell().textContent = display(value);
      fragment.append(tr);
    }
    body.replaceChildren(fragment);
  }

  function status(text) {
    $("status").textContent = text;
  }

  function invalidateResults() {
    scores = null;
    $("score-wait").textContent = "";
    $("reveal").checked = false;
    $("observation").textContent = "";
    $("points").textContent = "";
    $("score-rows").textContent = "";
    $("scores").hidden = true;
  }

  function clearAdapter() {
    adapter = null;
    invalidateResults();
  }

  function clearInputs() {
    slots.fill(null);
    $("confirm-pair").checked = false;
    predictSecond = null;
    clearAdapter();
  }

  function loadExample() {
    example ??= globalThis.ArrayPinch.example();
    slots[0] = {trial: math.fromExample(example, q, 1), digest: "example:" + q + ":1", source: {originalName: true}};
    slots[1] = {trial: math.fromExample(example, q, 2), digest: "example:" + q + ":2", source: {originalName: true}};
  }

  function changeSource() {
    stopJob();
    clearInputs();
    q = Number($("target").value);
    if ($("source").value === "invented") loadExample();
    status("");
    refresh();
  }

  function trialOverlap(record) {
    return Boolean(record && fit.training?.packet_sha256?.includes(record.digest));
  }

  function binding() {
    return fitHash && slots[0] && slots[1] ?
      [fitHash, q, slots[0].digest, slots[1].digest].join(":") : null;
  }

  function currentAdapter() {
    return adapter && adapter.binding === binding() ? adapter.coefficients : null;
  }

  function getPair() {
    return sources.pairState(slots[0], slots[1], $("confirm-pair").checked);
  }

  function canCompare(pair) {
    return !trialOverlap(slots[1]) && (pair === "ready" ||
      pair === "missing" && !slots[0] && slots[1]?.source.originalName);
  }

  function refresh() {
    const matMode = $("source").value === "mat";
    const pair = getPair();
    const comparison = canCompare(pair);
    const coefficients = currentAdapter();
    $("mat-controls").hidden = !matMode;
    $("source-note").textContent = matMode
      ? "The browser reads your selected files here. Start with repeat 2 to see the frozen and adjusted forecasts."
      : "Both repeats use invented force and electrode signals. Their scores are a demonstration.";
    for (const role of [1, 2]) {
      $("repeat" + role).disabled = !matMode || Boolean(job);
      const record = slots[role - 1];
      $("repeat" + role + "-status").textContent = record ?
        (record.source.originalName ? "Archive name matches this role." : "Relabelled file read. Check the original source.") : "No file loaded.";
      $("drop-repeat" + role).hidden = !record;
    }
    const canConfirm = pair === "confirm" ||
      pair === "ready" && slots.some(slot => !slot?.source.originalName);
    $("confirm-label").hidden = !matMode || !canConfirm;
    $("pair-status").textContent = matMode ? roleMessages[pair] : "";
    $("model-status").textContent = fit === bundled
      ? "Bundled forecast weights fitted on invented signals."
      : "Selected fit. The file reports weights " + descriptions[fit.fit_origin] + ".";
    $("model-file").disabled = Boolean(job);
    $("reset-model").disabled = fit === bundled;
    $("adapt").disabled = Boolean(job) || pair !== "ready" || !fitHash ||
      slots.some(trialOverlap) || Boolean(coefficients);
    $("clear-adapter").hidden = !coefficients;
    $("adapter-status").textContent = coefficients ? "Practice fitted on repeat 1. The coefficients stay in this tab."
      : trialOverlap(slots[0]) ? "Repeat 1 matches a training recording. Use a separate practice repeat."
      : trialOverlap(slots[1]) ? "Repeat 2 matches a training recording. Use a separate comparison repeat."
      : "Fit on repeat 1 to open the two adapted forecasts.";
    $("progress-controls").hidden = !job || job.trigger === $("score");
    $("cancel-score").hidden = job?.trigger !== $("score");
    $("score").disabled = Boolean(job);
    $("comparison").hidden = !comparison;
    if (comparison) {
      $("overlap").textContent = matMode && fit.fit_origin !== "invented_signals"
        ? (fit.training?.packet_sha256 ? "The decoded comparison does not match any recorded training fingerprint. Check participant and recording overlap at the source."
          : "This fit has no training fingerprints. Check training overlap at the source.")
        : "";
      safeRender();
    }
  }

  function beginJob(trigger) {
    const task = {trigger, abort: new AbortController(), cancelRead: null};
    job = task;
    $("progress").removeAttribute("value");
    refresh();
    return task;
  }

  function stopJob() {
    if (!job) return;
    const task = job;
    job = null;
    task.abort.abort();
    task.cancelRead?.();
    $("score-wait").textContent = "";
  }

  function progress(task, value) {
    if (job === task) $("progress").value = value;
  }

  function finishJob(task) {
    if (job !== task) return;
    job = null;
    refresh();
  }

  function cancel() {
    const trigger = job?.trigger;
    stopJob();
    status("Cancelled.");
    refresh();
    if (trigger && !trigger.disabled && trigger.getClientRects().length) trigger.focus();
    else $("source").focus();
  }
  $("cancel").addEventListener("click", cancel);
  $("cancel-score").addEventListener("click", cancel);
  $("source").addEventListener("change", changeSource);
  $("target").addEventListener("change", changeSource);

  for (const role of [1, 2]) {
    const picker = $("repeat" + role);
    const clearSlot = () => {
      stopJob();
      slots[role - 1] = null;
      $("confirm-pair").checked = false;
      if (role === 2) predictSecond = null;
      clearAdapter();
    };
    $("drop-repeat" + role).addEventListener("click", () => {
      clearSlot();
      status("");
      refresh();
      picker.focus();
    });
    picker.addEventListener("change", async () => {
      const file = picker.files[0];
      picker.value = "";
      if (!file) return;
      clearSlot();
      let task;
      try {
        const source = sources.sourceName(file, q, role);
        task = beginJob(picker);
        status("Reading repeat " + role + "…");
        const importJob = globalThis.CemhseyMat.start(file, {onProgress: item => {
          if (job !== task) return;
          if (item.phase === "reading") progress(task, item.fraction * .2);
          else progress(task, item.fraction * .7 + .2);
        }});
        task.cancelRead = importJob.cancel;
        const trial = await importJob.promise;
        if (job !== task) return;
        status("Checking the decoded recording…");
        const digest = await identity.packetIdentity(trial);
        if (job !== task) return;
        slots[role - 1] = {source, trial, digest};
        status("");
      } catch (error) {
        if (!task || job === task) status(error.message);
      } finally {
        if (task) finishJob(task);
        else refresh();
      }
    });
  }

  $("confirm-pair").addEventListener("change", () => {
    stopJob();
    clearAdapter();
    status("");
    refresh();
  });

  async function useFit(bytes, next, task) {
    const hash = await identity.digest(bytes);
    if (job !== task) return;
    fit = next;
    fitHash = hash;
    predictSecond = null;
    status("");
  }

  $("model-file").addEventListener("change", async event => {
    const picker = event.currentTarget;
    const file = picker.files[0];
    picker.value = "";
    if (!file) return;
    stopJob();
    clearAdapter();
    const task = beginJob(picker);
    status("Checking forecast weights…");
    try {
      if (file.size > 128 * 1024) throw Error("Choose a model under 128 KiB.");
      const bytes = await file.arrayBuffer();
      if (job === task) await useFit(bytes, sources.readFit(bytes, bundled), task);
    } catch (error) {
      if (job === task) status(error.message);
    } finally {
      finishJob(task);
    }
  });

  $("reset-model").addEventListener("click", () => {
    stopJob();
    clearAdapter();
    fit = bundled;
    fitHash = bundledHash;
    predictSecond = null;
    status("");
    refresh();
  });

  const pause = () => new Promise(resolve => setTimeout(resolve, 0));

  async function eachIssue(task, update) {
    for (let index = 0; index < math.nIssues; index++) {
      task.abort.signal.throwIfAborted();
      update(index);
      if (index % 24 === 23) {
        progress(task, (index + 1) / math.nIssues);
        await pause();
      }
    }
  }

  $("adapt").addEventListener("click", async () => {
    const stamp = binding();
    if (!stamp || getPair() !== "ready" || slots.some(trialOverlap)) return;
    const trial = slots[0].trial;
    const read = math.cache(trial, fit);
    const total = math.newAdapter();
    const task = beginJob($("adapt"));
    status("Fitting two practice coefficients…");
    try {
      await eachIssue(task, index => {
        const {tick, estimates} = read(index);
        math.addAdapterSample(total, estimates, tick, q, trial.force[tick + math.horizon]);
      });
      if (job !== task || binding() !== stamp) return;
      adapter = {binding: stamp, coefficients: math.finishAdapter(total)};
      invalidateResults();
      status("");
    } catch (error) {
      if (job === task) status(error.message);
    } finally {
      finishJob(task);
    }
  });

  $("clear-adapter").addEventListener("click", () => {
    stopJob();
    clearAdapter();
    status("");
    refresh();
    $("adapt").focus();
  });

  const select = $("plot-arm");
  for (const name of math.arms) select.add(new Option(math.labels[name], name));
  select.value = "history_phase_paired_grid_adjusted";

  function prediction(index, coefficients) {
    predictSecond ??= math.cache(slots[1].trial, fit);
    const {tick, estimates} = predictSecond(index);
    return {tick, values: math.estimates(estimates, tick, q, coefficients)};
  }

  function render() {
    const coefficients = currentAdapter();
    for (const option of select.options) option.disabled = !coefficients && option.value.endsWith("_adapted");
    if (select.selectedOptions[0].disabled) select.value = select.value.replace(/_adapted$/, "_adjusted");
    const index = Number($("cutoff").value);
    const {tick, values} = prediction(index, coefficients);
    const end = tick + math.horizon;
    const source = slots[1].trial;
    const revealed = $("reveal").checked;
    $("cutoff-time").textContent = (tick / 200).toFixed(2) + " s → " + (end / 200).toFixed(2) + " s";
    const phase = identity.phaseAt(tick);
    $("phase").textContent = {initial_rest: "Initial rest", ramp_up: "Ramp up", hold: "Hold",
      release: "Ramp down", final_rest: "Final rest"}[phase];
    $("observation").hidden = !revealed;
    $("observation").textContent = revealed ? "Gauge at " + (end / 200).toFixed(2) + " s · " +
      display(source.force[end]) + " of MVC" : "";
    $("observed-key").hidden = !revealed;
    setRows($("points"), math.arms.map(name => [math.labels[name], values[name]]));
    const series = [];
    const addPoint = pointIndex => {
      const point = prediction(pointIndex, coefficients);
      series.push({tick: point.tick, point: point.values[select.value],
        observed: revealed ? source.force[point.tick + math.horizon] : undefined});
    };
    const step = Math.max(1, Math.ceil(index / 124));
    for (let i = 0; i < index; i += step) addPoint(i);
    addPoint(index);
    globalThis.PinchPlot.draw($("forecast-plot"), series, tick, false);
    $("scores").hidden = !scores;
    if (scores) {
      $("score-source").textContent = $("source").value === "invented"
        ? "Invented comparison repeat. The errors come from this example."
        : "Selected comparison repeat. These are descriptive errors for this trial.";
      setRows($("score-rows"), math.arms.map(arm => {
        const row = scores[arm];
        return [math.labels[arm], row?.mae, row?.rmse, row?.bias, row?.target_relative_mae];
      }));
    }
  }

  function safeRender() {
    try { render(); }
    catch (error) {
      $("comparison").hidden = true;
      status(error.message);
    }
  }

  $("cutoff").addEventListener("input", () => {
    if (job?.trigger === $("score")) stopJob();
    invalidateResults();
    refresh();
  });
  for (const control of [select, $("reveal")]) control.addEventListener("change", safeRender);
  window.addEventListener("resize", () => { if (!$("comparison").hidden) safeRender(); });

  $("score").addEventListener("click", async () => {
    if (!canCompare(getPair())) return;
    const trial = slots[1].trial;
    const coefficients = currentAdapter();
    const total = math.newScores();
    const task = beginJob($("score"));
    $("score-wait").textContent = "Scoring the comparison repeat…";
    try {
      await eachIssue(task, index => {
        const {tick, values} = prediction(index, coefficients);
        math.addScore(total, values, trial.force[tick + math.horizon]);
      });
      if (job !== task) return;
      scores = math.finishScores(total, q);
      $("score-wait").textContent = "592 cutoffs scored.";
    } catch (error) {
      if (job === task) $("score-wait").textContent = error.message;
    } finally {
      finishJob(task);
    }
  });

  let bundledHash;
  identity.digest(bundledBytes).then(value => {
    bundledHash = value;
    fitHash ??= value;
    refresh();
  }).catch(() => {
    status("Open the downloaded reader on your device or use its HTTPS page for file and practice checks.");
  });
  $("source").disabled = false;
  $("target").disabled = false;
  changeSource();
})();
