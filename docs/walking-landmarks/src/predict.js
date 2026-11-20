// Portable single-history implementation of the released walking landmark predictors.
const LandmarkPredictor = (() => {
  const models = ['transformer_combined','transformer_markers','ridge_combined','ridge_markers','velocity','persistence'];
  const valid = Number.isFinite;
  function tokens(history, muscle) {
    if (!Array.isArray(history) || history.length!==40 || history.some(f=>!Array.isArray(f) || f.length!==8 ||
      f.some(p=>!Array.isArray(p) || p.length!==3))) throw Error('Expected 40 frames of eight XYZ landmarks.');
    if (muscle != null && (!Array.isArray(muscle)||muscle.length!==8||muscle.some(x=>!Array.isArray(x)||x.length!==8||
      x.some(v=>valid(v)&&v<0)))) throw Error('Expected eight rows of eight nonnegative muscle envelopes.');
    return Array.from({length:8},(_,k)=>{
      const last = history[5*k+4], first = history[5*k];
      const centered = [], motion = [], cflags = [], mflags = [];
      const pelvic = last.slice(6).every(p=>p.every(valid));
      const center = pelvic ? last[6].map((v,i)=>(v+last[7][i])/2) : [];
      for (let m=0;m<8;m++) {
        const seen = last[m].every(valid);
        cflags.push(Number(seen && pelvic)); mflags.push(Number(seen && first[m].every(valid)));
        for(let i=0;i<3;i++) {
          centered.push(cflags[m]?last[m][i]-center[i]:NaN);
          motion.push(mflags[m]?last[m][i]-first[m][i]:NaN);
        }
      }
      const e = muscle ? muscle[k].map(v=>valid(v)?v:NaN) : Array(8).fill(NaN);
      return [...centered,...motion,...cflags,...mflags,...e,...e.map(v=>Number(valid(v)))];
    });
  }
  function residual(z,p) {
    const add=(a,b)=>a.map((v,i)=>v+b[i]);
    const dot=(a,b)=>{let v=0;for(let i=0;i<a.length;i++)v+=a[i]*b[i];return v};
    function affine(x,name) {
      const weight=p(name+'.weight'), bias=p(name+'.bias');
      return weight.map((row,i)=>dot(row,x)+bias[i]);
    }
    function norm(x,name) {
      const mean = x.reduce((a,b)=>a+b,0)/x.length;
      const sd = Math.sqrt(x.reduce((s,v)=>s+(v-mean)**2,0)/x.length+1e-5);
      const scale=p(name+'.weight'), offset=p(name+'.bias');
      return x.map((v,i)=>(v-mean)/sd*scale[i]+offset[i]);
    }
    const positions = p('pos');
    const learned = positions.length===1 ? positions[0] : positions;
    const h=z.map((x,i)=>add(affine(x,'embed'),learned[i]));
    const width=h[0].length, heads=Number(p('heads')), unit=width/heads;
    const vectors=h.map(x=>affine(norm(x,'ln1'),'qkv'));
    // The head reads only the last token. Keys and values still include all eight.
    const query = vectors[vectors.length-1];
    const mix = Array(width).fill(0);
    for(let head=0;head<heads;head++) {
      const start=head*unit, scores=vectors.map(k=>{
        let s=0;for(let d=start;d<start+unit;d++)s+=query[d]*k[width+d];return s/Math.sqrt(unit);
      });
      const ceiling=Math.max(...scores), exp=scores.map(v=>Math.exp(v-ceiling)), sum=exp.reduce((a,b)=>a+b,0);
      vectors.forEach((v,t)=>{for(let d=start;d<start+unit;d++)mix[d]+=exp[t]/sum*v[2*width+d]});
    }
    const last=add(h[h.length-1],affine(mix,'out'));
    const hidden=affine(norm(last,'ln2'),'ff1').map(v=>Math.max(0,v));
    return affine(add(last,affine(hidden,'ff2')),'head');
  }
  function predict(history,muscle,model,weights) {
    if(!models.includes(model)) throw Error('Unknown predictor.');
    const feat=tokens(history,muscle);
    if(model==='persistence')return Array.from({length:6},()=>[0,0,0]);
    if(model==='velocity')return Array.from({length:6},(_,i)=>feat[7].slice(24+i*3,27+i*3).map(v=>valid(v)?5*v:0));
    const family=model.split('_')[1], p=key=>weights[family+'.'+key];
    const mean=p('mean'), sd=p('sd');
    const z=feat.map(row=>mean.map((v,i)=>valid(row[i])?(row[i]-v)/sd[i]:0));
    const y=p('intercept').slice(), beta=p('beta'), flat=z.flat();
    for(let i=0;i<flat.length;i++) for(let j=0;j<18;j++)y[j]+=flat[i]*beta[i][j];
    if(model.startsWith('transformer')) {
      const correction=residual(z,p), scale=p('resid_sd');
      for(let j=0;j<18;j++)y[j]+=correction[j]*scale[j];
    }
    return Array.from({length:6},(_,i)=>y.slice(i*3,i*3+3));
  }
  return {models,predict,tokens};
})();
if(typeof module!=='undefined')module.exports=LandmarkPredictor;
