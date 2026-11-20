document.addEventListener("DOMContentLoaded", () => {
  "use strict";
  // Capture the unmodified public page before running examples or accepting reader input.
  const save = document.querySelector(".save");
  if (!document.querySelector("script[src]")) {
    const original = "<!doctype html>\n" + document.documentElement.outerHTML;
    save.href = URL.createObjectURL(new Blob([original], {type:"text/html;charset=utf-8"}));
  }
  let data;
  const byId = id => document.getElementById(id);
  const picker = byId("history-select");
  const source = byId("source-select");
  const drafts = new Map();
  const angleModes = [
    {id:"motion", width:2, label:"Movement only"},
    {id:"emg", width:6, label:"Movement + forearm EMG"},
    {id:"full", width:14, label:"Movement + forearm EMG + scalp EEG"}
  ];
  let revision = 0;
  let model;
  let practice = false;

  function element(tag, content, className) {
    const node = document.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (className) node.className = className;
    return node;
  }

  function format(value, places = 2) {
    if (Math.abs(value) >= 1e6) return value.toExponential(2);
    return value.toLocaleString("en", {useGrouping:false, minimumFractionDigits:places, maximumFractionDigits:places});
  }

  function studyTable() {
    const angleTable = byId("angle-bench").tBodies[0];
    for (const [key, label] of [
      ...angleModes.map(({id,label}) => ["pretrained."+id, label]),
      ["corrected.motion","Shared movement forecast + motion-only correction"],
      ["corrected.emg","Shared movement forecast + motion and forearm correction"],
      ["prior_motion_cnn","Wrist-specific convolutional network"],
      ["prior_emg_corrected_cnn","Wrist-specific network + forearm correction"],
      ["persistence","Repeat the cutoff angles"]
    ]) {
      const row = angleTable.insertRow();
      const th = element("th",label); th.scope = "row"; row.append(th);
      row.insertCell().textContent = format(data.angleScores[key],3);
    }
    const body = byId("bench").tBodies[0];
    for (const [key, title] of [
      ["joint", "Shared Transformer"], ["recent", "Keep the latest speed"],
      ["still", "Predict zero movement"], ["ridge_log", "Domain-only linear fit on log distance"],
      ["ridge_cm", "Domain-only linear fit on distance"], ["solo32", "One-domain Transformer · matched exposure"],
      ["solo64", "One-domain Transformer · matched batch size"]
    ]) {
      const tr = body.insertRow();
      const th = element("th",title);
      th.scope = "row";
      tr.append(th);
      for (const domain of ["wrist", "rat"]) tr.insertCell().textContent = format(data.aggregate[domain][key], 3);
    }
    const interval = (domain, arm) => data.aggregate[domain].intervals[arm]
      .map(value => (value > 0 ? "+" : "") + format(value, 3)).join(" to ");
    byId("intervals-report").textContent =
      "Against the matched-exposure Transformer, the paired intervals for shared minus single-domain error crossed zero in both cases. The wrist interval was " +
      interval("wrist","solo32") + " cm and the rat interval was " + interval("rat","solo32") +
      " cm. Against the matched-batch Transformer, the intervals were " + interval("wrist","solo64") +
      " cm and " + interval("rat","solo64") + " cm respectively.";
  }

  function meanMedianMax(values) {
    const sorted = values.slice().sort((a,b) => a-b);
    return [values.reduce((sum,v) => sum + v, 0) / 4, (sorted[1]+sorted[2])/2, sorted[3]];
  }

  function ridgeDistance(domain, intervals, recent) {
    const fit = data.ridge[domain];
    const lengths = intervals.map(row => row[0]);
    const scaled = intervals.map(row => .25 * row[0] / row[1]);
    const design = intervals.flatMap(([length, duration, age, twoStep, cosine],i) =>
      [Math.log1p(length), (duration-.25)/.05, age/.05, Math.log1p(twoStep), cosine, Math.log1p(scaled[i])]);
    design.push(...lengths, ...scaled, ...intervals.map(row => row[3]), recent, ...meanMedianMax(lengths), ...meanMedianMax(scaled));
    const logDistance = design.reduce((sum,v,i) => sum + (v-fit.mu[i])/fit.sd[i]*fit.coef[i], fit.intercept);
    const cm = Math.expm1(Math.max(0,logDistance));
    if (!Number.isFinite(cm)) throw new RangeError("The linear comparison exceeds the numerical range. Check the coordinate units.");
    return cm;
  }

  function plot(intervals, cm) {
    const node = byId("bars");
    const values = [...intervals.map(row => row[0]), cm];
    const max = Math.max(...values, Number.MIN_VALUE);
    node.replaceChildren();
    ["−0.75 s", "−0.50 s", "−0.25 s", "0 s", "+0.25 s"].forEach((end, i) => {
      const future = i === 4;
      const column = element("div", undefined, "bar-column"+(future ? " foreseen" : ""));
      column.setAttribute("aria-label", (future ? "Forecast" : "Past interval") +
        " ending at " + end + ", " + format(values[i]) + " centimetres");
      const number = element("span", format(values[i]));
      const track = element("div", undefined, "track");
      const fill = element("i", undefined, "fill");
      fill.style.height = (values[i]/max*100) + "%";
      track.append(fill);
      column.append(number, track, element("span",end));
      node.append(column);
    });
  }

  function featureTable(intervals) {
    const table = element("table");
    const caption = element("caption","Four intervals in time order. Age is the lag from the sample to its scheduled tap. The turn cosine ranges from −1 for a reversal to +1 for straight ahead.");
    table.append(caption);
    const head = table.createTHead().insertRow();
    for (const name of ["Step","Length (cm)","Time (s)","Age (s)","Two-step (cm)","Turn cosine"]) {
      const th = element("th",name); th.scope = "col"; head.append(th);
    }
    const body = table.createTBody();
    intervals.forEach((row, i) => {
      const tr = body.insertRow();
      const th = element("th",String(i+1)); th.scope = "row"; tr.append(th);
      row.forEach((v, k) => { tr.insertCell().textContent = format(v, [2,3,3,2,3][k]); });
    });
    byId("features").replaceChildren(table);
  }

  function clearResults(message) {
    revision++;
    byId("arm-results").hidden = true;
    byId("arm-values").tBodies[0].replaceChildren();
    byId("point-results").hidden = true;
    byId("point-result").textContent = "";
    byId("plate-results").hidden = true;
    byId("plate-force").textContent = "";
    byId("moment-results").hidden = true;
    for (const id of ["moment-name", "moment-right", "moment-left", "moment-timing"]) byId(id).textContent = "";
    byId("knee-results").hidden = true;
    for (const id of ["knee-name", "knee-right", "knee-left", "knee-timing"]) byId(id).textContent = "";
    byId("angular-results").hidden = true;
    byId("angle-values").tBodies[0].replaceChildren();
    byId("correction-values").tBodies[0].replaceChildren();
    byId("angle-timing").textContent = byId("angle-interpretation").textContent = "";
    byId("results").hidden = true;
    byId("joint").textContent = byId("recent").textContent = byId("ridge").textContent = "—";
    for (const id of ["joint","recent","ridge"]) delete byId(id).dataset.cm;
    byId("bars").replaceChildren();
    byId("features").replaceChildren();
    byId("measured").textContent = "";
    byId("outcome").open = false;
    byId("outcome").hidden = true;
    byId("status").textContent = message;
  }

  async function showForecast(domain, intervals, recorded, token) {
    const result = await SharedMotion.forecastMovement({domain, intervals});
    if (token !== revision) return;
    if (result.unit !== "cm" || result.domain !== domain) throw new Error("The distance model returned incompatible units.");
    const cm = result.distanceCm;
    const recent = SharedMotion.recentDistance(intervals);
    const ridge = ridgeDistance(domain, intervals, recent);
    for (const [key,value] of Object.entries({joint:cm, recent, ridge})) byId(key).dataset.cm = String(value);
    byId("joint").textContent = format(cm);
    byId("recent").textContent = format(recent) + " cm";
    byId("ridge").textContent = format(ridge) + " cm";
    byId("forecast-caption").textContent = domain === "rat"
      ? "2D tracked position on the maze. Nominal endpoint 0.25 s after cutoff."
      : "3D right-wrist position. Nominal endpoint 0.25 s after cutoff.";
    plot(intervals,cm);
    featureTable(intervals);
    byId("outcome").hidden = !recorded;
    if (recorded) {
      const rat = data.examples.rat;
      byId("measured").textContent = "The camera measured " + format(rat.measuredCm,3) +
        " cm between endpoints " + format(rat.leadS,4) + " s apart. The shared forecast missed by " +
        format(Math.abs(rat.measuredCm-cm),3) + " cm. This example helped train the model.";
    }
    byId("status").textContent = "";
    byId("results").hidden = false;
  }

  const ratHeader = ["time_s","x_cm","y_cm"];
  const wristHeader = ["time_s","grid_s","x_cm","y_cm","z_cm","active","valid","tracked"];
  const currentDomain = () => picker.value;
  const isCustom = () => source.value === "custom";

  async function compareAngles(record, token) {
    if (record?.domain !== "wrist_angle") throw new Error("Choose wrist_angle for angles in degrees.");
    const highest = angleModes.findIndex(entry => entry.id === record.mode);
    if (highest < 0) throw new Error("Choose motion, emg or full for the available measurements.");
    // Validate the source as supplied, including its exact width, clocks and allowed keys.
    // Only then form comparisons from that same admitted history.
    const complete = await SharedMotion.forecastMovement(record);
    if (token !== revision) return;
    const {forearmResidual, forearm_residual, ...window} = record;
    const requestedCorrection = forearmResidual ?? forearm_residual ?? null;
    const available = angleModes.slice(0, highest + 1);
    const direct = available.map(mode => ({mode, correction:null, table:"angle-values"}));
    const adjusted = available.filter(mode => mode.id !== "full")
      .map(mode => ({mode, correction:mode.id, table:"correction-values"}));
    const results = await Promise.all([...direct, ...adjusted].map(async forecast => {
      const {mode, correction} = forecast;
      const result = mode.id === record.mode && correction === requestedCorrection ? complete
        : await SharedMotion.forecastMovement({
          ...window, mode:mode.id, bins:record.bins.map(row => row.slice(0,mode.width)), forearmResidual:correction
        });
      if (result.unit !== "deg" || result.domain !== "wrist_angle" || result.targetTick !== complete.targetTick) {
        throw new Error("The angle model returned incompatible units or timing.");
      }
      return {...forecast, result};
    }));
    if (token !== revision) return;
    for (const {mode, table, result} of results) {
      const tr = byId(table).tBodies[0].insertRow(); tr.dataset.mode = mode.id;
      const th = element("th",mode.label); th.scope = "row"; tr.append(th);
      for (const v of result.angleDeg) {
        const cell = tr.insertCell(); cell.dataset.deg = String(v); cell.textContent = format(v);
      }
    }
    const [x,y] = record.anchorDeg;
    byId("angle-timing").textContent = "At tick " + record.cutoffTick + " the wrist was at " + format(x) + "° extension and " + format(y) +
      "° radial deviation. Each forecast uses the same 16 bins and cue slot to estimate both angles at tick " +
      complete.targetTick + ", a quarter second later (128 ticks at 512 Hz).";
    const outsideRange = results.some(({result}) => result.angleDeg.some(angle => Math.abs(angle) > 180));
    byId("angle-interpretation").textContent = (outsideRange ? "A forecast here falls outside the −180° to 180° range accepted for measured wrist angles. " : "") +
      (highest === 0 ? "Add the four measured forearm channels to compare the two corrections. " : "") +
      "This input supplies no measured future angle.";
    byId("angular-results").hidden = false;
    byId("status").textContent = isCustom() && !anglePractice ? "Forecasts from your input. Source and clock alignment are unverified." : "Forecasts from invented wrist measurements.";
  }
  let anglePractice = false;

  function parseRows(domain) {
    const wrist = domain === "wrist";
    const header = wrist ? wristHeader : ratHeader;
    const text = byId("rows").value.trim();
    if (!text) throw new Error("Enter rows of past positions or fill in the practice samples.");
    const lines = text.split(/\r?\n/).filter(line => line.trim());
    if (lines[0].split(",").map(v => v.trim()).join(",") === header.join(",")) lines.shift();
    if (lines.length < 5) throw new Error("Enter a full second of samples. Five sparse tap positions alone cannot establish continuous tracking.");
    return lines.map((line, i) => {
      const fields = line.split(",").map(v => v.trim());
      if (fields.length !== header.length || fields.some(v => !v)) throw new Error("Check the columns in data row " + (i+1) + ".");
      const values = fields.slice(0, wrist ? 5 : 3).map(Number);
      if (!values.every(Number.isFinite)) throw new Error("Enter finite times and centimetre coordinates in row " + (i+1) + ".");
      if (!wrist) return {timeS: values[0], positionCm: values.slice(1)};
      const flags = fields.slice(5);
      if (flags.some(v => v !== "0" && v !== "1")) throw new Error("Use 1 or 0 for each tracking flag in row " + (i+1) + ".");
      return {timeS:values[0], gridTimeS:values[1], positionCm:values.slice(2),
        active:flags[0]==="1", valid:flags[1]==="1", tracked:flags[2]==="1"};
    });
  }

  async function showKnees(record, token) {
    if (record?.domain !== "knee_angle") throw new Error("Use a knee_angle input for this forecast.");
    const result = await SharedMotion.forecastMovement(record);
    if (token !== revision) return;
    const options = Array.from(byId("knee-mode").options);
    byId("knee-name").textContent = options.find(option => option.value === result.mode).text;
    byId("knee-right").textContent = format(result.angleDeg[0], 3);
    byId("knee-left").textContent = format(result.angleDeg[1], 3);
    const target = BigInt(result.cutoffFrame) + BigInt(result.horizonStoredFrames);
    byId("knee-timing").textContent = "Frame " + target + ", 15 frames after the last input (0.25 s at 60 Hz). The closest earlier stride was " + result.periodFrames + " frames back.";
    byId("knee-results").hidden = false;
    byId("status").textContent = "";
  }

  function inventedPlate() {
    const record = structuredClone(data.plateExample);
    record.mode = byId("plate-mode").value;
    if (record.mode.includes("combined")) {
      const scale = Number(byId("plate-scale").value);
      record.emg_uV = record.emg_uV.map(row => row.map(value => value * scale));
    } else {
      delete record.emg_uV;
      delete record.emg_valid;
    }
    return record;
  }

  async function showPlate(record, token) {
    if (record?.domain !== "right_plate_force") throw new Error("Supply one right_plate_force input.");
    const result = await SharedMotion.forecastMovement(record);
    if (token !== revision) return;
    const force = result.right_vertical_plate_force_N;
    byId("plate-force").textContent = format(force, 2);
    byId("plate-timing").textContent = "Frame " + (result.offset_frames + result.lead_frames) +
      " after right-foot strike. The history ends at frame " + result.offset_frames +
      ", 0.10 s before the target on the stored 100 Hz clock.";
    byId("plate-negative").hidden = force >= 0;
    byId("plate-results").hidden = false;
    byId("status").textContent = isCustom()
      ? "Custom input. Check the recorded strike time, plate assignment, geometry and channels at the source."
      : "Forecast from invented inputs. There is no measured plate load for this example.";
  }

  async function showMoment(record, token) {
    if (record?.domain !== "knee_moment" || !Array.isArray(record.frames) || Array.isArray(record.frames[0])) {
      throw new Error("Supply one knee_moment walking history for this view.");
    }
    const result = await SharedMotion.forecastMovement(record);
    if (token !== revision) return;
    const [right, left] = result.internal_knee_moment_Nm_per_kg[0];
    const method = Array.from(byId("moment-mode").options).find(option => option.value === result.mode);
    byId("moment-name").textContent = method.text;
    byId("moment-right").textContent = format(right, 5);
    byId("moment-left").textContent = format(left, 5);
    const cutoff = record.frames[399];
    byId("moment-timing").textContent = "25 frames after cutoff " + cutoff + " (0.25 s at 100 Hz). The stride match spans " + result.period_frames[0] + " frames.";
    byId("moment-results").hidden = false;
    byId("status").textContent = "";
  }

  let pointPlot = null;
  function drawPoint() {
    if (!pointPlot || byId("point-results").hidden) return;
    const canvas = byId("point-plot");
    const width = Math.max(210, Math.floor(canvas.clientWidth));
    const stacked = width < 465, height = stacked ? 292 : 162;
    const dpi = Math.min(window.devicePixelRatio || 1, 2);
    canvas.style.height = height + "px";
    canvas.width = Math.round(width*dpi); canvas.height = Math.round(height*dpi);
    const g = canvas.getContext("2d");
    g.scale(dpi,dpi); g.font = "12px system-ui, sans-serif";
    const {points,delta} = pointPlot, end = points[8];
    const trace = points.map(row => row.map((n,k) => n-end[k]));
    const cloud = [...trace,delta];
    const ranges = [0,1,2].map(axis => {
      const numbers = cloud.map(row => row[axis]);
      return [Math.min(...numbers), Math.max(...numbers)];
    });
    const panelW = stacked ? width : width/2, panelH = stacked ? height/2 : height;
    const scale = Math.min((panelW-44)/Math.max(1,ranges[0][1]-ranges[0][0]),
      (panelH-55)/Math.max(1,...ranges.slice(1).map(([a,b])=>b-a)));
    if (!Number.isFinite(scale) || scale<=0) return;
    for (const axis of [1,2]) {
      const x0 = !stacked && axis===2 ? panelW : 0, y0 = stacked && axis===2 ? panelH : 0;
      const midX = ranges[0][0]/2+ranges[0][1]/2, midY = ranges[axis][0]/2+ranges[axis][1]/2;
      const X = p => x0+panelW/2+(p[0]-midX)*scale;
      const Y = p => y0+(panelH+19)/2-(p[axis]-midY)*scale;
      g.fillStyle="#f5f8f9";g.fillRect(x0+1,y0+1,panelW-2,panelH-2);
      g.fillStyle="#253e4d";g.fillText(axis===1?"Top view · X and Y":"Side view · X and Z",x0+9,y0+16);
      g.lineWidth=2;g.strokeStyle="#28667a";g.beginPath();
      trace.forEach((p,i)=>i?g.lineTo(X(p),Y(p)):g.moveTo(X(p),Y(p)));g.stroke();
      for(const p of trace){g.fillStyle="#28667a";g.beginPath();g.arc(X(p),Y(p),2.4,0,2*Math.PI);g.fill();}
      g.strokeStyle="#ad5a22";g.setLineDash([4,3]);g.beginPath();g.moveTo(X([0,0,0]),Y([0,0,0]));g.lineTo(X(delta),Y(delta));g.stroke();g.setLineDash([]);
      const x=X(delta),y=Y(delta);
      g.fillStyle="#ad5a22";g.beginPath();g.moveTo(x,y-5);g.lineTo(x+5,y);g.lineTo(x,y+5);g.lineTo(x-5,y);g.closePath();g.fill();
    }
  }
  new ResizeObserver(drawPoint).observe(byId("point-plot"));

  async function showPoint(positions, token) {
    const out = await SharedMotion.forecastMovement({domain:"marker_displacement", mode:byId("point-mode").value, positions_mm:positions});
    if (token !== revision) return;
    byId("point-result").textContent = out.displacement_xyz_mm.map((x,i) => ["X","Y","Z"][i] + " " + format(x,2) + " mm").join(" · ");
    pointPlot = {points: positions, delta: out.displacement_xyz_mm};
    byId("point-results").hidden = false;
    drawPoint();
    byId("status").textContent = isCustom() ? "Forecast from supplied positions." : "Forecast from invented positions.";
  }

  const armNames = [
    ['elbow flexion','bend my right elbow'],['elbow extension','straighten my right elbow'],
    ['supination','turn my right palm up'],['pronation','turn my right palm down'],
    ['hand close','close my right hand'],['hand open','open my right hand'],['rest','rest']
  ];
  const asArmCue = raw => {
    const key = raw.trim().toLowerCase().replace(/[.!?]+$/,'').replace(/\s+/g,' ');
    return armNames.find(([label,phrase])=>key===label || key===phrase)?.[0];
  };
  // Use only a recognizer that can require on-device processing.
  const Voice = window.SpeechRecognition || window.webkitSpeechRecognition;
  const localVoice = !!(Voice && 'processLocally' in Voice.prototype);
  const mic = byId('arm-mic'), voiceNote = byId('arm-voice-status');
  let listening = null;

  function endDictation(message='') {
    const active = listening;
    listening = null;
    if (active) {
      active.onresult = active.onerror = active.onend = null;
      try { active.abort(); } catch {}
    }
    mic.textContent = 'Dictate on this device';
    mic.setAttribute('aria-pressed','false');
    voiceNote.textContent = message;
  }

  mic.hidden = !localVoice;
  if (!localVoice) voiceNote.textContent = 'Type the instruction here. On-device dictation is unavailable in this browser.';
  mic.addEventListener('click', () => {
    if (!localVoice || currentDomain() !== 'cued_arm_change' || byId('arm-cue-field').hidden) return;
    if (listening) { endDictation('Dictation cancelled.'); return; }
    try {
      const active = new Voice();
      active.processLocally = true;
      if (active.processLocally !== true) throw new Error('No on-device recognizer');
      active.lang = 'en-US';
      active.continuous = false;active.interimResults = false;active.maxAlternatives = 1;
      listening = active;
      active.onresult = event => {
        if (listening !== active) return;
        const result = event.results?.[event.resultIndex ?? 0];
        const words = result?.[0]?.transcript?.trim();
        if (!result?.isFinal || !words) return;
        endDictation('Read the words, edit them if needed, then press Enter.');
        byId('arm-cue').value = words;
        clearResults('Review the dictated instruction.');byId('arm-cue').focus();
      };
      active.onend = () => { if (listening === active) endDictation('Dictation ended. You can type an instruction.'); };
      active.onerror = event => {
        if (listening !== active) return;
        const message = event.error === 'not-allowed' ? 'Microphone access was not granted. You can type the instruction.' : 'On-device dictation is unavailable. You can type the instruction.';
        endDictation(message);
      };
      mic.textContent='Cancel dictation';mic.setAttribute('aria-pressed','true');
      voiceNote.textContent='Listening on this device…';clearResults('Listening for an instruction.');
      active.start();
    } catch { endDictation('On-device dictation is unavailable. You can type the instruction.'); }
  });
  byId('arm-cue').addEventListener('input',()=>{if(listening)endDictation();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden && listening)endDictation();});
  window.addEventListener('pagehide',()=>{if(listening)endDictation();});

  function displayGroupStudy(){
    const dataSet=data.groupArmScores, all=dataSet.unseen_person, later=dataSet.after_first_run;
    if(!all?.models || !later?.models) {
      byId('group-arm-coverage').textContent='This build contains fitted weights. Held-person results are unavailable in this copy.';
      byId('group-arm-table').replaceChildren();byId('group-arm-conclusion').textContent='';return;
    }
    byId('group-arm-coverage').textContent='The group model fitted '+dataSet.training.eligible_trials+' trials from '+dataSet.training.eligible_people+' people. The assessment used '+all.coverage.trials+' trials from '+all.coverage.people+' other people. The first-run comparison used '+later.coverage.trials+' later trials.';
    const methods=[['still','No change'],['cue','Cue alone, fitted mean'],['cue_median','Typical movement for the cue'],['s1_shared_cue_motion','Shared encoder fitted on one person'],['shared_motion','Group encoder without the cue'],['wrong_cue','Group encoder given a different cue'],['cue_motion','Group linear fit with cue and motion'],['shuffled_cue_motion','Group fit with shuffled encoder'],['shared_cue_motion','Group fit with the original encoder'],['offset_free_linear','Linear fit without absolute levels'],['offset_free_shared','Shared encoder without absolute levels'],['personal_median','Cue median from the person’s first run'],['calibrated_shared','Group encoder corrected using that first run']];
    const cell=(study,k)=>Number.isFinite(study.models[k]?.standardized_mae)?study.models[k].standardized_mae.toFixed(3):'—';
    byId('group-arm-table').replaceChildren(...methods.map(([k,title])=>{
      const tr=document.createElement('tr'),h=document.createElement('th');h.scope='row';h.textContent=title;tr.append(h);
      for(const study of [all,later]){const td=document.createElement('td');td.textContent=cell(study,k);tr.append(td);}return tr;
    }));
    const formatScore=(study,key)=>cell(study,key);
    byId('group-arm-conclusion').textContent='Before using a new person’s outcomes, the original single-person encoder averaged '+formatScore(all,'s1_shared_cue_motion')+' and the group encoder averaged '+formatScore(all,'shared_cue_motion')+'. The group cue median reached '+formatScore(all,'cue_median')+'. On later runs the first-run correction lowered shared-model error from '+formatScore(later,'shared_cue_motion')+' to '+formatScore(later,'calibrated_shared')+'. The person’s own first-run cue median scored '+formatScore(later,'personal_median')+'. A dash means that method was not part of the comparison.';
  }
  async function showArm(token) {
    const pooled=byId('arm-fit').value==='group',selector=byId('arm-method');
    for(const name of ['cue_median','calibrated_shared','offset_free_linear','offset_free_shared']){const opt=selector.querySelector('option[value="'+name+'"]');opt.hidden=!pooled;opt.disabled=!pooled;}
    if(!pooled&&['cue_median','calibrated_shared','offset_free_linear','offset_free_shared'].includes(selector.value))selector.value='cue';
    const mode=selector.value, usesCue=['cue','cue_median','cue_motion','shared_cue_motion','shuffled_cue_motion','calibrated_shared','offset_free_linear','offset_free_shared'].includes(mode);
    const usesMotion=!['cue','cue_median','still'].includes(mode);
    byId('arm-study').hidden=pooled;byId('group-arm-study').hidden=!pooled;
    if(pooled)displayGroupStudy();
    byId('arm-profile').hidden=mode!=='calibrated_shared';
    const custom=isCustom();
    byId('arm-cue-field').hidden=!usesCue;
    byId('arm-custom-bins').hidden=!(usesMotion && custom);
    const record={domain:pooled?'group_arm_change':'cued_arm_change',mode};
    if (mode==='calibrated_shared') {
      try {record.calibration=JSON.parse(byId('arm-profile-values').value);}
      catch {throw new Error('Load an invented correction or paste a profile made from an earlier run.');}
    }
    if (usesCue) {
      record.cue=asArmCue(byId('arm-cue').value);
      if (!record.cue) throw Error('Choose a listed right-arm action, or enter its study name.');
    }
    if (usesMotion) {
      if (custom) {
        try { record.bins=JSON.parse(byId('arm-bins').value); }
        catch { throw Error('Enter four sensor rows or fill the box with invented values.'); }
      } else record.bins=data.armExample.bins;
    }
    const r=await SharedMotion.forecastMovement(record);
    if(token!==revision)return;
    const caption=byId('arm-result-label');
    caption.textContent=usesCue ? 'Matched task: '+record.cue+'.' : 'This method does not use an action label.';
    const body=byId('arm-values').tBodies[0];
    body.replaceChildren(...r.change_native_units.map((v,k)=>{
      const tr=document.createElement('tr');
      const h=document.createElement('th');h.scope='row';h.textContent=r.horizon_after_cutoff_s[k].toFixed(1)+' s';tr.append(h);
      v.forEach(x=>{const td=document.createElement('td');td.textContent=x.toFixed(4);tr.append(td);});
      return tr;
    }));
    byId('arm-results').hidden=false;
    byId('status').textContent=usesMotion ? (custom?'Forecast from the supplied sensor bins.':'Forecast from invented sensor bins.') : 'Forecast needs no sensor history.';
  }

  async function runCustom() {
    if (listening) endDictation();
    clearResults("");
    const token = revision;
    try {
      if (currentDomain() === "cued_arm_change") { await showArm(token); return; }
      if (currentDomain() === "marker_displacement") {
        await showPoint(JSON.parse(byId("point-input").value), token);
        return;
      }
      if (currentDomain() === "right_plate_force") {
        let record;
        try { record = JSON.parse(byId("plate-input").value); }
        catch { throw new Error("Paste the complete right-plate input or choose Show invented input."); }
        await showPlate(record, token);
        return;
      }
      if (currentDomain() === "knee_moment") {
        let record;
        try { record = JSON.parse(byId("moment-input").value); }
        catch { throw new Error("Paste the complete knee moment input or choose Show invented input."); }
        await showMoment(record, token);
        return;
      }
      if (currentDomain() === "knee_angle") {
        let record;
        try { record = JSON.parse(byId("knee-input").value); }
        catch { throw new Error("Paste the complete knee JSON object or choose Show invented input."); }
        await showKnees(record, token);
        return;
      }
      if (currentDomain() === "wrist_angle") {
        const raw = byId("angle-input").value.trim();
        if (!raw) throw new Error("Enter your wrist measurements or fill in an invented input.");
        let record;
        try { record = JSON.parse(raw); } catch { throw new Error("Enter one complete JSON input object."); }
        await compareAngles(record,token);
        return;
      }
      const cutoff = byId("cutoff").valueAsNumber;
      if (!Number.isFinite(cutoff)) throw new Error("Enter a finite forecast cutoff in seconds.");
      const domain = currentDomain();
      const intervals = SharedMotion.historyFromGeometry({domain,cutoffS:cutoff,samples:parseRows(domain)});
      await showForecast(domain,intervals,false,token);
      if (token === revision) byId("status").textContent = practice ? "Forecast from invented practice samples." : "Forecast from your inputs. Their source and tracking quality are unverified.";
    } catch (e) { if (token === revision) clearResults(e.message); }
  }

  function selectDomain() {
    source.replaceChildren(new Option("Invented example","invented"));
    if (currentDomain() === "wrist_angle") source.add(new Option("Invented forearm example","forearm"));
    if (currentDomain() === "rat") source.add(new Option("Recorded maze trip","recorded"));
    source.add(new Option("Enter my own measurements","custom"));
    selectInput();
  }

  async function selectInput() {
    if (listening) endDictation();
    clearResults("");
    const token = revision;
    const domain = currentDomain();
    const custom = isCustom();
    const angular = domain === "wrist_angle";
    const knee = domain === "knee_angle";
    const arm = domain === "cued_arm_change";
    byId("arm-controls").hidden = !arm;
    byId("arm-study").hidden = !arm || byId("arm-fit").value==="group";
    byId("group-arm-study").hidden = !arm || byId("arm-fit").value!=="group";
    const point = domain === "marker_displacement";
    byId("point-controls").hidden = !point;
    byId("point-study").hidden = !point;
    byId("point-custom").hidden = !custom;
    const plate = domain === "right_plate_force";
    byId("plate-controls").hidden = !plate;
    byId("plate-custom").hidden = !custom;
    byId("plate-example-controls").hidden = custom;
    byId("plate-scale-control").hidden = !byId("plate-mode").value.includes("combined");
    byId("plate-study").hidden = !plate;
    const moment = domain === "knee_moment";
    const recorded = source.value === "recorded";
    const forearm = source.value === "forearm";
    byId("moment-controls").hidden = !moment;
    byId("moment-custom").hidden = !custom;
    byId("moment-example-method").hidden = custom;
    byId("moment-study").hidden = !moment;
    byId("knee-controls").hidden = !knee;
    byId("knee-custom").hidden = !custom;
    byId("knee-example-method").hidden = custom;
    byId("knee-study").hidden = !knee;
    byId("custom").hidden = arm || point || plate || moment || knee || angular || !custom;
    byId("angular-custom").hidden = !angular || !custom;
    byId("angle-study").hidden = !angular;
    byId("distance-study").hidden = arm || point || plate || moment || angular || knee;
    byId("source-line").textContent = custom
      ? "Enter a history from one trial or recording that you have permission to use. The source clock and units must match this task."
      : recorded
        ? "Recorded camera positions from rat JS14. This is the first eligible training window, two seconds into W-track trip 55."
        : forearm ? "An invented half-second from the forearm correction example. It contains wrist angles and four forearm channels. No person supplied these measurements."
        : arm ? "Choose an instruction from the supported right-arm tasks. The fitted model estimates three instrument changes."
        : point ? "Nine invented positions follow one moving point in the laboratory coordinate system."
        : plate ? "Four invented heel and forefoot positions use the centre of one force plate as their origin. The eight muscle channels are invented too."
        : moment ? "Four seconds of invented leg angles. This walking example has no measured future moment."
        : knee ? "Two invented mathematical waves show the input format. They do not come from a person. The example has no measured future angle."
        : angular ? "Invented wrist angles, forearm muscle activity and scalp voltages. All five forecasts use the same half-second."
          : domain === "rat" ? "Invented positions on a two-dimensional maze. There is no measured future endpoint."
            : "Invented right-wrist movement in three dimensions. There is no measured future endpoint.";
    if (!custom) {
      try {
        if (arm) await showArm(token);
        else if (point) await showPoint(data.pointExample.positions_mm, token);
        else if (plate) await showPlate(inventedPlate(), token);
        else if (moment) await showMoment({...data.momentExample, mode:byId("moment-mode").value}, token);
        else if (knee) await showKnees({...data.kneeExample, mode:byId("knee-mode").value}, token);
        else if (angular) await compareAngles(forearm ? data.forearmExample : data.angleExample,token);
        else {
          const intervals = domain === "rat" && !recorded ? data.inventedRat : data.examples[domain].intervals;
          await showForecast(domain,intervals,recorded,token);
        }
      } catch (e) { if (token === revision) clearResults(e.message); }
      return;
    }
    if (arm) { await runCustom(); return; }
    if (point) { clearResults("Supply nine XYZ positions in millimetres."); return; }
    if (plate) {
      clearResults("Supply one marker history from an assigned right-foot plate.");
      return;
    }
    if (moment || knee) {
      clearResults("Supply the earlier frame numbers and angles to forecast the next quarter second.");
      return;
    }
    if (angular) {
      clearResults("Enter the earlier measurements to compare the available models.");
      return;
    }
    const saved = drafts.get(domain);
    byId("cutoff").value = saved?.cutoff ?? "1";
    byId("rows").value = saved?.rows ?? "";
    practice = saved?.practice ?? false;
    const wrist = domain === "wrist";
    const columns = (wrist ? wristHeader : ratHeader).join(", ");
    byId("rows").placeholder = columns;
    byId("schema").textContent = "Enter " + columns + " in that order. " + (wrist
      ? "Use native wrist time and video-frame time in seconds. All positions are in centimetres. Each tracking flag is 1 or 0."
      : "Use camera time in seconds and coordinates in centimetres.");
    clearResults("Run the forecast when the cutoff and samples are ready.");
  }

  function remember() {
    drafts.set(currentDomain(),{rows:byId("rows").value, cutoff:byId("cutoff").value, practice});
  }

  function fillPractice() {
    const wrist = currentDomain() === "wrist";
    const lines = [(wrist ? wristHeader : ratHeader).join(",")];
    for (let i=0; i<=20; i++) {
      const t = i/20;
      const pos = [4*t, 2*t*t].map(v => v.toFixed(5));
      const row = wrist ? [t,t,...pos,(.75*t).toFixed(5),1,1,1] : [t,...pos];
      lines.push(row.join(","));
    }
    byId("rows").value = lines.join("\n"); byId("cutoff").value = "1";
    practice = true;
    remember();
    clearResults("These practice positions are invented. Run a forecast or replace them with your samples.");
  }

  picker.addEventListener("change",selectDomain);
  source.addEventListener("change",selectInput);
  document.addEventListener("keydown",e=>{
    if(e.key.toLowerCase()!=="f" || e.repeat || e.ctrlKey || e.metaKey || e.altKey ||
       e.target.closest?.("input, textarea, select, button, [contenteditable=true]")) return;
    e.preventDefault();
    picker.value="cued_arm_change";
    byId("arm-method").value="cue";
    selectDomain();
    byId("arm-cue").focus();byId("arm-cue").select();
  });
  byId("arm-fit").addEventListener("change",selectInput);
  byId("arm-profile-values").addEventListener("input",()=>clearResults("Run the forecast with this earlier-run profile."));
  byId("arm-profile-practice").addEventListener("click",()=>{byId("arm-profile-values").value=JSON.stringify(data.groupArmExample.calibration);clearResults("Invented correction loaded. Run the forecast.");});
  byId("arm-run").addEventListener("click",runCustom);
  byId("arm-method").addEventListener("change",selectInput);
  byId("arm-cue").addEventListener("input",()=>clearResults("Run the forecast for this instruction."));
  byId("arm-cue").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();runCustom();}});
  byId("arm-bins").addEventListener("input",()=>clearResults("Run the forecast for these readings."));
  byId("arm-fill").addEventListener("click",()=>{byId("arm-bins").value=JSON.stringify(data.armExample.bins);clearResults("Invented sensor readings filled.");});
  byId("point-mode").addEventListener("change", selectInput);
  byId("point-input").addEventListener("input", () => clearResults("Inputs changed. Run the forecast again."));
  byId("point-fill").addEventListener("click", () => { byId("point-input").value = JSON.stringify(data.pointExample.positions_mm); clearResults("Invented history filled. Run the forecast."); });
  byId("point-run").addEventListener("click", runCustom);
  byId("plate-mode").addEventListener("change", selectInput);
  byId("plate-scale").addEventListener("change", selectInput);
  byId("plate-run").addEventListener("click", runCustom);
  byId("plate-input").addEventListener("input", () => clearResults("Inputs changed. Run the forecast for this history."));
  byId("plate-fill").addEventListener("click", () => {
    byId("plate-input").value = JSON.stringify(inventedPlate(), null, 2);
    clearResults("Run the forecast for this invented history, or enter your own measurements.");
  });
  byId("moment-mode").addEventListener("change", selectInput);
  byId("moment-run").addEventListener("click", runCustom);
  byId("moment-input").addEventListener("input", () => clearResults("Inputs changed. Run the forecast to use these angles."));
  byId("moment-fill").addEventListener("click", () => {
    byId("moment-input").value = JSON.stringify(data.momentExample);
    clearResults("Run the forecast on these invented angles, or replace them with your own.");
  });
  byId("knee-mode").addEventListener("change", selectInput);
  byId("knee-run").addEventListener("click", runCustom);
  byId("knee-input").addEventListener("input", () => clearResults("Inputs changed. Run the knee forecast to use these values."));
  byId("knee-fill").addEventListener("click", () => {
    byId("knee-input").value = JSON.stringify(data.kneeExample);
    clearResults("These are invented waves. Run the forecast or replace them with your own angles.");
  });
  byId("angle-run").addEventListener("click",runCustom);
  byId("angle-input").addEventListener("input", () => {
    anglePractice = false;
    clearResults("Inputs changed. Run the comparison to use these values.");
  });
  byId("angle-fill").addEventListener("click", () => {
    byId("angle-input").value = JSON.stringify(data.angleExample,null,2);
    anglePractice = true;
    clearResults("These wrist measurements are invented. Run the comparison or replace them with your own.");
  });
  byId("run").addEventListener("click",runCustom);
  byId("practice").addEventListener("click",fillPractice);
  for (const id of ["cutoff","rows"]) {
    byId(id).addEventListener("input", () => {
      practice = false;
      remember();
      clearResults("Inputs changed. Run the forecast to use these values.");
    });
  }
  byId("retry").addEventListener("click", () => window.location.reload());
  async function start() {
    try {
      const encoded = new TextEncoder().encode(byId("data").textContent);
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",encoded)), v => v.toString(16).padStart(2,"0")).join("");
      if (hash !== "__DATA_DIGEST__") throw new Error("The examples and study comparisons failed their SHA-256 check.");
      data = JSON.parse(byId("data").textContent);
      model = await SharedMotion.loadSharedMotion();
      if (model.checkpointSha256 !== "9a3649cb8f2119984e7f9f0b96a07bdc95e1833c7068f0e9caef2680f22e3179") {
        throw new Error("The checkpoint differs from the one used for these comparisons.");
      }
      if (model.movementCheckpointSha256 !== "901922e1db489a06cc3252212232b7df65784128695f86f84a751726b9f0521c") {
        throw new Error("The movement checkpoint differs from the studied model.");
      }
      studyTable();
      picker.disabled = source.disabled = false;
      if (location.hash === "#arm-transfer") {picker.value="cued_arm_change";byId("arm-fit").value="group";byId("arm-method").value="cue_median";}
      if (location.hash === "#cued-arm") picker.value = "cued_arm_change";
      if (location.hash === "#point-motion") picker.value = "marker_displacement";
      if (location.hash === "#right-plate") picker.value = "right_plate_force";
      selectDomain();
    } catch(e) {
      clearResults("The model could not load. " + e.message + " Reopen a complete saved copy or retry.");
      byId("retry").hidden = false;
    }
  }
  start();
}, {once:true});
