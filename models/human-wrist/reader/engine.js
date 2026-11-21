"use strict";
globalThis.WristEngine = (() => {
  const sides = ["right", "left"];
  const modalities = ["full", "pose"];
  const treatments = ["direct", "anchored", "bounded_zero"];
  const horizons = [8, 15];
  const shapes = {
    input_w:[26,8], input_b:[8], position:[5,8], q:[8,8], k:[8,8], v:[8,8],
    o:[8,8], ff1:[8,12], ff1_b:[12], ff2:[12,8], ff2_b:[8], readout:[8,4], bias:[4]
  };
  const expected = {};
  for (const side of sides) {
    const prefix = 'main__' + side + '__';
    for (const [key, shape] of Object.entries({feature_mean:[26],feature_scale:[26],mean:[2,2],scale:[2,2],damping:[2]})) {
      expected[prefix + key] = shape;
    }
    for (const treatment of treatments) for (const modality of modalities) {
      for (const [key,shape] of Object.entries(shapes)) {
        expected[prefix + 'transformer_' + treatment + '_' + modality + '_s17__' + key] = shape;
      }
    }
  }

  function keys(value, required, optional = []) {
    if (!value || typeof value !== "object" || Array.isArray(value)) throw Error("Expected a JSON object.");
    const allowed = new Set([...required, ...optional]);
    if (Object.keys(value).some(k => !allowed.has(k)) || required.some(k => !Object.hasOwn(value, k))) {
      throw Error("Unexpected or missing package fields.");
    }
  }
  function numbers(value, shape, level=0) {
    if (level === shape.length) {
      if (!Number.isFinite(value) || Math.abs(value)>1e8) throw Error("All entries must be bounded finite numbers.");
      return;
    }
    if (!Array.isArray(value) || value.length!==shape[level]) throw Error("A numeric array has the wrong shape.");
    for (const item of value) numbers(item,shape,level+1);
  }
  function validate(pkg) {
    keys(pkg, ["format", "weights", "cases"]);
    if (pkg.format !== "wrist-forecast-v1") throw Error("Unsupported package version.");
    keys(pkg.weights,Object.keys(expected));
    for (const [k,shape] of Object.entries(expected)) numbers(pkg.weights[k],shape);
    for (const side of sides) {
      const p = 'main__'+side+'__';
      if (pkg.weights[p+"feature_scale"].some(x=>x<1e-8) || pkg.weights[p+"scale"].flat().some(x=>x<1)
          || pkg.weights[p+"damping"].some(x=>x<0 || x>1)) throw Error("Invalid normalization or damping coefficient.");
    }
    if (!Array.isArray(pkg.cases) || pkg.cases.length<1 || pkg.cases.length>8) throw Error("Choose a package with one to eight examples.");
    for (const c of pkg.cases) {
      keys(c, ["pose_px","ecog_uv"],["future_px"]);
      numbers(c.pose_px,[15,2,3,2]);
      numbers(c.ecog_uv,[250,8]);
      if ("future_px" in c) numbers(c.future_px,[2,2,2]);
      if (c.ecog_uv.some(r=>r.every(x=>x===0)) || c.ecog_uv.every(r=>r.every((x,j)=>x===c.ecog_uv[0][j]))) {
        throw Error("The model needs varying voltage and a complete recording window.");
      }
    }
    return pkg;
  }
  const add = (a,b)=>a.map((x,i)=>x+b[i]);
  const sub = (a,b)=>a.map((x,i)=>x-b[i]);
  const dot = (a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
  const linear = (a,w)=>w[0].map((_,j)=>a.reduce((sum,x,i)=>sum+x*w[i][j],0));
  function normalize(a) {
    const s=Math.sqrt(dot(a,a)/a.length+1e-5);
    return a.map(x=>x/s);
  }
  function temporal(tokens, p) {
    const states=tokens.map((t,i)=>add(add(linear(t,p.input_w),p.input_b),p.position[i]));
    const normalized=states.map(normalize);
    const query=normalized.map(s=>linear(s,p.q));
    const key=normalized.map(s=>linear(s,p.k));
    const value=normalized.map(s=>linear(s,p.v));
    // Only the final token feeds the readout. This single attention layer has no later cross-token steps.
    const last=states.length-1;
    const logits=key.map(k=>dot(query[last],k)/Math.sqrt(8));
    const maximum=Math.max(...logits);
    const unscaled=logits.map(x=>Math.exp(x-maximum));
    const sum=unscaled.reduce((a,b)=>a+b,0);
    const context=value[0].map((_,j)=>value.reduce((a,v,i)=>a+v[j]*unscaled[i]/sum,0));
    const residual=add(states[last],linear(context,p.o));
    const hidden=add(linear(normalize(residual),p.ff1),p.ff1_b).map(Math.tanh);
    const final=add(residual,add(linear(hidden,p.ff2),p.ff2_b));
    return add(linear(final,p.readout),p.bias);
  }
  function features(arm, voltage) {
    return Array.from({length:5},(_,i)=>{
      const end=arm[3*i+2];
      const relative=[...sub(end[0],end[2]),...sub(end[1],end[2])];
      const move=end.flatMap((joint,j)=>sub(joint,arm[0][j]));
      const segment=voltage.slice(50*i,50*(i+1));
      const means=segment[0].map((_,j)=>segment.reduce((a,row)=>a+row[j],0)/50);
      const logs=segment[0].map((_,j)=>Math.log(Math.max(1e-6,Math.sqrt(segment.reduce((a,row)=>a+row[j]**2,0)/50))));
      return [...relative,...move,...means,...logs];
    });
  }
  function predict(weights,c,treatment,modality,edit=[0,0,1]) {
    const voltage = c.ecog_uv.map(r=>r.map(x=>x*edit[2]));
    return sides.map((side,s)=>{
      const arm=c.pose_px.map((r,t)=>r[s].map((xy,j)=>[xy[0]+(j===0?edit[s]*t/14:0),xy[1]]));
      const prefix='main__'+side+'__';
      const get=k=>weights[prefix+k];
      const input=features(arm,voltage).map(row=>row.map((x,j)=>modality==='pose' && j>=10?0:(x-get('feature_mean')[j])/get('feature_scale')[j]));
      const p={};
      for (const k of Object.keys(shapes)) p[k]=get('transformer_'+treatment+'_'+modality+'_s17__'+k);
      const read=temporal(input,p);
      const origin=arm[14][0];
      const displacement=sub(origin,arm[0][0]);
      const velocity=horizons.map(h=>displacement.map(x=>x*h/14));
      const damping=velocity.map((xy,h)=>xy.map(x=>x*get('damping')[h]));
      const mean=get('mean'), scale=get('scale'), zero=[[0,0],[0,0]];
      const learned=horizons.map((_,h)=>scale[h].map((sc,j)=>{
        const z=read[2*h+j];
        if(treatment==='direct') return mean[h][j]+sc*z;
        return (treatment==='anchored'?damping[h][j]:0)+.25*sc*Math.tanh(z);
      }));
      const result={origin, history:arm.map(r=>sub(r[0],origin)), velocity,damping,mean,zero,learned};
      if(c.future_px && edit[0]===0 && edit[1]===0 && edit[2]===1) result.reference=c.future_px.map(row=>sub(row[s],origin));
      return result;
    });
  }
  return {validate,predict};
})();
