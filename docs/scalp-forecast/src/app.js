"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const {element, number, namedChart, makeTable} = ForecastCharts;
  const {model, example, reports} = JSON.parse($("reader-data").textContent);
  const methods = {
    scalp:["Cue + motion + scalp",["history","scalp"]],
    history:["Cue + motion",["history"]],
    eye:["Cue + motion + eye",["history","eye"]],
    scalp_eye:["Cue + motion + scalp + eye",["history","scalp","eye"]],
    scalp_only:["Scalp alone",["scalp"]],
    eye_only:["Eye alone",["eye"]],
    bilateral:["Cue + motion + scalp differences",["history","scalp"]],
    ridge:["Linear fit · cue + motion + scalp",["history","scalp"]],
    history_ridge:["Linear fit · cue + motion",["history"]],
    mispaired_fit:["Fit on mismatched scalp trials",["history","scalp"]],
    cue_median:["Typical for the cue (median)",[]],
    cue_mean:["Average for the cue (mean)",[]],
    still:["No change",[]]
  };
  const cues = [["elbow flexion","Bend the elbow"],["elbow extension","Straighten the elbow"],["supination","Turn palm up"],["pronation","Turn palm down"],["hand close","Close the hand"],["hand open","Open the hand"],["rest","Rest"]];
  const sensors = ["Elbow","Forearm rotation","Index-finger glove"];
  const groups = {
    history:{label:"Movement sensors",channels:sensors,help:"Each movement bin covers eight readings at 64 Hz. Enter the median and the change within that bin (last four readings’ median minus first four readings’ median). Keep each instrument in its native units.",window:"L is the final 64 Hz movement row available at the cutoff. Alignment to that clock can place the final row up to seven 512 Hz ticks before the cutoff."},
    scalp:{label:"Scalp electrodes (EEG)",channels:["FC3","FC4","C3","C4","CP3","CP4"],help:"Enter the mean native-file reading for each 64-sample bin. The predictor subtracts this channel’s first-bin mean before using the four values.",window:"At 512 Hz, tick 0 is the cue. The second bin includes the cue tick. The last input tick is +128 (0.25 s)."},
    eye:{label:"Eye electrodes (EOG)",channels:["EOG 62","EOG 63","EOG 64"],help:"Enter the mean eye-channel reading in native file units. Channel numbers follow acquisition order. The predictor subtracts each channel’s own first-bin mean.",window:"At 512 Hz, tick 0 is the cue. The second bin includes the cue tick. The last input tick is +128 (0.25 s)."}
  };
  const electricalTimes=["−127…−64","−63…0","+1…+64","+65…+128"];
  const motionTimes=["L−31…L−24","L−23…L−16","L−15…L−8","L−7…L"];
  const clone = data => JSON.parse(JSON.stringify(data));
  let draft = clone(example);
  function fillSelect(id, entries, selected) {
    const target=$(id);
    target.replaceChildren(...entries.map(([value,label])=>new Option(label,value)));
    if (entries.some(([key])=>key===selected)) target.value=selected;
  }
  function nameOf(key) { return methods[key]?.[0] || reports.labels[key] || key; }
  function requestFor(key) {
    const fields=methods[key][1];
    const req={method:key};
    if (!["scalp_only","eye_only","still"].includes(key)) req.cue=$("cue").value;
    for (const field of fields) {
      const arr=draft[field];
      for (let i=0;i<arr.length;i++) {
        for(let j=0;j<arr[i].length;j++) {
          if(!Number.isFinite(arr[i][j])) {
            const channels=groups[field].channels;
            const ch=channels[j%channels.length];
            const kind=field==="history"?(j<3?" median":" within-bin change"):" mean";
            throw new Error(ch+kind+" is missing in bin "+(i+1)+".");
          }
        }
      }
      req[field]=arr;
    }
    return req;
  }
  function clippedCount(req) {
    let n=0;
    function check(name,values) {
      const [mean,sd]=model.scales[name];
      values.forEach((v,i)=>{if(Math.abs((v-mean[i])/sd[i])>6) n++;});
    }
    if(req.history) {
      const anchor=req.history[3].slice(0,3);
      check("anchor",anchor);
      req.history.forEach(row=>check("history",row.map((v,i)=>i<3?v-anchor[i]:v)));
    }
    for(const group of ["scalp","eye"]) {
      if(!req[group]) continue;
      req[group].forEach(row=>{
        const d=row.map((v,i)=>v-req[group][0][i]);
        if(req.method==="bilateral") check("bilateral",[0,2,4].map(i=>d[i]-d[i+1]));
        else check(group,d);
      });
    }
    return n;
  }
  function infer(key, errors) {
    if (key==="none") return null;
    try {
      const req=requestFor(key);
      const result=EarlyScalpArm.predict(model,req), clipped=clippedCount(req);
      if(clipped) errors.push(nameOf(key)+" clipped "+clipped+" standardized input "+(clipped===1?"value":"values")+" at the fitted limit.");
      return result;
    }
    catch(error) { errors.push(nameOf(key)+" — "+error.message); return null; }
  }
  function draw() {
    const key=$("method").value, ref=$("reference").value, errors=[];
    const first=infer(key,errors), second=infer(ref,errors);
    $("forecast-status").textContent=errors.join(" ");
    const notes=[[key,"Forecast",""],[ref,"Comparison","ref"]].filter(([k])=>k!=="none");
    $("method-notes").replaceChildren(...notes.map(([k,prefix,cls])=>{
      const label=element("span",undefined,"legend");
      const line=element("span",undefined,"swatch "+cls);line.setAttribute("aria-hidden","true");
      label.append(line,document.createTextNode(prefix+" · "+nameOf(k)));return label;
    }));
    $("plots").replaceChildren(...sensors.map((name,sensor)=>namedChart(name,first,second,sensor)));
    const vals=[];
    for(const [i,sensor] of sensors.entries()) {
      [[key,first],[ref,second]].filter(([k])=>k!=="none").forEach(([k,result])=>{
        vals.push({name:sensor+" · "+nameOf(k),values:[0,1,2].map(h=>number(result?.delta[h][i],6))});
      });
    }
    makeTable("numbers-table","Forecast changes in each instrument’s native units",["Sensor and model","+0.5 s","+1.0 s","+1.5 s"],vals);
  }
  function editFields() {
    const key=$("recording").value, c=Number($("channel").value), group=groups[key];
    $("feature-help").textContent=group.help;
    $("window-help").textContent=group.window;
    const isMotion=key==="history";
    $("edit-fields").replaceChildren(...draft[key].map((row,b)=>{
      const field=element("fieldset");
      field.append(element("legend",(isMotion?"Rows ":"Ticks ")+(isMotion?motionTimes:electricalTimes)[b]));
      (isMotion?[["Median",c],["Within-bin change",c+3]]:[["Mean",c]]).forEach(([text,column])=>{
        const label=element("label",text);
        const input=element("input");input.id="reading-"+b+"-"+column;input.type="number";input.step="any";input.inputMode="decimal";
        input.setAttribute("aria-label",group.channels[c]+" bin "+(b+1)+" "+text);
        input.value=Number.isFinite(row[column])?String(row[column]):"";
        input.addEventListener("input",()=>{row[column]=input.value.trim()===""?null:input.valueAsNumber;draw();});
        label.append(input);field.append(label);
      });
      return field;
    }));
  }
  function selectRecording() {
    fillSelect("channel",groups[$("recording").value].channels.map((name,i)=>[String(i),name]),"0");
    editFields();
  }
  function showContrast() {
    const group=reports.cohorts[$("cohort").value], rec=group.contrasts[$("contrast").value];
    if(!rec) { $("contrast-result").textContent="No paired comparison was released for this group.";return; }
    const delta=number(Math.abs(rec.delta),4);
    const pair=rec.delta===0
      ? nameOf(rec.a)+" and "+nameOf(rec.b)+" had equal overall error."
      : nameOf(rec.a)+" had "+delta+" "+(rec.delta>0?"higher":"lower")+" overall error than "+nameOf(rec.b)+".";
    const ci=rec.interval ? " The exploratory 95% interval for the signed difference runs from "+number(rec.interval[0],4)+" to "+number(rec.interval[1],4)+"." : "";
    const gate=rec.pass===true?" The assessment met the prespecified criterion.":rec.pass===false?" The assessment fell short of the prespecified criterion.":"";
    $("contrast-result").textContent=pair+" The first model had lower error in "+rec.wins+" of "+group.n_people+" people."+ci+gate;
  }
  function showScores() {
    const group=reports.cohorts[$("cohort").value], sensor=Number($("score-sensor").value);
    $("score-scope").textContent=group.description+" "+group.n_trials+" scored trials across "+group.n_people+" people. Lower error means a closer forecast.";
    const ordered=[...Object.keys(methods),...Object.keys(group.methods).filter(k=>!methods[k])];
    const rows=ordered.map(key=>{
      const rec=group.methods[key];
      return {name:nameOf(key),active:key==="scalp",values:[0,1,2].map(h=>number(rec.native_mae[h][sensor],4)).concat(number(rec.normalized_mae,6))};
    });
    makeTable("score-table","Mean absolute errors for "+sensors[sensor],["Model or scoring control","+0.5 s","+1.0 s","+1.5 s","Overall"],rows);
    const saved=$("contrast").value || "scalp_over_history";
    fillSelect("contrast",Object.entries(group.contrasts).map(([k,v])=>[k,nameOf(v.a)+" vs "+nameOf(v.b)]),saved);
    showContrast();
  }
  const entries=Object.entries(methods).map(([key,[label]])=>[key,label]);
  fillSelect("method",entries,"scalp");fillSelect("reference",[["none","Show one forecast"],...entries],"history");
  fillSelect("cue",cues,example.cue);
  fillSelect("recording",Object.entries(groups).map(([k,g])=>[k,g.label]),"scalp");
  fillSelect("score-sensor",sensors.map((n,i)=>[String(i),n]),"0");
  fillSelect("cohort",Object.entries(reports.cohorts).map(([k,g])=>[k,g.label]),"assessment");
  $("metric-note").textContent="The three time columns show mean absolute error on the selected sensor’s own scale. Overall combines all nine errors after dividing each by its fitting group’s standard deviation, with equal weight for each person. An assessment comparison passes when mean error falls by at least 5% and every person’s error falls. Rows labelled “shuffled” substitute scalp readings from other trials with the same cue. Those comparisons require recorded trials.";
  $("eye-evidence").textContent=reports.eye_observation;
  $("study-result").textContent=reports.assessment_result;
  for(const id of ["cue","method","reference"]) $(id).addEventListener("change",draw);
  $("recording").addEventListener("change",selectRecording);$("channel").addEventListener("change",editFields);
  $("restore").addEventListener("click",()=>{draft=clone(example);$("cue").value=example.cue;editFields();draw();});
  for(const id of ["cohort","score-sensor"]) $(id).addEventListener("change",showScores);
  $("contrast").addEventListener("change",showContrast);
  if (location.protocol==="https:" || location.protocol==="http:") {
    document.querySelector(".download").hidden=false; $("related").hidden=false;
  }
  selectRecording();draw();showScores();
})();
