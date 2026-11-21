"use strict";
(() => {
  const $ = id => document.getElementById(id);
  if (!globalThis.CYLINDER_WEIGHTS || !globalThis.CYLINDER_DATA) {
    $('feedback').textContent = 'The model files could not be loaded. Extract the whole offline folder, then open index.html again.';
    return;
  }
  const {records, scores} = CYLINDER_DATA;
  const modes = {full:'Both sensors + target', gyro_task:'Gyroscope + target', accel_task:'Acceleration + target',
    sensors:'Both sensors without target', task:'Hand, target and time only', wrong:'Borrowed acceleration',
    gyro_loss:'Both sensors + target, gyro loss only'};
  const baselines = {persistence:'Repeat the recent mean', linear_trend:'Extend the recent trend', hand_target_time_mean:'Training mean for hand, target and time'};
  const methodNotes = {
    full:'Uses both sensor histories, elapsed time, hand and assigned target.',
    gyro_task:'Uses earlier angular velocity, hand, elapsed time and target.',
    accel_task:'Uses earlier acceleration, hand, elapsed time and target.',
    sensors:'Uses both sensors, hand and elapsed time. The destination is withheld.',
    task:'Uses hand, assigned target and elapsed time. Sensor values are withheld.',
    wrong:'Uses another recording’s acceleration. The gyroscope, hand, target and elapsed times come from the chosen recording.',
    gyro_loss:'Uses full inputs. Training rewarded only angular velocity, so there is no acceleration forecast.',
    persistence:'Repeats the average of the last ten readings.',
    linear_trend:'Adds the difference between the two earlier ten-sample averages to the most recent average.',
    hand_target_time_mean:'Uses a mean learned on earlier training repetitions for this hand, target and cutoff.'
  };
  const methods = {};
  for (const [family, suffix] of [['Temporal', 'temporal'], ['Linear', 'ridge']]) {
    for (const [mode,label] of Object.entries(modes)) {
      if (suffix === 'ridge' && mode === 'gyro_loss') continue;
      methods[mode + ':' + suffix] = family + ' · ' + label;
    }
  }
  Object.assign(methods, baselines);
  function options(select, entries) {
    select.replaceChildren(...entries.map(([value, text]) => new Option(text, value)));
  }
  const units = {gyro:'rad/s', accel:'m/s²'};
  const pretty = value => Number.isFinite(value) ? (Math.abs(value) < .00005 ? 0 : value).toFixed(4) : '—';
  const groupNames = {overall:'All participants and conditions', hand_left:'Left hand', hand_right:'Right hand'};
  for (let i=1; i<=9; i++) groupNames['target_'+i] = 'Target '+i;
  for (let i=200; i<=2600; i+=400) groupNames['cutoff_'+i+'ms'] = i+' ms cutoff';
  options($('record'), records.map((r,i) => [i, r.hand[0].toUpperCase()+r.hand.slice(1)+' hand · recording '+(r.trial+1)+' · target '+r.target]));
  options($('method'), Object.entries(methods));
  options($('group'), Object.entries(groupNames));
  if (location.protocol === 'file:') $('download').hidden = true;
  let record, windowData, history, forecasts, edit, chartState;
  function table(body, rows) {
    const fragment = document.createDocumentFragment();
    for (const row of rows) {
      const tr = document.createElement('tr');
      row.forEach((value, i) => {
        const cell = document.createElement(i === 0 ? 'th' : 'td');
        if (!i) cell.scope = 'row';
        cell.textContent = value;
        tr.append(cell);
      });
      fragment.append(tr);
    }
    body.replaceChildren(fragment);
  }
  function refreshRecord() {
    record = records[Number($('record').value)];
    const previous = $('cutoff').selectedOptions[0]?.textContent;
    options($('cutoff'), record.windows.map((w, i) => [i, w.cutoff+' ms']));
    const preferred = Array.from($('cutoff').options).find(o => o.textContent === (previous || '600 ms'));
    if (preferred) $('cutoff').value = preferred.value;
    $('identity').textContent = 'Source participant '+record.person+' · repetition '+(record.repetition+1)+' for this target · '+record.selection.join(' and ')+'.';
    refreshWindow();
  }
  function refreshWindow() {
    windowData = record.windows[Number($('cutoff').value)];
    options($('sample'), windowData.time.map((t,i) => [i, Math.round(1000*t)+' ms · sample '+(i+1)]));
    $('sample').value = '19';
    $('delta').value='0';
    recalculate();
  }
  function recalculate() {
    const sample = Number($('sample').value), axis = Number($('edit-axis').value);
    edit = Number($('delta').value);
    const accel = windowData.accel.map(row => row.slice());
    accel[sample][axis] += edit;
    history = {gyro: windowData.gyro, accel, time:windowData.time, hand:record.hand,target:record.target};
    forecasts = CylinderForecast.runAll(CYLINDER_WEIGHTS, history, windowData.donor, windowData.trainMean);
    const sign = edit > 0 ? '+' : '';
    $('delta-label').textContent = sign+edit.toFixed(1)+' m/s²';
    $('delta').setAttribute('aria-valuetext', sign+edit.toFixed(1)+' metres per second squared');
    $('edit-reading').textContent = 'Recorded '+pretty(windowData.accel[sample][axis])+' → copy '+pretty(accel[sample][axis])+' m/s². Switching sample or axis starts from the original.';
    render();
  }
  function keyFor(method, seed) {
    if (!method.includes(':')) return method;
    const [mode,family] = method.split(':');
    return mode+'-'+(family === 'temporal' ? seed : 'ridge');
  }
  function render() {
    const quantity = $('quantity').value, axis = Number(document.querySelector('input[name=axis]:checked').value);
    const meth = $('method').value, [mode, family] = meth.split(':'), seed = $('seed').value;
    const wrong = mode === 'wrong', donor = windowData.donor;
    const useObserved = !edit && !wrong;
    const prediction = forecasts[keyFor(meth,seed)], offset = quantity === 'gyro' ? 0 : 3;
    const predicted = prediction && prediction.length >= offset+3 ? prediction.slice(offset,offset+3) : null;
    const observed = useObserved ? windowData['y_'+quantity] : null;
    const accInput = wrong ? donor?.accel : history.accel;
    const past = quantity === 'gyro' ? history.gyro : accInput;
    $('clip-state').textContent = edit ? 'Edited sensor history' : wrong ? 'Borrowed-input control' : 'Recorded sensor history';
    $('method-note').textContent = methodNotes[mode];
    $('seed').disabled = family !== 'temporal';
    $('observed-key').hidden = !observed;
    $('vector-title').textContent = 'Next ten-sample mean ('+units[quantity]+')';
    const vectorRows = [['Forecast', ...(predicted || [null,null,null]).map(pretty)]];
    if (observed) vectorRows.push(['Recorded', ...observed.map(pretty)]);
    table($('vectors'), vectorRows);
    let feedback = '';
    if (wrong && !donor) feedback = 'This window has no eligible earlier match. The borrowed-input forecast is unavailable.';
    else if (!predicted) feedback = mode === 'gyro_loss' ? 'This single-task fit has no trained acceleration output.' : 'This comparison is unavailable for this window.';
    else if (!useObserved) feedback = 'No measured future accompanies this changed history.';
    else feedback = 'Three-axis distance from the recorded mean is '+pretty(Math.hypot(...predicted.map((v,i)=>v-observed[i])))+' '+units[quantity]+'.';
    $('feedback').textContent = feedback;
    const t = windowData.cutoff;
    $('caption').textContent = 'Twenty readings span '+(t-200)+'–'+(t-10)+' ms. Each horizontal mark on the right is one mean over the ten samples at '+t+'–'+(t+90)+' ms.';
    $('cue').textContent = 'Assigned target '+record.target+' of nine · '+record.hand+' hand · '+t+' ms after the first exported sensor row. The exact instant the person received the cue is unknown.';
    $('raw-note').textContent = (wrong ? (donor ? 'Accelerometer values come from earlier recording '+(donor.trial+1)+' (repetition '+(donor.repetition+1)+'). ' : 'No earlier recording supplies acceleration here. ') :
      edit ? 'The accelerometer column includes the one edited reading. ' : 'Both sensors show the original earlier measurements. ')+
      'Gyroscope values belong to the chosen recording. The table shows the available channels, including any omitted by the selected fit. Acceleration includes gravity.';
    if ($('histories').open) {
      table($('raw'), history.time.map((time,i) => [Math.round(time*1000), ...history.gyro[i].map(pretty), ...(accInput?.[i] || [null,null,null]).map(pretty)]));
    }
    if ($('all-fits').open) {
      const rows = [];
      for (const [method,label] of Object.entries(methods)) {
        const temporal = method.endsWith(':temporal');
        for (const n of (temporal ? ['17','41','73'] : [''])) {
          const p = forecasts[keyFor(method,n)];
          rows.push([label+(temporal ? ' · '+n : ''), ...(p && p.length >= offset+3 ? p.slice(offset,offset+3) : [null,null,null]).map(pretty)]);
        }
      }
      $('fits-title').textContent = 'Forecast components ('+units[quantity]+'). A dash means unavailable.';
      table($('fits'), rows);
    }
    chartState={past:past?.map(row=>row[axis]), predicted:predicted?.[axis], observed:observed?.[axis], cutoff:t,
      unit:units[quantity],axis:['X','Y','Z'][axis],time:history.time};
    draw();
  }
  function draw() {
    if (!chartState) return;
    const canvas = $('chart'), ctx=canvas.getContext('2d'), b=canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio||1, 2);
    canvas.width=Math.round(b.width*dpr); canvas.height=Math.round(b.height*dpr); ctx.scale(dpr,dpr);
    const {past,predicted,observed,cutoff,unit,axis,time}=chartState;
    const vals=[...(past||[]),predicted,observed].filter(Number.isFinite);
    if (!vals.length) {ctx.fillStyle='#405357';ctx.fillText('No matched readings available',10,50);return;}
    const lo=Math.min(...vals), hi=Math.max(...vals), pad=Math.max((hi-lo)*.14,.012);
    const left=50, right=b.width-16, top=32, bottom=b.height-32;
    const x=ms => left+(ms-(cutoff-200))/300*(right-left);
    const y=v => bottom-(v-lo+pad)/(hi-lo+2*pad)*(bottom-top);
    function line(points,color,width,dash=[]) {
      ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();
      points.forEach(([a,c],i)=> i ? ctx.lineTo(a,c) : ctx.moveTo(a,c));ctx.stroke();ctx.setLineDash([]);
    }
    ctx.fillStyle='#e8f2ec';ctx.fillRect(x(cutoff),top,right-x(cutoff),bottom-top);
    ctx.font='11px Arial, sans-serif';ctx.textBaseline='middle';ctx.textAlign='right';
    for(let i=0;i<4;i++){
      const v=lo-pad+(hi-lo+2*pad)*i/3, py=y(v);
      line([[left,py],[right,py]],'#d0dcd6',1);
      ctx.fillStyle='#45595b';ctx.fillText(v.toFixed(2),left-6,py);
    }
    ctx.textAlign='left';ctx.fillStyle='#2a464c';ctx.fillText(axis+' · '+unit,left,14);
    ctx.textAlign='right';ctx.fillText('Next 100 ms',right,14);
    line([[x(cutoff),top],[x(cutoff),bottom]],'#78918c',1,[3,4]);
    if (past) {
      line(past.map((v,i)=>[x(time[i]*1000),y(v)]),'#253c44',2);
      ctx.fillStyle='#253c44';past.forEach((v,i)=>{ctx.beginPath();ctx.arc(x(time[i]*1000),y(v),2,0,Math.PI*2);ctx.fill();});
    }
    if (Number.isFinite(predicted)) line([[x(cutoff),y(predicted)],[right,y(predicted)]],'#006d6a',3);
    if (Number.isFinite(observed)) line([[x(cutoff),y(observed)],[right,y(observed)]],'#a34421',2,[6,4]);
    for(const t of [cutoff-200,cutoff-100,cutoff,cutoff+100]){
      ctx.textAlign=t===cutoff+100?'right':'center';ctx.fillStyle='#45595b';ctx.fillText(t+' ms',x(t),bottom+16);
    }
    canvas.setAttribute('aria-label',axis+' axis in '+unit+'; earlier readings then '+(Number.isFinite(predicted)?'forecast '+pretty(predicted):'forecast unavailable')+
       (Number.isFinite(observed)?', recorded mean '+pretty(observed):', no measured outcome shown')+'.');
  }
  function resultName(key) {
    if (baselines[key]) return baselines[key];
    const pos=key.indexOf('_'), fam=key.slice(0,pos);
    let mode=key.slice(pos+1);if(mode==='wrong_accel')mode='wrong';
    return (fam==='transformer'?'Temporal':'Linear')+' · '+modes[mode];
  }
  function showScores() {
    const quantity=$('metric').value, group=scores.groups[[$('population').value,$('group').value,quantity].join('/')];
    $('counts').textContent = group.windows+' usable windows from '+group.recordings+' original recordings by '+group.participants+' participants.';
    $('score-unit').textContent='Three-axis error ('+units[quantity]+')';
    const keys=['transformer_full','transformer_gyro_task','transformer_wrong_accel','transformer_gyro_loss','transformer_accel_task','transformer_sensors','transformer_task',
      'ridge_full','ridge_gyro_task','ridge_wrong_accel','ridge_accel_task','ridge_sensors','ridge_task',...Object.keys(baselines)];
    table($('scores'), keys.filter(k=>Object.hasOwn(group.scores,k)).map(k=>{
      const d=group.differences[k];
      return [resultName(k),pretty(group.scores[k]),d?pretty(d.difference):'Reference',d?d.interval.map(pretty).join(' to '):'—'];
    }));
  }
  const primary=scores.groups['matched/overall/gyro'];
  const d=primary.differences;
  const difference=k=>pretty(d[k].difference)+' rad/s (95% interval '+d[k].interval.map(pretty).join(' to ')+')';
  $('primary').textContent=(scores.primaryPassed?'Earlier acceleration passed both held comparisons.':'Earlier acceleration fell short of the two-part held test.')+
    ' On later repetitions by the same '+primary.participants+' people, the mean error difference for the full temporal model was '+difference('transformer_gyro_task')+
    ' against gyroscope plus target and '+difference('transformer_wrong_accel')+' against borrowed acceleration.';
  $('simpler').textContent='On those same windows, both sensors with hand and elapsed time but without the target had the lowest mean angular-velocity error ('+
    pretty(primary.scores.transformer_sensors)+' rad/s). The full temporal model reached '+pretty(primary.scores.transformer_full)+
    ' rad/s. Repeating the latest ten-sample mean gave '+pretty(primary.scores.persistence)+' rad/s.';
  $('record').onchange=refreshRecord; $('cutoff').onchange=refreshWindow;
  for (const id of ['sample','edit-axis']) $(id).onchange=()=>{$('delta').value='0'; recalculate();};
  $('delta').oninput=recalculate;$('restore').onclick=()=>{$('delta').value='0';recalculate();};
  for(const id of ['method','seed','quantity']) $(id).onchange=render;
  for(const radio of document.querySelectorAll('input[name=axis]')) radio.onchange=render;
  for(const id of ['histories','all-fits']) $(id).ontoggle=render;
  for(const id of ['population','group','metric']) $(id).onchange=showScores;
  new ResizeObserver(draw).observe($('chart').parentElement);
  refreshRecord();showScores();
})();
