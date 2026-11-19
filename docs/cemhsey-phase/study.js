"use strict";
(() => {
  const data = globalThis.PINCH_PHASE_RESULTS;
  const phases = {overall:"Whole trial", initial_rest:"Initial rest", ramp_up:"Rise", hold:"Hold", release:"Release", final_rest:"Final rest"};
  const simple = "persistence_plus_cue_change";
  const parents = {[simple]:"Current force + cue change", history_phase:"Force history", history_phase_paired_grid:"Five forearm grids"};
  const variants = {unchanged:"Original", pooled:"One coefficient", split:"Separate rise and fall"};
  const metrics = {mae:"Mean absolute error",rmse:"Root mean square error",target_relative_mae:"Mean absolute error relative to target"};
  const labels = {persistence:"Current force alone",scheduled_cue:"Scheduled target alone"};
  for (const [parent,label] of Object.entries(parents)) {
    for (const [v,title] of Object.entries(variants)) labels[parent+"_"+v]=label+" · "+title.toLowerCase();
  }
  const pairs=[];
  for(const parent of Object.keys(parents)){
    for(const [a,b] of [["split","unchanged"],["split","pooled"],["pooled","unchanged"]]){
      pairs.push([parent+"_"+a,parent+"_"+b,parents[parent]+" · "+variants[a]+" versus "+variants[b].toLowerCase()]);
    }
  }
  for(const parent of ["history_phase","history_phase_paired_grid"])
    for(const version of ["pooled","split"])
      pairs.push([parent+"_"+version,simple+"_"+version,variants[version]+" · "+parents[parent]+" versus "+parents[simple]]);
  const id=name=>document.getElementById(name);
  function element(tag,text) {const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;}
  function option(value,text){const node=element("option",text);node.value=value;return node;}
  const decimal=n=>Number((100*Math.abs(n)).toPrecision(5)).toString();
  const signed=n=>n===0?"0":(n>0?"+":"−")+decimal(n);
  const scoreRow=key=>data.results.find(row=>row.phase===key&&row.target_percent_mvc===50);
  const effect=(row,pair)=>row.contrasts.find(c=>c.candidate===pair[0]&&c.comparator===pair[1]);
  function track(value,max,fill){
    const ns="http://www.w3.org/2000/svg";
    const svg=document.createElementNS(ns,"svg");svg.setAttribute("aria-hidden","true");svg.setAttribute("width","100%");svg.setAttribute("height","100%");
    const rect=document.createElementNS(ns,"rect");rect.setAttribute("width",max>0?(100*value/max)+"%":"0%");rect.setAttribute("height","100%");rect.setAttribute("fill",fill);svg.append(rect);
    const div=element("div");div.className="track";div.append(svg);return div;
  }
  function render(){
    const phase=id("phase").value,metric=id("metric").value,comparison=pairs[Number(id("pair").value)];
    const row=scoreRow(phase), scores=row.arms, unit=metric==="target_relative_mae"?"% of target":"% MVC";
    const max=Math.max(...Object.keys(parents).flatMap(p=>Object.keys(variants).map(v=>scores[p+"_"+v][metric])));
    id("scale").textContent=metrics[metric]+" during "+phases[phase].toLowerCase()+". All bars share a scale from 0 to "+decimal(max)+" "+unit+".";
    const groups=id("groups");groups.replaceChildren();
    for(const [parent,title] of Object.entries(parents)){
      const group=element("div");group.className="group";group.append(element("h3",title));
      const bars=element("div");bars.className="bars";
      for(const [version,label] of Object.entries(variants)){
        const arm=parent+"_"+version,v=scores[arm][metric],bar=element("div");bar.className="bar";bar.dataset.arm=arm;
        const name=element("span",label);name.className="bar-label";const value=element("span",decimal(v)+" "+unit);value.className="bar-value";
        bar.append(name,track(v,max,{"unchanged":"#879990","pooled":"#467784","split":"#276653"}[version]),value);bars.append(bar);
      }
      group.append(bars);groups.append(group);
    }
    id("support").textContent=row.issues.toLocaleString("en")+" forecast cutoffs across both repeats from each of three test participants.";
    const paired=effect(row,comparison);
    id("summary").textContent=phases[phase]+". "+labels[comparison[0]]+" compared with "+labels[comparison[1]]+". Mean gain "+signed(paired.mae_gain_mean)+" percentage points of MVC. The three gains fall between "+signed(paired.mae_gain_lower_bound)+" and "+signed(paired.mae_gain_upper_bound)+". Lower error for "+paired.wins+", equal for "+paired.ties+", higher for "+paired.losses+".";
    const body=id("gains");body.replaceChildren();
    for(const [key,title] of Object.entries(phases)){
      const c=effect(scoreRow(key),comparison),tr=element("tr");tr.dataset.phase=key;tr.classList.toggle("selected",key===phase);
      const th=element("th"),btn=element("button",title);th.scope="row";btn.className="phase-button";btn.type="button";btn.setAttribute("aria-pressed",String(key===phase));
      btn.addEventListener("click",()=>{id("phase").value=key;render();body.querySelector('[data-phase="'+key+'"] button').focus({preventScroll:true});});
      th.append(btn);tr.append(th);
      for(const val of [signed(c.mae_gain_mean),signed(c.mae_gain_lower_bound)+" to "+signed(c.mae_gain_upper_bound),c.wins,c.ties,c.losses])tr.append(element("td",val));
      body.append(tr);
    }
    id("table-phase").textContent=phases[phase]+", at a target of 50% MVC. Each test participant has equal weight.";
    const table=id("scores");table.replaceChildren();
    for(const [key,title] of Object.entries(labels)){
      const v=scores[key],tr=element("tr");tr.dataset.arm=key;const th=element("th",title);th.scope="row";tr.append(th);
      for(const name of ["mae","rmse","signed_error","target_relative_mae"])tr.append(element("td",(100*v[name]).toFixed(5)));
      table.append(tr);
    }
  }
  try {
    if(!data||data.format!=="cemhsey-pinch-phase-summary-v1"||data.protocol_sha256!=="e8d7cd2cb14e5546d42a07ea38aed134b456ab75a284e7e12bd3b5a09dbf8640"||data.results.length!==6)throw Error("Missing study");
    for(const key of Object.keys(phases)){
      const row=scoreRow(key);
      if(!row||row.participants!==3||row.trials!==6||!Object.keys(labels).every(arm=>row.arms[arm])||!pairs.every(pair=>effect(row,pair)))throw Error("Incomplete study");
    }
    id("phase").replaceChildren(...Object.entries(phases).map(([key,title])=>option(key,title)));
    id("pair").replaceChildren(...pairs.map((pair,i)=>option(i,pair[2])));
    for(const key of ["phase","pair","metric"]){const c=id(key);c.disabled=false;c.addEventListener("change",render);}
    render();
  }catch{
    for(const c of document.querySelectorAll("select"))c.disabled=true;
    id("summary").textContent="The interactive comparison could not open. The complete findings are in the study report and CSV downloads below.";
  }
})();
