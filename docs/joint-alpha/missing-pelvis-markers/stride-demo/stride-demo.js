"use strict";

const example = document.querySelector("#example");
const target = document.querySelector("#target");
const rate = document.querySelector("#rate");
const canvas = document.querySelector("#graph");
const context = canvas.getContext("2d");
const horizonMs = 100;
const colors = { recorded: "#18594c", matched: "#98601d", future: "#28528c", muted: "#3e5f53" };
const summaries = ["four", "rear"].map(key => [
  document.querySelector("#" + key), document.querySelector("#" + key + "-base"),
]);
let display;

function invented(samplesPerSecond, scenario) {
  const count = Math.round(0.8 * samplesPerSecond);
  const issue = count - 1;
  return Array.from({ length: count }, (_, i) => {
    const seconds = (i - issue) / samplesPerSecond;
    const angle = (seconds / 0.34 - 0.075) * 2 * Math.PI;
    const reading = [0, 0.17, 0.24, 0.31].map((phase, marker) =>
      920 + marker * 11 + 34 * Math.sin(angle + phase)
      + 5 * Math.sin(2 * angle + phase) + 2 * Math.sin(seconds * 7 + marker));
    if (scenario === "gap" && seconds >= -0.45 && seconds < -0.34) reading[2] = null;
    if (scenario === "fallback") return i === issue ? [reading[0], null, reading[2], null] : reading.fill(null);
    if (scenario === "withhold" && i === issue) return [reading[0], null, null, null];
    return reading;
  });
}

function change(value) {
  if (value === null) return "—";
  const rounded = Math.round(value * 10) / 10;
  if (rounded === 0) return "0 mm";
  return (rounded > 0 ? "+" : "−") + Math.abs(rounded).toFixed(1) + " mm";
}

function meanHeight(row, side) {
  const points = side ? row.slice(2) : row;
  return points.every(value => value !== null)
    ? points.reduce((sum, value) => sum + value, 0) / points.length
    : null;
}

function trace(points, x, y, color, width, dash = []) {
  context.strokeStyle = color;
  context.lineWidth = width;
  context.setLineDash(dash);
  context.beginPath();
  let active = false;
  for (const [time, height] of points) {
    if (height === null) {
      active = false;
    } else if (active) {
      context.lineTo(x(time), y(height));
    } else {
      context.moveTo(x(time), y(height));
      active = true;
    }
  }
  context.stroke();
  context.setLineDash([]);
}

function draw() {
  if (!display) return;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (width === 0 || height === 0) return;
  const pixels = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * pixels);
  canvas.height = Math.round(height * pixels);
  context.setTransform(pixels, 0, 0, pixels, 0, 0);
  const { history, samplesPerSecond, prediction } = display;
  const side = Number(target.value);
  const issue = history.length - 1;
  const series = history.map((row, i) => [1000 * (i - issue) / samplesPerSecond, meanHeight(row, side)]);
  const past = series.map(([, value]) => value).filter(value => value !== null);
  const start = series[issue][1];
  const canPlot = start !== null && prediction.prediction[side] !== null;
  const predicted = canPlot ? start + prediction.prediction[side] : null;
  const vertical = predicted === null ? past : [...past, predicted];
  const bottom = vertical.length ? Math.floor((Math.min(...vertical) - 5) / 20) * 20 : 880;
  const top = vertical.length ? Math.ceil((Math.max(...vertical) + 5) / 20) * 20 : 960;
  const margin = { left: 43, right: 17, top: 17, bottom: 42 };
  const x = ms => margin.left + (ms + 800) / 900 * (width - margin.left - margin.right);
  const y = mm => height - margin.bottom - (mm - bottom) / (top - bottom) * (height - margin.bottom - margin.top);
  const lagMs = prediction.cycleFrames * 1000 / samplesPerSecond;

  context.fillStyle = "#f1f5f9";
  context.fillRect(x(0), y(top), x(100) - x(0), y(bottom) - y(top));
  if (lagMs) {
    context.fillStyle = "#f7edd8";
    context.fillRect(x(-lagMs), y(top), x(horizonMs - lagMs) - x(-lagMs), y(bottom) - y(top));
  }
  context.font = "12px system-ui, sans-serif";
  context.fillStyle = colors.muted;
  context.textAlign = "right";
  for (const mm of [bottom, (bottom + top) / 2, top]) {
    trace([[-800, mm], [100, mm]], x, y, "#dae3dd", 1);
    context.fillText(String(mm), margin.left - 6, y(mm) + 4);
  }
  context.textAlign = "center";
  for (const time of [-800, -600, -400, -200, 0, 100]) {
    context.fillText(time > 0 ? "+" + time : String(time).replace("-", "−"), x(time), height - 22);
  }
  context.fillText("Time from the last reading (ms)", (margin.left + width - margin.right) / 2, height - 4);
  trace(series, x, y, colors.recorded, 2);
  if (lagMs) {
    const startAt = issue - prediction.cycleFrames;
    const endAt = startAt + Math.round(samplesPerSecond * horizonMs / 1000);
    trace(series.slice(startAt, endAt + 1), x, y, colors.matched, 3);
  }
  if (predicted !== null) {
    trace([[0, start], [horizonMs, predicted]], x, y, colors.future, 2, [4, 4]);
    context.fillStyle = colors.future;
    context.beginPath();
    context.arc(x(horizonMs), y(predicted), 4, 0, 2 * Math.PI);
    context.fill();
  }
  const shown = side ? "The plot averages the two rear markers." : "The plot averages all four markers.";
  let lineNote = " The line breaks when one of those readings is missing.";
  if (!prediction.issued) lineNote = " The model withheld the forecast.";
  else if (!canPlot) lineNote = " The last reading must include every selected marker to plot a forecast height. See the estimated change beside the plot.";
  document.querySelector("#plot-note").textContent = shown + lineNote;
}

function render() {
  const samplesPerSecond = Number(rate.value);
  const history = invented(samplesPerSecond, example.value);
  const prediction = globalThis.StrideCore.predict(history, samplesPerSecond, globalThis.StrideWeights);
  display = { history, samplesPerSecond, prediction };
  const visible = history.at(-1).filter(value => value !== null).length;
  summaries.forEach(([number, base], i) => {
    number.textContent = change(prediction.prediction[i]);
    base.textContent = prediction.cycleFrames ? "Earlier-stride estimate " + change(prediction.stride[i]) : "";
  });
  const title = document.querySelector("#support-title");
  const support = document.querySelector("#support");
  if (!prediction.issued) {
    title.textContent = "Forecast withheld";
    support.textContent = "The last reading shows only one marker. The model needs at least two.";
  } else if (!prediction.cycleFrames) {
    title.textContent = "Zero movement assumed";
    support.textContent = "The last reading shows " + visible + " markers. There are too few earlier readings to match a stride.";
  } else {
    const lag = Math.round(1000 * prediction.cycleFrames / samplesPerSecond);
    title.textContent = "An earlier stride matched";
    support.textContent = "The last reading shows " + visible + " markers. The model used a stretch starting " + lag + " ms before that reading.";
  }
  draw();
}

try {
  document.querySelector("#controls").hidden = false;
  document.querySelector("#workspace").hidden = false;
  document.querySelector("#download").hidden = location.protocol === "file:";
  render();
  document.querySelector("#loading").hidden = true;
  example.addEventListener("change", render);
  rate.addEventListener("change", render);
  target.addEventListener("change", draw);
  new ResizeObserver(draw).observe(canvas);
} catch (error) {
  document.querySelector("#controls").hidden = true;
  document.querySelector("#workspace").hidden = true;
  document.querySelector("#loading").textContent = "The stride model could not start. Keep the extracted files together and reopen this page.";
  console.error(error);
}
