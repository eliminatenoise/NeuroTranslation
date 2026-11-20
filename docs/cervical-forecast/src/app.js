"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const channels = [
    ["Armpit · Biceps", "Surface electrodes over the left armpit picked up a nerve-related voltage. Only the six early armpit dots enter the arm-signal model."],
    ["Neck · SC6", "A skin electrode over the sixth cervical vertebra measured voltage relative to an electrode on the mid-back."],
    ["Thumb · muscle", "Surface electrodes picked up electrical activity over the muscle at the base of the thumb. They did not measure thumb position."],
    ["Scalp · CP4", "A scalp electrode over the right side of the head measured voltage relative to the right mastoid, behind the ear."],
    ["Heart · ECG", "Two torso electrodes recorded voltage associated with the heartbeat. This input can help both models account for shared electrical activity."]
  ];
  const methods = [
    ["transformer_eng", "Transformer with early armpit signal"],
    ["transformer_noneng", "Transformer without armpit signal"],
    ["transformer_deranged", "Transformer with wrong-event armpit signal"],
    ["event_mean", "Fitting-group mean change"],
    ["baseline_subtraction", "Fitting-group later neck mean minus current baseline"],
    ["ridge_time", "Linear fit using event order"],
    ["ridge_pre", "Linear fit using pre-pulse readings and order"],
    ["ridge_noneng", "Linear fit without armpit signal"],
    ["ridge_eng", "Linear fit with early armpit signal"],
    ["ridge_deranged", "Linear fit with wrong-event armpit signal"]
  ];
  const prec = (n, digits = 3) => n.toFixed(digits).replace(/^-/, "−");
  const signed = (n, digits = 3) => (n > 0 ? "+" : "") + prec(n, digits);
  const addOption = (element, value, name) => element.add(new Option(name, String(value)));
  function tableRow(body, title, value) {
    const row = body.insertRow();
    const header = document.createElement("th");
    header.scope = "row";
    header.textContent = title;
    row.append(header);
    row.insertCell().textContent = value;
  }
  function showEvidence(study) {
    const people = study.people, events = study.events_per_person;
    const comparisons = study.paired_gain_comparator_minus_full;
    const paired = comparisons.transformer_noneng, mismatch = comparisons.transformer_deranged;
    const mainMAE = study.macro.transformer_eng.mae_uV, maskedMAE = study.macro.transformer_noneng.mae_uV;
    $("cohort").textContent = "Four development folds each fitted on three people and predicted the fourth. Each of the " + people +
      " people contributed " + events + " consecutive wrist-pulse events. Average errors give each person equal weight. The interactive models above were then fitted to all four people.";
    $("verdict").textContent = "The Transformer averaged " + prec(mainMAE) + " µV of error with the armpit reading and " +
      prec(maskedMAE) + " µV without it. Including the armpit recording reduced the error for " + paired.people_improved + " of " + people + " people.";
    $("mismatch").textContent = "Shift the early armpit readings by 37 events within each person, wrapping at the end. This breaks the match to the wrist pulse while preserving the values. The separately fitted model then averaged " +
      prec(study.macro.transformer_deranged.mae_uV) + " µV of error. Correct pairing gave lower error in " + mismatch.people_improved + " of " + people + " people.";
    $("uncertainty").textContent = "Across the four people, the reduction in error from adding the arm channel ranged from " +
      signed(paired.range_uV[0]) + " to " + signed(paired.range_uV[1]) + " µV. A negative reduction means the forecast got worse. The two-sided sign test gave p = " +
      prec(study.primary_exact_two_sided_sign_p) + ". This small development comparison supplies no reliable error interval for an individual prediction.";
    $("gate").textContent = (study.predeclared_development_criterion_met ? "The model met" : "The model fell short of") +
      " the prespecified rule requiring lower mean error against both matched comparisons and an improvement against both in at least three of four people. Both comparisons favoured the full model in " +
      study.people_improved_on_both + " of four.";
    for (const [key, name] of methods) tableRow($("scores"), name, prec(study.macro[key].mae_uV));
  }
  function showAssessment(report) {
    const trans = report.transformer, robust = report.robust;
    const score = key => prec(trans.macro[key].mae_uV);
    const pairs = trans.contrasts, noArm = pairs.transformer_noneng, wrong = pairs.transformer_same_fit_wrong;
    const rows = [
      ["Transformer with early armpit signal", trans.macro.transformer_eng],
      ["Transformer without armpit signal", trans.macro.transformer_noneng],
      ["Same Transformer with a wrong-event armpit signal", trans.macro.transformer_same_fit_wrong],
      ["Repeat latest neck change", trans.macro.neck_persistence],
      ["Fitting-group mean change", trans.macro.event_mean],
      ["Linear fit without armpit signal", trans.macro.ridge_noneng],
      ["Linear fit with early armpit signal", trans.macro.ridge_eng],
      ["Robust linear fit with armpit signal", robust.macro.with_axilla],
      ["Robust linear fit without armpit signal", robust.macro.other_sites],
      ["Same robust fit with wrong-event armpit signal", robust.macro.wrong_event]
    ];
    for (const [label, result] of rows) tableRow($("held-scores"), label, prec(result.mae_uV));
    $("held-verdict").textContent = "With the early armpit recording, the Transformer averaged " + score("transformer_eng") +
      " µV of error. Without it, the error was " + score("transformer_noneng") + " µV. The armpit reading reduced error for " + noArm.people_improved + " of six people. Simply repeating the last neck reading was closer, at " + score("neck_persistence") + " µV.";
    $("held-neck").textContent = "Repeating the change already observed at the neck during 7–8 ms gave " + score("neck_persistence") +
      " µV of error. A robust linear fit that used the arm and other sites to adjust that last neck reading scored " + prec(robust.macro.with_axilla.mae_uV) + " µV.";
    $("held-pair").textContent = "Give the fixed Transformer the armpit signal from the event 37 places ahead within the same person, wrapping at 80. Error became " + score("transformer_same_fit_wrong") +
      " µV. The correctly paired model beat both the no-arm and wrong-event comparisons for " + trans.people_improved_on_both + " of six people. " +
      (trans.criterion_met ? "It met" : "It fell short of") + " the prespecified threshold of five people and lower mean error against both.";
    $("held-range").textContent = "Individual error reductions for adding the armpit reading ranged from " + signed(noArm.range_uV[0]) + " to " + signed(noArm.range_uV[1]) +
      " µV (two-sided sign-test p = " + prec(noArm.exact_two_sided_sign_p) + "). Correct versus wrong pairing gave reductions from " +
      signed(wrong.range_uV[0]) + " to " + signed(wrong.range_uV[1]) + " µV (p = " + prec(wrong.exact_two_sided_sign_p) +
      "). Negative values mean a larger error with the correctly paired armpit signal.";
    $("held-robust").textContent = "The robust linear fit improved on both its other-sites and wrong-event controls for " + robust.people_improved_on_both +
      " of six. Its separate rule required at least 5% lower mean error against both and improvement in all six. The robust fit " +
      (robust.criterion_met ? "met" : "fell short of") + " that criterion. These six people came from one study.";
  }
  function start() {
    const {weights, development, assessment} = CERVICAL_STUDY;
    showAssessment(assessment);
    showEvidence(development);
    const model = CervicalModel;
    const state = {tokens: [], channel: 0, phase: 1, bin: 12, order: 39, x: []};
    const ci = () => state.channel;
    const phaseFirst = () => state.phase ? 10 : 0;
    const phaseCount = () => state.phase ? 6 : 10;
    const phaseMean = () => weights.transform.mean[state.phase][ci()];
    const phaseSD = () => weights.transform.sd[state.phase][ci()];
    const bound = t => (t < 10 ? -15 + t / 2 : 5 + (t - 10) / 2);
    const time = n => (n > 0 ? "+" : "") + String(n).replace(/^-/, "−");
    const binLabel = t => time(bound(t)) + " to " + time(bound(t) + 0.5) + " ms";
    function synthetic() {
      return Array.from({length:16}, (_, t) => channels.map((_, c) => {
        const p = Number(t >= 10);
        const wave = Math.sin((t + 1) * 0.85 + c * 0.54) * 0.26;
        return weights.transform.mean[p][c] + weights.transform.sd[p][c] * wave;
      }));
    }
    function populateBins() {
      $("bin").replaceChildren();
      for (let t = phaseFirst(); t < phaseFirst() + phaseCount(); t++) addOption($("bin"), t, binLabel(t));
      $("bin").value = state.bin;
    }
    function draw() {
      const canvas = $("signal"), ctx = canvas.getContext("2d");
      const rect = canvas.getBoundingClientRect();
      const w = Math.max(120, rect.width), h = rect.height;
      const scale = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(w * scale);
      canvas.height = Math.round(h * scale);
      ctx.scale(scale, scale);
      ctx.font = "11px Arial, sans-serif";
      const points = state.tokens.slice(phaseFirst(), phaseFirst() + phaseCount()).map(row => row[ci()]);
      const valid = points.filter(Number.isFinite);
      const center = phaseMean(), sigma = phaseSD();
      const low = Math.min(center - 0.55 * sigma, ...valid), high = Math.max(center + 0.55 * sigma, ...valid);
      const label = value => Math.abs(value) >= 10000 ? value.toExponential(1) : Number(value.toFixed(1)).toString();
      const margin = Math.max(36, ...[low, high].map(v => ctx.measureText(label(v)).width + 7));
      const right = w - 14, top = 14, bottom = h - 28;
      const x = i => margin + (i + 0.5) / points.length * (right - margin);
      const y = v => bottom - (v - low) / (high - low) * (bottom - top);
      state.x = points.map((_, i) => x(i));
      ctx.textAlign = "right";
      for (const v of [low, (low + high) / 2, high]) {
        ctx.strokeStyle = "#cfdbcf"; ctx.beginPath(); ctx.moveTo(margin, y(v)); ctx.lineTo(right, y(v)); ctx.stroke();
        ctx.fillStyle = "#496158"; ctx.fillText(label(v), margin - 5, y(v) + 4);
      }
      ctx.strokeStyle = "#25734d"; ctx.lineWidth = 2; ctx.beginPath();
      points.forEach((v, i) => {
        if (v === null) return;
        if (!i || points[i - 1] === null) ctx.moveTo(x(i), y(v)); else ctx.lineTo(x(i), y(v));
      });
      ctx.stroke();
      points.forEach((v, i) => {
        if (v === null) return;
        const selected = i + phaseFirst() === state.bin;
        ctx.beginPath(); ctx.arc(x(i), y(v), selected ? 6 : 3.5, 0, Math.PI * 2);
        ctx.fillStyle = selected ? "#f2b956" : "#216246"; ctx.fill();
        if (selected) {ctx.strokeStyle="#3a4d36"; ctx.lineWidth=1.5; ctx.stroke();}
      });
      const first = phaseFirst(), last = first + phaseCount() - 1;
      ctx.fillStyle="#496158"; ctx.textAlign="left"; ctx.fillText(time(bound(first)) + " ms", margin, h - 7);
      ctx.textAlign="right"; ctx.fillText(time(bound(last) + 0.5) + " ms", right, h - 7);
      $("chart-label").textContent = channels[ci()][0] + " · half-millisecond means";
      $("chart-summary").textContent = "Synthetic " + channels[ci()][0] + " voltage. " + points.length +
        " dots. Selected time " + binLabel(state.bin) + ". Values are available in the table.";
    }
    function predictAll() {
      const baseNeck = state.tokens.slice(0, 10).map(row => row[1]);
      const lastNeck = state.tokens.slice(14, 16).map(row => row[1]);
      const carry = $("persistence-value");
      const mean = values => values.reduce((sum, v) => sum + v / values.length, 0);
      const carryValue = mean(lastNeck) - mean(baseNeck);
      if ([...lastNeck, ...baseNeck, carryValue].every(Number.isFinite)) {
        carry.textContent = signed(carryValue) + " µV";
        carry.dataset.value = carryValue;
      } else {carry.textContent = "Input needed"; delete carry.dataset.value;}
      for (const [name, id] of [["eng","full-value"],["noneng","base-value"]]) {
        const inputs = state.tokens.map((row, t) => row.map((v, c) => c === 0 && (t < 10 || name === "noneng") ? 0 : v));
        let result = null;
        if (inputs.every(row => row.every(Number.isFinite))) {
          try {result = model.predict(inputs, state.order, weights, name);} catch (e) {
            if (!(e instanceof RangeError)) throw e;
          }
        }
        const cell = $(id);
        cell.textContent = result === null ? "Input needed" : signed(result) + " µV";
        if (result === null) delete cell.dataset.value; else cell.dataset.value = result;
      }
    }
    function render(editVoltage = true) {
      const value = state.tokens[state.bin][ci()];
      if (editVoltage) $("voltage").value = value === null ? "" : Number(value.toPrecision(12));
      $("voltage").setAttribute("aria-invalid",value === null ? "true" : "false");
      $("adjust").value = value === null ? 0 : (value - phaseMean()) / phaseSD();
      $("adjust").setAttribute("aria-valuetext", value === null ? "No value" : prec(value) + " microvolts");
      $("input-status").textContent = value === null ? "Enter a finite dot voltage to use this channel." :
        Math.abs((value - phaseMean()) / phaseSD()) > 3 ? "This value is beyond the slider range. The models use the number you entered." : "";
      $("channel-info").textContent = channels[ci()][1];
      $("dot-table").replaceChildren();
      for (let t = phaseFirst(); t < phaseFirst() + phaseCount(); t++) {
        const v = state.tokens[t][ci()];
        tableRow($("dot-table"), binLabel(t), v === null ? "Missing" : prec(v));
      }
      draw(); predictAll();
    }
    function changePhase() {
      $("phase").options[1].disabled = ci() === 0;
      if (ci() === 0) $("phase").value = "1";
      const updated = Number($("phase").value);
      if (updated !== state.phase) { state.phase = updated; state.bin = phaseFirst(); }
      populateBins(); render();
    }
    for (const [c, [name]] of channels.entries()) addOption($("channel"), c, name);
    for (let i=0; i<80; i++) addOption($("event"), i, i+1 + " of 80");
    function restore() {
      state.tokens = synthetic(); state.channel = 0; state.phase = 1; state.bin = 12; state.order = 39;
      $("channel").value = "0"; $("phase").value = "1"; $("event").value = "39"; changePhase();
    }
    $("channel").onchange = () => {state.channel = Number($("channel").value); changePhase();};
    $("phase").onchange = changePhase;
    $("event").onchange = () => {state.order = Number($("event").value); predictAll();};
    $("bin").onchange = () => {state.bin = Number($("bin").value); render();};
    $("voltage").oninput = () => {
      const value = $("voltage").valueAsNumber;
      state.tokens[state.bin][ci()] = Number.isFinite(value) ? value : null; render(false);
    };
    $("adjust").oninput = () => {state.tokens[state.bin][ci()] = phaseMean() + Number($("adjust").value) * phaseSD(); render();};
    $("signal").onclick = event => {
      const pos = event.clientX - $("signal").getBoundingClientRect().left;
      const nearest = state.x.reduce((best, x, i, xs) => Math.abs(x - pos) < Math.abs(xs[best] - pos) ? i : best, 0);
      state.bin = phaseFirst() + nearest; $("bin").value = state.bin; render();
    };
    $("restore").onclick = restore;
    restore();
    new ResizeObserver(draw).observe($("signal"));
  }
  if (["http:", "https:"].includes(location.protocol)) {
    document.querySelector(".zip").hidden = false;
    $("paper-link").hidden = false;
  }
  try {start();} catch (error) {
    $("load-error").hidden = false;
    $("load-error").textContent = "The model could not load. Extract the complete reader or reload this page.";
    throw error;
  }
})();
