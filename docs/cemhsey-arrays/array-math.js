"use strict";

(() => {
  const COUNT = 320;
  const NROWS = 594;
  const Nticks = 592;
  const windows = ["older", "recent"];
  const phases = ["initial_rest", "ramp_up", "hold", "release", "final_rest"];
  const phaseLabels = ["Initial rest", "Ramp up", "Hold", "Ramp down", "Final rest"];
  const edges = [0, 1000, 2000, 4000, 5000, 6000];
  const historyKeys = ["force_now", "force_delta_5", "force_delta_10", "force_delta_20", "force_delta_40"];
  const phaseKeys = [...phases.map(s=>"phase_"+s), ...phases.map(s=>"phase_age_"+s)];
  const globalKeys = windows.flatMap(w=>["median","q90"].map(s=>"emg_"+w+"_"+s));
  const gridKeys = windows.flatMap(w=>Array.from({length:5},(_,g)=>"emg_"+w+"_grid_"+(g+1)+"_log_median_contrast"));
  const baseKeys = [...historyKeys,...phaseKeys], amplitudeKeys=[...baseKeys,...globalKeys], spatialKeys=[...amplitudeKeys,...gridKeys];
  const layout = {history_phase:baseKeys, history_phase_paired_emg:amplitudeKeys,
    history_phase_paired_grid:spatialKeys, history_phase_paired_grid_rank:[...spatialKeys,"emg_channel_rank_persistence"]};
  const labels = {persistence:"Last force reading",history_phase:"Force history and cue",
    history_phase_paired_emg:"Add whole-forearm amplitude", history_phase_paired_grid:"Add five grid contrasts",
    history_phase_paired_grid_rank:"Add channel-rank similarity"};
  const fitOrigins = ["invented_signals", "measured_train_local", "user_supplied_local"];
  const bindingKeys = ["protocol_sha256", "population_sha256", "baseline_sha256", "baseline_protocol_sha256"];
  const vector=(v,n)=>Array.isArray(v) && v.length===n && v.every(Number.isFinite);
  const same=(a,b)=>Array.isArray(a) && a.length===b.length && a.every((e,i)=>e===b[i]);
  function checkFit(fit, protocol) {
    if(fit?.format!=="cemhsey-array-reader-fit-v1" ||
       !bindingKeys.every(key=>typeof fit[key]==="string" && /^[a-f0-9]{64}$/.test(fit[key])) ||
       (protocol && fit.protocol_sha256!==protocol) || fit.timing_mode!=="nominal_release_index" ||
       !fitOrigins.includes(fit.fit_origin) || !fit.models ||
       !same(Object.keys(fit.models).sort(), Object.keys(layout).sort())) throw Error("Choose a compatible four-model array fit from this edition.");
    for (const [key,keys] of Object.entries(layout)) {
      const m=fit.models[key];
      if(!same(m?.feature_names,keys)||!vector(m.center,keys.length)||!vector(m.scale,keys.length)||
         !vector(m.coef,keys.length)||m.scale.some(x=>x<=0)||!Number.isFinite(m.intercept)||m.add_force_now!==true)
        throw Error("The fitted coefficients or feature order are invalid.");
    }
    return fit;
  }
  function decode64(text,count,name) {
    const bytes=8*count;
    if(typeof text!=="string" || text.length!==4*Math.ceil(bytes/3) || !/^[a-zA-Z0-9+/]*={0,2}$/.test(text))
      throw Error("The encoded "+name+" array has the wrong length or alphabet.");
    const binary=atob(text);if(binary.length!==bytes)throw Error("The "+name+" array has the wrong byte length.");
    const raw=new Uint8Array(bytes);
    for(let i=0;i<bytes;i++)raw[i]=binary.charCodeAt(i);
    const view=new DataView(raw.buffer), out=new Float64Array(count);
    for(let i=0;i<count;i++){const v=view.getFloat64(i*8,true);
      if(!Number.isFinite(v)||(name==="RMS"&&v<0))throw Error("The "+name+" array contains an invalid reading.");out[i]=v;}
    return out;
  }
  function packet(encoded,protocol) {
    if(encoded?.format!=="cemhsey-array-trial-v1" || encoded.protocol_sha256!==protocol || encoded.timing_mode!=="nominal_release_index")
      throw Error("Choose an array trial packet generated for this protocol.");
    return {force:decode64(encoded.force_base64,6000,"force"),rms:decode64(encoded.channel_rms_base64,NROWS*COUNT,"RMS")};
  }
  function channelLocations(maps) {
    if (!Array.isArray(maps) || maps.length !== 5) throw Error("The five-grid map is missing.");
    const locations = new Array(COUNT).fill(null);
    maps.forEach((grid, g) => {
      const cells = grid.matlab_row_1based_by_local_cell;
      const columns = cells[0]?.length;
      if (grid.grid_id !== g + 1 || !columns || cells.some(row => row.length !== columns)) {
        throw Error("The electrode grid has an invalid layout.");
      }
      let count = 0;
      cells.forEach((row, y) => row.forEach((channel, x) => {
        if (channel === null) return;
        if (!Number.isInteger(channel) || channel <= g * 64 || channel > (g + 1) * 64 || locations[channel - 1]) {
          throw Error("The electrode grid repeats or misplaces a channel.");
        }
        count++;
        locations[channel - 1] = {grid: g, x: x / (columns - 1), y: y / (cells.length - 1)};
      }));
      if (count !== 64) throw Error("An electrode grid is missing channels.");
    });
    return locations;
  }
  function example(maps = globalThis.CEMHSEY_ARRAY_MAP) {
    // Draw the invented gradient in the same array-local cells the reader displays.
    const locations = channelLocations(maps);
    const force = new Float64Array(6000);
    const rms = new Float64Array(NROWS * COUNT);
    const level = t => t < 5 ? 0 : t < 10 ? (t - 5) / 5 : t < 20 ? 1 : t < 25 ? (25 - t) / 5 : 0;
    for (let tick = 0; tick < force.length; tick++) {
      const t = tick / 200;
      force[tick] = .016 + .29 * level(t) + .006 * Math.sin(2.4 * t) + .002 * Math.cos(9.7 * t);
    }
    for (let j = 0; j < NROWS; j++) {
      const t = .05 * j + .05;
      const strength = level(t);
      locations.forEach(({grid, x, y}, channel) => {
        const dx = x - .48 - .20 * Math.sin(.55 * t + .6 * grid);
        const dy = y - .52 - .16 * Math.cos(.49 * t + grid);
        const spot = Math.exp(-(dx * dx + dy * dy) / .043);
        rms[j * COUNT + channel] = .011 + .006 * (1 + Math.sin(9 * x + 5 * y + grid)) +
          .004 * (1 + Math.cos(2 * t + 6 * y)) +
          strength * (.036 + .050 * (1 + Math.sin(.5 * t + grid)) + .14 * spot);
      });
    }
    return {force, rms};
  }
  function quantile(sorted,p){const q=(sorted.length-1)*p,i=Math.floor(q);return sorted[i]+(q-i)*(sorted[Math.ceil(q)]-sorted[i]);}
  function ranks(values) {
    const indices=Array.from(values.keys()).sort((a,b)=>values[a]-values[b]);
    const ranked=new Float64Array(values.length);let i=0;
    while(i<indices.length){let j=i+1;while(j<indices.length&&values[indices[j]]===values[indices[i]])j++;
      const mid=(i+j-1)/2-(indices.length-1)/2;
      for(let n=i;n<j;n++)ranked[indices[n]]=mid;i=j;}
    return ranked;
  }
  function bin(rows,n) {
    const v=rows.subarray(n*COUNT,(n+1)*COUNT),sorted=Float64Array.from(v).sort();
    const med=Array.from({length:5},(_,grid)=>quantile(Float64Array.from(v.subarray(grid*64,(grid+1)*64)).sort(),.5));
    const logMed=med.map(Math.log1p), mean=logMed.reduce((a,b)=>a+b,0)/5;
    return {values:v, median:med,contrast:logMed.map(x=>x-mean),marginals:[Math.log1p(quantile(sorted,.5)),Math.log1p(quantile(sorted,.9))],rank:ranks(v),max:sorted[COUNT-1]};
  }
  function rankSimilarity(a,b){let ab=0,aa=0,bb=0;for(let c=0;c<COUNT;c++){ab+=a[c]*b[c];aa+=a[c]*a[c];bb+=b[c]*b[c];}return aa&&bb?Math.max(-1,Math.min(1,ab/Math.sqrt(aa*bb))):0;}
  function features(trial,index,older=bin(trial.rms,index),recent=bin(trial.rms,index+2)) {
    if(!Number.isInteger(index)||index<0||index>=Nticks)throw Error("Choose a scheduled cutoff.");
    const tick=60+10*index,now=trial.force[tick];
    const phase=edges.findIndex((end,j)=>j>0&&tick<end)-1,one=phases.map((_,i)=>i===phase?1:0);
    const age=(tick-edges[phase])/(edges[phase+1]-edges[phase]);const base=[now,...[5,10,20,40].map(k=>now-trial.force[tick-k]),...one,...one.map(b=>b*age)];
    const amp=[...base,...older.marginals,...recent.marginals],grid=[...amp,...older.contrast,...recent.contrast];
    const rank=rankSimilarity(older.rank,recent.rank);
    return {tick,now,phase:phaseLabels[phase],older,recent,rank,inputs:{history_phase:base,history_phase_paired_emg:amp,
      history_phase_paired_grid:grid,history_phase_paired_grid_rank:[...grid,rank]}};
  }
  function forecast(fit,row) {
    const estimates={persistence:row.now};
    for(const [k,vec] of Object.entries(row.inputs)){const model=fit.models[k];let x=model.intercept;
      for(let i=0;i<vec.length;i++)x+=model.coef[i]*(vec[i]-model.center[i])/model.scale[i];
      estimates[k]=x+row.now;if(!Number.isFinite(estimates[k]))throw Error("The inputs exceed the model’s numerical range.");}
    return estimates;
  }
  async function score(fit,trial,isCurrent=()=>true) {
    const sums=Object.fromEntries(Object.keys(labels).map(k=>[k,[0,0]]));
    const bins=new Array(NROWS);
    for(let i=0;i<Nticks;i++){
      if(!isCurrent())return null;
      const a=bins[i]??(bins[i]=bin(trial.rms,i)),b=bins[i+2]??(bins[i+2]=bin(trial.rms,i+2));
      const row=features(trial,i,a,b),pred=forecast(fit,row),target=trial.force[row.tick+24];
      for(const [k,value] of Object.entries(pred)){const e=value-target;sums[k][0]+=Math.abs(e);sums[k][1]+=e*e;}
      if(i%20===19)await new Promise(resolve=>setTimeout(resolve,0));
    }
    const output={};for(const [k,[abs,sq]] of Object.entries(sums)){if(!Number.isFinite(abs)||!Number.isFinite(sq)) throw Error("Trial errors exceed the numerical range.");output[k]={mae:abs/Nticks,rmse:Math.sqrt(sq/Nticks)};}
    return isCurrent()?output:null;
  }
  globalThis.ArrayPinch={labels,checkFit,packet,example,channelLocations,bin,features,forecast,score};
})();
