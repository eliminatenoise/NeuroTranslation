"use strict";

(() => {
  const el = id => document.getElementById(id);
  const read = id => JSON.parse(el(id).textContent);
  const model = read("model-data"), reports = read("report-data"), example = read("example-data");
  const methods = {
    transformer:"Transformer", cue:"Cue average", still:"No change", ridge:"Linear ridge",
    mlp:"Feed-forward network", transformer_no_cue:"Transformer without cue",
    mlp_no_cue:"Feed-forward without cue", ridge_no_cue:"Ridge without cue", unconditional:"Training average"
  };
  const explanations = {
    transformer:"The Transformer learns how much weight to give the instruction and each of the four early sensor bins.",
    cue:"The cue average uses the mean change for this instruction in the fitting group.",
    still:"No change keeps each sensor at its final early median.",
    ridge:"Linear ridge assigns fitted weights to the instruction and the early readings.",
    mlp:"A feed-forward network combines the same instruction and readings through one nonlinear layer.",
    transformer_no_cue:"This separately trained Transformer uses only the early sensor readings.",
    ridge_no_cue:"This separately fitted linear model uses only the early sensor readings.",
    mlp_no_cue:"This separately trained feed-forward network uses only the early sensor readings.",
    unconditional:"The training average predicts the same change for every instruction and history."
  };
  const labels = ["Elbow","Forearm rotation","Index finger"];
  const cues = {
    "elbow flexion":"Bend the elbow", "elbow extension":"Straighten the elbow", supination:"Turn the palm up",
    pronation:"Turn the palm down", "hand close":"Close the hand", "hand open":"Open the hand", rest:"Rest"
  };
  const groups = {assessment:"New people",development:"Training group"};
  const groupNotes = {
    assessment:"One model fitted to people S1–S7 made every forecast for people S8–S12. Those five people were set aside until the weights and scoring rules were fixed.",
    development:"Each of seven fits learned from six people in S1–S7 and predicted the seventh. The fitting groups overlap. The model in the experiment above was fitted once to all seven."
  };
  const entries = Object.entries;
  const options = (selector, pairs) => el(selector).replaceChildren(...pairs.map(([id,label])=>new Option(label,id)));
  const selected = selector => el(selector).value;
  const numbers = new Intl.NumberFormat("en",{maximumSignificantDigits:3,useGrouping:false});
  const fmt = value => {
    if (value===null || !Number.isFinite(value)) return "—";
    const abs = Math.abs(value);
    if (abs && (abs < .001 || abs >= 100000)) return value.toExponential(2);
    return numbers.format(value);
  };
  const node = (tag,content) => {const element=document.createElement(tag); element.textContent=content;return element;};
  function methodLabel(key) {
    if (methods[key]) return methods[key];
    const base = key.replace(/_(?:wrong|swapped|incorrect)(?:_cue|_cues|_labels)?$/, "");
    if (base !== key && methods[base]) return methods[base]+" · incorrect cues";
    return key.replaceAll("_"," ");
  }
  const state = {history:null,series:[],names:[]};
  const sensorOptions = labels.map((name,index)=>[String(index),name]);
  options("cue",entries(cues)); options("sensor",sensorOptions);
  options("method",entries(methods)); options("reference",[["none","None"],...entries(methods)]);
  options("cohort",entries(groups).filter(([key])=>reports[key]));
  options("error-cue",[["all","All instructions"],...entries(cues)]);
  options("error-sensor",sensorOptions);
  if (location.protocol==="file:") document.querySelector("a.download").hidden=true;

  function editRows() {
    const sensor = Number(selected("sensor"));
    el("edit-rows").replaceChildren(...state.history.map((row, bin) => {
      const tr = document.createElement("tr"), th = node("th",String(bin+1)); th.scope="row";tr.append(th);
      for (const [offset,quantity] of [[0,"median"],[3,"change"]]) {
        const td = document.createElement("td"), input = document.createElement("input");
        input.type="number"; input.step="any";input.id=`value-${bin}-${offset}`;
        input.setAttribute("aria-label",`${labels[sensor]} bin ${bin+1} ${quantity}`);
        input.value = row[sensor+offset] ?? "";
        input.addEventListener("input",() => {
          const valid = Number.isFinite(input.valueAsNumber);
          state.history[bin][sensor+offset] = valid ? input.valueAsNumber : null;
          input.setAttribute("aria-invalid",String(!valid));updateForecast();
        });
        if(row[sensor+offset]===null) input.setAttribute("aria-invalid","true");
        td.append(input);tr.append(td);
      }
      return tr;
    }));
  }
  function draw() {drawForecasts(el("charts"),state.series,labels,state.names,fmt);}
  function forecastTable() {
    const target = el("forecast-values");target.replaceChildren();
    state.series.forEach((series, method) => {
      const table=document.createElement("table"),thead=table.createTHead(),tr=thead.insertRow();
      table.createCaption().textContent=state.names[method]+" · change from cutoff";
      for (const header of ["Sensor","+0.5 s","+1.0 s","+1.5 s"]) {const th=node("th",header);th.scope="col";tr.append(th);}
      const tbody=table.createTBody();
      labels.forEach((name,index)=>{const row=tbody.insertRow();const th=node("th",name);th.scope="row";row.append(th);series.delta.forEach(values=>row.insertCell().textContent=fmt(values[index]));});
      target.append(table);
    });
  }
  function updateForecast() {
    el("method-note").textContent=explanations[selected("method")];
    const chosen = [...new Set([selected("method"), selected("reference")].filter(id=>id!=="none"))];
    try {
      if (state.history.some(row=>row.includes(null))) throw new Error("Enter a number for each reading. An empty cell stops the forecast.");
      state.series = chosen.map(method=>CuedArmTransfer.predict(model,{cue:selected("cue"),history:state.history,method}));
      state.names=chosen.map(methodLabel);
      el("input-status").textContent=state.series[0].outside_fit_range ? "At least one reading falls outside the range seen during fitting. Treat this example as an extrapolation." : "";
    } catch(error) {
      state.series=[];state.names=[];el("input-status").textContent=error.message;
    }
    el("legend").replaceChildren(...state.names.map((label,i)=>{const span=node("span",label);span.className=i?"ref":"";span.prepend(document.createElement("i"));return span;}));
    if(state.series.length)draw();else el("charts").replaceChildren(node("p","Complete the sensor history to calculate a forecast."));
    forecastTable();
  }
  function restore() {
    state.history=example.history.map(row=>row.slice());
    el("cue").value=example.cue;el("method").value="transformer";el("reference").value="cue";el("sensor").value="0";
    editRows();updateForecast();
  }
  function groupChanged() {
    const report=reports[selected("cohort")];
    options("contrast",Object.keys(report.summary.contrasts).filter(k=>k.startsWith("transformer_vs_")).map(k=>[k,methodLabel(k.slice("transformer_vs_".length))]));
    el("contrast").value="transformer_vs_cue";
    updateScores();
  }
  function updateScores() {
    const cohort=selected("cohort"), report=reports[cohort], cue=selected("error-cue");
    const sensor=Number(selected("error-sensor"));
    const scores=cue==="all" ? report.summary.methods : report.by_cue[cue].methods;
    const availableKeys=Object.keys(scores);
    const ordered=[...Object.keys(methods).filter(k=>availableKeys.includes(k)),...availableKeys.filter(k=>!methods[k])];
    const n=cue==="all"?report.n:report.by_cue[cue].n;
    const count=cue==="all"?report.n_people:report.by_cue[cue].n_people;
    el("split-note").textContent=groupNotes[cohort];
    el("score-scope").textContent=`${count} held-out people · ${n} scored trials · ${cue==="all"?"all seven instructions":cues[cue]}`;
    if(cue==="all") el("score-scope").textContent+=` · ${report.n_outside_fit_range} of ${report.n} trials had a sensor summary outside its fitting range`;
    el("scores-caption").textContent=labels[sensor]+" · mean absolute error";
    el("scores-body").replaceChildren(...ordered.map(key=>{
      const values=scores[key];
      const row=document.createElement("tr"),th=node("th",methodLabel(key));th.scope="row";th.className="method-name";row.append(th);
      for(const h of [0,1,2]) row.insertCell().textContent=fmt(values.native_mae[h][sensor]);
      row.insertCell().textContent=fmt(values.score);
      return row;
    }));
    const k=report.summary;
    el("result-title").textContent=(cohort==="assessment"?"The fixed model on five new people":"Seven development fits")+" · all seven instructions together";
    const eligibility=k.complete_people_cues_runs?"": " Some people, cues or runs were missing.";
    el("overall-result").textContent=(cohort==="assessment"
      ? (k.overall_advantage?"The Transformer met the prespecified overall improvement criterion.":"The Transformer fell short of the prespecified overall improvement criterion.")+" The test required at least 5% lower overall error and a lower error in every person against each of six comparisons."
      : "Each development result comes from a different fit. The spread across these people describes this small group; the fixed model’s separate assessment tests its performance on new people."
    )+eligibility+(cue==="all"?"":" This summary always pools all seven instructions; the table above shows only the instruction you chose, so its numbers differ.");
    if(cohort==="assessment" && k.criteria) {
      const domains=[["cue_contribution","using the correct cue"],["attention_architecture","beating both fitted alternatives"],["net_benefit","beating the cue average and no change"]];
      const passed=domains.filter(([key])=>k.criteria[key]).map(([,label])=>label);
      const missed=domains.filter(([key])=>!k.criteria[key]).map(([,label])=>label);
      if(passed.length) el("overall-result").textContent+=" The threshold was met for "+passed.join(", ")+".";
      if(missed.length) el("overall-result").textContent+=" It was missed for "+missed.join(", ")+".";
    }
    const ranked=Object.entries(k.methods).filter(([key,value])=>methods[key] && Number.isFinite(value.score)).sort((a,b)=>a[1].score-b[1].score);
    if(ranked.length) el("overall-result").textContent+=` Across the group, ${methodLabel(ranked[0][0])} had the lowest overall error (${fmt(ranked[0][1].score)}). The Transformer scored ${fmt(k.methods.transformer.score)}.`;
    const flat=report.n_runs_with_constant_glove_target_all_horizons;
    if(flat>0) el("overall-result").textContent+=` In ${flat} of ${report.n_runs} runs, finger-sensor changes were constant across trials at all three forecast times. The recordings cannot separate a still finger from a sensor problem in these runs.`;
    const contrast=k.contrasts[selected("contrast")];
    if(contrast?.defined) {
      const [lo,hi]=contrast.paired_percentile_95;
      el("interval").textContent=`Across the whole group, the Transformer’s error minus this comparator’s error was ${fmt(contrast.mean_difference)}. It was smaller in ${contrast.people_with_lower_error} of ${report.n_people} people. The exploratory 95% interval was ${fmt(lo)} to ${fmt(hi)}, from 10,000 resamples of whole people. A negative difference favours the Transformer.`;
      if(cohort==="assessment" && Number.isFinite(contrast.relative_change)) {
        const direction=contrast.relative_change<0?"lower":"higher";
        el("interval").textContent+=` Relative to this comparator the group error was ${fmt(Math.abs(100*contrast.relative_change))}% ${direction}. This comparison ${contrast.pass?"met":"missed"} the improvement criterion.`;
      }
    } else el("interval").textContent="A normalized comparison could not be calculated for this group.";
  }
  for(const selector of ["method","cue","reference"]) el(selector).addEventListener("change",updateForecast);
  el("sensor").addEventListener("change",editRows);el("restore").addEventListener("click",restore);
  el("cohort").addEventListener("change",groupChanged);
  for(const selector of ["error-cue","error-sensor","contrast"]) el(selector).addEventListener("change",updateScores);
  let lastWidth;
  new ResizeObserver(([entry])=>{const width=entry.contentRect.width;if(width!==lastWidth){lastWidth=width;if(state.series.length)draw();}}).observe(el("charts"));
  restore();groupChanged();
})();
