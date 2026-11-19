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
  let matImport=null;
  const mat=globalThis.CemhseyMat;
  const example=el("example"), packetFile=el("file"), matFile=el("mat-file"), matConfirm=el("mat-confirm");
  const importProgress=el("import-progress"), progressBar=el("mat-progress"), cancelImport=el("cancel-trial");
  const saveTrial=el("save-trial"), status=el("status");
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
      el("later").textContent=reveal.checked?(source==="Invented pinch"?"Later invented force ":"Later normalized force in this trial ")+prediction(trial.force[row.tick+24]):"";
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
  function show(record,name,fromMat=false){
    api.forecast(fit,api.features(record,160));
    trial=record;source=name;cutoff.value="160";bands.setTrial(record,name==="Invented pinch");lockedScale=null;lock.checked=false;reveal.checked=false;gridIndex=0;selected=0;gridSelect.value="0";createGrids();clearScore();
    saveTrial.hidden=!fromMat;
    el("trial").hidden=false;el("values").open=false;el("status").textContent=name+" · 320 electrode channels · 592 cutoffs.";render();
  }
  function dismissImport(restoreFocus=false){
    const hadFocus=document.activeElement===cancelImport;
    importProgress.hidden=true;
    progressBar.removeAttribute("value");
    if(restoreFocus && hadFocus)matFile.focus();
  }
  function supersedeImport(){
    trialToken++;
    if(matImport){
      matImport.cancel();
      matImport=null;
    }
    dismissImport();
    return trialToken;
  }
  function reportImport(message){
    status.textContent=message+(trial?" Still showing the previous trial.":"");
  }
  function trialSource(name){
    const archiveStyle=/^s(.*?)_day([^_]*)_session([^_]*)_task([^_]*)_trial([^_]*)\.mat$/i.exec(name);
    if(archiveStyle){
      const fields=archiveStyle.slice(1);
      const decimal=fields.map(label=>label.replace(/^0+/,""));
      if(decimal.some(label=>!/^[1-9]\d*$/.test(label))){
        throw Error("Archive-style names need positive whole numbers for participant, day, session, task and repeat.");
      }
      const participant=decimal[0];
      const [day,session,task,repeat]=decimal.slice(1).map(Number);
      if(day>11 || session!==5 || task!==2 || (repeat!==1 && repeat!==2)){
        throw Error("The archive-style name is outside Session 5, Task 2, days 1 to 11 and repeats 1 or 2. Check the source and choose a compatible trial.");
      }
      if(participant.length>2 || Number(participant)>13){
        return "Local MATLAB trial · participant label is outside the archive roster · task confirmed by you";
      }
      if(fields.every((label,index)=>label===decimal[index])){
        return "Local MATLAB trial · archive name matches Session 5, Task 2";
      }
    }
    const namedTask=/(?:^|[_-])session(\d+)[_-]task(\d+)(?=[_.-]|$)/i.exec(name);
    if(namedTask && (Number(namedTask[1])!==5 || Number(namedTask[2])!==2)){
      throw Error("The filename names a different session or task. Check the source and choose a Session 5, Task 2 trial.");
    }
    return "Local MATLAB trial · source task confirmed by you";
  }
  gridSelect.addEventListener("change",()=>{gridIndex=Number(gridSelect.value);createGrids();renderCells();});
  lock.addEventListener("change",()=>{if(!row)return;lockedScale=lock.checked?Math.max(row.older.max,row.recent.max):null;renderCells();});
  el("values").addEventListener("toggle",renderCells);
  cutoff.addEventListener("input",()=>{reveal.checked=false;clearScore();render();});
  reveal.addEventListener("change",render);
  example.addEventListener("click",()=>{
    supersedeImport();
    packetFile.value="";
    try { show(api.example(maps),"Invented pinch"); }
    catch (error) { el("status").textContent=error.message; }
  });
  packetFile.addEventListener("change",async e=>{
    const input=e.currentTarget,file=input.files[0];
    if(!file)return;
    const token=supersedeImport();
    status.textContent="Reading a private array packet…";
    try{if(file.size>3*1024*1024)throw Error("Choose a compact JSON array packet smaller than 3 MiB.");
      const encoded=JSON.parse(await file.text());if(token!==trialToken)return;
      show(api.packet(encoded,bundled.protocol_sha256),"Local trial packet");
    }catch(error){if(token===trialToken){
      input.value="";
      const message=error instanceof SyntaxError?"The selected packet is not valid JSON.":error.message;
      reportImport(message);
    }}
  });
  matConfirm.addEventListener("change",()=>{
    matFile.disabled=!matConfirm.checked;
    if(!matConfirm.checked && matImport){
      supersedeImport();
      reportImport("MATLAB import cancelled.");
    }
  });
  matFile.addEventListener("change",async()=>{
    const file=matFile.files[0];
    matFile.value="";
    if(!file || !matConfirm.checked)return;
    const token=supersedeImport();
    let phase;
    try{
      if(!/\.mat$/i.test(file.name))throw Error("Choose an original MATLAB file ending in .mat.");
      const sourceName=trialSource(file.name);
      importProgress.hidden=false;
      status.textContent="Reading the original MATLAB file…";
      matImport=mat.start(file,{onProgress:({phase:next,fraction})=>{
        if(token!==trialToken)return;
        if(next!==phase){
          phase=next;
          status.textContent=next==="reading"?"Reading the original MATLAB file…":"Calculating electrode summaries…";
        }
        if(Number.isFinite(fraction)){
          progressBar.max=1;
          progressBar.value=Math.max(0,Math.min(1,fraction));
        }else progressBar.removeAttribute("value");
      }});
      const record=await matImport.promise;
      if(token!==trialToken)return;
      show(record,sourceName,true);
    }catch(error){
      if(token===trialToken)reportImport(error.message);
    }finally{
      if(token===trialToken){
        matImport=null;
        dismissImport(true);
      }
    }
  });
  cancelImport.addEventListener("click",()=>{
    supersedeImport();
    matFile.focus();
    reportImport("MATLAB import cancelled.");
  });
  window.addEventListener("pagehide",()=>{
    if(!matImport)return;
    supersedeImport();
    reportImport("MATLAB import cancelled.");
  });
  saveTrial.addEventListener("click",()=>{
    try{
      const file=new Blob([JSON.stringify(mat.packet(trial))+"\n"],{type:"application/json"});
      const url=URL.createObjectURL(file);
      const link=document.createElement("a");
      link.href=url;
      link.download="cemhsey-array-trial.json";
      document.body.append(link);
      try{link.click();}
      finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    }catch{
      status.textContent="The browser could not save this array packet.";
    }
  });
  function useFit(next,label,exactBytes) {
    bands.validateTraining(next);
    if (trial) api.forecast(next,api.features(trial,Number(cutoff.value)));
    fit=next;modelLabel=label;bands.setFit(next,exactBytes);el("fit-status").textContent=label+".";el("reset-model").disabled=fit===bundled;
    reveal.checked=false;clearScore();if(trial)render();
  }
  function useLocalFit(exactBytes) {
    if(exactBytes.byteLength>128*1024)throw Error("Choose a model under 128 KiB.");
    const item=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(exactBytes));
    const loaded=api.checkFit(item,bundled.protocol_sha256);
    for(const key of ["population_sha256","baseline_sha256","baseline_protocol_sha256"]){
      if(loaded[key]!==bundled[key])throw Error("Choose weights built with this version of the reader tools.");
    }
    useFit(loaded,"Local model · "+modelOrigins[loaded.fit_origin]+" (from the model record)",exactBytes);
  }
  el("model-file").addEventListener("change",async e=>{
    const input=e.currentTarget,file=input.files[0];if(!file)return;const token=++modelToken;
    el("reset-model").disabled=false;
    el("fit-status").textContent="Checking the local model…";
    try{
      if(file.size>128*1024)throw Error("Choose a model under 128 KiB.");
      const exactBytes = await file.arrayBuffer();
      if(token!==modelToken)return;
      useLocalFit(exactBytes);
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
  function setupFitter() {
    const fitter=globalThis.CemhseyBrowserFit;
    if(typeof fitter?.mount!=="function")return;
    const disclosure=el("fit-local");
    const openFromLink=()=>{if(location.hash==="#fit-local")disclosure.open=true;};
    const mount=()=>{
      if(!disclosure.open)return;
      disclosure.removeEventListener("toggle",mount);
      fitter.mount(el("embedded-fit"),{onApply:exactBytes=>{
        useLocalFit(exactBytes);
        modelToken++;
        el("model-file").value="";
      }});
    };
    disclosure.addEventListener("toggle",mount);
    window.addEventListener("hashchange",openFromLink);
    openFromLink();
    mount();
  }
  scoreButton.addEventListener("click",async()=>{
    if(!trial)return;
    if(scoring){clearScore();el("score-status").textContent="Scoring cancelled.";return;}
    const overlap=bands.trainingOverlap();
    if(overlap==="checking"){
      el("score-status").textContent="Wait for the fitting packet check, then score this trial.";
      return;
    }
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
      const fitScope=overlap==="matched"?" Fitting recording (in-sample).":
        overlap==="unknown"||overlap==="unavailable"?" Training overlap is unknown.":"";
      el("score-status").textContent = source + " · " + total + " matched cutoffs." + fitScope +
        (result.bandError ? " " + result.bandError : result.bands.length ? "" : " Point forecasts only.");
    }catch(error){if(token===scoreToken)el("score-status").textContent=error.message;}
    finally{if(token===scoreToken){scoring=false;scoreButton.textContent="Score this trial";}}
  });
  try{
    api.channelLocations(maps);
    api.checkFit(bundled);bands.setFit(bundled,bands.bundledFitBytes(bundled));for(const [i,g] of maps.entries()){const option=document.createElement("option");option.value=String(i);option.textContent="Grid "+g.grid_id+" · "+g.site_right_forearm;gridSelect.append(option);}
    example.disabled=false;packetFile.disabled=false;el("model-file").disabled=false;el("fit-status").textContent=bundledLabel+".";
    matConfirm.disabled=!mat;
    matFile.disabled=!mat || !matConfirm.checked;
    status.textContent=mat?"Choose a local trial or try an invented pinch.":"To read MATLAB files, reopen the complete reader. JSON packets and the invented pinch are available.";
  }catch(error){el("status").textContent="The reader could not open its bundled fits and electrode map. Extract the complete download.";}
  setupFitter();
})();
