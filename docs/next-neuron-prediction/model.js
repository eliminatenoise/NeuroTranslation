const spikeWeights = [0.12307927914771065, 0.3550649147762503, 0.0918770010111547, 1.1436723238998823, -0.1853918623008996];
function forecastSpikes(units,bins) {
  if (!Array.isArray(units)||units.length<2||!units.every(s=>(typeof s==='string'&&s.trim().length>0)||Number.isSafeInteger(s))||new Set(units).size!==units.length)throw Error('Use distinct local unit names.');
  let last=null, through=null, occupied=0, logits=null,probs=null;
  const total=units.map(()=>0), traces=units.map(()=>[0,0,0]),taus=[10,100,1000];
  for(const {end_ms,counts} of bins) {
    if(!Number.isSafeInteger(end_ms)||(through!==null&&end_ms<=through)||!Array.isArray(counts)||counts.length!==units.length||counts.some(v=>!Number.isSafeInteger(v)||v<0))throw Error('Supply increasing whole milliseconds and an observed count for each unit.');
    through=end_ms;
    if(counts.every(v=>v===0))continue;
    logits=counts.map((count,k)=>{
      total[k]+=count;
      traces[k]=traces[k].map((v,i)=>(last===null?0:v*Math.exp(-(end_ms-last)/taus[i]))+count);
      const input=[Math.log1p(total[k]),...traces[k].map(Math.log1p),Number(count>0)];
      return input.reduce((sum,x,i)=>sum+x*spikeWeights[i],0);
    });
    const peak=Math.max(...logits), exps=logits.map(l=>Math.exp(l-peak)), denom=exps.reduce((a,b)=>a+b,0);
    probs=exps.map(a=>a/denom);last=end_ms;occupied++;
  }
  return {local_units:units,candidate_units:units.length,observed_through_ms:through,forecast_time_ms:last,occupied_bins:occupied,logits,next_unit_probabilities:probs};
}
globalThis.forecastSpikes=forecastSpikes;
