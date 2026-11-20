/* Portable NeuroTranslation forecast for one clocked, instructed right-arm trial. */
(function (root) {
  "use strict";
  const cues = ["elbow flexion","elbow extension","supination","pronation","hand close","hand open","rest"];
  const networks = ["history","scalp","eye","scalp_eye","scalp_only","eye_only","bilateral","mispaired_fit"];
  const ridges = ["ridge","history_ridge"];
  const methods = [...networks,...ridges,"cue_median","cue_mean","still"];
  const channels = ["elbow","forearm_rotation","index_glove"];
  const only = ["scalp_only","eye_only"];
  const hasScalp = ["scalp","scalp_eye","scalp_only","mispaired_fit","ridge"];
  const hasEye = ["eye","eye_only","scalp_eye"];
  const add = (a,b) => a.map((v,i)=>v+b[i]);
  const dot = (a,b) => a.reduce((total,v,i)=>total+v*b[i],0);
  const affine = (a,w,k) => w[k+".weight"].map((row,i)=>dot(row,a)+w[k+".bias"][i]);
  const scaled = (v,mean,sd) => v.map((n,i)=>Math.max(-6,Math.min(6,(n-mean[i])/sd[i])));
  function normalize(row,w,name) {
    const mean = row.reduce((v,x)=>v+x,0)/row.length;
    const centered = row.map(v=>v-mean);
    const sd = Math.sqrt(dot(centered,centered)/row.length+1e-5);
    return centered.map((v,i)=>v/sd*w[name+".weight"][i]+w[name+".bias"][i]);
  }
  function transformer(w,z,anchor,cue) {
    const first = add(w["cue.weight"][cue],affine(anchor,w,"anchor"));
    const h = [first,...z.map(row=>affine(row,w,"project"))].map((row,i)=>add(row,w.position[i]));
    const [q,k,v] = ["q","k","v"].map(name=>h.map(row=>affine(row,w,name)));
    // A single block only needs the output of the first token. Its keys and values cover every token.
    const context = [];
    for (const start of [0,4]) {
      const query = q[0].slice(start,start+4);
      const logits = k.map(key=>dot(query,key.slice(start,start+4))/2);
      const peak = Math.max(...logits);
      const exp = logits.map(n=>Math.exp(n-peak));
      const total = exp.reduce((a,b)=>a+b,0);
      for (let d=start; d<start+4; d++) {
        context.push(exp.reduce((sum,p,i)=>sum+(p/total)*v[i][d],0));
      }
    }
    const h1 = normalize(add(h[0],affine(context,w,"attn_out")),w,"norm1");
    const h2 = normalize(add(h1,affine(affine(h1,w,"ff1").map(Math.tanh),w,"ff2")),w,"norm2");
    return affine(h2,w,"head");
  }
  function check(x,shape,positive=false) {
    if (!shape.length) {
      if (!Number.isFinite(x) || (positive && x<=0)) throw Error("Invalid numeric coefficient or scale");
      return;
    }
    if (!Array.isArray(x) || x.length!==shape[0]) throw Error("Wrong input or coefficient shape");
    for (const item of x) check(item,shape.slice(1),positive);
  }
  function validate(model) {
    if (!model || model.format!=="early-scalp-arm-v1") throw Error("Unsupported coefficient file");
    check(model.target_sd,[9],true);
    check(model.global_median,[9]);
    for (const n of ["cue_mean","cue_median"]) check(model[n],[7,9]);
    for (const [k,n] of Object.entries({history:6,anchor:3,scalp:6,eye:3,bilateral:3})) {
      check(model.scales[k][0],[n]);
      check(model.scales[k][1],[n],true);
    }
    for (const n of networks) {
      const w=model.fits[n];
      check(w["cue.weight"],[8,8]); check(w.position,[5,8]);
      for (const [l,i,o] of [["project",15,8],["anchor",3,8],["q",8,8],["k",8,8],["v",8,8],
                             ["attn_out",8,8],["ff1",8,12],["ff2",12,8],["head",8,9]]) {
        check(w[l+".weight"],[o,i]); check(w[l+".bias"],[o]);
      }
      for (const l of ["norm1","norm2"]) {
        check(w[l+".weight"],[8]); check(w[l+".bias"],[8]);
      }
    }
    for (const n of ridges) {
      check(model.fits[n].coef,[70,9]); check(model.fits[n].bias,[9]);
    }
    return model;
  }
  function predict(model,r) {
    validate(model);
    const fields=["cue","method","history","scalp","eye"];
    if (!r || typeof r!=="object" || Array.isArray(r) || Object.keys(r).some(k=>!fields.includes(k)))
      throw Error("Unknown request fields");
    const method=r.method===undefined ? "scalp" : r.method;
    if (!methods.includes(method)) throw Error("Unknown method");
    const cue=r.cue===undefined ? null : r.cue;
    if ((cue!==null || (!only.includes(method) && method!=="still")) && !cues.includes(cue))
      throw Error("Unknown or missing instruction");
    const hasHistory=(networks.includes(method)||ridges.includes(method)) && !only.includes(method);
    for (const [key,width,req] of [["history",6,hasHistory],["scalp",6,hasScalp.includes(method)||method==="bilateral"],
                                   ["eye",3,hasEye.includes(method)]]) {
      if (req || key in r) check(r[key],[4,width]);
    }
    const id=cue===null ? 0 : cues.indexOf(cue);
    let delta;
    if (method==="still") delta=Array(9).fill(0);
    else if (method==="cue_mean" || method==="cue_median") delta=model[method][id];
    else {
      const sch=model.scales;
      const normScale=(row,name)=>scaled(row,sch[name][0],sch[name][1]);
      const anchor=hasHistory ? r.history[3].slice(0,3) : [0,0,0];
      const a=hasHistory ? normScale(anchor,"anchor") : [0,0,0];
      const z=Array.from({length:4},()=>Array(15).fill(0));
      for (let t=0;t<4;t++) {
        if (hasHistory) z[t].splice(0,6,...normScale(r.history[t].map((v,j)=>j<3 ? v-anchor[j] : v),"history"));
        if (hasScalp.includes(method) || method==="bilateral") {
          let row=r.scalp[t].map((v,j)=>v-r.scalp[0][j]);
          if (method==="bilateral") row=[0,2,4].map(j=>row[j]-row[j+1]);
          z[t].splice(6,row.length,...normScale(row,method==="bilateral" ? "bilateral" : "scalp"));
        }
        if (hasEye.includes(method)) {
          const row=r.eye[t].map((v,j)=>v-r.eye[0][j]);
          z[t].splice(method==="scalp_eye" ? 12 : 6,3,...normScale(row,"eye"));
        }
      }
      const w=model.fits[method];
      let res;
      if (ridges.includes(method)) {
        const d=[...z.flat(),...a,...cues.map((_,i)=>Number(i===id))];
        res=w.bias.map((b,j)=>d.reduce((sum,v,i)=>sum+v*w.coef[i][j],b));
      } else res=transformer(w,z,a,only.includes(method) ? 7 : id);
      const base=only.includes(method) ? model.global_median : model.cue_median[id];
      delta=res.map((v,j)=>base[j]+v*model.target_sd[j]);
    }
    if (!delta.every(Number.isFinite)) throw Error("Input exceeds numeric range");
    return {cue,method,channels:channels.slice(),horizons_s:[0.5,1,1.5],delta:[delta.slice(0,3),delta.slice(3,6),delta.slice(6)]};
  }
  const api={predict,validate,cues:cues.slice(),methods:methods.slice(),channels:channels.slice()};
  root.EarlyScalpArm=api;
  if (typeof module!=="undefined" && module.exports) module.exports=api;
})(globalThis);
