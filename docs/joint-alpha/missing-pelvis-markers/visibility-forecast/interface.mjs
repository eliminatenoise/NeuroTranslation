import {loadVisibilityModel, MARKERS, TIMES} from "./engine.mjs";

const exampleHeights = [
  [698, 694, 673, 668],
  [706, 702, 680, 674],
  [714, 710, 687, 680],
  [722, 718, 694, 686],
  [730, 726, 701, 692],
];
// Each row lists the marker columns to show, in the same order as the table.
const examples = {
  complete: [[0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 2, 3]],
  noRepeat: [[], [2], [], [3], [0, 1]],
  frontProxy: [[2, 3], [2, 3], [0, 1], [0, 1], [0, 1, 2, 3]],
  insufficient: [[0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 2, 3], [2]],
};
const evidenceText = {
  unavailable: "At least two markers must be visible at 0 ms.",
  no_repeat: "Zero movement assumed. No marker appeared twice.",
  measured_repeat: "The model used height changes from markers seen at both times.",
  back_marker_repeat: "At least one back marker appears at both selected times.",
  front_marker_proxy: "Front-marker speed stands in for back-marker speed. Neither back marker appeared at both selected times.",
};
const methods = {
  direct: "The model estimates the change in height from the five rows and recent marker speed.",
  correction: "The model carries recent speed forward, then adjusts the result using the marker readings.",
};
const byId = id => document.getElementById(id);
const timeText = time => String(time).replace("-", "−");
const amount = new Intl.NumberFormat("en", {maximumFractionDigits: 2});
const list = new Intl.ListFormat("en");
const preset = byId("example");
const choices = byId("methods");
const targets = [
  {key: "four_marker_centre", name: "Four-marker centre", value: byId("four-value"), evidence: byId("four-evidence")},
  {key: "back_pair_centre", name: "Back-pair centre", value: byId("back-value"), evidence: byId("back-evidence")},
];
let readings = [];
let model;

function forecastText(value) {
  if (value === null) return "No forecast";
  if (value === 0) return "0 mm";
  const direction = value > 0 ? "up" : "down";
  if (Math.abs(value) < 0.005) return `Under 0.01 mm ${direction}`;
  return `${amount.format(Math.abs(value))} mm ${direction}`;
}

function renderReadings(support) {
  const end = support?.interval_ms > 0 ? -support.age_ms : null;
  const start = end === null ? null : end - support.interval_ms;
  const repeated = end === null ? [] : readings[TIMES.indexOf(start)].map((height, column) =>
    height !== null && readings[TIMES.indexOf(end)][column] !== null);

  markerButtons.forEach((row, index) => row.forEach((button, column) => {
    const height = readings[index][column];
    button.textContent = height === null ? "Missing" : String(height);
    button.setAttribute("aria-pressed", String(height !== null));
    button.toggleAttribute("data-in-pair", Boolean(repeated[column] && (TIMES[index] === start || TIMES[index] === end)));
  }));

  byId("pair").textContent = end === null
    ? "No pair used."
    : `${timeText(start)} to ${timeText(end)} ms (${support.interval_ms} ms apart).`;
  const repeatedNames = MARKERS.filter((_, column) => repeated[column]);
  byId("repeated").textContent = repeatedNames.length === 0 ? "" : `Seen at both times — ${list.format(repeatedNames)}.`;
}

function showError(message) {
  renderReadings();
  byId("pair").textContent = message;
  for (const target of targets) {
    target.value.textContent = "—";
    target.evidence.textContent = "";
  }
  byId("announcement").textContent = message;
}

function update() {
  const method = choices.querySelector("input:checked").value;
  byId("method-description").textContent = methods[method];
  try {
    const result = model.predict({heights_mm: readings, unit: "mm"}, method);
    renderReadings(result.support);
    for (const target of targets) {
      const forecast = result.targets[target.key];
      target.value.textContent = forecastText(forecast.value_mm);
      target.evidence.textContent = evidenceText[forecast.evidence];
    }
    const summary = targets.map(target => `${target.name}, ${target.value.textContent}. ${target.evidence.textContent}`);
    byId("announcement").textContent = [...summary, byId("pair").textContent, byId("repeated").textContent].join(" ");
  } catch {
    showError("The forecast could not run for these readings. Choose an example to try again.");
  }
}

function useExample() {
  readings = exampleHeights.map((row, index) => row.map((height, column) =>
    examples[preset.value][index].includes(column) ? height : null));
  if (model) update();
  else renderReadings();
}

const markerButtons = TIMES.map((time, row) => {
  const tr = document.createElement("tr");
  const heading = document.createElement("th");
  heading.scope = "row";
  heading.textContent = timeText(time);
  tr.append(heading);
  byId("markers").append(tr);

  return MARKERS.map((name, column) => {
    const cell = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "marker";
    button.disabled = true;
    button.setAttribute("aria-label", `Show ${name.toLowerCase()} at ${timeText(time)} ms, ${exampleHeights[row][column]} mm`);
    button.addEventListener("click", () => {
      readings[row][column] = readings[row][column] === null ? exampleHeights[row][column] : null;
      update();
    });
    tr.append(cell);
    cell.append(button);
    return button;
  });
});

preset.addEventListener("change", useExample);
choices.addEventListener("change", update);
useExample();
byId("pair").textContent = "Loading model…";

try {
  model = await loadVisibilityModel();
  preset.disabled = false;
  choices.disabled = false;
  for (const button of markerButtons.flat()) button.disabled = false;
  update();
} catch {
  showError("The model did not load. Reload the page to try again.");
}
