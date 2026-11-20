const get = id => document.getElementById(id);
const modelNames = ElbowPredict.names, methods = ElbowPredict.modes, models = ELBOW_MODEL.models;
const decimal = n => n.toFixed(4);
const signed = n => (n > 0 ? "+" : "") + decimal(n);
const keys = [
  ["elbow_medians", "Elbow sensor · medians"],
  ["c3_means", "Scalp electrode C3 · means"],
  ["eog_means", "Eye electrodes · means"]
];
const descriptions = {
  persistence: "Carry the last elbow reading forward. The predicted change is zero.",
  cue_median: "Use the middle change seen for this cue during fitting. Earlier readings have no influence on this estimate.",
  cue_mechanics: "Use the cue, the latest elbow reading and three recent changes in that reading.",
  cue_mechanics_c3: "Add changes in four early scalp readings to the cue and elbow history.",
  cue_mechanics_eog: "Replace the scalp input with changes measured near the eyes. This checks one source of interference.",
  temporal_attention: "Weight four early scalp readings using their values and order, then add the result to cue and elbow history."
};
for (const mode of methods) get("mode").add(new Option(modelNames[mode],mode));
for (const [key,title] of keys) {
  const field = document.createElement("fieldset"); field.className = "signal";
  const legend = document.createElement("legend"); legend.textContent=title; field.append(legend);
  const bins = document.createElement("div"); bins.className="bins";
  for (let i=0;i<4;i++) {
    const label=document.createElement("label"),name=document.createElement("span"),input=document.createElement("input");
    name.textContent="Bin "+(i+1);input.id=key+"-"+i;input.type="number";input.step="any";
    input.min=-100000000;input.max=100000000;input.required=true;input.setAttribute("aria-label",title+", bin "+(i+1));
    label.append(name,input);bins.append(label);
  }
  field.append(bins);get("signals").append(field);
}
function row(label, values, featured=false) {
  const tr = document.createElement("tr");
  if (featured) tr.className = "featured";
  const heading=document.createElement("th");heading.scope="row";heading.textContent=label;tr.append(heading);
  for(const value of values){const td=document.createElement("td");td.textContent=value;tr.append(td);}
  return tr;
}
function rawInput() {
  const obj = {cue: document.querySelector("input[name=cue]:checked").value};
  for(const [key] of keys) obj[key]=Array.from({length:4},(_,i)=>{
    const field=get(key+"-"+i);return field.validity.valid?field.valueAsNumber:NaN;
  });
  return obj;
}
function updateForecast() {
  const input=rawInput(), mode=get("mode").value, observed=get("observe").checked;
  get("mode-description").textContent=descriptions[mode];
  get("cue-description").textContent = input.cue === "flexion" ? "Elbow flexion · event 0x600" : "Elbow extension · event 0x601";
  get("future-input").hidden = !observed;
  const futureValue = get("future").validity.valid ? get("future").valueAsNumber : NaN;
  const outcome = observed && Number.isFinite(futureValue) ? futureValue : null;
  get("outcome-key").hidden = outcome === null;
  get("predictions").replaceChildren();
  if (keys.some(([key])=>input[key].some(n=>!Number.isFinite(n)))) {
    get("marks").replaceChildren();get("chart-desc").textContent="An input is missing or outside the display range.";
    get("delta").textContent="—";get("comparison").textContent="Enter four finite readings in every row, between −100 million and +100 million.";
    return;
  }
  const change = ElbowPredict.forecast(models,mode,input);
  const cutoff=input.elbow_medians[3],endpoint=cutoff+change;
  get("delta").textContent=signed(change);
  plotElbow(input.elbow_medians,change,outcome);
  let summary=`Cutoff reading ${decimal(cutoff)}. Predicted endpoint ${decimal(endpoint)}.`;
  if (outcome !== null) summary+=` Invented outcome ${decimal(outcome)}. Absolute error ${decimal(Math.abs(outcome-endpoint))}.`;
  else if (observed) summary+=" Enter a finite later reading within the display range to compare.";
  get("comparison").textContent=summary;
  for (const name of methods) {
    const pred=ElbowPredict.forecast(models,name,input);
    get("predictions").append(row(modelNames[name],[signed(pred),decimal(cutoff+pred)],mode===name));
  }
}
function updateEvidence() {
  const S=ELBOW_SCORES,group=get("group").value,all=group==="all";
  const runs=["1","2","3"].map(n=>all?S.by_run[n]:S.by_run_cue[n][group]);
  const mean=all?S.balanced_mae:S.by_cue[group].mae;
  const body=get("scores").tBodies[0];body.replaceChildren();
  for (const name of [...methods,"shifted_c3"]) {
    body.append(row(modelNames[name], [...runs.map(g=>decimal(g.mae[name])),decimal(mean[name])], name==="cue_mechanics_c3"));
  }
  const observed=all?S.pooled:S.by_cue[group];
  get("denominators").textContent = `${runs[0].n} trials per run · ${observed.n} trials shown · native elbow units. ${observed.small_abs_le_0_1} had a measured change of at most 0.1 units in magnitude. ${observed.opposite_training_cue_median} had a sign opposite to the median for their cue in the two training runs.`;
  const d=S.decision,primary=S.balanced_mae;
  const statement=d.incremental_c3_gate_passed ? "Scalp readings met the prespecified improvement test in this participant." : "Scalp readings did not meet the prespecified improvement test in this participant.";
  get("finding").textContent = `${statement} Adding C3 changed mean error from ${decimal(primary.cue_mechanics)} to ${decimal(primary.cue_mechanics_c3)} native units. Error fell in ${d.runs_c3_beats_mechanics} of 3 runs and ${d.cue_groups_c3_beats_mechanics} of 2 cue groups. These three runs cannot tell us how the forecasts would fare on another person.`;
}
function resetExample() {
  document.querySelector(`input[name=cue][value="${ELBOW_EXAMPLE.cue}"]`).checked=true;
  for(const [key] of keys)ELBOW_EXAMPLE[key].forEach((n,i)=>{get(key+"-"+i).value=n;});
  get("mode").value="cue_mechanics";get("observe").checked=false;get("future").value=44.1;
  updateForecast();
}
get("download").hidden = !["http:", "https:"].includes(window.location.protocol);
get("future").min=-100000000;get("future").max=100000000;
get("experiment").addEventListener("input",updateForecast);
get("reset").addEventListener("click",resetExample);
get("group").addEventListener("change",updateEvidence);
window.addEventListener("resize",updateForecast);
resetExample();updateEvidence();
