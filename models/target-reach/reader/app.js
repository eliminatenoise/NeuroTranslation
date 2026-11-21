(() => {
  "use strict";
  const el = id => document.getElementById(id);
  const name = {
    transformer_full:"Transformer · motion + target",transformer_pose_only:"Transformer · motion only",
    transformer_goal_only:"Transformer · target only",ridge_full:"Linear · motion + target",
    ridge_pose_only:"Linear · motion only",ridge_goal_only:"Linear · target only",
    stationary:"Stay at the last position",velocity:"Continue recent velocity",goal_hand_mean:"Training mean · hand + target",
    transformer_wrong_target:"Transformer · eight wrong targets",ridge_wrong_target:"Linear · eight wrong targets"
  };
  const handName = h => h[0].toUpperCase()+h.slice(1);
  const norm = (a,b) => Math.hypot(...a.map((v,i)=>v-b[i]));
  const sub = (a,b) => a.map((v,i)=>v-b[i]);
  const num = x => x == null ? "—" : (Math.abs(x) < 5e-9 ? 0 : x).toFixed(7).replace(/(\.\d{5,}?)0+$/, "$1");
  const unitTime = t => t.toFixed(3)+" s";
  const msKeys=["400","600","800"];
  let target=5, currentPlot, recording;
  function row(table, label, values, active=false) {
    const tr=document.createElement("tr");
    const th=document.createElement("th");th.scope="row";th.textContent=label;tr.append(th);
    const headers=table.parentElement.tHead.rows[0].cells;
    values.forEach((v,i)=>{const td=document.createElement("td");td.dataset.label=headers[i+1].textContent;td.textContent=v;tr.append(td);});
    if(active) tr.className="focusRow";
    table.append(tr);
  }
  function infer(method, assignedTarget) {
    const align=el("alignment").value;
    const history={xyz:recording.xyz,time:recording.time,hand:recording.hand,target:assignedTarget};
    if (method.startsWith("transformer_") || method.startsWith("ridge_")) {
      const first=method.indexOf("_");
      const mode=method.slice(first+1);
      const seed=method.slice(0,first)==="ridge" ? "ridge" : el("seed").value;
      return TargetReach.predict(TargetReachWeights[align][mode+"-"+seed],history);
    }
    return TargetReach.baseline(method,history,TargetReachData.means[align]);
  }
  function chart() {
    if (currentPlot) TargetReachPlot.draw(el("chart"),currentPlot.traces,currentPlot.horizon,el("projection").value);
  }
  function render() {
    const clock=el("alignment").value, method=el("method").value, h=Number(el("horizon").value);
    const edited=target!==recording.target;
    const selected=infer(method,target);
    const original=edited?infer(method,recording.target):null;
    const sample=recording.observed[h];
    el("seed").disabled=!method.startsWith("transformer_");
    el("reset").disabled=!edited;
    el("command").value="target "+target;
    const syncId=String(target);
    [...el("targets").children].forEach(button=>button.setAttribute("aria-pressed",String(button.value===syncId)));
    el("status").textContent=edited ? "Edited to target "+target+". The same five input points stay in place." :
      "Assigned target "+target+". The recording supplies the comparison.";
    el("referenceLegend").className=edited?"original":"actual";
    el("referenceLegend").textContent=edited?"Assigned-target forecast":"Recorded endpoints";
    const past=recording.xyz.map(p=>sub(p,recording.xyz[4]));
    currentPlot={horizon:h,traces:[
      {kind:"input",points:past,color:"#8fd6fc"},
      {kind:"forecast",points:selected,color:"#f5bd65"},
      {kind:edited?"original":"recorded",points:edited?original:recording.observed,color:edited?"#c3b9ff":"#b1eeae"}
    ]};
    chart();
    const t=unitTime(TargetReach.horizons[h]);
    el("caption").textContent="Rings mark "+t+" from the clock start. Lines join the sampled points for reading. The view fits this trial’s coordinates.";
    el("chart").setAttribute("aria-label",name[method]+" for the "+recording.hand+" hand and target "+target+", compared with "+(edited?"the assigned-target forecast.":"recorded optical endpoints.")+" The coordinate table gives exact values.");
    const coords=el("coordinates");coords.replaceChildren();
    el("distanceHead").textContent=edited?"Shift from original (m)":"3D error (m)";
    row(coords,name[method]+" · target "+target, [...selected[h].map(num),num(edited?norm(selected[h],original[h]):sample&&norm(selected[h],sample))],true);
    if(edited) row(coords,"Assigned-target forecast · "+recording.target,[...original[h].map(num),"—"]);
    else row(coords,"Recorded cylinder",sample ? [...sample.map(num),"—"] : ["Missing","Missing","Missing","—"]);
    const baselineMethods=["stationary","velocity","goal_hand_mean"].filter(m=>m!==method);
    baselineMethods.forEach(m=>{
      const end=infer(m,target)[h];
      const delta=edited?norm(end,infer(m,recording.target)[h]):sample&&norm(end,sample);
      row(coords,name[m],[...end.map(num),num(delta)]);
    });
    el("endpointNote").textContent=edited ?
      "The person saw target "+recording.target+". No measured endpoint exists for this edited destination on this start. Shift compares the two forecasts of each method." :
      (sample ? "The cameras supplied this endpoint at "+unitTime(recording.observedTime[h])+" from the selected clock start." :
      "This optical endpoint is missing. Forecast coordinates remain available and there is no error to report.");
    const input=el("inputs");input.replaceChildren();
    recording.xyz.forEach((p,i)=>row(input,unitTime(recording.time[i]),p.map(num)));
    const group=el("group").value;const key=msKeys[h]+"/"+group;
    const cohort=TargetReachData.groups[clock][key];const context=TargetReachData.coverage[clock];
    const endpointSupport=context.endpoints[msKeys[h]][group];
    el("benchmarkContext").textContent="At "+t+" from "+(clock==="acquisition"?"the first optical sample":"the confirmed 15 mm crossing")+
       ", "+endpointSupport.n+" recordings from "+endpointSupport.people+" held-out people supply a measured endpoint in this group. The study used 24 other people to fit the models.";
    el("gateResult").textContent=clock==="acquisition"?
       "The primary test at 0.600 s found no error reduction from adding the assigned target to the early optical history. The cylinder often barely moved in this window." :
       "At 0.600 s after the crossing, the assigned target beat the eight wrong targets on average. The difference from motion alone was too uncertain to establish an advantage.";
    const scores=el("scores");scores.replaceChildren();
    for (const [id,label] of Object.entries(name)) {
      const s=cohort?.scores[id];
      if(s) row(scores,label,[num(s.mean),s.ci.map(num).join(" to ")],id===method);
    }
    const pairedScores=el("pairs");pairedScores.replaceChildren();
    for(const [id,stat] of Object.entries(cohort?.comparisons||{})){
      row(pairedScores,name[id],[num(stat.mean),stat.ci.map(num).join(" to ")]);
    }
    const all=context.endpoints[msKeys[h]].both.n;
    const total=TargetReachData.overall[clock].rows;
    const reasonText=Object.entries(context.reasons).filter(([key])=>key!=="included").map(([k,v])=>v+" "+k).join(", ");
    el("coverage").textContent="Across both hand sessions, "+total+" of "+context.candidate+" candidate recordings supplied a complete history on this clock. The other recordings fell out for these reasons — "+reasonText+". Of these "+total+", "+(total-all)+" lacked the "+t+" endpoint. The subject split and original measurement exclusions remain the same when you edit a destination.";
  }
  function selectCase() {
    recording=TargetReachData.cases[el("alignment").value].find(c=>c.hand===el("hand").value && c.target===Number(el("trial").value));
    target=recording.target;
    el("clockHint").textContent=el("alignment").value==="acquisition" ?
      "Zero is the first usable optical frame. It can precede the reach by seconds." :
      "Zero is the third consecutive frame at least 15 mm from the start."+(recording.secondsFromFirst==null?"":" Here that happened "+unitTime(recording.secondsFromFirst)+" after the first optical sample.");
    el("selectedCase").textContent=handName(recording.hand)+" hand · assigned target "+recording.target+" · "+recording.markerCount+" optical marker"+(recording.markerCount===1?"":"s")+". One held-out recording per hand and target, chosen by original order.";
    render();
  }
  function loadCases(wantedTarget=5) {
    const select=el("trial");select.replaceChildren();
    const rows=TargetReachData.cases[el("alignment").value].filter(c=>c.hand===el("hand").value);
    for (const c of rows) select.add(new Option("Target "+c.target,c.target));
    if(rows.some(c=>c.target===wantedTarget)) select.value=String(wantedTarget);
    selectCase();
  }
  try {
    if(location.protocol==="file:"){el("download").href="https://eliminatenoise.github.io/NeuroTranslation/target-reach-offline.zip";el("download").textContent="Online ZIP ↗";}
    for(let i=1;i<=9;i++) {
      const button=document.createElement("button");button.type="button";button.value=i;button.textContent=i;
      button.setAttribute("aria-label","Forecast target "+i);button.addEventListener("click",()=>{target=i;render();});el("targets").append(button);
    }
    el("commandForm").addEventListener("submit",event=>{
      event.preventDefault();const result=TargetReach.parseTarget(el("command").value);
      if(result===null){el("status").textContent="Enter a number from 1 to 9, for example “target 5”.";return;}
      target=result;render();
    });
    el("reset").addEventListener("click",()=>{target=recording.target;render();});
    for(const id of ["hand","alignment"])el(id).addEventListener("change",()=>loadCases(recording.target));
    el("trial").addEventListener("change",selectCase);
    for(const id of ["method","seed","horizon","group"]) el(id).addEventListener("change",render);
    el("projection").addEventListener("change",chart);
    loadCases();
    if (typeof ResizeObserver==="function") new ResizeObserver(chart).observe(el("chart"));
    else window.addEventListener("resize",chart);
  } catch(error) {
    el("fatal").hidden=false;el("fatal").textContent="Could not open the forecasts. Extract the entire reader folder and reopen index.html.";
    throw error;
  }
})();
