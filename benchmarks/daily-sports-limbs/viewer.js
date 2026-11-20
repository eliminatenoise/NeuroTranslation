"use strict";

const part = document.querySelector("#part");
const input = document.querySelector("#record");
const run = document.querySelector("#run");
const restore = document.querySelector("#restore");
const status = document.querySelector("#status");
const context = document.querySelector("#context");
const values = document.querySelector("#values");
const chart = document.querySelector("#chart");
const colors = ["#136c52", "#8a4516", "#505295"];
let examples;
let revision = 0;
let activeTrace = null;
let chartWidth = 0;

function clearResult(message) {
  revision++;
  activeTrace = null;
  chart.replaceChildren();
  values.replaceChildren();
  status.textContent = message;
  context.textContent = "The forecast uses the selected sensor's own frame.";
  run.disabled = !examples;
}

function drawTrace(record, result) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  activeTrace = [record, result];
  chartWidth = chart.clientWidth;
  const width = Math.max(260, chartWidth);
  svg.setAttribute("viewBox", "0 0 " + width + " 170");
  function add(name, properties) {
    const el = document.createElementNS(ns, name);
    for (const [key, value] of Object.entries(properties)) el.setAttribute(key, value);
    svg.append(el);
    return el;
  }
  const all = [...record.samples.flat(), ...result.forecast.shared_forecast, ...(result.measured_target || [])];
  const min = Math.min(...all), max = Math.max(...all);
  const span = max - min || 1;
  const x = i => 45 + (width - 62) * i / 18;
  const y = v => 145 - 123 * (v - min) / span;
  for (const level of new Set([min, max])) {
    add("line",{x1:x(0),x2:x(18),y1:y(level),y2:y(level),stroke:"#dee5dd"});
    add("text",{x:3,y:y(level)+3,fill:"#526659","font-size":10}).textContent=Number(level.toPrecision(3));
  }
  for (const row of [15, 18]) {
    add("line", {x1:x(row), x2:x(row), y1:10, y2:146, stroke:"#909d91", "stroke-dasharray":"3,4"});
  }
  for (const [i, color] of colors.entries()) {
    const points = record.samples.map((sample, j) => [x(j),y(sample[i])].join(",")).join(" ");
    add("polyline", {points, fill:"none", stroke:color, "stroke-width":2});
    if (result.measured_target) {
      add("rect", {x:x(18)-3, y:y(result.measured_target[i])-3, width:6, height:6, fill:color});
    }
    add("circle", {cx:x(18), cy:y(result.forecast.shared_forecast[i]), r:4.5,
                   fill:"none", stroke:color, "stroke-width":2});
  }
  for (const [index, title] of [[0,"0 ms"],[15,"600 ms"],[18,"720 ms"]]) {
    add("text",{x:x(index),y:163,"text-anchor":index===0 ? "start" : "end",
                fill:"#526659","font-size":11}).textContent=title;
  }
  chart.replaceChildren(svg);
}

function addRow(label, numbers) {
  const row = document.createElement("tr");
  const name = document.createElement("th");
  name.scope = "row";
  name.textContent = label;
  row.append(name);
  for (const val of numbers) {
    const cell = document.createElement("td");
    cell.textContent = val.toFixed(3);
    row.append(cell);
  }
  values.append(row);
}

async function forecast() {
  clearResult("Computing the forecast…");
  const active = revision;
  run.disabled = true;
  try {
    const record = JSON.parse(input.value);
    const response = await fetch("/forecast", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({selected:part.value, record})
    });
    const result = await response.json();
    if (active !== revision) return;
    if (!response.ok) throw Error(result.error || "Could not read the recording.");
    const f = result.forecast;
    drawTrace(record, result);
    addRow("Shared model", f.shared_forecast);
    if (result.measured_target) addRow("Measured target", result.measured_target);
    addRow("Repeat last reading", f.persistence);
    addRow("Ridge model", f.ridge);
    context.textContent = result.measured_target
      ? "First parking-lot walking clip from TRAIN participant p1. Target at 720 ms."
      : "Your input window. No independently measured target was supplied.";
    status.textContent = "Forecast complete · target timestamp " + f.target_timestamp_ms + " ms.";
  } catch (err) {
    if (active === revision) status.textContent = err.message;
  } finally {
    if (active === revision) run.disabled = false;
  }
}

function restoreExample() {
  const record = examples.examples[part.value].input;
  input.value = JSON.stringify(record, null, 2);
  forecast();
}

new ResizeObserver(() => {
  if (activeTrace && chart.clientWidth !== chartWidth) drawTrace(...activeTrace);
}).observe(chart);

part.addEventListener("change", restoreExample);
restore.addEventListener("click", restoreExample);
run.addEventListener("click", forecast);
input.addEventListener("input", () => clearResult("Input changed. Run the forecast to see the new result."));
part.disabled = run.disabled = restore.disabled = true;
fetch("/examples.json").then(r => {
  if (!r.ok) throw Error("Could not load recorded examples.");
  return r.json();
}).then(data => {
  examples = data;
  part.disabled = restore.disabled = false;
  restoreExample();
}).catch(err => {status.textContent = err.message;});
