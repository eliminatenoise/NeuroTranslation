"use strict";

const data = JSON.parse(document.querySelector("#data").textContent);
const load = document.querySelector("#load");
const stance = document.querySelector("#stance");
const mask = document.querySelector("#mask");
const methods = {
  camera_speed: "Continue the recent camera speed",
  camera: "Camera alone",
  camera_force: "Camera and floor force",
  camera_emg: "Camera and thigh electrical signals",
  camera_force_emg: "Camera, floor force and thigh electrical signals",
};
const hints = {
  complete: "The model receives all five sets of camera readings.",
  left_front_hidden: "The left front marker is hidden in all five sets of camera readings.",
  rear_pair_recently_hidden: "Both rear markers are hidden in the last two sets of camera readings.",
};

function cell(tag, value) {
  const node = document.createElement(tag);
  node.textContent = value;
  return node;
}

function table(id, category, targets) {
  const tbody = document.querySelector("#" + id + " tbody");
  const metrics = targets.map(target => target[category]);
  const best = metrics.map(group => Math.min(...Object.values(group)));
  const rows = Object.entries(methods).map(([method, name]) => {
    const row = document.createElement("tr");
    const label = cell("th", name);
    label.scope = "row";
    row.append(label);
    metrics.forEach((group, index) => {
      const value = group[method];
      const item = cell("td", value.toFixed(2));
      if (value === best[index]) item.classList.add("best");
      row.append(item);
    });
    return row;
  });
  tbody.replaceChildren(...rows);
}

function signed(value) {
  return (value > 0 ? "+" : "") + value.toFixed(2).replace("-", "−");
}

function render() {
  const score = data.scores[load.value][stance.value][mask.value];
  const targets = [score.four_markers, score.rear_pair];
  table("average", "mean_absolute_error_mm", targets);
  table("tail", "pooled_p90_mm", targets);
  const counts = targets.map(target => target.people + " people, " + target.windows + " forecasts");
  const support = counts[0] === counts[1]
    ? counts[0] + " per target."
    : "Four markers from " + counts[0] + ". Rear pair from " + counts[1] + ".";
  document.querySelector("#support").textContent = support + " " + hints[mask.value];

  const changes = targets.map((target, index) => {
    const name = index === 0 ? "Four markers" : "Rear pair";
    const pair = target.paired_comparisons.force_minus_camera;
    const interval = pair.interval_95_mm.map(signed).join(" to ");
    return name + " " + signed(pair.change_mm) + " mm (95% interval " + interval + " mm).";
  });
  document.querySelector("#difference").textContent =
    "Change in error from adding floor force. " + changes.join(" ");
}

render();
[load, stance, mask].forEach(control => control.addEventListener("change", render));
document.querySelector("#controls").hidden = false;
document.querySelector("#interactive").hidden = false;
