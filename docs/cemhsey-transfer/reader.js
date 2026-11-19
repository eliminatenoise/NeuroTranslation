"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const math = globalThis.PinchTransfer;
  const identity = globalThis.PinchIntervals;
  const sources = globalThis.TransferSources;
  const carry = globalThis.PinchCarry;
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
  let earlier = null;
  let activePrior = null;
  let carryMessage = "";

  function forgetEarlier() {
    earlier = null;
    activePrior = null;
    carryMessage = "";
    $("profile-key").value = "";
    $("profile-key").type = "password";
    $("show-key").checked = false;
  }

  function context() {
    return {q, fitHash, kind: $("source").value === "invented" ? "invented" : "local_recording"};
  }

  function sourceIdentity(slot) {
    if (!slot) return null;
    const {source, digest} = slot;
    if (source.originalName) return {...source, digest};
    const number = Number($("archive-person").value);
    const person = String(number);
    const day = Number($("archive-day").value);
    if (!$("confirm-pair").checked || !Number.isInteger(number) || number < 1 || number > 13 ||
        ![9, 10].includes(day) || (source.person && source.person !== person) ||
        (source.day && source.day !== day)) return null;
    return {person, day, digest};
  }

  function trainingChecked() {
    return fit === bundled || $("source").value === "invented" || $("training-check").checked;
  }

  function usableFirst() {
    if (!slots[0] || !fitHash || !slots[0].digest || trialOverlap(slots[0])) return false;
    if (slots[1]) return Boolean(slots[1].digest) && getPair() === "ready" && !trialOverlap(slots[1]);
    return slots[0].source.originalName || $("confirm-pair").checked;
  }


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
    activePrior = null;
    invalidateResults();
  }

  function clearInputs() {
    slots.fill(null);
    $("archive-person").value = "";
    $("archive-day").value = "";
    $("confirm-pair").checked = false;
    predictSecond = null;
    clearAdapter();
  }

  function loadExample() {
    example ??= globalThis.ArrayPinch.example();
    const day = Number($("example-day").value);
    for (const index of [0, 1]) {
      const trial = math.fromExample(example, q, index + 1, day);
      const slot = {trial, digest: null, source: {originalName: true, person: "invented", day}};
      slots[index] = slot;
      identity.packetIdentity(trial).then(digest => {
        if (slots[index] === slot) {
          slot.digest = digest;
          refresh();
        }
      }).catch(error => { if (slots[index] === slot) status(error.message); });
    }
  }

  function changeSource(event) {
    stopJob();
    if (event?.currentTarget !== $("example-day")) {
      forgetEarlier();
      $("training-check").checked = false;
    }
    clearInputs();
    carryMessage = "";
    q = Number($("target").value);
    if ($("source").value === "invented") loadExample();
    status("");
    refresh();
  }

  function trialOverlap(record) {
    return Boolean(record && fit.training?.packet_sha256?.includes(record.digest));
  }

  function binding() {
    return fitHash && slots[0]?.digest ? [fitHash, q, slots[0].digest].join(":") : null;
  }

  function currentAdapter() {
    return adapter && adapter.binding === binding() && usableFirst() ? adapter.coefficients : null;
  }

  function getPair() {
    return sources.pairState(slots[0], slots[1], $("confirm-pair").checked);
  }

  function canCompare(pair) {
    return Boolean(slots[1]?.digest) && !trialOverlap(slots[1]) && (pair === "ready" ||
      pair === "missing" && !slots[0] && slots[1]?.source.originalName);
  }

  function refresh() {
    const matMode = $("source").value === "mat";
    const pair = getPair();
    const comparison = canCompare(pair);
    $("example-day-label").hidden = matMode;
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
    const renamed = slots.some(slot => slot && !slot.source.originalName);
    const canConfirm = renamed && ["missing", "ready", "confirm"].includes(pair);
    $("confirm-copy").textContent = slots[0] && slots[1]
      ? "I checked both originals. The files match the same participant, day and selected Session 5 target. Repeat 1 is practice and repeat 2 is the comparison."
      : "I checked the original archive. This file matches the selected Session 5 target and its assigned repeat.";
    $("source-identity").hidden = !matMode || !canConfirm;
    $("confirm-label").hidden = !matMode || !canConfirm;
    $("pair-status").textContent = !matMode ? "" : slots[0] && !slots[1]
      ? "Only repeat 1 is open. You can fit practice here before choosing a comparison repeat." : roleMessages[pair];
    $("model-status").textContent = fit === bundled
      ? "Bundled forecast weights fitted on invented signals."
      : "Selected fit. The file reports weights " + descriptions[fit.fit_origin] + ".";
    $("model-file").disabled = Boolean(job);
    $("reset-model").disabled = fit === bundled;
    $("adapt").disabled = Boolean(job) || !usableFirst() || Boolean(coefficients);
    $("clear-adapter").hidden = !coefficients;
    $("adapter-status").textContent = coefficients ? "Practice fitted on repeat 1. Both coefficients use this first repeat alone."
      : trialOverlap(slots[0]) ? "Repeat 1 matches a training recording. Use a separate practice repeat."
      : trialOverlap(slots[1]) ? "Repeat 2 matches a training recording. Use a separate comparison repeat."
      : "Fit on repeat 1 to open the two adapted forecasts.";
    refreshCarry();
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
  $("example-day").addEventListener("change", changeSource);

  for (const role of [1, 2]) {
    const picker = $("repeat" + role);
    const clearSlot = () => {
      stopJob();
      slots[role - 1] = null;
      $("training-check").checked = false;
      carryMessage = "";
      $("archive-person").value = "";
      $("archive-day").value = "";
      $("confirm-pair").checked = false;
      activePrior = null;
      if (role === 2) predictSecond = null;
      if (role === 1 || !slots[0]?.source.originalName) clearAdapter();
      else invalidateResults();
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

  function changeIdentity() {
    $("training-check").checked = false;
    if (earlier?.firstDigest && earlier.firstDigest === slots[0]?.digest) forgetEarlier();
    carryMessage = "";
    stopJob();
    clearAdapter();
    refresh();
  }
  $("archive-person").addEventListener("input", changeIdentity);
  $("archive-day").addEventListener("change", changeIdentity);
  $("confirm-pair").addEventListener("change", changeIdentity);

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
    forgetEarlier();
    $("training-check").checked = false;
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
    forgetEarlier();
    $("training-check").checked = false;
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
    if (!stamp || !usableFirst()) return;
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
    carryMessage = "";
    status("");
    refresh();
    $("adapt").focus();
  });

  const select = $("plot-arm");
  let previousMenu;
  function setArmMenu(coefficients) {
    const names = activePrior ? math.carryArms : math.arms;
    if (previousMenu !== names) {
      const selected = select.value || "history_phase_paired_grid_adjusted";
      select.replaceChildren(...names.map(name => new Option(math.label(name, Boolean(activePrior)), name)));
      select.value = names.includes(selected) ? selected : selected.replace(/_carried$/, "_adjusted");
      previousMenu = names;
    }
    for (const option of select.options) option.disabled = !coefficients && option.value.endsWith("_adapted");
    if (select.selectedOptions[0].disabled) select.value = select.value.replace(/_adapted$/, "_adjusted");
    return names;
  }

  function prediction(index, coefficients) {
    predictSecond ??= math.cache(slots[1].trial, fit);
    const {tick, estimates} = predictSecond(index);
    return {tick, values: math.estimates(estimates, tick, q, coefficients, activePrior)};
  }

  function render() {
    const coefficients = currentAdapter();
    const arms = setArmMenu(coefficients);
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
    setRows($("points"), arms.map(name => [math.label(name, Boolean(activePrior)), values[name]]));
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
      setRows($("score-rows"), arms.map(arm => {
        const row = scores[arm];
        return [math.label(arm, Boolean(activePrior)), row?.mae, row?.rmse, row?.bias, row?.target_relative_mae];
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
    const total = math.newScores(Boolean(activePrior));
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

  function refreshCarry() {
    const first = sourceIdentity(slots[0]);
    const second = sourceIdentity(slots[1]);
    const trained = Boolean(currentAdapter());
    const local = $("source").value === "mat";
    const incomplete = local && slots.some(slot => slot && !sourceIdentity(slot));
    const day9 = first?.day === 9;
    const day10 = first?.day === 10 && second?.day === 10 && first.person === second.person;
    const busy = Boolean(job);
    $("training-check-label").hidden = fit === bundled || $("source").value === "invented";
    $("keep-prior").disabled = busy || !day9 || !trained || !usableFirst() || !trainingChecked();
    $("profile-file").disabled = busy || !fitHash;
    $("save-prior").disabled = busy || !earlier?.created;
    $("apply-prior").disabled = busy || !earlier || !trained || !day10 || !trainingChecked() ||
      !usableFirst() || !/^[0-9a-f]{32}$/i.test($("profile-key").value) || Boolean(activePrior);
    $("clear-prior").hidden = !earlier && !$("profile-key").value;
    $("carry-status").textContent = carryMessage || (activePrior
      ? "Day 9 and day 10 corrections now appear beside the fixed forecasts."
      : incomplete ? "Check the renamed files against the originals, enter their archive participant number and day, and confirm the repeat roles. Known source details must agree."
      : !trainingChecked() ? "Check this imported parent model’s training sources before using a local practice fit across days."
      : first && second && first.person !== second.person ? "Both day 10 repeats must belong to the same participant."
      : earlier && day10 && trained ? "Day 10 is ready. Enter the saved key if needed, then compare both days."
      : earlier ? "Day 9 fit selected. Open both day 10 repeats, check their source and fit repeat 1."
      : day9 ? "Fit day 9 repeat 1, then keep the fit. You can do this with the first repeat alone."
      : local ? "Choose day 9 repeat 1 to make a prior fit, or open a saved fit to use on day 10."
      : "For the example, choose day 9 above to start. You can also open a previously saved day 9 fit.");
  }

  function clearPriorForecasts() {
    if (activePrior) invalidateResults();
    activePrior = null;
    carryMessage = "";
  }

  $("training-check").addEventListener("change", () => {
    stopJob();
    if (!$("training-check").checked) {
      forgetEarlier();
      invalidateResults();
    }
    refresh();
  });

  $("keep-prior").addEventListener("click", async () => {
    if ($("keep-prior").disabled) return;
    const task = beginJob($("keep-prior"));
    try {
      const first = sourceIdentity(slots[0]);
      const key = carry.keyText();
      const profile = await carry.create(context(), first, currentAdapter(), key);
      if (job !== task) return;
      clearPriorForecasts();
      earlier = {profile, created: true, firstDigest: first.digest};
      $("profile-key").value = key;
      $("profile-key").type = "password";
      $("show-key").checked = false;
      carryMessage = "Day 9 fit kept in this tab. Switch to day 10 and fit repeat 1, or save the private fit and keep its key separately.";
    } catch (error) { if (job === task) carryMessage = error.message; }
    finally { finishJob(task); }
  });

  $("save-prior").addEventListener("click", () => {
    if (!earlier?.created) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(earlier.profile, null, 2) + "\n"], {type: "application/json"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "private-day-9-pinch-fit.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    carryMessage = "Save the private key separately before closing this tab. It is under “Reopen a saved fit or view its private key”.";
    refreshCarry();
  });

  $("profile-file").addEventListener("change", async event => {
    const picker = event.currentTarget;
    const file = picker.files[0];
    picker.value = "";
    if (!file) return;
    stopJob();
    clearPriorForecasts();
    forgetEarlier();
    const task = beginJob(picker);
    try {
      if (file.size > 4096) throw Error("Choose a private practice-fit JSON under 4 KiB.");
      const profile = carry.read(await file.arrayBuffer());
      if (job !== task) return;
      carry.compatible(profile, context());
      earlier = {profile, created: false};
      carryMessage = "Private fit opened. Enter its separately saved key. Check both day 10 repeats and fit repeat 1.";
    } catch (error) { if (job === task) carryMessage = error.message; }
    finally { finishJob(task); }
  });

  $("profile-key").addEventListener("input", () => {
    stopJob();
    clearPriorForecasts();
    // A changed key no longer belongs to a fit generated in this tab.
    if (earlier) earlier.created = false;
    refresh();
  });
  $("show-key").addEventListener("change", () => {
    $("profile-key").type = $("show-key").checked ? "text" : "password";
  });

  $("apply-prior").addEventListener("click", async () => {
    if ($("apply-prior").disabled) return;
    clearPriorForecasts();
    const task = beginJob($("apply-prior"));
    try {
      const coefficients = await carry.match(earlier.profile, $("profile-key").value, context(),
        sourceIdentity(slots[0]), sourceIdentity(slots[1]), fit.training?.packet_sha256 ?? []);
      if (job !== task) return;
      activePrior = coefficients;
      invalidateResults();
      carryMessage = "Comparing 11 forecasts on day 10 repeat 2. Each model uses the same fixed parents and separate day 9 and day 10 practice corrections.";
    } catch (error) { if (job === task) carryMessage = error.message; }
    finally { finishJob(task); }
  });
  $("clear-prior").addEventListener("click", () => {
    stopJob();
    clearPriorForecasts();
    forgetEarlier();
    invalidateResults();
    refresh();
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
