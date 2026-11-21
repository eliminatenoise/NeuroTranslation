/* First-use prediction for tracked points in a plane. Original project code is CC0. */
(function () {
  'use strict';
  const valid = p => Array.isArray(p) && p.length===2 && p.every(Number.isFinite);
  const dot = (p,q) => p[0]*q[0]+p[1]*q[1];
  const diff = (p,q) => [p[0]-q[0],p[1]-q[1]];
  const size = p => Math.hypot(...p);
  const mean = numbers => numbers.reduce((s,n)=>s+n,0)/numbers.length;
  const centroid = points => [mean(points.map(x=>x[0])),mean(points.map(x=>x[1]))];
  const linear = (row, W, bias) => bias.map((b,j)=>row.reduce((acc,x,i)=>acc+x*W[i][j],b));

  function slope(t, path) {
    const ix = t.map((_,i)=>i).filter(i=>valid(path[i]));
    const avg = mean(ix.map(i=>t[i]));
    const center = centroid(ix.map(i=>path[i]));
    const denom = ix.reduce((s,i)=>s+(t[i]-avg)**2,0);
    if (!(denom>0)) return [0,0];
    return [0,1].map(k=>ix.reduce((s,i)=>s+(t[i]-avg)*(path[i][k]-center[k]),0)/denom);
  }

  function predict(history, seconds, dt, fit, mode='shape') {
    if (!['shape','no_shape','persistence'].includes(mode)) throw Error('Choose a supported forecast method.');
    if (!Array.isArray(history)||history.length<1||seconds.length!==history.length||
        !seconds.every((v,k)=>Number.isFinite(v)&&(k===0||v>seconds[k-1]))||!Number.isFinite(dt)||dt<=0)
      throw Error('Supply one or more frames with increasing times in seconds and a positive horizon.');
    const frame=history.at(-1);
    if (!Array.isArray(frame)||frame.length<1||history.some(r=>r.length!==frame.length))
      throw Error('Every frame needs the same list of tracked points.');
    const output = frame.map(p=>({xy:valid(p)?[...p]:null,how:valid(p)?'last_position':'unobserved'}));
    const t=seconds.slice(-5).map(v=>v-seconds.at(-1)), frames=history.slice(-5);
    if (mode==='persistence'||t.length<5||-t[0]>fit.protocol.maximum_history_span_s||
        t.slice(1).some((v,i)=>v-t[i]>fit.protocol.maximum_interframe_gap_s)) return output;
    const items=[];
    for (let j=0;j<frame.length;j++) {
      const path=frames.map(x=>x[j]), count=path.filter(valid).length;
      if (!valid(path[4])||count<fit.protocol.minimum_observations_per_point_including_origin) continue;
      let lastIndex=3;
      while(lastIndex>=0&&!valid(path[lastIndex]))lastIndex--;
      if (lastIndex<0) continue;
      const long=slope(t,path), recent=path.slice(-3).filter(valid).length>=2?slope(t.slice(-3),path.slice(-3)):long;
      const age=-t[lastIndex];
      items.push({j,origin:frame[j],count,age,long,recent,last:diff(path[4],path[lastIndex]).map(v=>v/age)});
    }
    if (!items.length) return output;
    const center=centroid(items.map(p=>p.origin));
    const globalRecent=centroid(items.map(p=>p.recent)),globalLong=centroid(items.map(p=>p.long));
    const activity=Math.sqrt(mean(items.map(p=>(dot(p.last,p.last)+dot(p.recent,p.recent)+dot(p.long,p.long))/3)))||1;
    const radius=Math.sqrt(mean(items.map(p=>dot(diff(p.origin,center),diff(p.origin,center)))));
    const unit=items.map(p=>radius?diff(p.origin,center).map(x=>x/radius):[0,0]);
    const xx=mean(unit.map(v=>v[0]*v[0])), yy=mean(unit.map(v=>v[1]*v[1])), xy=mean(unit.map(v=>v[0]*v[1]));
    const e=Math.max(0,(xx+yy-Math.hypot(xx-yy,2*xy))/2);
    const w=fit.models[mode];
    for(let i=0;i<items.length;i++) {
      const p=items[i], u=unit[i], off=diff(p.recent,globalRecent);
      let geometry=[0,0,0,0,0,0,0];
      if (mode==='shape'&&radius>0&&items.length>1) {
        const distance=unit.map(q=>size(diff(u,q)));
        const affinity=distance.map((v,j)=>j===i?0:Math.exp(-Math.min(700,2*v*v)));
        const den=affinity.reduce((a,b)=>a+b,0);
        const weights=affinity.map(a=>a/Math.max(den,2.2250738585072014e-308));
        const near=[0,1].map(k=>items.reduce((a,item,j)=>a+weights[j]*item.recent[k],0));
        geometry=[size(u),distance.reduce((s,d,j)=>s+weights[j]*d,0),mean(distance),e,
          dot(u,off)/(activity*Math.max(size(u),Number.EPSILON)),size(diff(p.recent,near))/activity,activity*dt/radius];
      }
      const features=[size(p.last)/activity,size(p.recent)/activity,size(p.long)/activity,
        size(diff(p.last,p.recent))/activity,size(diff(p.recent,p.long))/activity,size(off)/activity,
        size(diff(p.long,globalLong))/activity,size(globalLong)/activity,p.count/5,p.age/-t[0],dt/-t[0],...geometry]
        .map(v=>Math.max(-10,Math.min(10,v)));
      const hidden=linear(features,w.w1,w.b1).map(Math.tanh);
      const logits=linear(hidden,w.w2,w.b2);
      const exp=logits.map(v=>Math.exp(v-Math.max(...logits))),sum=exp.reduce((a,b)=>a+b,0);
      const moves=[[0,0],p.last,p.recent,p.long,globalRecent,globalLong];
      output[p.j]={xy:[0,1].map(k=>p.origin[k]+dt*moves.reduce((a,v,j)=>a+v[k]*exp[j]/sum,0)),how:'learned'};
    }
    return output;
  }
  globalThis.bodyForecast={predict,valid};
})();
