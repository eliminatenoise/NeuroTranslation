(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const data = JSON.parse(el('bundle').textContent);
  const {weights, assessment:a} = data;
  const e = WalkingExample;
  for(const [i,name] of e.muscles.entries()) el('channel').add(new Option(name, String(i)));
  for(const [i,name] of e.muscles.entries()) el('inspect').add(new Option('Right '+name.toLowerCase()+' (µV)',String(i+24)));
  for(const [i,name] of e.markers.entries()) for(const [j,axis] of ['X','Y','Z'].entries()) {
    el('inspect').add(new Option(name+' '+axis+' (m)',String(i*3+j)));
  }
  const methodNames = {transformer:'Temporal Transformer',ridge:'Linear ridge'};
  const modalityNames = {combined:'Movement and muscle',markers:'Movement only',emg:'Muscle only'};
  const names = {'transformer-combined':'Transformer · movement and muscle','transformer-markers':'Transformer · movement only',
    'transformer-emg':'Transformer · muscle only','ridge-combined':'Linear ridge · movement and muscle','ridge-markers':'Linear ridge · movement only',
    'ridge-emg':'Linear ridge · muscle only','marker-kernel':'Nonlinear ridge · movement only','wrong-repeat-emg':'Transformer · muscle signals from another repeat',
    'current-plate-persistence':'Earlier plate reading','training-mean':'Training-set mean','constant-zero':'Always zero'};
  const credit='Source data: Florent Moissenet and Céline Schreiber, figshare v8 (2020), doi:10.6084/m9.figshare.7734767.v8, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). NeuroTranslation derived the models and results. Invented inputs are CC0.';
  let series=[], timer=0;
  const settings=()=>({speed:Number(el('speed').value),offset:Number(el('offset').value),
    gain:Number(el('gain').value),shift:Number(el('shift').value),channel:el('channel').value});
  const method=()=>el('method').value, modality=()=>el('modality').value, cursor=()=>Number(el('anchor').value);
  const ms=v=>(v>0?'+':'')+String(v)+' ms';
  const signed=(v,unit=' N')=>(v>0?'+':'')+v.toFixed(1)+unit;
  function table(head, rows){
    const node=document.createElement('table');
    const line=(cell,values)=>{const tr=document.createElement('tr');for(const v of values){const c=document.createElement(cell);c.textContent=String(v);tr.append(c)}return tr};
    node.createTHead().append(line('th',head));
    const body=node.createTBody();for(const row of rows)body.append(line('td',row));
    const wrap=document.createElement('div');wrap.className='scroll';wrap.append(node);return wrap;
  }
  function currentHistory(){
    const o=settings(),t=e.anchors[cursor()];
    return {kind:'invented',attribution:credit,method:method(),modality:modality(),anchor_ms:t,target_ms:t+100,
      bin_ms:30,edited_settings:o,reference_settings:e.reference(o),edited_rows:e.history(t,o),
      reference_rows:e.history(t,e.reference(o)),edited_prediction_N:series[cursor()].edited_N,
      reference_prediction_N:series[cursor()].reference_N,model_sha256:data.signatures[method()+'-'+modality()+'.npz']};
  }
  function updateInputs(){
    const d=currentHistory(),col=Number(el('inspect').value),digits=col<18?3:1;
    el('inputs').replaceChildren(table(['Bin end relative to last sample','Edited','Reference'],
      d.edited_rows.map((r,i)=>[String((i-7)*30)+' ms',r[col].toFixed(digits),d.reference_rows[i][col].toFixed(digits)])));
  }
  function drawCurve(){
    const w=Math.max(280,Math.round(el('plot').clientWidth));
    const svg=ForceCharts.curve(series,cursor(),w);
    svg.style.cursor='crosshair';
    function pick(ev){
      const bounds=svg.getBoundingClientRect(),px=(ev.clientX-bounds.left)*w/bounds.width;
      const frac=(px-Number(svg.dataset.left))/(Number(svg.dataset.right)-Number(svg.dataset.left));
      el('anchor').value=String(Math.min(48,Math.max(0,Math.round(frac*48)))); readPoint();
    }
    svg.addEventListener('click',pick);
    el('plot').replaceChildren(svg);
  }
  function readPoint(){
    const p=series[cursor()];el('anchor-out').value=(p.target_ms/1000).toFixed(2)+' s';
    el('edited').textContent=p.edited_N.toFixed(1)+' N';
    el('reference').textContent=p.reference_N.toFixed(1)+' N';
    el('difference').textContent=signed(p.edited_N-p.reference_N);
    drawCurve();updateInputs();
  }
  function compute(){
    if(timer)cancelAnimationFrame(timer);timer=0;
    const o=settings(),base=e.reference(o),f=method(),m=modality();
    el('gain-out').value=o.gain.toFixed(2)+'×';el('shift-out').value=ms(o.shift);
    el('speed-out').value=o.speed.toFixed(2)+' m/s';el('offset-out').value=(o.offset>0?'+':'')+o.offset+' cm';
    series=e.anchors.map(t=>{
      const pred=WalkingForce.predict(e.history(t,base),weights,f,m);
      const same=(m==='markers'||(o.gain===1&&o.shift===0));
      const edited=same?pred:WalkingForce.predict(e.history(t,o),weights,f,m);
      return {input_end_ms:t,target_ms:t+100,edited_N:edited,reference_N:pred};
    });readPoint();
  }
  const rows=['transformer-combined','transformer-markers','marker-kernel','ridge-combined','current-plate-persistence'].map(k=>({
    short:names[k],mae:a.metrics[k].MAE_N,kind:k==='current-plate-persistence'?'privileged':'standard',primary:k==='transformer-combined'}));
  function drawBars(){el('bars').replaceChildren(ForceCharts.bars(rows,Math.max(270,Math.round(el('bars').clientWidth))));}
  function para(parent,text){const p=document.createElement('p');p.textContent=text;parent.append(p)}
  function results(){
    el('result-intro').textContent='Of 10 people reserved for this assessment, '+a.held_people+' contributed eligible recordings. Their '+a.held_trials+
      ' barefoot walks supplied '+a.held_anchors.toLocaleString('en-US')+
      ' overlapping predictions. Each measured target is the combined upward force recorded by two plates during slow walking at 0.4–0.8 m/s.';
    const both=a.metrics['transformer-combined'].MAE_N,kin=a.metrics['transformer-markers'].MAE_N;
    el('result-summary').textContent='With both signals, the Transformer missed the recorded load by '+both.toFixed(1)+
      ' N on average. With movement alone, it missed by '+kin.toFixed(1)+' N. '+(a.incremental_EMG_gate_passed?
      'Adding muscle signals met the prespecified improvement rule against all three comparisons.':
      'The combined model fell short of the prespecified improvement rule across the three comparisons. These walks do not establish that adding muscle signals improves the forecast.');
    const c=a.incremental_EMG_comparisons['wrong-repeat-emg'];
    el('strong-control').textContent= c.people ? 'Keeping each marker history and substituting the same person’s muscle signals from another walk gave '+c.comparator_MAE_N.toFixed(1)+' N error. Correctly paired signals gave '+c.combined_MAE_N.toFixed(1)+' N on those same '+c.anchors.toLocaleString('en-US')+' windows from '+c.people+' walkers.' : 'No eligible wrong-repeat pairs were available.';
    const s=el('stats');
    para(s,'Thirty people were designated for fitting. After the source quality check, 25 contributed 62 walks and 4,846 input windows. Ten other people were designated for assessment and a further ten remained unopened. Only trials whose source annotations identify reliable contacts on two distinct plates were retained. That choice limits the walks represented here. The supplied recordings were already cropped around walking events. Values near zero can also reflect the source processing: the code replaces missing force samples with zero and suppresses small forces around 50 N per plate. The paper describes a 5 N threshold.');
    para(s,'Errors are averaged within each walk, then within each person, then across people. RMSE squares the errors before averaging, then takes the square root, so large misses count more. Positive bias means the model estimated too much force.');
    const fmt=v=>Number.isFinite(v)?v.toFixed(2):'—';
    s.append(table(['Comparison','People','Walks','Windows','Mean absolute error (N)','RMSE (N)','Bias (N)'],Object.entries(a.metrics).map(([k,r])=>[names[k],r.people,r.trials,r.anchors,fmt(r.MAE_N),fmt(r.RMSE_N),fmt(r.bias_N)])));
    para(s,'To count as an improvement, the combined Transformer had to reduce error by at least 5% against each comparison, with the entire 95% interval for the difference below zero and at least eight people contributing. Intervals come from 10,000 resamples of whole people. Wrong-repeat muscle signals come from the same person at a similar pose in another walk. Poses can still differ.');
    s.append(table(['Combined minus comparison','People','Windows','Difference (N)','95% interval (N)','Error reduction','Met rule'],Object.entries(a.incremental_EMG_comparisons).map(([k,r])=>[names[k],r.people,r.anchors??0,fmt(r.difference_N),r.paired_95pct_bootstrap_N?.map(fmt).join(' to ')??'—',Number.isFinite(r.relative_reduction)?(100*r.relative_reduction).toFixed(1)+'%':'—',r.pass?'Yes':'No'])));
    para(s,'When both plates return a source-coded zero, the task differs from predicting a nonzero reading. The breakdown below is for the combined Transformer. People and walks can appear in both rows.');
    s.append(table(['Measured target','People','Walks','Windows','Mean absolute error (N)'],Object.entries(a.target_strata).map(([k,v])=>{const r=v['transformer-combined'];return [k==='nonzero'?'Nonzero':'Source-coded zero',r.people,r.trials,r.anchors,fmt(r.MAE_N)]})));
    para(s,'The nonlinear movement-only ridge compares marker paths with examples drawn from training walks. The measured assessment includes this control. Its training examples stay in the original dataset. Each of the six models in the invented-input experiment ships as fitted coefficients.');
    drawBars();
  }
  function save(name,body,type){
    const u=URL.createObjectURL(new Blob([body],{type}));const link=document.createElement('a');link.href=u;link.download=name;
    document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(u),2000);
    el('feedback').textContent='Saved '+name+'.';
  }
  function svgFile(node){
    const meta=document.createElementNS(node.namespaceURI,'metadata');meta.textContent=credit;node.append(meta);
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+new XMLSerializer().serializeToString(node)+'\n';}
  el('save-input').addEventListener('click',()=>{if(timer) compute();const d=currentHistory();save('walking-force-input.json',JSON.stringify(d,null,2)+'\n','application/json')});
  el('save-plot').addEventListener('click',()=>{
    if(timer)compute();
    const svg=ForceCharts.curve(series,cursor(),850,true,methodNames[method()]+' · '+modalityNames[modality()]+' · 100 ms ahead on the stored clock');
    const detail=document.createElementNS(svg.namespaceURI,'desc');detail.textContent=JSON.stringify({model:methodNames[method()],inputs:modalityNames[modality()],settings:settings(),weights_sha256:data.signatures[method()+'-'+modality()+'.npz']});svg.append(detail);
    save('invented-walk-load.svg',svgFile(svg),'image/svg+xml');
  });
  el('save-scores').addEventListener('click',()=>save('held-walkers-error.svg',svgFile(ForceCharts.bars(rows,670,true,a.held_people+' people, '+a.held_trials+' walks, '+a.held_anchors.toLocaleString('en-US')+' predictions.')),'image/svg+xml'));
  el('save-csv').addEventListener('click',()=>{
    if(timer)compute();
    const o=settings(),key=data.signatures[method()+'-'+modality()+'.npz'];
    const head='input_end_ms,target_ms,edited_N,reference_N,model,inputs,speed_m_per_s,marker_offset_cm,edit_channel,edit_gain,edit_shift_ms,weights_sha256,attribution';
    save('invented-walk-load.csv',head+'\n'+series.map(v=>[v.input_end_ms,v.target_ms,v.edited_N,v.reference_N,method(),modality(),o.speed,o.offset,o.channel,o.gain,o.shift,key,JSON.stringify(credit)].join(',')).join('\n')+'\n','text/csv');
  });
  const knobs=['speed','offset','channel','gain','shift','modality','method'];
  for(const id of knobs) el(id).addEventListener('input',()=>{cancelAnimationFrame(timer);timer=requestAnimationFrame(compute)});
  el('anchor').addEventListener('input',readPoint);el('inspect').addEventListener('change',updateInputs);
  el('reset').addEventListener('click',()=>{
    for(const [key,v] of Object.entries(e.defaults))el(key).value=v;
    el('anchor').value=24;el('inspect').value=24;el('feedback').textContent='Inputs reset.';compute();
  });
  let resize=0;window.addEventListener('resize',()=>{cancelAnimationFrame(resize);resize=requestAnimationFrame(()=>{drawCurve();drawBars()})});
  results();compute();
})();
