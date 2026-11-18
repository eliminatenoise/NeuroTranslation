"use strict";

(() => {
  const byId = id => document.getElementById(id);
  const example = byId("example"), input = byId("archive"), status = byId("source-status");
  const block = byId("block"), trial = byId("trial");
  const axis = byId("axis"), quantity = byId("quantity"), clear = byId("clear");
  const canvas = byId("plot"), model = globalThis.WristForearmModel;
  const errorOption = quantity.querySelector('[value="error"]');
  const methods = ["frozen_motion", "motion_correction", "motion_emg_correction"];
  const colors = ["#68726f","#a14928","#006b80","#262e3d"];
  let current = null;
  let worker = null, workerURL = null, request = 0, hasOpened = false;

  function note(state, text) {
    status.dataset.state = state;
    status.textContent = text;
  }

  function stopWorker() {
    request++;
    hasOpened = false;
    if (worker) worker.terminate();
    worker = null;
    if (workerURL) URL.revokeObjectURL(workerURL);
    workerURL = null;
  }

  function setTrialControls(active) {
    byId("trial-controls").hidden = !active;
    block.disabled = trial.disabled = !active;
  }

  function showWaiting(title, text) {
    current = null;
    byId("figure-title").textContent = title;
    byId("figure-note").textContent = text;
    byId("values").replaceChildren();
    byId("results").hidden = byId("plot-controls").hidden = byId("jump").hidden = true;
  }

  function dataPoints() {
    const dim = axis.value === "extension" ? 0 : 1;
    const error = current.measured && quantity.value === "error";
    return current.rows.map((row,i) => {
      const values = methods.map(method => error ? row[method][dim] - current.measured[i][dim] : row[method][dim]);
      if (current.measured && !error) values.push(current.measured[i][dim]);
      return {seconds:row.target_offset_seconds, values};
    });
  }

  function paint() {
    if (!current || canvas.hidden) return;
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      canvas.hidden = true;
      byId("details").open = true;
      return;
    }
    const ratio = Math.min(devicePixelRatio || 1, 3);
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    ctx.setTransform(ratio,0,0,ratio,0,0);
    const points = dataPoints();
    const vals = points.flatMap(p => p.values);
    const min = Math.min(...vals,0), max = Math.max(...vals,0);
    const rough = (max-min || 1)/4, scale = 10 ** Math.floor(Math.log10(rough));
    const step = [1,2,2.5,5,10].find(v => v * scale >= rough) * scale;
    const bottom = Math.floor(min/step)*step, top = Math.max(bottom+step, Math.ceil(max/step)*step);
    const left=43, right=width-18, upper=27, lower=height-45;
    const x=i => left+i*(right-left)/5, y=v => lower-(v-bottom)/(top-bottom)*(lower-upper);
    ctx.font = '12px system-ui,sans-serif';
    ctx.fillStyle="#354e55"; ctx.textAlign="left";
    ctx.fillText(quantity.value==="error" ? "Forecast − measured angle (°)" : "Wrist angle (°)",1,14);
    for(let n=0;n<=Math.round((top-bottom)/step);n++) {
      const v=bottom+n*step, pos=y(v);
      ctx.strokeStyle=Math.abs(v)<1e-10 ? "#8b9c96" : "#d8e1dd"; ctx.lineWidth=1;
      ctx.beginPath(); ctx.moveTo(left,pos); ctx.lineTo(right,pos); ctx.stroke();
      ctx.textAlign="right"; ctx.fillText(String(Number(v.toFixed(3))),left-6,pos+4);
    }
    ctx.textAlign="center";
    points.forEach((p,i) => ctx.fillText(p.seconds.toFixed(2),x(i),lower+17));
    ctx.fillText("Time after cue (s)",(left+right)/2,height-5);
    for (let s=0;s<points[0].values.length;s++) {
      ctx.strokeStyle=ctx.fillStyle=colors[s];ctx.lineWidth=1.7;
      const radius=[6.2,4.6,3.4,2.8][s];
      points.forEach((p,i) => {
        const px=x(i), py=y(p.values[s]); ctx.beginPath();
        if (s===0 || s===2) {ctx.arc(px,py,radius,0,2*Math.PI); if(s===0)ctx.stroke();else ctx.fill();}
        else if(s===1) ctx.strokeRect(px-radius,py-radius,2*radius,2*radius);
        else {ctx.moveTo(px,py-4);ctx.lineTo(px+4,py);ctx.lineTo(px,py+4);ctx.lineTo(px-4,py);ctx.closePath();ctx.fill();}
      });
    }
  }

  function render() {
    if (!current) return;
    const isReal = current.measured !== null;
    errorOption.disabled = !isReal;
    if (!isReal) quantity.value="angle";
    const error = quantity.value==="error";
    const showMeasurement = isReal && !error;
    byId("figure-title").textContent = current.title;
    byId("figure-note").textContent = isReal
      ? (error ? "Zero means the forecast landed on the measured angle. Positive errors lie towards extension or the thumb on the selected axis." : "Each diamond is an angle the encoder measured. The other marks show what the three models forecast from earlier readings.")
      : "These six windows contain invented wrist and muscle inputs. The points are model forecasts. This example has no measured target angles.";
    byId("measured-key").hidden = byId("measured-head").hidden = !showMeasurement;
    byId("plot-controls").hidden = byId("results").hidden = false;
    byId("jump").hidden = !isReal;
    const axisName = axis.value==="extension" ? "flexion and extension" : "radial and ulnar deviation";
    byId("caption").textContent = (error ? "Forecast minus measured angle" : "Angle") + " in degrees, " + axisName + ". Positive angles point towards " + (axis.value==="extension"?"extension.":"the thumb.");
    canvas.setAttribute("aria-label",byId("caption").textContent + " Six time points, with exact values in the table.");
    const nodes=document.createDocumentFragment();
    for(const p of dataPoints()) {
      const tr=document.createElement("tr"), th=document.createElement("th");
      th.scope="row";th.textContent=p.seconds.toFixed(2)+" s";tr.append(th);
      for(const v of p.values){const td=document.createElement("td");td.textContent=v.toFixed(3)+"°";td.dataset.value=String(v);tr.append(td);}
      nodes.append(tr);
    }
    byId("values").replaceChildren(nodes);
    paint();
  }

  function discard() {
    stopWorker();
    input.value=""; clear.hidden=true; setTrialControls(false);
  }

  function showExample(index) {
    discard();
    example.value=String(index);
    const batch=model.syntheticCases().slice(6*index,6*index+6);
    current={title:"Invented window set "+(index+1), rows:model.predictTrial(batch.map(c=>c.input)), measured:null};
    render();
    if (status.dataset.state !== "unavailable") {
      note("ready", "Showing invented inputs. To compare against measured angles, choose an original development ZIP.");
    }
  }

  function failArchive(message) {
    discard();
    example.value="none";
    showWaiting("Choose an input", "Select an invented example or open an original development recording.");
    note("error",message);
    if(!input.disabled)input.focus();
  }

  function readSelection() {
    if(!worker || !hasOpened) return;
    const id=++request, b=Number(block.value), t=Number(trial.value);
    showWaiting("Reading the selected trial", "Preparing the earlier wrist and forearm measurements…");
    note("reading", "Reading block "+b+", trial "+t+" on this device…");
    worker.postMessage({type:"read",id,block:b,trial:t});
  }

  function openFile(file) {
    stopWorker();
    setTrialControls(false);
    example.value="none"; clear.hidden=false;
    showWaiting("Checking the recording", "The archive is verified locally before the selected trial is read.");
    if (!file || ![38005702,40419910,39692667].includes(file.size)) {
      failArchive("This file does not match a development ZIP used by the study. Choose an original, unmodified ZIP."); return;
    }
    note("opening","Checking the original archive fingerprint…");
    try {
      workerURL=URL.createObjectURL(new Blob([globalThis.WristArchiveWorkerSource],{type:"text/javascript"}));
      const job = new Worker(workerURL);
      worker=job;
      job.onerror=() => {
        if(worker===job)failArchive("The recording reader stopped. Reopen the ZIP or use the downloadable desktop runner.");
      };
      job.onmessage=({data})=>{
        if(worker!==job) return;
        if(data.type==="opened") {
          hasOpened=true; block.value=trial.value="1"; setTrialControls(true);readSelection();return;
        }
        if(data.type==="open-error") {
          failArchive("The archive could not be verified as an original development file. Choose an unmodified ZIP from the study.");return;
        }
        if(data.id!==request) return;
        if(data.type==="read-error") {
          failArchive("This trial could not be verified from the recording. Reopen the original ZIP to try again.");return;
        }
        if(data.type==="result") {
          try {
            const {windows,measured}=data.trial;
            const label="Block "+block.value+" · Trial "+trial.value;
            const rows=model.predictTrial(windows);
            if (!Array.isArray(measured) || measured.length!==rows.length || measured.some(pair=>!Array.isArray(pair)||pair.length!==2||!pair.every(Number.isFinite))) throw new Error("Invalid targets");
            current={title:label,rows,measured};
            render();note("verified","Original archive verified. Showing the six targets for "+label.toLowerCase()+".");
          } catch {
            failArchive("The fitted model could not evaluate this trial. Open the original ZIP again or use the desktop runner.");
          }
        }
      };
      job.postMessage({type:"open",file});
    } catch {
      failArchive("A local background reader is unavailable in this browser. Use the desktop runner for recordings.");
    }
  }

  function populate(select,max) {
    for(let n=1;n<=max;n++)select.add(new Option(String(n),String(n)));
  }
  populate(block,8); populate(trial,40);
  if (!model) {
    note("error","The fitted models could not be loaded. The study results and desktop runner are available below.");
    return;
  }
  example.disabled=false;
  example.addEventListener("change",()=>showExample(Number(example.value)));
  block.addEventListener("change",readSelection);trial.addEventListener("change",readSelection);
  for(const control of [axis,quantity])control.addEventListener("change",render);
  clear.addEventListener("click",()=>{showExample(0);note("ready","Recording cleared. Showing invented window set 1.");input.focus();});
  input.addEventListener("change",()=>{if(input.files[0])openFile(input.files[0]);else showExample(0);});
  if(window.ResizeObserver)new ResizeObserver(paint).observe(canvas);
  else window.addEventListener("resize",paint);
  showExample(0);
  let rawInflate = false;
  try { new DecompressionStream("deflate-raw"); rawInflate = true; } catch { /* Use the desktop reader on older browsers. */ }
  const supported = typeof Worker==="function" && typeof globalThis.WristArchiveWorkerSource==="string" && globalThis.crypto?.subtle && rawInflate;
  if(supported) input.disabled=false;
  else note("unavailable","Invented inputs are available. This browser cannot open the original ZIP locally; use the desktop runner below.");
})();
