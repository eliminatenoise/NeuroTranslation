"use strict";
const el = id => document.getElementById(id);
let catalog, task, record, serial = 0;
const copy = value => JSON.parse(JSON.stringify(value));
const isRank = () => Array.isArray(record.X[0][0][0]);
const series = () => isRank() ? record.X[0][Number(el("candidate").value)] : record.X[0];
const row = () => catalog.tasks[task];
const label = text => String(text).replaceAll("_", " ");

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw Error(body.error || "Could not read the forecast.");
  return body;
}
function tell(message, failed=false) {
  el("status").textContent = message;
  el("status").classList.toggle("error", failed);
}
function options(node, labels) {
  node.replaceChildren(...labels.map((label, index) => new Option(label, String(index))));
}
function showSeries() {
  const values = series().map(frame => frame[Number(el("channel").value)]);
  const unit = row().schema.input_units[Number(el("channel").value)];
  el("unit").textContent = unit ? "(" + unit + ")" : "";
  el("value").value = values[Number(el("step").value)] ?? "";
  const canvas = el("plot"), ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height, pad = 13;
  ctx.clearRect(0, 0, w, h);
  const finite = values.filter(value => typeof value === "number" && Number.isFinite(value));
  if (!finite.length) {canvas.setAttribute("aria-label","All selected input readings are missing."); el("range").textContent="All readings are missing."; return;}
  const lo = Math.min(...finite), hi = Math.max(...finite);
  const number = v => v.toLocaleString(undefined,{maximumSignificantDigits:5});
  el("range").textContent = values.length===1 ? "One observation · "+number(lo)+" "+unit :
    "Earliest to latest · Range "+number(lo)+" to "+number(hi)+" "+unit;
  const point = (v,i) => [pad+(w-2*pad)*(values.length===1?.5:i/(values.length-1)),
    hi===lo?h/2:h-pad-(h-2*pad)*(v-lo)/(hi-lo)];
  ctx.strokeStyle="#096e63";ctx.fillStyle="#096e63";ctx.lineWidth=3;
  let drawing=false;
  ctx.beginPath();
  values.forEach((v,i) => {
    if (v === null) {drawing=false;return;}
    const [x,y]=point(v,i);
    if(drawing) ctx.lineTo(x,y); else ctx.moveTo(x,y);
    drawing=true;
  });
  ctx.stroke();
  values.forEach((v,i) => {
    if (v === null) return;
    const [x,y]=point(v,i);ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill();
  });
  canvas.setAttribute("aria-label", "Input readings in order: "+values.map(v=>v===null?"missing":v).join(", ")+" "+unit);
}
function initializeControls() {
  el("candidate-wrap").hidden = !isRank();
  if (isRank()) options(el("candidate"), record.X[0].map((_,i)=>"Candidate "+(i+1)));
  options(el("channel"), row().schema.channels.map(label));
  options(el("step"), series().map((_,i)=>String(i+1)+(i===series().length-1?" (latest)":"")));
  el("step").value=String(series().length-1);
  showSeries();
}
function displayForecast(result) {
  const values=result.prediction[0];
  const table = document.createElement("table");
  const head=table.createTHead().insertRow();
  for (const text of ["Target","Forecast","Unit"]) {
    const th=document.createElement("th");th.textContent=text;th.scope="col";head.append(th);
  }
  const body=table.createTBody();
  const indices=values.map((_,i)=>i);
  if(isRank()) indices.sort((a,b)=>values[b]-values[a] || a-b);
  for (const i of indices) {
    const tr=body.insertRow(), target=document.createElement("th");
    target.scope="row";target.textContent=isRank()?"Candidate "+(i+1)+(record.valid && !record.valid[0][i]?" (excluded)":""):label(row().schema.outputs[i]);tr.append(target);
    tr.insertCell().textContent=Number(values[i]).toLocaleString(undefined,{maximumSignificantDigits:6});
    tr.insertCell().textContent=isRank()?"probability":row().schema.output_units[i];
  }
  el("output").replaceChildren(table);
}
async function forecast() {
  const version=++serial;
  const payload=JSON.stringify(record);
  el("output").replaceChildren();tell("Computing forecast…");
  try {
    const result = await api("/api/forecast",{method:"POST",headers:{"Content-Type":"application/json"},body:payload});
    if(version!==serial) return;
    if (result.task!==task || result.checkpoint_sha256!==catalog.checkpoint_sha256) throw Error("The reported model identity changed. Reopen the demo.");
    displayForecast(result);tell("Forecast ready.");
  } catch(error){if(version===serial)tell(error.message,true);}
}
function resetCase() {
  el("run").disabled=false;
  task=el("task").value;
  record=copy(row().example);
  el("source").textContent="Invented example";el("upload").value="";
  el("task-note").textContent=row().description.input;
  el("horizon").textContent=row().description.horizon;
  el("forecast-note").textContent=row().description.forecast;
  el("missing-hint").textContent=task==="human_touch_afferent" ? "Provide all five readings in every 20 ms bin." : "A null channel value represents a missing reading.";
  initializeControls();forecast();
}
function dirty() {
  ++serial;el("output").replaceChildren();tell("Input changed. Run the forecast again.");
}
el("task").addEventListener("change",()=>{el("intent-result").replaceChildren();resetCase();});
el("reset").addEventListener("click",resetCase);
el("run").addEventListener("click",forecast);
for(const id of ["candidate","channel","step"]) el(id).addEventListener("change",() => {el("run").disabled=false;showSeries();});
el("value").addEventListener("input",() => {
  const field=el("value");
  if (field.validity.badInput) {dirty();el("run").disabled=true;return;}
  el("run").disabled=false;
  const value=field.value===""?null:Number(field.value);
  series()[Number(el("step").value)][Number(el("channel").value)]=value;
  dirty();const position=field.value;showSeries();field.value=position;
});
el("upload").addEventListener("change",async e=>{
  const file=e.target.files[0];if(!file)return;
  try {
    if(file.size>2_000_000)throw Error("Choose one input under 2 MB.");
    const input=JSON.parse(await file.text());
    if(input.task!==task || !Array.isArray(input.X) || input.X.length!==1)throw Error("Choose one input for the selected task.");
    const version=++serial;
    const result=await api("/api/forecast",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(input)});
    if(version!==serial)return;
    record=input;el("source").textContent="Input file · "+file.name;
    initializeControls();displayForecast(result);tell("Forecast ready.");
  }catch(error){tell(error.message,true);}
});
el("save").addEventListener("click",()=>{
  const a=document.createElement("a"), url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+"\n"],{type:"application/json"}));
  a.href=url;a.download=task+"-input.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
function sayIntent(message) {
  const p=document.createElement("p");p.textContent=message;el("intent-result").replaceChildren(p);
}
function proposeTask(id) {
  if (!catalog.tasks[id]) {sayIntent("This checkpoint does not include that task.");return;}
  const title=catalog.tasks[id].description.title;
  if (task===id) {
    sayIntent(title+" · Forecasting from the current input history.");forecast();return;
  }
  sayIntent(title+" uses different measurements. Load its invented example to replace the current history?");
  const accept=document.createElement("button"),cancel=document.createElement("button");
  accept.textContent="Load invented example and forecast";cancel.textContent="Keep current input";
  accept.onclick=()=>{el("task").value=id;resetCase();sayIntent(title+" · Invented input loaded.");};
  cancel.onclick=()=>sayIntent("Current task and input kept.");
  el("intent-result").append(accept,cancel);
}
function handleIntent(intent) {
  if(intent.kind==="forecast"){proposeTask(intent.task);return;}
  if(intent.kind==="game_goal"){
    if(!catalog.game_mounted){sayIntent(intent.label+" is a simulation goal. Open the demo with a compatible local game to try it.");return;}
    sayIntent(intent.label+" is a simulation goal. Open it in the local game and confirm it there.");
    const link=document.createElement("a");
    link.href="/game/?"+new URLSearchParams({effector:intent.effector,goal:intent.goal});
    link.textContent="Open proposed goal in game";el("intent-result").append(link);return;
  }
  sayIntent(intent.message);
  for(const id of intent.choices||[]){
    if (!catalog.tasks[id]) continue;
    const button=document.createElement("button");button.textContent=catalog.tasks[id].description.title;
    button.onclick=()=>proposeTask(id);el("intent-result").append(button);
  }
 }
el("outcome-form").addEventListener("submit",event=>{
  event.preventDefault();handleIntent(globalThis.NeuroOutcome.parseOutcome(el("outcome-text").value));
});
el("proposal-form").addEventListener("submit",event=>{
  event.preventDefault();
  try {handleIntent(globalThis.NeuroOutcome.validateProposal(JSON.parse(el("proposal").value)));}
  catch {sayIntent("Paste one JSON proposal with the supported task or game goal.");}
});
(async()=>{
  try{
    catalog=await api("/api/tasks");el("digest").textContent=catalog.checkpoint_sha256;
    for (const [key,spec] of Object.entries(catalog.tasks)) el("task").add(new Option(spec.description.title,key));
    if (catalog.initial_task && catalog.tasks[catalog.initial_task]) {
      el("task").value=catalog.initial_task;
      document.title=catalog.model;
      document.querySelector("h1 span").textContent="Touch study";
      el("outcome-text").placeholder="How many spikes will the touch nerve send?";
    }
    el("work").hidden=false;resetCase();
  }catch(error){tell(error.message,true);}
})();
