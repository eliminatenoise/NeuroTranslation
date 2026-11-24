import {loadPelvisModel, MARKERS, TARGETS, TIMES, validateHistory} from "./engine.mjs";

const byId = id => document.getElementById(id);
const canvas = byId("history-plot");
const forecastForm = byId("forecast-form");
const markerChoice = byId("markers");
const trainingChoice = byId("training");
const floorForce = byId("floor-force");
const readings = byId("readings");
const inputError = byId("input-error");
const status = byId("forecast-status");
const outputs = [byId("four-forecast"), byId("back-forecast")];
const contrast = matchMedia("(forced-colors: active)");
const amountFormat = new Intl.NumberFormat("en", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const heightFormat = new Intl.NumberFormat("en", {maximumFractionDigits: 2});
const DASHES = [[], [7, 5], [2, 4], [9, 3, 2, 3]];
let model;
let example;
let data;
let plotted = [];

function masked(readings, mask, includeForce) {
  const heights = readings.heights_mm.map((row, timeIndex) => row.map((height, markerIndex) => {
    const hidden = (mask === "back" && markerIndex < 2) || (mask === "left" && markerIndex === 0) ||
      (mask === "right" && markerIndex === 1) || (mask === "brief" && markerIndex === 0 && (timeIndex === 1 || timeIndex === 2));
    return hidden ? null : height;
  }));
  const result = {heights_mm: heights};
  if (includeForce && readings.force_log_change !== undefined) result.force_log_change = readings.force_log_change;
  return result;
}

function printForecast(value) {
  const magnitude = Math.abs(value);
  if (magnitude < 0.005) return "0.00 mm";
  return `${amountFormat.format(magnitude)} mm ${value > 0 ? "up" : "down"}`;
}

function clearForecast(message) {
  outputs.forEach(output => {
    output.textContent = "—";
  });
  status.textContent = message;
  byId("forecast-announcement").textContent = "";
}

function use(input, label) {
  data = input;
  byId("input-source").textContent = label;
  floorForce.disabled = input.force_log_change === undefined;
  if (floorForce.disabled) floorForce.checked = false;
  byId("floor-note").hidden = !floorForce.disabled;
  inputError.textContent = "";
  update();
}

function update() {
  const input = masked(data, markerChoice.value, floorForce.checked);
  plotted = input.heights_mm;
  renderTable();
  draw();
  try {
    const result = model.predict(input, trainingChoice.value);
    outputs.forEach((output, i) => {
      output.textContent = printForecast(result.estimates[TARGETS[i]]);
    });
    status.textContent = "Forecast updated";
    byId("forecast-announcement").textContent = `Four-marker centre ${outputs[0].textContent}. Back-marker centre ${outputs[1].textContent}.`;
  } catch (error) {
    clearForecast(error.message);
  }
}

function renderTable() {
  const rows = plotted.map((row, index) => {
    const tr = document.createElement("tr");
    const time = document.createElement("th");
    time.scope = "row";
    time.textContent = `${TIMES[index]} ms`;
    tr.append(time);
    for (const height of row) {
      const td = document.createElement("td");
      td.textContent = height === null ? "Missing" : heightFormat.format(height);
      tr.append(td);
    }
    return tr;
  });
  byId("history-rows").replaceChildren(...rows);
}

function draw() {
  if (plotted.length === 0) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const density = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * density);
  canvas.height = Math.round(height * density);
  ctx.scale(density, density);
  const styles = getComputedStyle(canvas);
  const legendStyles = getComputedStyle(byId("history-title"));
  const color = contrast.matches ? legendStyles.color : styles.getPropertyValue("--muted").trim();
  const gridColor = contrast.matches ? color : styles.getPropertyValue("--line").trim();
  const present = plotted.flat().filter(value => value !== null);
  const minimum = Math.min(...present);
  const maximum = Math.max(...present);
  const range = maximum - minimum;
  if (!present.length || !Number.isFinite(range)) return;
  const pad = Math.max(range * 0.075, 1);
  const low = minimum - pad;
  const span = range + 2 * pad;
  const top = 26;
  const bottom = height - 31;
  const left = width < 300 ? 40 : 55;
  const right = width - 12;
  const xAt = timeIndex => left + (right - left) * (timeIndex / (TIMES.length - 1));
  const yAt = value => bottom - (value - low) / span * (bottom - top);

  ctx.font = "12px system-ui, sans-serif";
  ctx.fillStyle = color;
  ctx.fillText("Height (mm)", left, 16);
  ctx.fillStyle = gridColor;
  for (let step = 0; step <= 4; step++) {
    const position = top + (bottom - top) * step / 4;
    ctx.fillRect(left, position, right - left, 1);
  }
  ctx.fillStyle = color;
  for (let step = 0; step <= 4; step += 2) {
    const value = low + span * (1 - step / 4);
    const label = Math.abs(value) >= 1e5 ? value.toExponential(0) : heightFormat.format(Math.round(value));
    ctx.textAlign = "right";
    ctx.fillText(label, left - 6, top + (bottom - top) * step / 4 + 4);
  }
  ctx.textAlign = "center";
  for (let i = 0; i < TIMES.length; i++) {
    ctx.fillText(i === TIMES.length - 1 ? "0 ms" : String(TIMES[i]), xAt(i), height - 10);
  }

  for (let marker = 0; marker < MARKERS.length; marker++) {
    ctx.strokeStyle = ctx.fillStyle = contrast.matches ? color : styles.getPropertyValue(`--series-${marker}`).trim();
    ctx.lineWidth = 1.7;
    ctx.setLineDash(DASHES[marker]);
    ctx.beginPath();
    let continuing = false;
    for (const [i, row] of plotted.entries()) {
      const markerHeight = row[marker];
      if (markerHeight === null) {
        continuing = false;
        continue;
      }
      if (continuing) ctx.lineTo(xAt(i), yAt(markerHeight));
      else ctx.moveTo(xAt(i), yAt(markerHeight));
      continuing = true;
    }
    ctx.stroke();
    ctx.setLineDash([]);
    for (const [i, row] of plotted.entries()) {
      if (row[marker] === null) continue;
      ctx.beginPath();
      ctx.arc(xAt(i), yAt(row[marker]), 3, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
}

forecastForm.addEventListener("submit", event => {
  event.preventDefault();
  if (model) update();
});
forecastForm.addEventListener("change", () => {
  if (model && data) update();
});
byId("readings-form").addEventListener("submit", event => {
  event.preventDefault();
  if (!model) return;
  try {
    const parsed = JSON.parse(readings.value);
    use(validateHistory(parsed), "Your prepared readings");
  } catch (error) {
    const message = error instanceof SyntaxError ? "The readings are not valid JSON." : error.message;
    inputError.textContent = `${message} The previous readings stay active.`;
  }
});
byId("reset").addEventListener("click", () => {
  readings.value = JSON.stringify(example, null, 2);
  markerChoice.value = "all";
  trainingChoice.value = "mixed";
  floorForce.checked = false;
  use(example, "Invented example");
});
new ResizeObserver(draw).observe(canvas);
contrast.addEventListener("change", draw);

try {
  [model, example] = await Promise.all([loadPelvisModel(), fetch("invented-inputs.json").then(response => {
    if (!response.ok) throw new Error("The example readings could not be loaded.");
    return response.json();
  })]);
  validateHistory(example);
  readings.value = JSON.stringify(example, null, 2);
  use(example, "Invented example");
  ["run", "apply", "reset"].forEach(id => {
    byId(id).disabled = false;
  });
} catch (error) {
  clearForecast(`${error.message} Reload the page to try again.`);
}
