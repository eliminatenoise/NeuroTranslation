const METHODS = {
  persistence: "Hold the latest force steady",
  recent_trend: "Continue the recent trend",
  walking_ridge: "Weighted correction · Walking",
  mixed_ridge: "Weighted correction · Mixed activities",
  walking_gru_residual: "Recurrent correction · Walking",
  mixed_gru_residual: "Recurrent correction · Mixed activities",
  mixed_gru_direct: "Direct recurrent forecast · Mixed activities",
  full_research_3: "Full Research Edition · Three passes",
};

const EXAMPLES = {
  rise: [0, 0, 0, 20, 105, 280, 510, 640, 700, 680],
  fall: [650, 690, 705, 690, 640, 530, 385, 230, 105, 38],
  quiet: [-0.6, -0.2, 0.1, 0.3, 0.2, -0.2, 0.1, 0.2, 0.1, 0.3],
};

const source = JSON.parse(document.querySelector("#frozen-study").textContent);
const weights = decodeWeights(source.weights);
const number = new Intl.NumberFormat("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const axisNumber = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const count = new Intl.NumberFormat("en");
const bins = document.querySelector("#bins");
const select = document.querySelector("#example");
const testGroup = document.querySelector("#test-group");
const status = document.querySelector("#status");
const canvas = document.querySelector("#plot");
const predictions = document.querySelector("#forecasts tbody");
const benchmark = document.querySelector("#benchmark-results tbody");
const scope = document.querySelector("#benchmark-scope");
const times = Array.from({ length: 10 }, (_, index) => (index - 9) * 20);
const signedMs = time => (time < 0 ? "−" + -time : String(time)) + " ms";
let plotted = [];

function row(label, value) {
  const entry = document.createElement("tr");
  const title = document.createElement("th");
  const result = document.createElement("td");
  title.scope = "row";
  title.textContent = label;
  result.textContent = value;
  entry.append(title, result);
  return { entry, result };
}

const input = times.map(time => {
  const label = document.createElement("label");
  const timeName = document.createElement("span");
  const cell = document.createElement("input");
  timeName.textContent = signedMs(time);
  cell.type = "number";
  cell.step = "any";
  cell.inputMode = "decimal";
  cell.required = true;
  cell.setAttribute("aria-label", "Force at " + signedMs(time));
  cell.addEventListener("input", updateForecast);
  label.append(timeName, cell);
  bins.append(label);
  return cell;
});

const results = new Map();
for (const name of Object.keys(METHODS)) {
  if (name === "full_research_3") continue;
  const item = row(METHODS[name], "—");
  predictions.append(item.entry);
  results.set(name, item.result);
}

function draw() {
  const bounds = canvas.getBoundingClientRect();
  const width = bounds.width;
  const height = bounds.height;
  if (!(width > 0 && height > 0)) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  if (plotted.length === 0) return;

  const lo = Math.min(0, ...plotted);
  const hi = Math.max(0, ...plotted);
  const step = Math.max(hi - lo, 2);
  const top = 20, bottom = height - 21, left = 42, right = width - 16;
  const y = value => bottom - (value - lo) * (bottom - top) / step;
  const x = index => left + index * (right - left) / 9;
  ctx.fillStyle = "#4d5d65";
  ctx.font = "11px system-ui, sans-serif";
  ctx.fillText("N", 8, 12);
  ctx.strokeStyle = "#cadbd1";
  for (const value of [lo, lo + step / 2, lo + step]) {
    const at = y(value);
    ctx.fillText(axisNumber.format(value), 3, at + 4, 37);
    ctx.beginPath();
    ctx.moveTo(left, at);
    ctx.lineTo(right, at);
    ctx.stroke();
  }
  for (const index of [0, 3, 6, 9]) {
    const label = signedMs(times[index]);
    const leftEdge = Math.min(right - ctx.measureText(label).width, x(index));
    ctx.fillText(label, leftEdge, height - 2);
  }
  ctx.strokeStyle = "#126457";
  ctx.lineWidth = 2.5;
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(x(0), y(plotted[0]));
  plotted.forEach((value, index) => ctx.lineTo(x(index), y(value)));
  ctx.stroke();
  ctx.fillStyle = "#126457";
  plotted.forEach((value, index) => {
    ctx.beginPath();
    ctx.arc(x(index), y(value), 2.7, 0, 2 * Math.PI);
    ctx.fill();
  });
}

function assignForecast(name, value) {
  const output = results.get(name);
  if (Number.isFinite(value)) {
    output.textContent = number.format(Math.abs(value) < .005 ? 0 : value);
    output.dataset.value = String(value);
  } else {
    output.textContent = "—";
    delete output.dataset.value;
  }
}

function updateForecast() {
  const values = input.map(cell => cell.valueAsNumber);
  for (const [i, cell] of input.entries()) {
    if (Number.isFinite(values[i])) cell.removeAttribute("aria-invalid");
    else cell.setAttribute("aria-invalid", "true");
  }
  let problem = "";
  try {
    const output = forecastMembers(values, weights);
    for (const [name, members] of Object.entries(output)) {
      assignForecast(name, members.reduce((sum, value) => sum + value, 0) / members.length);
    }
  } catch (error) {
    if (!(error instanceof RangeError)) throw error;
    problem = error.message;
    for (const name of results.keys()) assignForecast(name, NaN);
  }
  status.textContent = problem;
  plotted = problem ? [] : values;
  draw();
}

function restore() {
  const example = EXAMPLES[select.value];
  input.forEach((cell, index) => { cell.value = example[index]; });
  updateForecast();
}

function updateBenchmarks() {
  const selection = source.cohorts[testGroup.value];
  const minimum = Math.min(...Object.values(selection.errors));
  const cutoff = ["dijon_loaded", "dijon_low"].includes(testGroup.value)
    ? "The 20 N cutoff uses the last 20 ms average in each input. " : "";
  scope.textContent = `${count.format(selection.rows)} forecast windows from ${selection.people} people. ` +
    cutoff + "The table averages each person’s errors before averaging across people. Lower error is better. " +
    "The study pages give the uncertainty around the differences.";
  benchmark.replaceChildren();
  for (const [name, label] of Object.entries(METHODS)) {
    const value = selection.errors[name];
    if (value === undefined) continue;
    const item = row(label, number.format(value));
    if (value === minimum) item.result.classList.add("best");
    benchmark.append(item.entry);
  }
}

if (location.protocol === "file:") document.querySelector("#download").hidden = true;
select.addEventListener("change", restore);
document.querySelector("#reset").addEventListener("click", restore);
testGroup.addEventListener("change", updateBenchmarks);
new ResizeObserver(draw).observe(canvas);
restore();
updateBenchmarks();
