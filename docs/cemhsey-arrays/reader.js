"use strict";
(() => {
  const el=id=>document.getElementById(id);
  const api=globalThis.ArrayPinch, maps=globalThis.CEMHSEY_ARRAY_MAP, bundled=globalThis.CEMHSEY_ARRAY_FIT;
  const modelOrigins={
    invented_signals:"Fitted on invented signals",
    measured_train_local:"Fitted on the study’s training recordings",
    user_supplied_local:"Fitted on a user-selected set of trials"
  };
  const bundledLabel=bundled?.fit_origin==="measured_train_local"?
    "Private study model · "+modelOrigins.measured_train_local:
    "Demonstration model · "+modelOrigins.invented_signals;
  let fit=bundled, modelLabel=bundledLabel, trial=null, source="", row=null, lockedScale=null, selected=0,gridIndex=0;
  let trialToken=0, modelToken=0, scoreToken=0, scoring=false;
  const gridSelect=el("grid"),cutoff=el("cutoff"),reveal=el("reveal"),lock=el("lock");
  const scoreButton=el("score");
  const bands = globalThis.PinchIntervalUI.setup(rows, clearScore);
  const instances=[];
  const amplitude=v=>Number(v.toPrecision(5)).toString();
  const prediction=v=>v.toFixed(7);
  const colours=[[240,244,220],[169,216,173],[83,172,156],[35,123,133],[32,64,102]];
  function paint(v,limit){
    const t=limit>0?Math.min(1,v/limit):0,scaled=t*(colours.length-1),i=Math.min(colours.length-2,Math.floor(scaled)),f=scaled-i;
    return "rgb("+colours[i].map((c,j)=>Math.round(c+(colours[i+1][j]-c)*f)).join(",")+")";
  }
  function rows(body,values) {
    const fragment=document.createDocumentFragment();
    for(const [name,...rest] of values){const tr=document.createElement("tr"),th=document.createElement("th");
      th.scope="row";th.textContent=name;tr.append(th);
      for(const v of rest){const td=tr.insertCell();td.textContent=v;}fragment.append(tr);}
    body.replaceChildren(fragment);
  }
  function clearScore(){
    scoreToken++;
    scoring=false;
    scoreButton.disabled=!trial;
    scoreButton.textContent="Score this trial";
    el("score-table").hidden=true;
    el("score-table").tBodies[0].replaceChildren();
    el("interval-scores").hidden = true;
    el("band-score-table").tBodies[0].replaceChildren();
    el("score-status").textContent="";
  }
  function createGrids(){
    instances.length=0;const grid=maps[gridIndex],cells=grid.matlab_row_1based_by_local_cell;
    if(!cells.some(line=>line.includes(selected)))selected=cells.flat().find(v=>v!==null);
    for(const [id,windowName] of [["older-map","Earlier"],["recent-map","Later"]]){
      const map=el(id),buttons=[];
      map.replaceChildren();map.style.setProperty("--cols",String(cells[0].length));
      map.setAttribute("aria-label",windowName+" window, grid "+grid.grid_id);
      map.setAttribute("aria-rowcount",String(cells.length));map.setAttribute("aria-colcount",String(cells[0].length));
      cells.forEach((line,r)=>{
        const tr=document.createElement("div");tr.setAttribute("role","row");map.append(tr);
        line.forEach((channel,c)=>{
          if(channel===null){const gap=document.createElement("span");gap.className="missing";gap.setAttribute("role","gridcell");gap.setAttribute("aria-label","No electrode");tr.append(gap);return;}
          const button=document.createElement("button");button.type="button";button.className="cell";button.setAttribute("role","gridcell");
          button.setAttribute("aria-rowindex",String(r+1));button.setAttribute("aria-colindex",String(c+1));tr.append(button);
          buttons[channel]=button;
          button.addEventListener("click",()=>chooseChannel(channel));
          button.addEventListener("keydown",e=>{
            const direction={ArrowLeft:[0,-1],ArrowRight:[0,1],ArrowUp:[-1,0],ArrowDown:[1,0]}[e.key];
            let target=null;if(direction){let y=r+direction[0],x=c+direction[1];
              while(y>=0&&y<cells.length&&x>=0&&x<line.length){if(cells[y][x]!==null){target=cells[y][x];break;}y+=direction[0];x+=direction[1];}}
            else if(e.key==="Home"||e.key==="End"){const seq=(e.ctrlKey?cells.flat():line).filter(v=>v!==null);target=e.key==="Home"?seq[0]:seq.at(-1);}
            else return;e.preventDefault();if(target!==null){chooseChannel(target);buttons[target].focus();}
          });
        });
      });instances.push({buttons,windowName});
    }
    el("orientation").textContent="Grid "+grid.grid_id+" · "+grid.site_right_forearm+" · "+grid.cell_pitch_mm_both_axes+" mm electrode spacing. Array-local "+grid.local_reference_frame+".";
  }
  function selection(){
    if(!row)return;
    const prev=row.older.values[selected-1],now=row.recent.values[selected-1];
    el("selection").textContent="Channel "+selected+" · earlier "+amplitude(prev)+" mV · later "+amplitude(now)+" mV · change "+amplitude(now-prev)+" mV.";
    for(const {buttons} of instances){buttons.forEach((b,c)=>{b.tabIndex=c===selected?0:-1;b.setAttribute("aria-selected",String(c===selected));});}
  }
  function chooseChannel(c){selected=c;selection();}
  function renderCells(){
    if(!row)return;
    const cap=lockedScale??Math.max(row.older.max,row.recent.max);lock.disabled=cap===0&&!lock.checked;
    const clipped=lockedScale!==null&&(row.older.max>cap||row.recent.max>cap);
    el("scale-text").textContent="0 to "+amplitude(cap)+" mV"+(lockedScale===null?" · both windows, all five grids":" · locked")+(clipped?" · higher values use the darkest colour":"");
    for(const [i,{buttons,windowName}] of instances.entries()){
      const values=(i===0?row.older:row.recent).values;
      buttons.forEach((b,c)=>{const v=values[c-1];b.style.backgroundColor=paint(v,cap);const label=windowName+" window, channel "+c+", "+amplitude(v)+" mV";b.setAttribute("aria-label",label);b.title=label;});
    }selection();
    if(el("values").open){const ids=maps[gridIndex].matlab_row_1based_by_local_cell.flat().filter(Number.isInteger).sort((a,b)=>a-b);
      rows(el("electrode-values"),ids.map(c=>[String(c),amplitude(row.older.values[c-1]),amplitude(row.recent.values[c-1]),amplitude(row.recent.values[c-1]-row.older.values[c-1])]));
    }else el("electrode-values").replaceChildren();
  }
  function render(){
    if(!trial)return;
    try{
      row=api.features(trial,Number(cutoff.value));const estimates=api.forecast(fit,row);
      const time=(row.tick/200).toFixed(2);
      el("time").textContent=time+" s → "+((row.tick+24)/200).toFixed(2)+" s";
      cutoff.setAttribute("aria-valuetext",time+" seconds from nominal trial start");
      el("phase").textContent=row.phase+" · cutoff "+(Number(cutoff.value)+1)+" of 592";
      rows(el("grid-contrasts"),maps.map((g,i)=>["Grid "+g.grid_id,row.older.contrast[i].toFixed(6),row.recent.contrast[i].toFixed(6)]));
      el("rank").textContent="Channel-rank similarity "+row.rank.toFixed(4)+". A value near 1 means the relative order of channel amplitudes held across both windows. A flat window gives zero.";
      el("origin").textContent=modelLabel+" · "+source;
      rows(el("predictions"),Object.entries(estimates).map(([k,v])=>[api.labels[k],prediction(v)]));
      el("later").hidden=!reveal.checked;
      el("later").textContent=reveal.checked?(source==="Invented pinch"?"Later invented force ":"Later normalized force in this packet ")+prediction(trial.force[row.tick+24]):"";
      renderCells();
    }catch(error){
      el("predictions").replaceChildren();
      el("later").hidden=true;
      el("later").textContent="";
      el("status").textContent=error.message;
    } finally {
      bands.render(Number(cutoff.value), reveal.checked);
    }
  }
  function show(record,name){
    api.forecast(fit,api.features(record,160));
    trial=record;source=name;cutoff.value="160";bands.setTrial(record,name==="Invented pinch");lockedScale=null;lock.checked=false;reveal.checked=false;gridIndex=0;selected=0;gridSelect.value="0";createGrids();clearScore();
    el("trial").hidden=false;el("values").open=false;el("status").textContent=name+" · 320 electrode channels · 592 cutoffs.";render();
  }
  gridSelect.addEventListener("change",()=>{gridIndex=Number(gridSelect.value);createGrids();renderCells();});
  lock.addEventListener("change",()=>{if(!row)return;lockedScale=lock.checked?Math.max(row.older.max,row.recent.max):null;renderCells();});
  el("values").addEventListener("toggle",renderCells);
  cutoff.addEventListener("input",()=>{reveal.checked=false;clearScore();render();});
  reveal.addEventListener("change",render);
  el("example").addEventListener("click",()=>{
    trialToken++;
    el("file").value="";
    try { show(api.example(maps),"Invented pinch"); }
    catch (error) { el("status").textContent=error.message; }
  });
  el("file").addEventListener("change",async e=>{
    const input=e.currentTarget,file=input.files[0];
    if(!file)return;
    const token=++trialToken;
    el("status").textContent="Reading a private array packet…";
    try{if(file.size>3*1024*1024)throw Error("Choose a compact JSON array packet smaller than 3 MiB.");
      const encoded=JSON.parse(await file.text());if(token!==trialToken)return;
      show(api.packet(encoded,bundled.protocol_sha256),"Local trial packet");
    }catch(error){if(token===trialToken){
      input.value="";
      const message=error instanceof SyntaxError?"The selected packet is not valid JSON.":error.message;
      el("status").textContent=message+(trial?" Still showing the previous trial.":"");
    }}
  });
  function useFit(next,label,exactBytes) {
    if (trial) api.forecast(next,api.features(trial,Number(cutoff.value)));
    fit=next;modelLabel=label;bands.setFit(next,exactBytes);el("fit-status").textContent=label+".";el("reset-model").disabled=fit===bundled;
    reveal.checked=false;clearScore();if(trial){el("status").textContent=source+" · 320 electrode channels · 592 cutoffs.";render();}
    else el("status").textContent="Choose a local packet or try an invented pinch.";
  }
  el("model-file").addEventListener("change",async e=>{
    const input=e.currentTarget,file=input.files[0];if(!file)return;const token=++modelToken;
    el("reset-model").disabled=false;
    el("fit-status").textContent="Checking the local model…";
    try{
      if(file.size>128*1024)throw Error("Choose a model under 128 KiB.");
      const exactBytes = await file.arrayBuffer();
      const item = JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(exactBytes));
      if(token!==modelToken)return;
      const loaded=api.checkFit(item,bundled.protocol_sha256);
      for (const key of ["population_sha256", "baseline_sha256", "baseline_protocol_sha256"]) {
        if (loaded[key]!==bundled[key]) throw Error("Choose weights built with this version of the reader tools.");
      }
      useFit(loaded,"Local model · "+modelOrigins[loaded.fit_origin]+" (from the file label)",exactBytes);
    }catch(error){if(token===modelToken){
      input.value="";
      el("fit-status").textContent="Could not load model. Active model: "+modelLabel+". "+error.message;
      el("reset-model").disabled=fit===bundled;
    }}
  });
  el("reset-model").addEventListener("click",()=>{
    modelToken++;
    el("model-file").value="";
    try { useFit(bundled,bundledLabel,bands.bundledFitBytes(bundled)); }
    catch (error) { el("fit-status").textContent=error.message; }
  });
  scoreButton.addEventListener("click",async()=>{
    if(!trial)return;
    if(scoring){clearScore();el("score-status").textContent="Scoring cancelled.";return;}
    clearScore();
    const token=++scoreToken;
    scoring=true;
    scoreButton.textContent="Cancel scoring";
    el("score-status").textContent="Scoring 592 matched cutoffs…";
    try {
      const result = await bands.score(() => token === scoreToken);
      if (!result || token !== scoreToken) return;
      rows(el("score-table").tBodies[0], result.predictions.map(([key, mae, rmse]) =>
        [api.labels[key], prediction(mae), prediction(rmse)]));
      el("score-table").hidden = false;
      const total = globalThis.PinchIntervals.nIssues;
      rows(el("band-score-table").tBodies[0], result.bands.map(item => [
        api.labels[item.model], bands.schemeLabel[item.scheme],
        (100 * item.covered / total).toFixed(1) + "% (" + item.covered + "/" + total + ")",
        item.below + " / " + item.above, prediction(item.width), prediction(item.penalty), prediction(item.score)
      ]));
      el("interval-scores").hidden = result.bands.length === 0;
      el("score-status").textContent = source + " · " + total + " matched cutoffs." +
        (result.bandError ? " " + result.bandError : result.bands.length ? "" : " Point forecasts only.");
    }catch(error){if(token===scoreToken)el("score-status").textContent=error.message;}
    finally{if(token===scoreToken){scoring=false;scoreButton.textContent="Score this trial";}}
  });
  try{
    api.channelLocations(maps);
    api.checkFit(bundled);bands.setFit(bundled,bands.bundledFitBytes(bundled));for(const [i,g] of maps.entries()){const option=document.createElement("option");option.value=String(i);option.textContent="Grid "+g.grid_id+" · "+g.site_right_forearm;gridSelect.append(option);}
    el("example").disabled=false;el("file").disabled=false;el("model-file").disabled=false;el("fit-status").textContent=bundledLabel+".";
    el("status").textContent="Choose a local packet or try an invented pinch.";
  }catch(error){el("status").textContent="The reader could not open its bundled fits and electrode map. Extract the complete download.";}
})();
