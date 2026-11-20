/** Named muscle activity and marker translation in the source coordinate system. */
export const muscles = ['left tibialis anterior','left soleus','left medial gastrocnemius','left peroneus longus',
  'right tibialis anterior','right soleus','right medial gastrocnemius','right peroneus longus',
  'right anterior deltoid','right brachioradialis','right flexor digitorum','right common extensor digitorum',
  'right first dorsal interosseous'];

function vector(length, fn) { return Array.from({length}, (_,i) => fn(i)); }
function dot(a,b) { return a.reduce((s,x,i) => s+x*b[i],0); }
function add(a,b) { return a.map((x,i)=>x+b[i]); }
function relu(a) { return a.map(x=>Math.max(0,x)); }
function mean(a) { return a.reduce((s,x)=>s+x,0)/a.length; }
function linear(state,key,x) {
  const bias=state[key+'.bias'];
  return state[key+'.weight'].map((w,i)=>dot(w,x)+bias[i]);
}
function norm(state,key,x) {
  const m=mean(x), sd=Math.sqrt(mean(x.map(y=>(y-m)**2))+1e-5);
  return x.map((v,i)=>(v-m)/sd*state[key+'.weight'][i]+state[key+'.bias'][i]);
}
function shape(x,expected) {
  if (!expected.length) return typeof x==='number' && Number.isFinite(x);
  return Array.isArray(x) && x.length===expected[0] && x.every(i=>shape(i,expected.slice(1)));
}
function validInput(e) {
  if (![0,1].includes(e.domain) || !Number.isInteger(e.session) ||
      (e.domain===0 ? ![0,1].includes(e.session)||![-1,1].includes(e.direction) : e.session<1||e.direction!==0))
    throw Error('Invalid study context');
  const mask=e.muscle_mask;
  if (!Array.isArray(mask)||mask.length!==13||mask.some(v=>typeof v!=='boolean') ||
      (e.domain===0 ? mask.some((v,j)=>v!==(j<8)) : mask.slice(0,8).some(Boolean)||mask.filter(Boolean).length<3))
    throw Error('Invalid muscle availability');
  if (!shape(e.patch_rms,[20,13])||!shape(e.past_rms,[13])||!shape(e.patch_xyz_mm,[20,3])||!shape(e.age_s,[20]))
    throw Error('Invalid dimensions or nonfinite input');
  if ([...e.patch_rms,e.past_rms].some(r=>r.some((v,j)=>v<0||(!mask[j]&&v!==0)))) throw Error('Invalid RMS or masked placeholder');
  if (e.age_s.some(v=>v< -1e-8||v>(e.domain ? 1/500 : 1/256)+1e-8) || Math.abs(e.age_s[19])>1e-7 ||
      e.patch_xyz_mm[19].some(v=>Math.abs(v)>1e-4)) throw Error('Marker time or cutoff-relative coordinate out of range');
}
export function predict(weights,e) {
  validInput(e);
  if (weights.format!=='scalp-muscle-motion-v1'||JSON.stringify(weights.muscles)!==JSON.stringify(muscles))
    throw Error('Unknown checkpoint format or muscle vocabulary');
  const s=weights.state, d=e.domain, mask=e.muscle_mask;
  const rmsScale=weights.scales.amp[d], xyzScale=weights.scales.xyz[d];
  const scalp=e.scalp_values, flags=e.scalp_mask, kind=weights.kind;
  if (!shape(scalp,[20,3,2]) || !Array.isArray(flags) || flags.length!==3 ||
      flags.some(x=>typeof x!=='boolean') || !flags.some(Boolean))
    throw Error('Supply 20 mean/RMS bins and three site availability flags');
  const branch=kind==='reference' ? 'central' : kind;
  const allowed=weights.site_names[branch][String(d)];
  if (flags.some((active,j)=>active&&!allowed[j])) throw Error('Unavailable site for study');
  const scaling=weights.scalp_scales[branch][String(d)];
  if (flags.some((present,j)=>present && !(scaling.count[j]>0))) throw Error('Site absent in fitting fold');
  const electrical=scalp.map(bin=>bin.flatMap(([m,r],j)=>{
    if (r<0 || Math.abs(m)>r+1e-5*Math.max(1,r) || (!flags[j] && (r!==0||m!==0)))
      throw Error('Invalid native scalp mean, RMS or missing-site placeholder');
    const present=flags[j] && kind!=='reference';
    return [present?Math.fround((m-scaling.mean[j][0])/scaling.scale[j][0]):0,
            present?Math.fround((r-scaling.mean[j][1])/scaling.scale[j][1]):0,Number(flags[j])];
  }));
  const active=muscles.map((_,j)=>j).filter(j=>mask[j]);
  const pose=e.patch_xyz_mm.map(x=>x.map(v=>v/xyzScale));
  const x=e.patch_rms.map((r,i)=>{
    const amps=active.map(j=>Math.log1p(r[j]/rmsScale[j]));
    const pool=vector(8,k=>mean(active.map((j,a)=>Math.max(0,s['names.weight'][j][k]+amps[a]*s.slope[k]))));
    const patch=linear(s,'patch',[...pool,...pose[i],e.age_s[i]*500,d===0?e.session:0,e.direction,d]);
    const offset=s['scalp_patch.weight'].map(w=>dot(w,electrical[i]));
    return add(add(add(patch,offset),s['time.weight'][i]),s['segment.weight'][d]);
  });
  // No later layer mixes tokens. Only the final query influences the two forecasts.
  const qkv=x.map(row=>linear(s,'qkv',row));
  const attended=[];
  for(let head=0;head<2;head++) {
    const offset=8*head;
    const q=qkv[19].slice(offset,offset+8);
    const logits=qkv.map(r=>dot(q,r.slice(16+offset,24+offset))/Math.sqrt(8));
    const mx=Math.max(...logits), exp=logits.map(v=>Math.exp(v-mx)), sum=exp.reduce((a,b)=>a+b,0);
    for(let k=0;k<8;k++) attended.push(exp.reduce((acc,p,t)=>acc+p/sum*qkv[t][32+offset+k],0));
  }
  const z=norm(s,'norm1',add(x[19],linear(s,'attn_out',attended)));
  const h=norm(s,'norm2',add(z,linear(s,'ff2',relu(linear(s,'ff1',z)))));
  const rstate=linear(s,'rms_state',h);
  const rms=muscles.map((_,j)=>mask[j] ? Math.max(0,e.past_rms[j]/rmsScale[j]+
    linear(s,'rms_out',relu(add(rstate,s['names.weight'][j])))[0])*rmsScale[j] : null);
  const hpath=linear(s,'path_state',h);
  const interval=1/32+e.age_s[18]-e.age_s[19];
  const velocity=pose[19].map((v,j)=>(v-pose[18][j])*(.125/interval));
  const path_mm=vector(32,i=>add(velocity,linear(s,'path_out',relu(add(hpath,s['path_time.weight'][i]))))
    .map(v=>v*((i+1)/32)*xyzScale));
  return {rms,path_mm};
}

