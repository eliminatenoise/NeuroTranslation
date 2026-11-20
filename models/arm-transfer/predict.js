/* Cued arm, portable single-history inference. Runs offline in browsers and Node. */
(function (root) {
  "use strict";
  const cues = ["elbow flexion","elbow extension","supination","pronation","hand close","hand open","rest"];
  const methods = ["transformer","transformer_no_cue","mlp","mlp_no_cue","ridge","ridge_no_cue",
                   "cue","unconditional","still"];
  const channels = ["elbow","forearm_rotation","index_near"];
  const add = (a,b) => a.map((v,i)=>v+b[i]);
  const dot = (a,b) => a.reduce((total,v,i)=>total+v*b[i],0);
  const affine = (a,w,k) => w[k+".weight"].map((row,i)=>dot(row,a)+w[k+".bias"][i]);
  const scaled = (v,mean,sd) => v.map((n,i)=>Math.max(-8,Math.min(8,(n-mean[i])/sd[i])));
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
  function predict(model,request) {
    if (!request || typeof request!=="object" || Object.keys(request).some(k=>!["cue","history","method"].includes(k))) {
      throw Error("Supply cue, history and optionally method.");
    }
    const {cue,history} = request;
    const method = Object.prototype.hasOwnProperty.call(request,"method") ? request.method : "transformer";
    if (!cues.includes(cue) || !methods.includes(method)) throw Error("Unknown cue or method.");
    if (!Array.isArray(history) || history.length!==4 || !Array.from(history).every(
        row=>Array.isArray(row) && row.length===6 && Array.from(row).every(Number.isFinite))) {
      throw Error("Supply four bins of six finite instrument readings.");
    }
    const s=model.scales, id=cues.indexOf(cue), w=model.fits[method];
    const outside=history.some((row,i)=>row.some((val,j)=>val<s.raw_min[i][j] || val>s.raw_max[i][j]));
    let delta;
    if (method==="still") delta=Array(9).fill(0);
    else if (method==="unconditional") delta=s.target_mean;
    else if (method==="cue") delta=w.mean[id];
    else {
      const anchor=history[3].slice(0,3);
      const a=scaled(anchor,s.anchor_mean,s.anchor_sd);
      const z=history.map(row=>scaled(row.map((val,j)=>j<3 ? val-anchor[j] : val),s.token_mean,s.token_sd));
      const selected=method.endsWith("_no_cue") ? 7 : id;
      let normalized;
      if (method.startsWith("transformer")) normalized=transformer(w,z,a,selected);
      else {
        const d=z.flat().concat(a,cues.map((_,i)=>Number(i===selected)));
        if (method.startsWith("mlp")) normalized=affine(affine(d,w,"layer").map(Math.tanh),w,"head");
        else normalized=w.bias.map((b,j)=>d.reduce((sum,x,i)=>sum+(x-w.mean[i])/w.sd[i]*w.coef[i][j],b));
      }
      delta=normalized.map((val,j)=>val*s.target_sd[j]+s.target_mean[j]);
    }
    if (!delta.every(Number.isFinite)) throw Error("Input exceeds numeric range.");
    return {cue,method,channels:channels.slice(),horizons_s:[0.5,1,1.5],
            delta:[delta.slice(0,3),delta.slice(3,6),delta.slice(6,9)],outside_fit_range:outside};
  }
  const api = {predict,cues:cues.slice(),methods:methods.slice(),channels:channels.slice()};
  root.CuedArmTransfer=api;
  if (typeof module!=="undefined" && module.exports) module.exports=api;
})(globalThis);
