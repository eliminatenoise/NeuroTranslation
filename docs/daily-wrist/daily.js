"use strict";

(() => {
  const el = id => document.getElementById(id);
  const engine = globalThis.UJIEngine;
  const tasks = [
    "Put a coin in a purse","Open and close a zip","Take a coin out of a purse","Move two wooden cubes","Move an iron",
    "Turn a screw","Thread a nut onto a bolt","Turn a key in a lock","Turn a door handle","Tie a shoelace",
    "Unscrew two lids","Fasten two buttons","Wrap a bandage","Cut clay using a knife and fork","Use a spoon",
    "Write with a pen","Fold paper and put it in an envelope","Clip the envelope flap","Type on a keypad","Pick up and replace a telephone",
    "Pour from a carton into a jug","Pour from a jug into a cup","Pour from a cup into a jug","Put toothpaste on a brush","Spray a tabletop","Wipe a table"
  ];
  const status=el("file-status"), file=el("window-file"), clear=el("clear");
  const example=el("example"),task=el("task"),elapsed=el("elapsed"),gain=el("gain"),spot=el("spot");
  const results=el("results"),canvas=el("activity");
  let current=null, readNumber=0;

  function say(state,message) {
    status.dataset.state=state;status.textContent=message;
  }
  function erase() {
    current=null;results.hidden=true;
    for (const cell of el("predictions").querySelectorAll("td")) {
      cell.textContent=""; delete cell.dataset.value;
    }
    el("amplitudes").replaceChildren();
    el("result-note").textContent="Choose an invented input or open a compatible file.";
  }

  function readCellData() {
    const channel=Number(spot.value);
    const fragment=document.createDocumentFragment();
    current.bins.forEach((bin,i)=>{
      const tr=document.createElement("tr"),th=document.createElement("th"),td=document.createElement("td");
      th.scope="row";th.textContent=(31.25*(16-i)).toFixed(2)+" to "+(31.25*(15-i)).toFixed(2);
      td.textContent=Number(bin[channel].toPrecision(7)).toString();td.dataset.value=String(bin[channel]);
      tr.append(th,td);fragment.append(tr);
    });
    el("input-caption").textContent="Spot "+(channel+1)+" · source-scale muscle amplitude";
    el("amplitudes").replaceChildren(fragment);
  }

  function paint() {
    if (!current || results.hidden) return;
    const width=canvas.clientWidth, height=canvas.clientHeight;
    if(!width || !height) return;
    const ctx=canvas.getContext("2d");
    if(!ctx){canvas.hidden=true;el("amplitudes").closest("details").open=true;return;}
    const ratio=Math.min(window.devicePixelRatio||1,3);
    canvas.width=Math.round(width*ratio); canvas.height=Math.round(height*ratio);
    ctx.setTransform(ratio,0,0,ratio,0,0); ctx.font="12px system-ui,sans-serif";
    const left=45,right=width-15,top=9,bottom=height-48,stepX=(right-left)/16,stepY=(bottom-top)/7;
    const maximum=current.displayMax || 1;
    current.bins.forEach((bin,i)=>bin.forEach((val,j)=>{
      const a=Math.min(1,val/maximum);
      ctx.fillStyle="rgb("+Math.round(238-224*a)+","+Math.round(245-148*a)+","+Math.round(241-125*a)+")";
      ctx.fillRect(left+i*stepX,top+j*stepY,Math.max(1,stepX-1),Math.max(1,stepY-1));
    }));
    ctx.fillStyle="#344e54";ctx.textAlign="right";
    for(let j=0;j<7;j++)ctx.fillText("Spot "+(j+1),left-5,top+(j+.5)*stepY+4);
    ctx.textAlign="center";
    [0,4,8,12,16].forEach(i=>ctx.fillText(String((16-i)*31.25),left+i*stepX,bottom+16));
    ctx.fillText("Milliseconds before the input cutoff",(left+right)/2,bottom+35);
  }

  function present(input,origin,displayMax) {
    const prepared=engine.prepare(input);
    let out;
    if(globalThis.UJIAxisBlend){
      try { out=UJIAxisBlend.infer(input); }
      catch { /* A mismatched optional adapter must not suppress valid base estimates. */ }
    }
    if(!out) out=engine.infer(input);
    const baseline=out.predictions.task_time,paired=out.predictions.task_time_emg;
    const axes=["extension_deg","radial_deviation_deg"];
    const values=[axes.map(k=>baseline[k]),axes.map(k=>paired[k]),axes.map(k=>paired[k]-baseline[k])];
    const rows=el("predictions").tBodies[0].rows;
    values.forEach((pair,i)=>pair.forEach((v,j)=>{
      const cell=rows[i].cells[j+1];
      cell.textContent=(i===2 && v>0?"+":"")+v.toFixed(2)+"°";cell.dataset.value=String(v);
    }));
    const blend=out.predictions.axis_blend;
    rows[3].hidden=!blend;
    el("blend-note").hidden=false;
    if(blend){
      axes.forEach((k,j)=>{const c=rows[3].cells[j+1];c.textContent=blend[k].toFixed(2)+"°";c.dataset.value=String(blend[k]);});
      const weights=out.emg_blend_weight_by_axis;
      el("blend-note").textContent="The weighted combination keeps "+(weights.extension_deg*100).toFixed(2)+"% of the EMG change for flexion–extension and "+(weights.radial_deviation_deg*100).toFixed(2)+"% for radial–ulnar deviation. These fractions were learned from predictions made with each training participant left out.";
    }else el("blend-note").textContent="The weighted combination is unavailable. The two fitted input models are shown.";
    const bins=prepared.rms_bins;
    const peak=Math.max(...bins.flat());
    current={bins,displayMax:displayMax??peak};
    const activity=tasks[input.task_id-1];
    el("result-note").textContent=origin+" · "+activity+". Last input "+Number(input.elapsed_anchor_s.toPrecision(6))+" s after the segment began"+
      (input.elapsed_anchor_s>30?". The model’s elapsed-time input is capped at 30 s.":".");
    el("signal-note").textContent="Each row is an electrode and each column spans 31.25 ms. Darker cells indicate greater root mean square (RMS) amplitude. The colour scale runs from zero to "+Number(current.displayMax.toPrecision(5))+" in source units.";
    canvas.setAttribute("aria-label","RMS amplitude at seven electrode spots in sixteen time bins. Peak "+Number(peak.toPrecision(5))+" on the source scale. Numerical values below.");
    results.hidden=false;readCellData();paint();
  }

  function renderExample() {
    erase();
    el("gain-readout").value=gain.value+"%";
    const t=elapsed.valueAsNumber;
    if (!Number.isFinite(t)||!elapsed.validity.valid) {
      say("error","Enter an elapsed input time from 0.5 to 30 seconds for this example.");return;
    }
    try {
      const input=engine.syntheticExample(example.value);
      input.task_id=Number(task.value);
      input.elapsed_anchor_s=t;
      const fullScale=Math.max(...input.rms_bins.flat())*2;
      const g=gain.valueAsNumber/100;
      input.rms_bins=input.rms_bins.map(bin=>bin.map(v=>v*g));
      present(input,"Invented window",fullScale);
      say("example","The example uses invented muscle values with the released, fitted models.");
    }catch{erase();say("error","This example could not be evaluated. The study results and desktop models are available below.");}
  }

  function resetExample(which) {
    readNumber++;
    file.value="";clear.hidden=true;el("synthetic-controls").disabled=false;
    const input=engine.syntheticExample(which);
    example.value=which;task.value=String(input.task_id);elapsed.value=String(input.elapsed_anchor_s);
    gain.value="100";renderExample();
  }

  function parseWindow(text) {
    const data=JSON.parse(text);
    // A repeated name could otherwise hide an earlier value of a task, clock or channel.
    const stack=[];
    for(const m of text.matchAll(/"(?:\\[\s\S]|[^"\\])*"|[{}\[\]]/g)){
      const token=m[0];
      if(token==="{")stack.push(new Set());
      else if(token==="[")stack.push(null);
      else if(token==="}"||token==="]")stack.pop();
      else {
        let end=m.index+token.length;
        while(end<text.length && /[ \n\t\r]/.test(text[end]))end++;
        if(text[end]!==":")continue;
        const key=JSON.parse(token),keys=stack.at(-1);
        if(keys.has(key))throw new Error("Repeated JSON field.");
        keys.add(key);
      }
    }
    return data;
  }

  tasks.forEach((name,i)=>task.add(new Option((i+1)+". "+name,String(i+1))));
  for(let k=0;k<7;k++)spot.add(new Option("Spot "+(k+1),String(k)));
  if(!engine) {say("error","The fitted model could not be loaded. You can read the results and use the desktop runner below.");return;}
  file.disabled=false;
  example.addEventListener("change",()=>resetExample(example.value));
  task.addEventListener("change",renderExample);
  elapsed.addEventListener("input",renderExample);gain.addEventListener("input",renderExample);
  spot.addEventListener("change",()=>{if(current)readCellData();});
  clear.addEventListener("click",()=>{resetExample("patterned");example.focus();});
  file.addEventListener("change",async()=>{
    const id=++readNumber,f=file.files[0];
    erase();
    if(!f){resetExample("patterned");return;}
    clear.hidden=false;el("synthetic-controls").disabled=true;
    if (!f.size||f.size>256*1024){say("error","Select a nonempty JSON window of 256 KiB or less.");file.value="";return;}
    say("reading","Reading the window on this device…");
    try {
      const windowData=parseWindow(await f.text());
      if(id!==readNumber)return;
      present(windowData,"User-supplied window");
      say("file","Read locally. The task, clock and amplitude convention come from the selected file.");
    }catch(e){
      if(id!==readNumber)return;
      erase();file.value="";
      const detail=e instanceof SyntaxError ? "The JSON syntax is invalid." : e instanceof Error ? e.message : "Invalid window.";
      say("error","Could not evaluate this window. "+detail.slice(0,220));
    }
  });
  if(window.ResizeObserver)new ResizeObserver(paint).observe(canvas);else window.addEventListener("resize",paint);
  resetExample("patterned");
})();
