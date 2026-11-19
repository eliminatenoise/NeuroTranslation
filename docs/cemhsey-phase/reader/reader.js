"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const math = PinchPhase, profiles = PhaseProfile, timing = PinchIntervals;
  const bundledBytes = new TextEncoder().encode(CEMHSEY_ARRAY_FIT_BYTES);
  const bundled = ArrayPinch.checkFit(JSON.parse(CEMHSEY_ARRAY_FIT_BYTES));
  const originNames = {measured_train_local: "the study’s 30% training recordings",
    user_supplied_local: "user-selected recordings", invented_signals: "invented recordings"};
  const phaseNames = ["initial rest", "rising target", "target hold", "falling target", "final rest"];
  let kind = "invented", model = null, modelHash = null, bundledHash = null;
  let seed = null, profile = null, secret = "", held = null, forecast = null, totals = null, revealed = false;
  let job = null;
  const fmt = n => Math.abs(n) < .0000005 ? "0.000000" : n.toFixed(6);
  function say(message, error = false) {
    $("status").dataset.error = String(error);
    $("status").textContent = message;
  }
  function context() {
    if (!model || !modelHash) throw Error("Choose a compatible parent model first.");
    if (kind === "archive" && !$("confirmed").checked) throw Error("Check the participant and recording identities against your sources.");
    return {kind, hash: modelHash, train: kind === "archive" ? profiles.trainingPeople($("training").value) : []};
  }
  function refresh() {
    const busy = Boolean(job), local = kind === "archive";
    $("invented-mode").setAttribute("aria-pressed", String(!local));
    $("archive-mode").setAttribute("aria-pressed", String(local));
    $("demo").hidden = local;
    $("archive").hidden = !local;
    $("run").disabled = busy || !bundledHash;
    $("model").disabled = busy;
    $("fit").disabled = busy || !model || !$("confirmed").checked || !$("cal-files").files.length;
    $("apply").disabled = busy || !profile || !$("test-file").files.length;
    $("cancel").hidden = !busy;
    $("score").disabled = busy || Boolean(totals);
    $("save-profile").disabled = busy || !profile;
    $("open-profile").disabled = busy || !model || !$("profile-file").files.length;
    $("inspect").hidden = !held;
    $("coeffs").hidden = !profile;
    $("scored").hidden = !totals;
  }
  function dropTest() {
    held = forecast = totals = null;
    revealed = false;
    $("reveal").setAttribute("aria-pressed", "false");
    $("reveal").textContent = "Reveal gauge reading";
    $("actual").hidden = true;
    $("points").replaceChildren();
    $("score-rows").replaceChildren();
  }
  function hideKey() {
    $("key").type = "password";
    $("show-key").textContent = "Show key";
    $("show-key").setAttribute("aria-pressed", "false");
  }
  function forget() {
    profile = null; secret = ""; $("key").value = ""; hideKey(); dropTest();
    $("gain-rows").replaceChildren();
  }
  function stop() {
    if (job) { const pending = job; job = null; pending.cancel?.(); }
  }
  function run(task) {
    stop();
    const token = {check() { if (job !== token) throw new DOMException("Cancelled", "AbortError"); }};
    job = token;
    refresh();
    Promise.resolve().then(() => task(token)).catch(error => {
      if (job === token) say(error.message, true);
    }).finally(() => { if (job === token) { job = null; refresh(); } });
  }
  function mode(next) {
    stop(); forget(); kind = next;
    for (const key of ["model","cal-files","test-file","profile-file","training"]) $(key).value = "";
    $("confirmed").checked = false;
    model = next === "invented" ? bundled : null;
    modelHash = next === "invented" ? bundledHash : null;
    $("model-label").textContent = "Choose a compatible local parent fit.";
    say(next === "invented" ? "The invented example is ready." : "Select your parent model and check its training sources.");
    refresh();
  }
  function table(id, rows) {
    const fragment = document.createDocumentFragment();
    for (const row of rows) {
      const tr = document.createElement("tr");
      row.forEach((value, i) => {
        const cell = document.createElement(i ? "td" : "th");
        if (!i) cell.scope = "row";
        cell.textContent = typeof value === "number" ? fmt(value) : value;
        tr.append(cell);
      });
      fragment.append(tr);
    }
    $(id).replaceChildren(fragment);
  }
  function useProfile(p, key) {
    profile = p; secret = key; $("key").value = key; hideKey();
    table("gain-rows", math.parents.map((p, i) => [math.parentNames[i], ...math.directions.map(d => profile.gains[p][d])]));
    refresh();
  }
  async function decode(file, token, label) {
    let progress = -1;
    const op = CemhseyMat.start(file, {onProgress: item => {
      const step = Math.floor(item.fraction * 4);
      if (job === token && item.phase === "converting" && step > progress) {
        progress = step; say(label + " · converting " + (step * 25) + "%");
      }
    }});
    token.cancel = op.cancel;
    try { const trial = await op.promise; token.check(); return trial; }
    finally { token.cancel = null; }
  }
  function makeExample(record) {
    seed ??= ArrayPinch.example();
    return math.example(seed, Number(record.person), record.repeat);
  }
  async function build(records, token) {
    const ctx = context();
    const sorted = profiles.roster(records, ctx.train), seen = [], inputs = [], sums = math.newFit();
    for (const record of sorted) {
      token.check();
      const message = "Calibrating trial " + (seen.length + 1) + " of 6";
      say(message + "…");
      const trial = ctx.kind === "archive" ? await decode(record.file, token, message) : makeExample(record);
      const digest = await timing.packetIdentity(trial);
      token.check();
      profiles.recordOK(digest, seen, model.training?.packet_sha256 ?? []);
      seen.push(digest);
      inputs.push({person: record.person, repeat: record.repeat, digest});
      await math.fitTrial(sums, trial, model, token.check);
    }
    const key = profiles.keyText(), p = await profiles.make(ctx, inputs, math.finish(sums), key);
    token.check(); useProfile(p, key);
  }
  async function holdTrial(record, token) {
    const ctx = context(), tag = await profiles.open(profile, secret, ctx);
    token.check();
    if (ctx.train.includes(record.person) || profile.fit_people.includes(await tag("person", record.person))) {
      throw Error("This test participant supplied calibration or parent training. Choose another participant.");
    }
    token.check();
    say("Opening the separate test repeat…");
    const trial = kind === "archive" ? await decode(record.file, token, "Test repeat") : makeExample(record);
    const digest = await timing.packetIdentity(trial);
    await profiles.separate(profile, tag, {person: record.person, digest}, model.training?.packet_sha256 ?? []);
    token.check();
    const predict = math.forecaster(trial, model, profile.gains);
    predict(Number($("cutoff").value)); // Check the selected issue before replacing the current view.
    held = trial; forecast = predict;
    $("test-origin").textContent = kind === "invented" ? "Invented force and EMG · separate invented person · repeat " + record.repeat :
      "Local file · archive labels identify a separate participant, day 1, 50% MVC, repeat " + record.repeat + ". The file reports parent weights fitted on " + originNames[model.fit_origin] + ".";
    refresh();
    try { render(); } catch (error) { dropTest(); refresh(); throw error; }
    say("Eleven forecasts are ready. Inspect a cutoff or score the whole test repeat.");
  }
  function render() {
    if (!held) return;
    const i = Number($("cutoff").value), selected = forecast(i), end = selected.tick + timing.horizon;
    $("time").textContent = (selected.tick / 200).toFixed(2) + " s";
    $("cutoff-note").textContent = "Forecast for " + (end / 200).toFixed(2) + " s · " +
      phaseNames[timing.phases.indexOf(timing.phaseAt(selected.tick))] + " at issue · scheduled change " +
      (selected.u > 0 ? "rising" : selected.u < 0 ? "falling" : "flat") + " over the horizon.";
    const arm = $("arm").value, series = [];
    $("estimate").textContent = math.names[arm] + " · " + fmt(selected.points[arm]) + " of MVC";
    for (let index = 0; index <= i; index += Math.max(1, Math.floor(i / 90))) {
      const {tick, points} = forecast(index);
      series.push({tick, point: points[arm]});
    }
    if (series.at(-1).tick !== selected.tick) series.push({tick: selected.tick, point: selected.points[arm]});
    if (revealed) for (const entry of series) entry.observed = held.force[entry.tick + timing.horizon];
    PinchPlot.draw($("plot"), series, selected.tick, false);
    $("actual").hidden = !revealed;
    $("actual").textContent = revealed ? "Gauge at " + (end / 200).toFixed(2) + " s · " + fmt(held.force[end]) +
      " of MVC. The dashed line shows the revealed gauge trace." : "";
    table("points", math.arms.map(key => [math.names[key], selected.points[key]]));
  }
  function safeRender() {
    try { render(); } catch (error) { stop(); dropTest(); refresh(); say(error.message, true); }
  }
  function showScores() {
    if (!totals) return;
    const group = totals[$("group").value];
    $("score-n").textContent = group.n + " issue times · one " + (kind === "invented" ? "invented " : "selected ") + "test repeat.";
    table("score-rows", math.arms.map(key => {
      const {mae, rmse, bias, relative} = group.rows[key];
      return [math.names[key], mae, rmse, bias, relative];
    }));
  }

  for (const key of math.arms) $("arm").add(new Option(math.names[key], key));
  $("arm").value = "persistence_plus_cue_change_split";
  $("invented-mode").onclick = () => { if (kind !== "invented") mode("invented"); };
  $("archive-mode").onclick = () => { if (kind !== "archive") mode("archive"); };
  $("cancel").onclick = () => { stop(); refresh(); say("Operation cancelled."); };
  $("run").onclick = () => {
    forget();
    run(async token => {
      await build(["1", "2", "3"].flatMap(person => [1, 2].map(repeat => ({person, repeat}))), token);
      await holdTrial({person:"4", repeat:2}, token);
    });
  };
  $("model").onchange = () => {
    forget(); model = modelHash = null; $("confirmed").checked = false;
    $("model-label").textContent = "Choose a compatible local parent fit.";
    const file = $("model").files[0];
    if (!file) { refresh(); return; }
    run(async token => {
      if (file.size > 128 * 1024) throw Error("Choose a parent JSON under 128 KiB.");
      const bytes = await file.arrayBuffer(), next = TransferSources.readFit(bytes, bundled);
      if (next.fit_origin === "invented_signals") throw Error("Use the invented example for invented parent weights. Choose your original 30% fit for archive trials.");
      const hash = await timing.digest(bytes); token.check();
      model = next; modelHash = hash;
      $("model-label").textContent = "The selected file reports weights fitted on " + originNames[next.fit_origin] +
        ". " + (next.training?.packet_sha256 ? "Training fingerprints are present." : "The file has no training fingerprints.");
      say("Check the three training identities against the parent model’s sources.");
    });
  };
  const clearOnCalibrationChange = () => { stop(); forget(); refresh(); say("The calibration inputs changed. Fit the selected files or reopen a compatible correction."); };
  $("training").oninput = () => { $("confirmed").checked = false; clearOnCalibrationChange(); };
  $("confirmed").onchange = clearOnCalibrationChange;
  $("cal-files").onchange = clearOnCalibrationChange;
  $("test-file").onchange = () => { stop(); dropTest(); refresh(); say("Choose Forecast the test trial to apply the current correction."); };
  $("fit").onclick = () => {
    forget();
    run(async token => {
      const records = Array.from($("cal-files").files, profiles.archiveName);
      await build(records, token);
      say("Six calibration repeats fitted. Choose one test repeat from a separate participant or save the correction.");
    });
  };
  $("apply").onclick = () => {
    dropTest();
    run(token => holdTrial(profiles.archiveName($("test-file").files[0]), token));
  };
  $("save-profile").onclick = () => {
    if (!profile) return;
    $("key").value = secret;
    const url = URL.createObjectURL(new Blob([JSON.stringify(profile) + "\n"], {type:"application/json"}));
    const a = document.createElement("a"); a.href = url; a.download = "private-pinch-correction.json"; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    say("Correction saved locally. Use Show key and keep the key separately for reopening.");
  };
  $("show-key").onclick = () => {
    const show = $("key").type === "password";
    $("key").type = show ? "text" : "password";
    $("show-key").textContent = show ? "Hide key" : "Show key";
    $("show-key").setAttribute("aria-pressed", String(show));
  };
  $("profile-file").onchange = () => { stop(); refresh(); };
  $("open-profile").onclick = () => {
    const key = $("key").value.trim().toLowerCase(), file = $("profile-file").files[0];
    forget(); $("key").value = key;
    run(async token => {
      const ctx = context();
      if (!file || file.size > 8192) throw Error("Choose a correction JSON under 8 KiB.");
      let p; try { p = JSON.parse(await file.text()); } catch { throw Error("Choose the original correction JSON."); }
      await profiles.open(p, key, ctx); token.check(); useProfile(p, key);
      if (kind === "invented") await holdTrial({person:"4", repeat:2}, token);
      else say("Correction reopened. Select a separate participant’s test repeat.");
    });
  };
  $("cutoff").oninput = () => { revealed = false; $("reveal").textContent = "Reveal gauge reading"; $("reveal").setAttribute("aria-pressed", "false"); safeRender(); };
  $("arm").onchange = safeRender;
  $("reveal").onclick = () => {
    revealed = !revealed; $("reveal").textContent = revealed ? "Hide gauge reading" : "Reveal gauge reading";
    $("reveal").setAttribute("aria-pressed", String(revealed)); safeRender();
  };
  $("score").onclick = () => run(async token => {
    say("Scoring all 592 issues on this test repeat…");
    const result = await math.score(held, forecast, token.check);
    token.check(); totals = result; showScores(); refresh(); say("Test repeat scored at 592 issue times.");
  });
  $("group").onchange = showScores;
  window.addEventListener("resize", safeRender);
  if (location.protocol === "file:") $("zip").hidden = true;
  refresh();
  timing.digest(bundledBytes).then(hash => {
    bundledHash = hash;
    if (kind === "invented") { model = bundled; modelHash = hash; }
    refresh();
  }).catch(error => say(error.message, true));
})();
