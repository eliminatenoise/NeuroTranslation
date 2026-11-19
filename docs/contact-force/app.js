"use strict";

const engine = globalThis.ContactForecast;
const metadata = globalThis.ContactModelData;
const el = (id) => document.getElementById(id);
const controls = {
  example: el("example"), file: el("file-input"), variant: el("variant"), signal: el("signal"),
  channel: el("channel"), reveal: el("show-target"), scrub: el("scrub"),
};
const offsetInputs = Array.from(document.querySelectorAll('input[name="offset"]'));
const labels = {
  short_history: "Fewer than 200 samples were recorded by this issue.",
  issue_outside_recording: "The recording ends before this issue.",
  left_censored: "Force was already at or above 0.5 N at the first sample after the go cue.",
  right_censored_incomplete_run: "The recording ends before the run reaches ten samples.",
  right_censored_below_at_end: "This recording never reaches ten consecutive samples at or above 0.5 N.",
};
const state = { origin: "synthetic", offset: 100, input: null,
  evaluated: new Map(), importGeneration: 0 };
const trackers = ["Object", "Index finger", "Thumb", "Wrist"];
const axis = ["X", "Y", "Z"];
const canvas = el("chart");
const ctx = canvas.getContext("2d");
const colors = { grip: "#8fe3cb", load: "#b5c5f0", trace: "#8fe3cb", ridge: "#7fefd1",
  cnn: "#ffa181", target: "#c9befa" };
const number = (value, digits = 3) => !Number.isFinite(value) ? "—" :
  Math.abs(value) >= 10000 ? value.toExponential(2) : value.toFixed(digits).replace(/^-/, "−");
const units = (value, unit, digits) => Number.isFinite(value) ? `${number(value, digits)} ${unit}` : "—";
const relTime = (value) => `${value > 0.05 ? "+" : ""}${number(value, 1)} ms`;

function toggleSecondary(message) {
  el("prediction-status").hidden = !message;
  el("prediction-status").textContent = message;
}

function setImport(message = "", error = false) {
  el("import-status").hidden = !message;
  el("import-status").classList.toggle("error", error);
  el("import-status").textContent = message;
}

function replaceInput(raw, origin) {
  const validated = engine.validate(raw);
  state.input = validated;
  state.origin = origin;
  state.evaluated.clear();
  state.offset = validated.kind === "window" ? validated.offset_from_confirmation_ms : 100;
  if (validated.kind === "capture" && Number.isFinite(validated.event.time) &&
      engine.throughIssue(validated, state.offset).status !== "ok") {
    state.offset = engine.OFFSETS.find((ms) => engine.throughIssue(validated, ms).status === "ok") ?? 0;
  }
  controls.reveal.checked = false;
  controls.scrub.value = 199;
  controls.signal.value = "force";
  controls.variant.value = "mechanics";
  render();
}

function current() {
  if (!state.evaluated.has(state.offset)) {
    state.evaluated.set(state.offset, engine.forecast(state.input, state.offset, metadata));
  }
  return state.evaluated.get(state.offset);
}

function modelPair(data) {
  const key = controls.variant.value;
  return {
    ridge: data.values?.[`ridge_${key}`],
    cnn: data.values?.[`cnn_${key}`],
  };
}

function setForceOutput(id, value) {
  const output = el(id);
  output.textContent = number(value);
  if (Number.isFinite(value)) {
    const unit = document.createElement("small");
    unit.textContent = " N";
    output.append(unit);
  }
}

function syncChoices(data) {
  const available = {
    force: true, position: data.status === "ok", eeg: Boolean(data.eeg), emg: Boolean(data.emg),
  };
  if (!available[controls.signal.value]) controls.signal.value = "force";
  for (const option of controls.signal.options) option.disabled = !available[option.value];

  const options = {
    mechanics: true, time: true, eeg: available.eeg, emg: available.emg, emg_eeg: available.emg && available.eeg,
  };
  if (!options[controls.variant.value]) controls.variant.value = "mechanics";
  for (const option of controls.variant.options) option.disabled = !options[option.value];
}

function syncChannel(data) {
  const signal = controls.signal.value;
  const names = {
    position: trackers.flatMap((name) => axis.map((dimension) => `${name} · ${dimension}`)),
    eeg: metadata.channels.eeg,
    emg: metadata.channels.emg,
  }[signal];
  el("channel-label").hidden = !names || data.status !== "ok";
  if (names && controls.channel.dataset.trace !== signal) {
    controls.channel.replaceChildren(...names.map((name, i) => new Option(name, i)));
    controls.channel.value = signal === "position" ? "2" : "0";
    controls.channel.dataset.trace = signal;
  }
}

function seriesFor(data) {
  const { signal, channel } = controls;
  const index = Number(channel.value);
  if (signal.value === "position") return {
    time: data.clock_s, scale: "Source position scale",
    lines: [{ key: "trace", label: channel.selectedOptions[0].text,
      values: data.position.map((row) => row[Math.floor(index / 3)][index % 3]) }],
  };
  if (signal.value === "eeg" || signal.value === "emg") return {
    time: signal.value === "emg" ? data.emg_clock_s : data.clock_s, scale: "Source amplitude scale",
    lines: [{ key: "trace", label: channel.selectedOptions[0].text,
      values: data[signal.value].map((row) => row[index]) }],
  };
  return {
    time: data.clock_s, scale: "Force (N)",
    lines: [{ key: "grip", label: "Grip", values: data.grip_n },
      { key: "load", label: "Load", values: data.load_n }],
  };
}

function updateLegend(entries) {
  el("legend").replaceChildren(...entries.map(({ key, label }) => {
    const container = document.createElement("span");
    const icon = document.createElement("i");
    icon.className = `plot-key ${key}`;
    icon.setAttribute("aria-hidden", "true");
    container.append(icon, label);
    return container;
  }));
}

function draw(data) {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const resolution = Math.min(devicePixelRatio || 1, 2);
  if (canvas.width !== Math.round(width * resolution)) canvas.width = Math.round(width * resolution);
  if (canvas.height !== Math.round(height * resolution)) canvas.height = Math.round(height * resolution);
  ctx.setTransform(resolution, 0, 0, resolution, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.font = "12px system-ui, sans-serif";
  ctx.fillStyle = "#c9dbd6";
  if (data.status !== "ok") {
    ctx.textAlign = "center";
    ctx.fillText("No history at this issue", width / 2, height / 2);
    el("trace-reader").hidden = true;
    updateLegend([]);
    canvas.setAttribute("aria-label", "No history at this issue");
    return;
  }
  const graph = seriesFor(data);
  const force = controls.signal.value === "force";
  const marks = force ? modelPair(data) : {};
  const target = controls.reveal.checked ? engine.comparisonTarget(state.input, data) : undefined;
  if (force && Number.isFinite(target)) marks.target = target;
  const timeFromConfirmation = (t) => (t - state.input.event.time) * 1000;
  const first = timeFromConfirmation(graph.time[0]);
  const issued = state.offset;
  const last = issued + 120;
  const points = [...graph.lines.flatMap((line) => line.values), ...Object.values(marks).filter(Number.isFinite)];
  if (force) points.push(0, engine.THRESHOLD);
  const magnitude = Math.max(1e-24, ...points.map(Math.abs));
  const normalized = points.map((value) => value / magnitude);
  const bottom = Math.min(...normalized);
  const top = Math.max(...normalized);
  const pad = (top - bottom || 0.2) * 0.12;
  const area = { left: width < 420 ? 47 : 58, right: width - 23, top: 37, bottom: height - 36 };
  const x = (value) => area.left + (value - first) / (last - first) * (area.right - area.left);
  const y = (value) => area.bottom - (value - bottom + pad) / (top - bottom + 2 * pad) *
    (area.bottom - area.top);
  const horizontal = (yPos, x0, x1) => { ctx.beginPath(); ctx.moveTo(x0, yPos); ctx.lineTo(x1, yPos); ctx.stroke(); };
  const vertical = (value, color, dash) => {
    ctx.strokeStyle = color;
    ctx.setLineDash(dash);
    ctx.beginPath();
    ctx.moveTo(x(value), area.top);
    ctx.lineTo(x(value), area.bottom);
    ctx.stroke();
    ctx.setLineDash([]);
  };

  ctx.fillStyle = "#1f3332";
  ctx.fillRect(x(issued), area.top, area.right - x(issued), area.bottom - area.top);
  ctx.font = `${width < 420 ? 10 : 11}px system-ui, sans-serif`;
  ctx.fillStyle = "#c9dbd6";
  ctx.textAlign = "left";
  ctx.fillText(graph.scale, 12, 20);
  ctx.textAlign = "right";
  ctx.fillText(force ? "120 ms ahead" : "No input after issue", area.right, 20);
  for (let tick = 0; tick <= 4; tick += 1) {
    const value = bottom + (top - bottom) * tick / 4;
    if (tick > 0 && top === bottom) break;
    const pos = y(value);
    ctx.strokeStyle = "#354b48";
    horizontal(pos, area.left, area.right);
    ctx.fillStyle = "#c9dbd6";
    ctx.fillText(number(value * magnitude, 1), area.left - 8, pos + 3);
  }
  if (force) {
    ctx.strokeStyle = "#9ab0a9";
    ctx.setLineDash([2, 3]);
    horizontal(y(engine.THRESHOLD / magnitude), area.left, x(issued));
    ctx.setLineDash([]);
  }
  vertical(issued, "#e2ece8", [4, 4]);
  if (first < -30 && issued > 35) vertical(0, "#80988f", [2, 3]);
  ctx.textAlign = "center";
  ctx.fillText(`${number(first, 0)} ms`, area.left, height - 13);
  ctx.fillText(`+${last} ms`, area.right - 3, height - 13);
  const issueTick = issued ? `+${issued} ms` : "0 ms";
  if (width < 420) {
    ctx.textAlign = "right";
    ctx.fillText(issueTick, x(issued) + 3, height - 13);
  } else {
    ctx.fillText(`${issueTick} · issue`, x(issued), height - 13);
  }
  if (first < -70 && issued > 70 && width > 580) {
    ctx.fillText("0 ms · confirmation", x(0), height - 13);
  }
  for (const line of graph.lines) {
    ctx.strokeStyle = colors[line.key];
    ctx.setLineDash(line.key === "load" ? [5, 4] : []);
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    line.values.forEach((value, i) => {
      const position = x(timeFromConfirmation(graph.time[i]));
      const ordinate = y(value / magnitude);
      if (i === 0) ctx.moveTo(position, ordinate);
      else ctx.lineTo(position, ordinate);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.lineWidth = 1;
  for (const [key, value] of Object.entries(marks)) {
    if (!Number.isFinite(value)) continue;
    const markX = x(last);
    const markY = y(value / magnitude);
    ctx.strokeStyle = colors[key];
    ctx.fillStyle = colors[key];
    ctx.beginPath();
    if (key === "cnn") {
      ctx.moveTo(markX, markY - 5);
      ctx.lineTo(markX + 5, markY);
      ctx.lineTo(markX, markY + 5);
      ctx.lineTo(markX - 5, markY);
      ctx.closePath();
      ctx.fill();
    } else {
      ctx.arc(markX, markY, key === "target" ? 7 : 4, 0, 2 * Math.PI);
      if (key === "target") {
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.lineWidth = 1;
      } else ctx.fill();
    }
  }
  const sample = controls.scrub;
  sample.max = graph.time.length - 1;
  const index = Number(sample.value);
  const sampleTime = timeFromConfirmation(graph.time[index]);
  if (index < graph.time.length - 1) vertical(sampleTime, "#8bf2cb", [2, 5]);
  el("sample").textContent = [relTime(sampleTime), ...graph.lines.map(({ label, values }) =>
    `${label} ${units(values[index], force ? "N" : "", 3).trim()}`)].join(" · ");
  el("scrub-label").textContent = "Read a history sample";
  el("trace-reader").hidden = false;
  const markers = { ridge: "Ridge forecast", cnn: "CNN forecast", target: "Revealed target" };
  const threshold = force ? [{ key: "threshold", label: "0.5 N threshold" }] : [];
  updateLegend([...graph.lines, ...threshold, ...Object.entries(marks).filter(([, value]) => Number.isFinite(value))
    .map(([key]) => ({ key, label: markers[key] }))]);
  canvas.setAttribute("aria-label", `${graph.lines.map(({ label }) => label).join(" and ")} history ` +
    `from ${relTime(first)} to issue at ${issued} ms after confirmation. ` +
    (force ? "Forecast markers sit 120 ms after issue." : "Use the history slider to read a sample."));
}

function render() {
  const data = current();
  const { input, origin, offset } = state;
  const ok = data.status === "ok";
  const window = input.kind === "window";
  el("source-indicator").classList.toggle("local", origin !== "synthetic");
  el("origin").textContent = origin === "synthetic" ? "Synthetic signals" :
    (window ? "Local prepared window" : "Local capture · source unverified");
  for (const control of offsetInputs) {
    control.checked = Number(control.value) === offset;
    control.disabled = window && !control.checked;
  }
  el("event-caption").textContent = window ? "Confirmation supplied with the window" :
    (Number.isFinite(input.event.time) ? `Confirmed at ${number(input.event.time)} s` : "Force confirmation unavailable");
  el("issue-caption").textContent = ok ? `Issue ${number(data.issue)} s · target ${number(data.target)} s` : "No forecast at this issue";
  syncChoices(data);
  syncChannel(data);
  const targetValue = engine.comparisonTarget(input, data);
  el("target-label").hidden = !Number.isFinite(targetValue) || controls.signal.value !== "force";
  el("target-row").hidden = !controls.reveal.checked || !Number.isFinite(targetValue);
  el("target-term").textContent = origin === "synthetic" ? "Synthetic target grip" : "Supplied target grip";
  el("target-value").textContent = units(targetValue, "N");
  let reason = labels[data.status] || "";
  if (ok && data.invalid.length) reason = "Some input values produced a forecast outside the finite numerical range.";
  else if (ok && controls.variant.value.startsWith("emg")) reason = "The released CNN has no surface EMG branch.";
  else if (ok && input.emg && !data.emg) reason = "This issue lacks a complete, aligned 4 kHz muscle history.";
  toggleSecondary(reason);
  const pair = modelPair(data);
  setForceOutput("ridge-value", pair.ridge);
  setForceOutput("cnn-value", pair.cnn);
  el("grip-value").textContent = units(data.values?.persistence, "N");
  el("slope-value").textContent = units(data.values?.backward_slope, "N");
  draw(data);
}

function setStudy() {
  const d = metadata.development;
  const rows = [
    ["Force and motion", d.ridge.mechanics, d.cnn.mechanics],
    ["Force, motion and aligned EEG", d.ridge.aligned_eeg, d.cnn.aligned],
    ["EEG from another lift at matched phase", d.ridge.rotated_eeg, d.cnn.rotated],
  ];
  const table = el("study-values");
  for (const [name, ridge, cnn] of rows) {
    const row = table.insertRow();
    const label = document.createElement("th");
    label.scope = "row";
    label.textContent = name;
    row.append(label);
    row.insertCell().textContent = number(ridge);
    row.insertCell().textContent = number(cnn);
  }
  const interval = (pair) => pair.map((n) => `${n > 0 ? "+" : ""}${number(n)}`).join(" to ");
  el("uncertainty").textContent = `Adding aligned EEG changed mean RMSE by +${number(d.ridgeDelta.mean)} N for ridge ` +
    `and +${number(d.cnnDelta.mean)} N for CNN. Descriptive 95% intervals, ridge ${interval(d.ridgeDelta.interval)} N ` +
    `and CNN ${interval(d.cnnDelta.interval)} N, both include zero.`;
}

controls.example.addEventListener("change", () => {
  state.importGeneration += 1;
  setImport();
  replaceInput(engine.synthetic(controls.example.value), "synthetic");
});
el("import-button").addEventListener("click", () => controls.file.click());
controls.file.addEventListener("change", async () => {
  const file = controls.file.files[0];
  controls.file.value = "";
  if (!file) return;
  const generation = ++state.importGeneration;
  setImport("Reading the local file…");
  try {
    if (file.size > 16 * 1024 * 1024) throw new Error("Choose a single JSON capture under 16 MiB.");
    const raw = JSON.parse(await file.text());
    if (generation !== state.importGeneration) return;
    replaceInput(raw, "local");
    controls.example.selectedIndex = -1;
    setImport("Opened locally. Use the example menu to return to synthetic signals.");
  } catch (error) {
    if (generation === state.importGeneration) {
      const message = error instanceof SyntaxError ? "The file is not valid JSON." : error.message;
      setImport(`${message} The previous input is still displayed.`, true);
    }
  }
});
for (const input of offsetInputs) {
  input.addEventListener("change", () => {
    state.offset = Number(input.value);
    controls.scrub.value = controls.scrub.max;
    render();
  });
}
controls.signal.addEventListener("change", () => {
  const maximum = controls.signal.value === "emg" ? 1599 : 199;
  controls.scrub.max = maximum;
  controls.scrub.value = maximum;
  render();
});
for (const control of [controls.reveal, controls.variant, controls.channel]) {
  control.addEventListener("change", render);
}
controls.scrub.addEventListener("input", () => draw(current()));
document.querySelector('a[href="#input-guide"]').addEventListener("click", () => { el("input-guide").open = true; });
function startupFailure() {
  el("workbench").hidden = true;
  el("study-table").hidden = true;
  const status = el("startup-status");
  status.textContent = "The fitted model files could not load. Extract the whole ZIP to one folder and reopen index.html.";
  status.classList.add("error");
}

function startViewer() {
  if (!engine?.validate || !metadata?.ridge || !metadata?.cnn || !metadata?.development) {
    startupFailure();
    return;
  }
  try {
    state.input = engine.validate(engine.synthetic());
    setStudy();
    el("study-table").hidden = false;
    el("workbench").hidden = false;
    render();
    new ResizeObserver(() => draw(current())).observe(canvas);
    el("startup-status").hidden = true;
    el("import-button").disabled = false;
    controls.example.disabled = false;
    controls.file.disabled = false;
  } catch (error) {
    startupFailure();
    console.error("Forecast startup failed", error);
  }
}

startViewer();
