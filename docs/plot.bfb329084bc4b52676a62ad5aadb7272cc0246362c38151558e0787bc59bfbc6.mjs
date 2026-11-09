/** Overflow-safe display coordinates; no alteration of recording/export values. */
export function normalizeFinite(value,low,high){
  if(![value,low,high].every(Number.isFinite)||high<low)throw new Error('Plot coordinates require a finite ordered range.');
  if(low===high)return .5;
  const scale=Math.max(Math.abs(low),Math.abs(high),Number.MIN_VALUE);
  return Math.max(0,Math.min(1,(value/scale-low/scale)/(high/scale-low/scale)));
}

/** Keep extrema and endpoints in each contiguous run; nulls always break runs. */
export function buildPlotSegments(values,targetBins){
  if(!Array.isArray(values)||!Number.isInteger(targetBins)||targetBins<1)throw new Error('Plot bins require an array and a positive integer width.');
  if(values.some(v=>v!==null&&!Number.isFinite(v)))throw new Error('Plot values must be finite or null.');
  const stride=Math.max(1,Math.ceil(values.length/targetBins)),segments=[];
  let i=0;
  while(i<values.length){
    if(values[i]===null){i++;continue;}
    const start=i;while(i<values.length&&values[i]!==null)i++;const end=i;
    const points=[start];const push=index=>{if(points.at(-1)!==index)points.push(index);};
    for(let bin=start;bin<end;bin+=stride){
      let min=bin,max=bin;
      for(let j=bin+1;j<Math.min(bin+stride,end);j++){if(values[j]<values[min])min=j;if(values[j]>values[max])max=j;}
      for(const index of [min,max].sort((a,b)=>a-b))push(index);
    }
    push(end-1);segments.push(points);
  }
  return segments;
}
