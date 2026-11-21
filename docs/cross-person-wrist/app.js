"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const names = {
    ridge:"One-arm ridge",damped_velocity:"Damped velocity",velocity:"Full velocity",persistence:"Last wrist position",
    intact:"Both arms",blocked:"Blocked across arms",intact_swapped:"Earlier partner, same weights",
    matched_intact:"Matched training, both arms",matched_blocked:"Matched training, blocked",
    matched_intact_swapped:"Matched training, earlier partner",trained_swap:"Trained with an earlier partner",
    zero:"Last wrist position",mean_px:"Mean move in camera pixels",mean_normalized:"Mean move in arm lengths",
    constant_velocity:"Five-frame velocity",kinematic_ridge:"Ridge on joint velocities"
  };
  const explanations = {
    ridge:"The ridge model combines the earlier wrist, elbow and shoulder positions on one arm. Each arm and each horizon has its own fit.",
    damped_velocity:"Damped velocity extends the wrist’s earlier movement by a fraction learned during training.",
    velocity:"Full velocity extends the movement from the first wrist position to the last, spread across 14 frame intervals.",
    persistence:"Last position keeps the wrist exactly where the camera last saw it.",
    intact:"The two-arm Transformer weighs 30 tokens, one per arm per frame. Each wrist forecast averages three trained networks.",
    blocked:"The blocked model was trained with each arm able to attend only to its own earlier frames.",
    intact_swapped:"The intact model keeps its weights. Only the opposite arm’s earlier frames come from a different event.",
    matched_intact:"Matched training uses only events with an eligible earlier partner. The intact model sees the two arms from the same event.",
    matched_blocked:"Matched blocked training uses the same events and prevents either arm from attending to the other.",
    matched_intact_swapped:"The matched intact model keeps its weights and receives an earlier event’s opposite arm.",
    trained_swap:"This matched model learned with the opposite arm taken from an earlier event and receives the same substitution here.",
    zero:"Last position assumes zero movement for both wrists.",
    mean_px:"The training events supply a mean displacement in shoulder-aligned camera pixels.",
    mean_normalized:"The training events supply a mean displacement scaled to each arm’s earlier projected length.",
    constant_velocity:"Five-frame velocity extends the displacement measured over the last four frame intervals.",
    kinematic_ridge:"This ridge model uses estimated velocities of the shoulder, upper arm and forearm over four, eight and fifteen frames."
  };
  const reasons = {
    missing_prior_shoulder:"A shoulder position is missing from the earlier frames.",
    shoulder_width_below_floor:"The shoulders are less than one pixel apart.",
    unstable_shoulder_direction:"The earlier shoulder direction changes too much.",
    ambiguous_image_up_axis:"The shoulder line leaves the image-up axis ambiguous.",
    nonconsecutive_prior_frames:"The 15 earlier frame indices contain a gap.",
    missing_role_landmark:"This arm has a gap in its earlier wrist, elbow or shoulder track.",
    incomplete_bilateral_prior:"The two-arm forecast needs complete earlier tracks from both arms.",
    invalid_projected_arm_scale:"The projected arm length is too small to use.",
    missing_earlier_donor:"This comparison needs a separate earlier arm history.",
    unfitted_head:"This role and horizon had no eligible training examples."
  };
  function why(code) {
    if (code.startsWith("donor_")) return "Earlier partner unavailable. "+why(code.slice(6));
    return reasons[code] || "Unavailable.";
  }
  function node(tag,value) {const e=document.createElement(tag);if(value!==undefined)e.textContent=value;return e;}
  const coord = xy => xy ? xy.map(v=>v.toFixed(2)).join(", ") : "—";
  const dist = (a,b) => a && b ? Math.hypot(a[0]-b[0],a[1]-b[1]) : null;
  const valid = p => Array.isArray(p) && p.length===2 && p.every(Number.isFinite);
  let privateInput=null, privateWeights=null, curves=[], runToken=0;
  let rememberedSide="L";

  function setControls() {
    const mode=$("family").value;
    const choices = mode==="ridge" ? ["damped_velocity","velocity","persistence"] :
      mode==="intact" ? ["blocked","intact_swapped","zero","mean_px","mean_normalized","constant_velocity","kinematic_ridge"] :
      ["matched_blocked","matched_intact_swapped","trained_swap"];
    const options=choices.map(id=>new Option(names[id],id));
    $("control").replaceChildren(...options);
  }
  function readInput() {
    return privateInput ? {input:privateInput,observed:null} : WristExamples.build($("case").value,$("gaps").value);
  }
  function redraw() {
    const canvases=[$("plot0"),$("plot1")];
    const sizes=canvases.map(c=>c.getBoundingClientRect());
    if (!curves.length || sizes.some(r=>!r.width || !r.height)) return;
    const ranges=curves.map(c=>{
      const p=[...c.path,c.prediction,c.comparator,c.actual].filter(valid);
      if (!p.length) return {center:[0,0],x:0,y:0};
      const bounds=[0,1].map(j=>[Math.min(...p.map(x=>x[j])),Math.max(...p.map(x=>x[j]))]);
      return {center:bounds.map(([a,b])=>(a+b)/2),x:bounds[0][1]-bounds[0][0],y:bounds[1][1]-bounds[1][0]};
    });
    const pixelsPerUnit=Math.min(...ranges.flatMap((r,s)=>[(sizes[s].width-36)/Math.max(35,r.x),(sizes[s].height-42)/Math.max(26,r.y)]));
    curves.forEach((item,s)=>{
      const canvas=canvases[s],w=sizes[s].width,h=sizes[s].height;
      const ctx=canvas.getContext("2d"), dpr=Math.min(window.devicePixelRatio||1,2);
      canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
      ctx.setTransform(dpr,0,0,dpr,0,0);
      const center=ranges[s].center;
      const project=p=>[w/2+(p[0]-center[0])*pixelsPerUnit,h/2+(p[1]-center[1])*pixelsPerUnit];
      function line(a,b,color,thickness,dash=[]) {
        ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=thickness;ctx.setLineDash(dash);
        ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();ctx.setLineDash([]);
      }
      function circle(p,r,fill) {ctx.beginPath();ctx.fillStyle=fill;ctx.arc(...p,r,0,2*Math.PI);ctx.fill();}
      const barSize=Math.pow(10,Math.floor(Math.log10(50/pixelsPerUnit)));
      const tick=barSize*pixelsPerUnit;
      if (Number.isFinite(tick) && tick>1) {
        line([10,h-12],[10+tick,h-12],"#78857e",1.4);
        ctx.fillStyle="#4c615c";ctx.font="10px Arial,sans-serif";ctx.fillText(String(barSize)+" px",10,h-16);
      }
      const path=item.path;
      path.forEach((p,i)=>{if(!valid(p))return;const v=project(p);
        if(i && valid(path[i-1]))line(project(path[i-1]),v,"#758780",1.6);
        circle(v,i===14?3.5:1.7,"#536763");});
      const last=valid(path[14])&&project(path[14]);
      if (item.prediction) {const p=project(item.prediction);if(last)line(last,p,"#00665d",1.8);circle(p,5.8,"#00665d");}
      if (item.comparator) {const p=project(item.comparator);if(last)line(last,p,"#ac4424",1.4,[3,3]);
        ctx.save();ctx.translate(...p);ctx.rotate(Math.PI/4);ctx.fillStyle="#ac4424";ctx.fillRect(-3.5,-3.5,7,7);ctx.restore();}
      if (item.actual) {const [x,y]=project(item.actual);
        for (const offset of [-1,1]) {line([x-5,y-5*offset],[x+5,y+5*offset],"#fff",4);line([x-5,y-5*offset],[x+5,y+5*offset],"#182c28",1.8);}}
    });
  }
  function results() {
    const {input,observed}=readInput();
    const family=$("family").value, control=$("control").value, h=Number($("horizon").value);
    const output=CrossWrist.run(input,privateWeights || SyntheticWristFit,[family,control]);
    const isLocal=Boolean(privateInput), localFit=Boolean(privateWeights);
    $("source").textContent=(isLocal?"Local input":"Fictional input")+" · "+(localFit?"Imported coefficients":"Weights trained on fictional movement");
    const ref=output.reference;
    $("geometry").textContent=ref?"Earlier shoulder width "+ref.width_px.toFixed(2)+" px.":"The earlier frames do not define a usable shoulder line.";
    const holder=node("div");holder.className="rows";curves=[];
    for (let s=0;s<2;s++) {
      const native=output.role_wrist[output.roles[s]], side=native.startsWith("R")?"Right wrist":"Left wrist";
      const role=s===0?"Opposite implant · contralateral":"Implant side · ipsilateral";
      $("title"+s).replaceChildren(document.createTextNode(side),node("small",role));
      const preds=output.methods[family], comps=output.methods[control];
      const pred=preds.endpoint_native_px[h][s], comp=comps.endpoint_native_px[h][s];
      const truth=observed?.[native]?.[h] || null;
      const path=input.prior_by_name[native] || [];
      curves.push({path,prediction:pred,comparator:comp,actual:truth});
      const messages=[];
      if (!pred) messages.push(why(preds.reason_by_horizon[h][s]));
      if (!comp && (!pred || preds.reason_by_horizon[h][s]!==comps.reason_by_horizon[h][s])) {
        const note=why(comps.reason_by_horizon[h][s]);if(!messages.includes(note))messages.push(note);
      }
      if (pred && comp===null && messages.length===0) messages.push(why(comps.reason_by_horizon[h][s]));
      if (!truth) messages.push(isLocal?"Local input contains earlier frames only.":"The later wrist has no reference at this horizon.");
      $("status"+s).textContent=messages.join(" ");
      const card=node("article"), table=node("table");
      const heading=node("h3",side+" · +"+CrossWrist.horizons[h]+" frames");card.append(heading);
      const head=table.createTHead().insertRow();
      for (const label of ["","Endpoint (px)","Error (px)","Error (widths)"])head.append(node("th",label));
      const body=table.createTBody();
      for (const [label,point] of [["Forecast",pred],["Comparison",comp],["Later wrist",truth]]) {
        const row=body.insertRow();row.append(node("th",label),node("td",coord(point)));
        const error=label==="Later wrist"?null:dist(point,truth);
        row.append(node("td",error===null?"—":error.toFixed(2)),node("td",error===null || !ref?"—":(error/ref.width_px).toFixed(3)));
      }
      card.append(table);holder.append(card);
    }
    $("results").replaceChildren(holder);
    $("ref-key").hidden=!curves.some(c=>c.actual);
    $("method-note").textContent=explanations[family]+" "+explanations[control];
    redraw();
  }
  function setCaseState() {
    const select=$("case");
    if (privateInput) {
      if (!select.querySelector('[value="local"]')) select.add(new Option("Local earlier frames","local"));
      select.value="local";
      $("gaps").disabled=true;
    } else {
      select.querySelector('[value="local"]')?.remove();
      select.value=rememberedSide;$("gaps").disabled=false;
    }
  }
  async function importFile(inputId,kind) {
    const file=$(inputId).files[0];
    if(!file) return;
    const token=++runToken;
    try {
      if(file.size>4*1024*1024)throw Error("Choose a JSON file smaller than 4 MiB.");
      const data=JSON.parse(await file.text());
      if(token!==runToken)return;
      if(kind==="case") {CrossWrist.validateCase(data);privateInput=data;setCaseState();}
      else {CrossWrist.validateWeights(data,SyntheticWristFit);privateWeights=data;}
      results();$("message").textContent=kind==="case"?"Earlier frames loaded from your device.":"Local checkpoint loaded.";
    } catch(err) {
      if(token===runToken)$("message").textContent="File could not be loaded. "+err.message;
    } finally {$(inputId).value="";}
  }
  $("case-file").addEventListener("change",()=>importFile("case-file","case"));
  $("weight-file").addEventListener("change",()=>importFile("weight-file","weights"));
  $("case").addEventListener("change",()=>{
    if($("case").value!=="local"){runToken++;rememberedSide=$("case").value;privateInput=null;setCaseState();$("message").textContent="";}
    results();
  });
  $("family").addEventListener("change",()=>{setControls();results();});
  for (const id of ["gaps","control","horizon"])$(id).addEventListener("change",results);
  $("reset").addEventListener("click",()=>{
    runToken++;privateInput=null;privateWeights=null;rememberedSide="L";setCaseState();
    $("gaps").value="none";$("family").value="ridge";$("horizon").value="1";setControls();results();
    $("message").textContent="Fictional example and its training weights restored.";
  });
  $("save").addEventListener("click",()=>{
    const example=WristExamples.build(rememberedSide,$("gaps").value);
    const link=node("a");link.href=URL.createObjectURL(new Blob([JSON.stringify(example.input,null,2)],{type:"application/json"}));
    link.download="fictional-wrist-input.json";link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
  });
  for (const paragraph of WristStudy) $("study-result").append(node("p",paragraph));
  setControls();setCaseState();results();
  new ResizeObserver(redraw).observe($("plot0").parentElement);
})();
