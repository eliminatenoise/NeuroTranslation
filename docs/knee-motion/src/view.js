const $ = id => document.getElementById(id);
const study = JSON.parse($("study").textContent);
const pristine = "<!doctype html>\n" + document.documentElement.outerHTML;
const display = value => value.toFixed(1) + "°";
let active = null;
let predictions = null;
let requestId = 0;
let revealed = false;

function svgChild(svg, name, attrs, content) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  if (content !== undefined) el.textContent = content;
  svg.append(el);
}
function draw(svg, leg, prediction, low, high) {
  svg.replaceChildren();
  const x = frame => 46 + (frame + 24) * 336 / 39;
  const y = angle => 141 - (angle - low) / (high - low) * 115;
  const label = (cx, cy, value, anchor = "middle") =>
    svgChild(svg, "text", {x:cx,y:cy,"text-anchor":anchor,fill:"#475b5b","font-size":13}, value);
  const line = (x1, y1, x2, y2, stroke, dash = "") =>
    svgChild(svg, "line", {x1,y1,x2,y2,stroke,"stroke-dasharray":dash});
  line(x(0), 16, x(0), 145, "#64777a", "3 4");
  for (let i = 0; i < 3; i++) {
    const tick = low + (high - low) * i / 2;
    line(x(-24), y(tick), x(15), y(tick), "#d5dfda");
    label(39, y(tick) + 4, tick.toFixed(0) + "°", "end");
  }
  for (const lag of lags) label(x(-lag), 163, lag === 0 ? "0" : "−" + lag);
  label(x(15), 163, "+15");
  label(x(0), 181, "cutoff");
  const points = active.history.map((row, t) => [x(-lags[t]), y(row[2 + leg])]);
  svgChild(svg,"polyline",{points:points.map(pair=>pair.join(",")).join(" "),fill:"none",stroke:"#056e6c","stroke-width":2});
  points.forEach(([cx,cy]) => svgChild(svg,"circle",{cx,cy,r:3.7,fill:"#056e6c"}));
  const px=x(15), py=y(prediction);
  svgChild(svg,"polygon",{points:[[px,py-6],[px+6,py],[px,py+6],[px-6,py]].map(pair=>pair.join(",")).join(" "),stroke:"#ae461c",fill:"white","stroke-width":2.7});
  if (revealed) {
    const ry=y(active.target[leg]);
    svgChild(svg,"path",{d:"M " + (px-5) + " " + (ry-5) + " l 10 10 m -10 0 l 10 -10",stroke:"#172b30","stroke-width":2.6,fill:"none"});
  }
}
function tableRow(parent, values, activeRow = false) {
  const tr = document.createElement("tr");
  if (activeRow) tr.className="active";
  values.forEach((value, i) => {
    const cell = document.createElement(i ? "td" : "th");
    if (!i) cell.scope="row";
    cell.textContent=value; tr.append(cell);
  });
  parent.append(tr);
}
function historyTable() {
  const table = document.createElement("table");
  const head = table.createTHead().insertRow();
  ["Frame", "R hip", "L hip", "R knee", "L knee", "R ankle", "L ankle"].forEach(name => {
    const th=document.createElement("th"); th.textContent=name; th.scope="col"; head.append(th);
  });
  const body=table.createTBody();
  active.history.forEach((row,i)=>tableRow(body,[String(active.cutoff - lags[i]),...row.map(display)]));
  $("history-table").replaceChildren(table);
}
function clearView() {
  active = null; predictions = null; revealed = false;
  for (const id of ["frames","reveal-note","forecast-rows","history-table","right-chart","left-chart"]) $(id).replaceChildren();
  for (const id of ["right-angle","left-angle"]) $(id).textContent="—";
  $("reveal").disabled = true; $("reveal").textContent="Reveal recorded angles";
  $("recorded-key").hidden = true; $("scrubbing").hidden = true; $("method").disabled = true;
}
function render() {
  const method=$("method").value, pair=predictions[method];
  const observed=active.mode === "recorded";
  $("method").disabled=false;
  const cutoff=active.cutoff;
  $("frames").textContent=(observed ? "Stored frames " : "Relative frames ") + (cutoff-24) + " to " + cutoff + " · target " + (cutoff+15);
  $("scrubbing").hidden=!observed;
  if (observed) {
    $("cut").max=String(active.trial.cuts.length-1); $("cut").value=String(active.index);
    $("frame-value").textContent="frame " + cutoff;
    $("cut").setAttribute("aria-valuetext","frame " + cutoff);
  }
  const values=active.history.flatMap(row => row.slice(2,4)).concat(pair, revealed ? active.target : []);
  const low=Math.floor(Math.min(...values)/10)*10-5;
  const high=Math.ceil(Math.max(...values)/10)*10+5;
  ["right","left"].forEach((side, i) => {
    $(side+"-angle").textContent=display(pair[i]);
    draw($(side+"-chart"),i,pair[i],low,high);
  });
  $("forecast-rows").replaceChildren();
  for (const name of methods) tableRow($("forecast-rows"),[labels[name],...predictions[name].map(display)],name===method);
  $("reveal").disabled=!observed;
  $("reveal").textContent=revealed ? "Hide recorded angles" : "Reveal recorded angles";
  $("recorded-key").hidden=!revealed;
  if (revealed) {
    const diff=pair.map((v,i) => Math.abs(v-active.target[i]));
    $("reveal-note").textContent="Stored frame " + (cutoff+15) + " · right " + display(active.target[0]) + ", left " + display(active.target[1]) +
      ". Absolute forecast error · right " + display(diff[0]) + ", left " + display(diff[1]) + ".";
  } else {
    $("reveal-note").textContent=observed ? "The later sensor-derived angles are hidden." : "Open an original held-out CSV to compare the forecast with a later recorded frame.";
  }
  historyTable();
}
function applyInput(input) {
  const forecast=Object.fromEntries(methods.map(name => [name,kneeForecast(input.history,study.weights,name)]));
  // SVG and text should display source-degree resolution; exceptionally large
  // custom numbers cannot preserve that resolution as JavaScript doubles.
  if ([...input.history.flat(),...Object.values(forecast).flat()].some(v=>Math.abs(v)>Number.MAX_SAFE_INTEGER)) throw Error("The entered magnitudes exceed the display’s supported degree range.");
  active=input; predictions=forecast; revealed=false;
  $("status").dataset.error="false";
  $("status").textContent=input.mode === "recorded" ? "Verified local walk · " + input.trial.member.path + " · 0.5 m/s." :
    input.mode === "invented" ? "Invented example · five input frames with no known future observation." : "Local JSON history · five input frames with no verified endpoint.";
  render();
}
function loadExample() {
  requestId++; clearView(); $("file").value="";
  applyInput({...customInput(study.example),mode:"invented"});
}
function download(text, name, type) {
  const url=URL.createObjectURL(new Blob([text],{type}));
  const a=document.createElement("a"); a.href=url; a.download=name; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
for (const name of methods) $("method").add(new Option(labels[name],name));
$("method").value="transformer";
$("method").addEventListener("change",()=>{ if (active) render(); });
$("reveal").addEventListener("click",()=>{if (active?.mode==="recorded"){revealed=!revealed;render();}});
$("example").addEventListener("click",loadExample);
$("cut").addEventListener("input",()=>{if (active?.trial) applyInput(recordedInput(active.trial,Number($("cut").value)));});
$("file").addEventListener("change",async event=>{
  const file=event.target.files[0];
  if (!file) return;
  const generation=++requestId;
  clearView(); $("status").dataset.error="false"; $("status").textContent="Checking the local file…";
  try {
    const input=await openInput(file,study.source);
    if (generation===requestId) applyInput(input);
  } catch(error) {
    if (generation!==requestId) return;
    clearView(); $("status").textContent=error.message; $("status").dataset.error="true";
  } finally { if (generation===requestId) $("file").value=""; }
});
$("save").addEventListener("click",()=>download(pristine,"knee-motion.html","text/html;charset=utf-8"));
$("template").addEventListener("click",()=>download(JSON.stringify(study.example,null,2)+"\n","knee-history.json","application/json"));
$("suggested-file").textContent=study.source.members[0].path;
$("results-intro").textContent="Fitted with " + study.trainPeople + " walkers. Tested on " + study.testPeople + " other walkers at 0.5 m/s. Each person counts equally across " + study.testWindows.toLocaleString("en-US") + " overlapping windows.";
for (const name of methods) tableRow($("scores"),[labels[name],study.errors[name].toFixed(2)+"°"]);
$("result-note").textContent=study.extended;
loadExample();
