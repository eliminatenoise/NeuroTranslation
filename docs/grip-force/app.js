"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let HORIZON;
  const branches = [
    { key: "strong", label: "Force + motion", color: "#9ef0c5", shape: "circle" },
    { key: "eeg", label: "+ Scalp EEG", color: "#dfc7ff", shape: "diamond" },
    { key: "emg", label: "+ Surface EMG", color: "#ffc38b", shape: "square" },
    { key: "emg_eeg", label: "+ EEG and EMG", color: "#94c9ff", shape: "triangle" },
  ];
  const plot = $("grip-plot"), details = $("signal-plot"), slider = $("cutoff");
  const fileInput = $("local-file");
  const sourceLabel = $("source-label"), sourceDescription = $("source-description");
  const profile = $("signal"), channel = $("channel"), channelLabel = $("channel-label");
  let predict, windowData, scores, isSynthetic = true, request = 0, downloadUrl;
  let replay = null, replayExample = false, showOutcome = false;
  let frame = 0;
  const hz500 = "500 Hz";
  const historyColor = "#cbeee0";

  function value(n) {
    const magnitude = Math.abs(n);
    return magnitude >= 1e4 || (magnitude > 0 && magnitude < 0.001) ? n.toExponential(2) : n.toFixed(3);
  }

  function axisValue(n) {
    const magnitude = Math.abs(n);
    if (magnitude >= 10000 || (magnitude > 0 && magnitude < 0.01)) return n.toExponential(1);
    return Number(n.toFixed(2)).toString();
  }

  function force(n) {
    return `${value(n)} N`;
  }

  function glyph(ctx, type, x, y, color) {
    if (type === "outcome") {
      ctx.beginPath();
      ctx.arc(x, y, 9, 0, 2 * Math.PI);
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
      return;
    }
    ctx.beginPath();
    if (type === "circle") ctx.arc(x, y, 5, 0, 2 * Math.PI);
    if (type === "square") ctx.rect(x - 4, y - 4, 8, 8);
    if (type === "diamond") {
      ctx.moveTo(x, y - 6); ctx.lineTo(x + 6, y); ctx.lineTo(x, y + 6); ctx.lineTo(x - 6, y); ctx.closePath();
    }
    if (type === "triangle") {
      ctx.moveTo(x, y - 6); ctx.lineTo(x + 6, y + 4); ctx.lineTo(x - 6, y + 4); ctx.closePath();
    }
    ctx.fillStyle = color;
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#192724";
    ctx.stroke();
  }

  function draw(canvas, times, samples, unit, predictions = []) {
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    const scale = Math.min(window.devicePixelRatio || 1, 3);
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    const ctx = canvas.getContext("2d");
    ctx.scale(canvas.width / width, canvas.height / height);
    ctx.font = `11px ${getComputedStyle(canvas).fontFamily}`;
    const forecasting = predictions.length > 0;
    const values = samples.concat(predictions.map(dot => dot.value));
    const amplitude = Math.max(...values.map(Math.abs)) || 1;
    const normalized = values.map(n => n / amplitude);
    let min = Math.min(...normalized), max = Math.max(...normalized);
    if (max === min) { min -= 0.1; max += 0.1; }
    const ticks = Array.from({ length: 5 }, (_, i) => min + (max - min) * i / 4);
    const tickLabels = ticks.map(tick => axisValue(tick * amplitude));
    const left = Math.max(38, ...tickLabels.map(label => ctx.measureText(label).width + 14));
    const right = width - (forecasting ? 27 : 32);
    const top = 25, bottom = height - 30;
    const end = forecasting ? HORIZON : 0;
    const x = ms => left + (ms + 400) / (end + 400) * (right - left);
    const y = n => bottom - 8 - (n - min) / (max - min) * (bottom - top - 16);
    const cutoff = x(0), future = x(end);
    function line(x1, y1, x2, y2, color, dashed = false) {
      ctx.beginPath();
      ctx.setLineDash(dashed ? [4, 4] : []);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      ctx.setLineDash([]);
    }
    if (forecasting) {
      ctx.fillStyle = "#223630";
      ctx.fillRect(cutoff, top - 4, future - cutoff + 10, bottom - top + 4);
    }
    ctx.fillStyle = "#cadad0";
    ctx.textBaseline = "middle";
    ctx.textAlign = "left";
    ctx.fillText(unit, 12, 13);
    for (const [i, t] of ticks.entries()) {
      const py = y(t);
      line(left, py, right, py, "#344a41");
      ctx.fillText(tickLabels[i], 8, py);
    }
    const tickTimes = width < 380 ? [-400, -200, 0] : [-400, -300, -200, -100, 0];
    if (forecasting) tickTimes.push(HORIZON);
    ctx.textAlign = "center";
    for (const time of tickTimes) {
      const px = x(time);
      const highlighted = time >= 0;
      line(px, top, px, bottom, highlighted ? "#8caaa0" : "#344a41", highlighted);
      const label = time === 0 ? "Cutoff" : time === HORIZON ? "+120 ms" : `−${Math.abs(time)}`;
      ctx.fillStyle = highlighted ? "#ecf9f0" : "#cadad0";
      ctx.fillText(label, px, bottom + 15);
    }
    ctx.fillStyle = "#cadad0";
    if (!forecasting) {
      ctx.textAlign = "right";
      ctx.fillText("Time before cutoff (ms)", width - 11, 13);
    }
    ctx.beginPath();
    samples.forEach((sample, i) => {
      const px = x(times[i] * 1000), py = y(sample / amplitude);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.strokeStyle = historyColor;
    ctx.lineWidth = forecasting ? 2.5 : 1.5;
    ctx.stroke();
    glyph(ctx, "circle", x(times.at(-1) * 1000), y(samples.at(-1) / amplitude), historyColor);
    for (const dot of predictions) glyph(ctx, dot.shape, future, y(dot.value / amplitude), dot.color);
  }

  function updateChannelOptions() {
    const meta = WayStudy.metadata;
    const options = {
      motion: GripForecast.TRACKERS.flatMap(tracker => ["X", "Y", "Z"].map(axis => `${tracker} ${axis}`)),
      eeg: meta.eegChannels,
      emg: meta.emgChannels,
    }[profile.value];
    channelLabel.hidden = !options;
    channel.replaceChildren(...(options ?? []).map((text, i) => new Option(text, i)));
    const preferred = { motion: 2, eeg: 13, emg: 0 }[profile.value];
    if (options) channel.value = preferred;
  }

  function signalWindow() {
    const main = windowData.time_from_cutoff_s.main;
    const i = Number(channel.value);
    if (profile.value === "motion") return {
      samples: windowData.position.map(row => row[Math.floor(i / 3)][i % 3]),
      clock: main, hz: hz500, label: channel.selectedOptions[0].text, unit: "source units",
    };
    if (profile.value === "eeg") return {
      samples: windowData.eeg.map(row => row[i]), clock: main, hz: hz500,
      label: `Scalp EEG · ${channel.selectedOptions[0].text}`, unit: "source units",
    };
    if (profile.value === "emg") return {
      samples: windowData.emg.map(row => row[i]), clock: windowData.time_from_cutoff_s.emg, hz: "4 kHz",
      label: `Surface EMG · ${channel.selectedOptions[0].text}`, unit: "source units",
    };
    return { samples: windowData.load_n, clock: main, hz: hz500, label: "Signed lift-axis force", unit: "N" };
  }

  function renderPlots() {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      if (!windowData) return;
      const points = branches.map(branch => ({ ...branch, value: scores[branch.key] }));
      if (replay && showOutcome) points.push({shape: "outcome", color: "#ffffff", value: replay.outcome(windowData.issue_offset)});
      draw(plot, windowData.time_from_cutoff_s.main, windowData.grip_n, "Grip force (N)", points);
      const signal = signalWindow();
      draw(details, signal.clock, signal.samples, signal.unit);
    });
  }

  function renderSignal() {
    if (!windowData) return;
    const { samples, hz, label, unit } = signalWindow();
    $("signal-source").textContent = `${label} · ${hz} · ${unit}`;
    $("signal-description").textContent =
      `${label}. ${samples.length.toLocaleString("en-AU")} samples. The last sample is ${value(samples.at(-1))} ${unit}.`;
    renderPlots();
  }

  function updateOutcome() {
    $("outcome-panel").hidden = !replay;
    $("outcome-data").hidden = !replay || !showOutcome;
    $("outcome-key").hidden = !replay || !showOutcome;
    const label = replayExample ? "invented" : "recorded";
    $("reveal").textContent = (showOutcome ? "Hide " : "Reveal ") + label + " grip at +120 ms";
    $("reveal").setAttribute("aria-expanded", String(showOutcome));
    $("error-rows").replaceChildren();
    $("observed-force").textContent = "";
    if (replay && showOutcome) {
      const observed = replay.outcome(windowData.issue_offset);
      $("outcome-label").textContent = replayExample ? "Invented later grip" : "Grip in your recording";
      $("outcome-key").textContent = replayExample ? "Invented later grip" : "Recorded later grip";
      $("observed-force").textContent = force(observed);
      $("error-rows").replaceChildren(...branches.map(({key, label}) => {
        const row = document.createElement("tr");
        const heading = document.createElement("th");
        heading.scope = "row";
        heading.textContent = label;
        row.append(heading);
        const error = scores[key] - observed;
        row.insertCell().textContent = (error > 0 ? "+" : "") + value(error);
        return row;
      }));
    }
  }

  function applyWindow(input, predictions, synthetic) {
    windowData = input;
    scores = predictions;
    isSynthetic = synthetic;
    $("error").hidden = true;
    sourceLabel.textContent = synthetic ? "Synthetic input" : "Local sensor window";
    sourceDescription.textContent = synthetic ? "Invented signals. No file is sent to a server." : "The file stays in this browser.";
    // Invented inputs are plain waves far from the recordings' scale: say so, so the forecasts are not read as results.
    const madeUp = " The signals are invented, and the EEG and EMG are plain waves far from the size of the recorded signals, so the four forecasts can disagree wildly or fall below zero. They show how each model reacts to made-up input, not how accurate it is: the development errors below come from real lifts.";
    document.querySelector(".forecast-note").textContent = synthetic
      ? "The example ends at cutoff. It has no later measurement for scoring these forecasts." + madeUp
      : "This input ends at cutoff. Scoring needs a separate grip measurement 120 ms later.";
    if (replay) {
      sourceLabel.textContent = replayExample ? "Invented trial replay" : "Local trial replay";
      sourceDescription.textContent = replayExample ? "All signals and later forces are invented." : "Sensor windows and plate readings stay in this tab.";
      document.querySelector(".forecast-note").textContent = "Move the cutoff through the lift. Reveal the later grip to compare it with these forecasts." + (replayExample ? madeUp : "");
    }
    $("reset").hidden = synthetic && !replay;
    $("demo-replay").hidden = replayExample;
    updateOutcome();
    slider.value = input.issue_offset * 2;
    slider.disabled = !synthetic && !replay;
    $("cutoff-value").textContent = `${(input.issue_offset * 2).toLocaleString("en-AU")} ms`;
    slider.setAttribute("aria-valuetext", `${input.issue_offset * 2} milliseconds after go cue`);
    $("present-force").textContent = force(scores.persistence);
    const readout = [];
    for (const { key, label } of branches) {
      const text = force(scores[key]);
      $(`p-${key}`).textContent = text;
      readout.push(`${label.replace(/^\+ /, "With ")} ${text}`);
    }
    const summary = `Grip at cutoff ${force(scores.persistence)}. At +120 milliseconds, ${readout.join(", ")}.`;
    $("grip-plot-description").textContent = `200 past samples followed by four point forecasts. ${summary}`;
    $("state").textContent = `${sourceLabel.textContent}. ${summary}`;
    renderSignal();
  }

  function setSynthetic() {
    replay = null;
    replayExample = false;
    showOutcome = false;
    const input = GripForecast.synthetic(Number(slider.value) / 2);
    applyWindow(input, predict(input), true);
  }

  function selectReplay(trial, example) {
    const issue = Number(slider.value) / 2;
    const input = trial.windowAt(issue);
    const predictions = trial.scoresAt(issue);
    replay = trial;
    replayExample = example;
    showOutcome = false;
    applyWindow(input, predictions, false);
  }

  function renderEvidence() {
    const { development: dev, eegChannels, emgChannels } = WayStudy.metadata;
    const n = size => size.toLocaleString("en-AU");
    const rmse = n => n.toFixed(6);
    $("dev-verdict").textContent = dev.gatePassed ? "EEG passed the registered test." : "The registered test did not support an EEG advantage.";
    $("dev-explanation").textContent =
      `The aligned EEG forecast narrowly lowered average error. EEG from the next trial at the same time after the cue scored better still. That control asks whether the signal had to come from the right lift. Root-mean-square error (RMSE) weights larger misses more heavily. The table gives each of the ${dev.participants} people equal weight.`;
    const rows = branches.map(({ key, label }) => [label.replace(/^\+ /, "With "), dev.wholeRmse[key]]);
    rows.push(["With time-matched EEG from the next trial", dev.matchedRmse.matched_rotated_eeg]);
    $("dev-rows").replaceChildren(...rows.map(([label, error]) => {
      const row = document.createElement("tr"), heading = document.createElement("th");
      heading.scope = "row";
      heading.textContent = label;
      row.append(heading);
      row.insertCell().textContent = rmse(error);
      return row;
    }));
    $("high-force").textContent =
      `On the ${n(dev.aboveHalfNewtonRows)} predictions with measured force above 0.5 N, the mechanical model scored ${rmse(dev.aboveHalfNewtonRmse.strong)} N and aligned EEG scored ${rmse(dev.aboveHalfNewtonRmse.eeg)} N.`;
    $("channel-order").textContent = `EEG order: ${eegChannels.join(", ")}. EMG order: ${emgChannels.join(", ")}.`;
  }

  function showError(message) {
    $("error").textContent = message;
    $("error").hidden = false;
  }

  try {
    if (typeof GripForecast === "undefined" || typeof GripForecast.fromBundle !== "function") {
      throw new Error("The forecast code could not load. Reload the page or extract the complete offline folder.");
    }
    if (typeof WayStudy === "undefined" || !WayStudy.models || !WayStudy.metadata) {
      throw new Error("The fitted models could not load. Reload the page or extract the complete offline folder.");
    }
    HORIZON = GripForecast.HORIZON_MS;
    predict = GripForecast.fromBundle(WayStudy.models);
    updateChannelOptions();
    renderEvidence();
    setSynthetic();
  } catch (error) {
    showError(error.message);
    $("open-file").disabled = true;
    slider.disabled = true;
    $("demo-replay").disabled = true;
    profile.disabled = true;
    channel.disabled = true;
    $("example").removeAttribute("href");
    $("example").setAttribute("aria-disabled", "true");
    return;
  }

  new ResizeObserver(renderPlots).observe(plot);
  new ResizeObserver(renderPlots).observe(details);
  profile.addEventListener("change", () => {
    updateChannelOptions();
    renderSignal();
  });
  channel.addEventListener("change", renderSignal);
  slider.addEventListener("input", () => {
    if (replay) {
      const input = replay.windowAt(Number(slider.value) / 2);
      applyWindow(input, replay.scoresAt(input.issue_offset), false);
    } else if (isSynthetic) setSynthetic();
  });
  $("demo-replay").disabled = typeof GripReplay === "undefined";
  $("demo-replay").addEventListener("click", () => {
    request++;
    selectReplay(GripReplay.invented(predict), true);
    slider.focus();
  });
  $("reveal").addEventListener("click", () => {
    if (!replay) return;
    showOutcome = !showOutcome;
    updateOutcome();
    renderPlots();
    $("state").textContent = showOutcome ? $("outcome-label").textContent + ": " + $("observed-force").textContent : "Later grip hidden.";
  });
  $("open-file").addEventListener("click", () => fileInput.click());
  $("reset").addEventListener("click", () => {
    request++;
    setSynthetic();
    slider.focus();
  });
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    fileInput.value = "";
    if (!file) return;
    const current = ++request;
    try {
      if (file.size > 3_000_000) throw new Error("Choose a window or a trial in a JSON file under 3 MB.");
      let input;
      try {
        input = JSON.parse(await file.text());
      } catch {
        throw new Error("This file could not be read as JSON.");
      }
      if (current !== request) return;
      if (input?.format === "way-grip-trial-v1") {
        if (typeof GripReplay === "undefined") throw new Error("The trial replay module could not load.");
        selectReplay(GripReplay.read(input, predict), false);
        return;
      }
      const predictions = predict(input);
      replay = null;
      replayExample = false;
      showOutcome = false;
      applyWindow(input, predictions, false);
    } catch (error) {
      if (current === request) showError(`${error.message} The displayed forecast is unchanged.`);
    }
  });
  $("example").addEventListener("click", event => {
    // Download the generated example only. A selected local file is never copied here.
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    const input = GripForecast.synthetic(Number(slider.value) / 2);
    downloadUrl = URL.createObjectURL(new Blob([JSON.stringify(input)], { type: "application/json" }));
    event.currentTarget.href = downloadUrl;
  });
})();
