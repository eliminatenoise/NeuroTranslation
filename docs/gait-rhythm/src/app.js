"use strict";
const get = id => document.getElementById(id);
const data = JSON.parse(get("study").textContent);
const selector = get("record"), muscleInput = get("muscle"), kneeInput = get("knee");
const format = value => Number(value).toFixed(2);
let activeWorker, workerURL, spectra;
function element(tag, label) {
  const node = document.createElement(tag);
  if (label !== undefined) node.textContent = label;
  return node;
}
function status(message, error = false) {
  get("file-state").textContent = message;
  get("file-state").classList.toggle("error", error);
}
function cancel() {
  if (activeWorker) activeWorker.terminate();
  if (workerURL) URL.revokeObjectURL(workerURL);
  activeWorker = null;
  workerURL = null;
}
function clearSpectra() {
  cancel();
  spectra = null;
  get("spectra").hidden = true;
  for (const kind of ["muscle", "knee"]) {
    const canvas = get(kind + "-plot");
    canvas.width = canvas.width;
    canvas.removeAttribute("aria-label");
    get(kind + "-caption").textContent = "";
  }
}
function clearFiles() {
  muscleInput.value = "";
  kneeInput.value = "";
}
function current() {
  return data.people.find(row => row.person === Number(selector.value));
}
function displayCase() {
  clearSpectra();
  clearFiles();
  const row = current();
  const other = row.wrong_person_source;
  const rows = [
    ["muscle", "Muscle activity", row.emg_cycles_min], ["knee", "Knee bending", row.angle_cycles_min],
    ["median", "Earlier cohort median", row.estimate_cycles_min.training_median],
    ["other", "Another person’s muscle", row.estimate_cycles_min.wrong_person],
  ];
  const list = get("rate-rows");
  list.replaceChildren();
  for (const [key, label, rate] of rows) {
    const item = element("div"), track = element("span"), dot = element("span");
    item.className = "rate-row row-" + key;
    track.className = "track";
    track.setAttribute("aria-hidden", "true");
    dot.className = "dot";
    dot.style.left = (rate - 30) * 5 + "%";
    track.append(dot);
    item.append(element("span", label), track, element("strong", format(rate)));
    list.append(item);
  }
  get("difference").textContent = "S" + row.person + " · Muscle and knee peaks differ by " +
    format(Math.abs(row.emg_cycles_min - row.angle_cycles_min)) + " cycles/min.";
  get("control-note").textContent = "The median uses the knee rates of 38 earlier participants. The other muscle rate comes from S" +
    other + ", the next available recording in a fixed rotation.";
  get("file-guide").textContent = "For S" + row.person + ", choose EMG_S" + row.person +
    "_0.5.csv and Joint_Angles_ZXY.csv from the IMU_S" + row.person + "_0.5 folder in the original IMU archive.";
  get("emg-source").href = "https://physionet.org/files/multimodal-gait-dataset/1.0.0/Dataset/EMG_Data/EMG_S" + row.person + "_0.5.csv";
  status("Choose both files to draw the spectra.");
}

function draw(kind, result, ceiling) {
  const canvas = get(kind + "-plot"), width = canvas.clientWidth, height = canvas.clientHeight;
  if (!width || !height) return;
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  const left = 33, right = width - 12, top = 10, bottom = height - 46;
  const x = bin => left + (right - left) * bin / 420;
  const y = value => bottom - (bottom - top) * value / ceiling;
  ctx.font = "12px Arial, sans-serif";
  ctx.fillStyle = "#49605d";
  ctx.strokeStyle = "#d5dbd3";
  for (const p of [0, ceiling / 2, ceiling]) {
    ctx.beginPath(); ctx.moveTo(left, y(p)); ctx.lineTo(right, y(p)); ctx.stroke();
    ctx.textAlign = "right";
    ctx.fillText(Number((p * 100).toFixed(1)) + "%", left - 4, y(p) + 3);
  }
  for (const [j, label] of [[0, "27"], [120, "45"], [220, "60"], [320, "75"], [420, "90"]]) {
    ctx.textAlign = "center"; ctx.fillText(label, x(j), bottom + 17);
  }
  ctx.fillText("Cycles per minute", (left + right) / 2, height - 6);
  const accent = kind === "muscle" ? "#00695f" : "#a44526";
  ctx.strokeStyle = accent; ctx.lineWidth = 2;
  ctx.beginPath();
  result.share.forEach((v, j) => j === 0 ? ctx.moveTo(x(j), y(v)) : ctx.lineTo(x(j), y(v)));
  ctx.stroke();
  ctx.fillStyle = accent;
  ctx.beginPath(); ctx.arc(x(result.peak), y(result.share[result.peak]), 4, 0, 2 * Math.PI); ctx.fill();
}
function drawBoth() {
  if (!spectra) return;
  const top = Math.ceil(Math.max(...spectra.emg.share, ...spectra.angles.share) * 100) / 100;
  draw("muscle", spectra.emg, top);
  draw("knee", spectra.angles, top);
}
function readFiles() {
  clearSpectra();
  if (!muscleInput.files.length || !kneeInput.files.length) {
    status("Choose both files to draw the spectra.");
    return;
  }
  const record = current();
  status("Checking both files and calculating their spectra…");
  function failed(message) {
    clearSpectra();
    clearFiles();
    status(message + " Both selections have been cleared.", true);
  }
  try {
    workerURL = URL.createObjectURL(new Blob([get("worker-source").textContent], {type: "text/javascript"}));
    const worker = new Worker(workerURL);
    activeWorker = worker;
    worker.onmessage = ({data: result}) => {
      if (activeWorker !== worker) return;
      if (result.error) return failed(result.error);
      cancel();
      spectra = result;
      get("spectra").hidden = false;
      for (const [kind, value] of [["muscle", result.emg], ["knee", result.angles]]) {
        const text = "Peak " + format(value.rate) + " cycles/min from " + value.rows.toLocaleString("en-US") + " samples.";
        get(kind + "-caption").textContent = text;
        get(kind + "-plot").setAttribute("aria-label", kind + " frequency spectrum. " + text);
      }
      drawBoth();
      status("Both file fingerprints and peak rates match recording S" + record.person + ".");
    };
    worker.onerror = () => { if (activeWorker === worker) failed("Your browser could not run the local calculation."); };
    worker.postMessage({record, files: [muscleInput.files[0], kneeInput.files[0]]});
  } catch {
    failed("Your browser could not start the local calculation.");
  }
}

for (const row of data.people) selector.add(new Option("S" + row.person, row.person));
for (const [key, label] of [["matched_emg","Same person’s muscle"],["training_median","Earlier cohort median"],
                          ["wrong_person","Another person’s muscle"],["affine_emg","Adjusted muscle estimate"]]) {
  const row = element("tr");
  const name = element("th", label);
  name.scope = "row";
  row.append(name, element("td", data.scores[key].mae.toFixed(3)));
  get("cohort-body").append(row);
}
selector.addEventListener("change", displayCase);
muscleInput.addEventListener("change", readFiles);
kneeInput.addEventListener("change", readFiles);
window.addEventListener("resize", drawBoth);
displayCase();
