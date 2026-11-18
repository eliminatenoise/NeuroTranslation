"use strict";

(() => {
  const element = id => document.getElementById(id);
  const plot = element("plot");
  const view = element("view");
  const axis = element("axis");
  const seed = element("seed");
  const input = element("packet");
  const clear = element("clear");
  const status = element("file-status");
  const trialOption = view.querySelector('[value="trial"]');
  const hasStudy = Array.isArray(window.WristStudy) && window.WristStudy.length === 6;
  let recording = null;
  let selection = 0;

  function displayRows() {
    const fit = seed.value;
    if (view.value === "study" || !recording) {
      return window.WristStudy.map(row => ({ time: row.seconds, values: row.fits[fit][axis.value] }));
    }
    const dim = axis.value === "extension" ? 0 : 1;
    return recording.rows.map(row => {
      const values = [row.forecasts.motion, row.forecasts.combined].map(method =>
        (fit === "mean" ? method.meanDegrees : method.bySeed[fit])[dim]
      );
      values.push(row.measuredDegrees[dim]);
      return { time: row.timeSeconds, values };
    });
  }

  function chart(rows, isTrial) {
    const width = plot.clientWidth;
    const height = plot.clientHeight;
    if (!width || !height) return;
    const context = plot.getContext("2d");
    if (!context) {
      element("chart").hidden = true;
      element("data-table").open = true;
      return;
    }
    const ratio = Math.min(window.devicePixelRatio || 1, 3);
    plot.width = Math.round(width * ratio);
    plot.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const values = rows.flatMap(row => row.values);
    const low = Math.min(0, ...values), high = Math.max(0, ...values);
    const rough = (high - low || 1) / 4;
    const magnitude = 10 ** Math.floor(Math.log10(rough));
    const unit = [1, 2, 2.5, 5, 10].find(v => v * magnitude >= rough) * magnitude;
    const bottom = Math.floor(low / unit) * unit, top = Math.max(bottom + unit, Math.ceil(high / unit) * unit);
    const left = 42, right = width - 12, upper = 27, lower = height - 49;
    const x = time => left + (time - rows[0].time) * (right - left) / (rows.at(-1).time - rows[0].time);
    const y = value => lower - (value - bottom) * (lower - upper) / (top - bottom);
    context.font = '12px system-ui, sans-serif';
    context.fillStyle = "#324951";
    context.textAlign = "left";
    context.fillText(isTrial ? "Wrist angle (°)" : "Root mean square error (°)", 1, 14);
    for (let i = 0; i <= Math.round((top - bottom) / unit); i++) {
      const value = bottom + i * unit;
      const line = y(value);
      context.strokeStyle = Math.abs(value) < 1e-10 ? "#90a29d" : "#dbe2df";
      context.lineWidth = 1;
      context.beginPath(); context.moveTo(left, line); context.lineTo(right, line); context.stroke();
      context.textAlign = "right";
      context.fillText(String(Number(value.toFixed(3))), left - 7, line + 4);
    }
    context.textAlign = "center";
    for (const row of rows) {
      context.fillText(row.time.toFixed(2), x(row.time), lower + 18);
    }
    context.fillText("Time after cue (s)", (left + right) / 2, height - 7);
    const colors = ["#075f78", "#a24423", "#44505c"];
    for (const row of rows) {
      row.values.forEach((value, index) => {
        const px = x(row.time), py = y(value);
        context.beginPath();
        context.strokeStyle = context.fillStyle = colors[index];
        context.lineWidth = 1.9;
        if (index === 0) {
          context.arc(px, py, 3.2, 0, 2 * Math.PI); context.fill();
        } else if (index === 1) {
          context.strokeRect(px - 4.4, py - 4.4, 8.8, 8.8);
        } else {
          context.moveTo(px, py - 6.7); context.lineTo(px + 6.7, py);
          context.lineTo(px, py + 6.7); context.lineTo(px - 6.7, py);
          context.closePath(); context.stroke();
        }
      });
    }
  }

  function draw() {
    if (!hasStudy) return;
    const isTrial = view.value === "trial" && recording !== null;
    const rows = displayRows();
    const axisLabel = axis.selectedOptions[0].textContent.toLowerCase();
    element("chart-title").textContent = isTrial ? "Where did the wrist go?" : "Forecast error during the turn";
    element("figure-note").textContent = isTrial
      ? "Each diamond is an angle measured by the wrist encoder. The circle and square are forecasts made from the preceding movement. The six points mark separate target times within this recording."
      : "Three development participants made 960 pointing movements. Each person contributes equally to the plotted root mean square error. Smaller values mean a closer forecast.";
    for (const id of ["reference-head", "reference-label"]) {
      element(id).textContent = isTrial ? "Measured angle" : "Last angle held";
    }
    const aggregation = seed.value === "mean"
      ? "Predictions are averaged across three fitted models" + (isTrial ? "." : " before scoring.")
      : "Showing one model fit for each input set, both trained with seed " + seed.value + ".";
    element("table-caption").textContent = (isTrial ? "Recorded and forecast angles for " : "Development error for ") +
      axisLabel + ", in degrees. " + aggregation;
    const body = element("values");
    const fragment = document.createDocumentFragment();
    for (const row of rows) {
      const tr = document.createElement("tr");
      const th = document.createElement("th");
      th.scope = "row"; th.textContent = row.time.toFixed(2) + " s"; tr.append(th);
      for (const value of row.values) {
        const td = document.createElement("td");
        td.textContent = value.toFixed(3) + "°"; td.dataset.value = String(value); tr.append(td);
      }
      fragment.append(tr);
    }
    body.replaceChildren(fragment);
    chart(rows, isTrial);
  }

  function forgetRecording() {
    recording = null;
    trialOption.disabled = true;
    view.value = "study";
    element("loaded-actions").hidden = true;
    draw();
  }

  function message(text, state) {
    status.dataset.state = state;
    status.textContent = text;
  }

  function parseUniqueFields(text) {
    const packet = JSON.parse(text);
    // JSON.parse accepts repeated names. Keep the converter's one-field-one-value rule.
    const containers = [];
    for (const match of text.matchAll(/"(?:\\[\s\S]|[^"\\])*"|[{}\[\]]/g)) {
      const token = match[0];
      if (token === "{") containers.push(new Set());
      else if (token === "[") containers.push(null);
      else if (token === "}" || token === "]") containers.pop();
      else {
        let end = match.index + token.length;
        while (/[ \t\r\n]/.test(text.charAt(end)) && end < text.length) end++;
        if (text[end] !== ":") continue;
        const key = JSON.parse(token);
        const objectKeys = containers.at(-1);
        if (objectKeys.has(key)) throw new Error("Repeated trial field");
        objectKeys.add(key);
      }
    }
    return packet;
  }

  if (hasStudy) {
    element("figure-controls").hidden = false;
    element("chart").hidden = false;
    for (const control of [view, axis, seed]) control.addEventListener("change", draw);
    draw();
    if (window.ResizeObserver) new ResizeObserver(() => chart(displayRows(), view.value === "trial")).observe(plot);
    else window.addEventListener("resize", draw);
  } else {
    element("data-table").open = true;
  }
  if (!hasStudy || !window.crypto?.subtle || typeof window.WristRecorded?.forecastRecordedTrial !== "function") {
    message("The replay tools could not be loaded in this browser. The development results remain available in the table.", "error");
    return;
  }

  input.disabled = false;
  message("Choose a converted trial. Its contents must match a recording in the published development study.", "ready");
  clear.addEventListener("click", () => {
    selection++;
    input.value = "";
    forgetRecording();
    message("Recording cleared. Showing the development results.", "ready");
    input.focus();
  });
  input.addEventListener("change", async () => {
    const current = ++selection;
    const file = input.files[0];
    forgetRecording();
    if (!file) {
      message("Choose a converted wrist trial.", "ready"); return;
    }
    if (!file.size || file.size > 64 * 1024) {
      input.value = "";
      message("Choose a nonempty wrist trial JSON file of 64 KiB or less.", "error"); return;
    }
    message("Checking the trial against the development recordings…", "working");
    try {
      const packet = parseUniqueFields(await file.text());
      const result = await window.WristRecorded.forecastRecordedTrial(packet);
      if (current !== selection) return;
      recording = result;
      trialOption.disabled = false;
      view.value = "trial";
      element("loaded-actions").hidden = false;
      draw();
      message("Recording verified. Six measured target times and all six fitted models are available above.", "verified");
    } catch {
      if (current !== selection) return;
      input.value = "";
      forgetRecording();
      message("This file could not be matched to an original development trial. Recreate it with the wrist trial converter and open it again.", "error");
    }
  });
})();
