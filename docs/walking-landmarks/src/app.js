(() => {
  'use strict';
  const el=id=>document.getElementById(id);
  const label={
    transformer_combined:'Transformer · markers + muscle',transformer_markers:'Transformer · markers only',
    ridge_combined:'Linear · markers + muscle',ridge_markers:'Linear · markers only',velocity:'Constant marker velocity',
    persistence:'Stay in place',phase:'Walking-phase template',personal:'Previous walk by this person',wrong_emg:'Muscle from an earlier repeat'
  };
  const num=(x,n=1)=>Number.isFinite(x)?x.toFixed(n):'—';
  const signed=x=>x>0?'+'+num(x):num(x);
  function row(body,values) {
    const tr=document.createElement('tr');
    values.forEach((v,i)=>{const cell=document.createElement(i?'td':'th');if(!i)cell.scope='row';cell.textContent=v;tr.append(cell)});
    body.append(tr);
  }
  const report = WALK_DATA.report, all=report.all_anchors, later=report.later_repeat_anchors;
  const m=all.transformer_combined, lin=all.ridge_markers, mm=x=>num(x)+' mm';
  const speed=all.velocity;
  const cv=m.coverage;
  el('evidenceIntro').textContent='Thirty walkers supplied the training data. In a separate group of '+cv.people+' walkers, the models made forecasts at '+cv.cutoffs.toLocaleString('en-US')+' points across '+cv.trials+' recorded walks. The error is the straight-line distance between the predicted and recorded endpoint. Each walker and each landmark carry equal weight in the overall mean. The intervals come from resampling whole walkers.';
  const muscleClaim=report.gates.incremental_emg?'The muscle signal passed both tests for added information.':'The muscle signal missed at least one of the two required tests for added information.';
  const transClaim=report.gates.transformer_advantage?'The combined Transformer met the required comparisons against all controls.':'The combined Transformer missed at least one required comparison with a simpler predictor.';
  el('outcome').textContent='The combined Transformer missed by '+mm(m.mean_mm)+' on average. A linear model using markers alone missed by '+mm(lin.mean_mm)+' and constant velocity by '+mm(speed.mean_mm)+'. '+muscleClaim+' '+transClaim;
  const ordered=[...LandmarkPredictor.models,'phase'];
  for(const key of ordered) {
    const r=all[key];row(el('summary').tBodies[0],[label[key],num(r.mean_mm),r.ci95_mm.map(x=>num(x)).join(' – ')]);
    el('measure').add(new Option(label[key],key));
  }
  function detailResults() {
    const r=all[el('measure').value];
    el('people').replaceChildren();el('joints').replaceChildren();
    r.walker_mean_quartiles_mm.forEach((v,i)=>row(el('people'),[['25th','50th (median)','75th'][i],num(v)]));
    Walk.names.forEach((name,i)=>{
      const rj=r.by_landmark[Walk.sourceLabels[i]];
      row(el('joints'),[name,num(rj.mean_mm),rj.ci95_mm.map(x=>num(x)).join(' – ')]);
    });
  }
  detailResults();el('measure').addEventListener('change',detailResults);
  function paragraph(id,str){const p=document.createElement('p');p.textContent=str;el(id).append(p)}
  paragraph('controlsText','For each comparison below, subtract the other predictor’s error from that of the combined Transformer. A negative difference favours the Transformer. The prespecified rule required a negative mean, a 95% interval entirely below zero and improvements in at least 70% of the walkers compared.');
  paragraph('controlsText','The phase template uses an annotated foot event and the time since that event. The personal control matches the current marker history to a previous walk by the same person. The wrong-muscle control keeps the markers and substitutes muscle activity from the preceding repeat. Those last two comparisons cover only later repeats with eligible targets.');
  const ctable=document.createElement('table'), caption=ctable.createCaption();caption.textContent='Combined Transformer minus each comparator';
  const head=ctable.createTHead().insertRow();['Comparator','Difference (mm)','95% interval (mm)','Improved walkers','Rule'].forEach(v=>{const th=document.createElement('th');th.textContent=v;head.append(th)});
  const cb=ctable.createTBody();for(const [key,comp] of Object.entries(report.combined_transformer_minus_comparator))
    row(cb,[label[key],signed(comp.mean_mm),comp.ci95_mm.map(signed).join(' to '),comp.walkers_improved+' / '+comp.walkers_compared,comp.passes?'Passed':'Missed']);
  const sc=document.createElement('div');sc.className='scroll';sc.append(ctable);el('controlsText').append(sc);
  paragraph('controlsText','On the later-repeat set, the normal combined Transformer missed by '+mm(later.transformer_combined.mean_mm)+', the wrong-muscle prediction by '+mm(later.wrong_emg.mean_mm)+' and the personal template by '+mm(later.personal.mean_mm)+'. Paired differences above use the same valid targets for each comparison.');
  const direction=WALK_DATA.direction, aligned=direction.transformer_minus_personal;
  paragraph('controlsText','Exploratory direction check. Walkers turned round between some recordings. Ten of 20 successive pairs ran in opposite laboratory directions. A follow-up analysis aligned travel directions before comparison. Mean errors fell to '+mm(direction.all_anchor_phase.mean_mm)+' for the phase template and '+mm(direction.later_repeat_personal.mean_mm)+' for the previous-walk template. On the later-repeat set, the combined Transformer minus this aligned personal template was '+signed(aligned.mean_mm)+' mm (95% interval '+aligned.ci95_mm.map(signed).join(' to ')+' mm). The interval crosses zero. This follow-up was prompted by the primary scores.');
  Walk.names.forEach((s,i)=>el('landmark').add(new Option(s,''+i)));
  const canvas=el('scene'), cam=LandmarkScene.presets;
  let state={}, yaw=cam.Oblique[0], tilt=cam.Oblique[1], picked='Oblique', frame=0, interval=0, dragging=null;
  const options=()=>Object.fromEntries(['phase','speed','cadence','gain'].map(k=>[k,Number(el(k).value)]));
  function draw() {
    frame=0;if(!state.sample)return;
    LandmarkScene.render(canvas,{...state,yaw,tilt,selected:Number(el('landmark').value),trails:el('trails').checked,
      forecasts:el('forecasts').checked,future:el('future').checked});
  }
  function drawSoon(){if(!frame)frame=requestAnimationFrame(draw)}
  function numbers() {
    const i=Number(el('landmark').value),d=state.delta[i],last=state.sample.observed[39],next=state.sample.next;
    el('detailheading').textContent=Walk.names[i]+' · 200 ms forecast';
    el('strip').textContent='X '+signed(d[0])+' mm   ·   Y '+signed(d[1])+' mm   ·   Z '+signed(d[2])+' mm';
    el('distance').textContent=mm(Walk.mag(d));el('miss').textContent=mm(Walk.mag(Walk.minus(Walk.plus(last[i],d),next[i])));
    el('coordRows').replaceChildren();Walk.names.forEach((name,k)=>{
      const disp=state.delta[k],miss=Walk.mag(Walk.minus(Walk.plus(last[k],disp),next[k]));
      row(el('coordRows'),[name,...disp.map(signed),num(miss)]);
    });
    drawSoon();
  }
  function update() {
    const o=options(),sample=Walk.sample(o),delta=LandmarkPredictor.predict(sample.observed,sample.envelopes,el('model').value,WALK_DATA.weights);
    if(!delta.flat().every(Number.isFinite))throw Error('Invalid model output');
    state={sample,delta,mesh:LandmarkScene.skin(sample.body)};
    el('phaseval').textContent=o.phase+'%';el('speedval').textContent=o.speed.toFixed(2)+' m/s';
    el('cadenceval').textContent=o.cadence+' steps/min';el('gainval').textContent=o.gain.toFixed(2)+'×';
    numbers();
  }
  function selectView(name) {
    picked=name;if(cam[name]) [yaw,tilt]=cam[name];
    document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===name)));drawSoon();
  }
  function orbit(dx,dy) {yaw+=dx;tilt=Math.max(-.36,Math.min(Math.PI/2,tilt+dy));selectView('Custom')}
  function stop() {if(interval)clearInterval(interval);interval=0;el('play').textContent='Play stride';el('play').setAttribute('aria-pressed','false')}
  el('play').addEventListener('click',()=>{
    if(interval){stop();return}
    el('play').textContent='Pause';el('play').setAttribute('aria-pressed','true');
    // Advance one percent of a cycle per tick, slowly enough to inspect a forecast.
    interval=setInterval(()=>{el('phase').value=(Number(el('phase').value)+1)%101;update()},85);
  });
  el('reset').addEventListener('click',()=>{stop();for(const id of ['phase','speed','cadence','gain'])el(id).value=el(id).defaultValue;
    el('model').selectedIndex=0;el('landmark').selectedIndex=0;for(const k of ['future','forecasts','trails'])el(k).checked=true;selectView('Oblique');update()});
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>selectView(b.dataset.view)));
  for(const id of ['phase','cadence','speed','gain'])el(id).addEventListener('input',update);
  el('model').addEventListener('change',update);el('landmark').addEventListener('change',numbers);
  for(const id of ['trails','forecasts','future'])el(id).addEventListener('change',drawSoon);
  canvas.addEventListener('pointerdown',e=>{dragging=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)});
  canvas.addEventListener('pointermove',e=>{if(!dragging)return;orbit((e.clientX-dragging[0])*.009,(e.clientY-dragging[1])*.007);dragging=[e.clientX,e.clientY]});
  for(const ev of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(ev,()=>{dragging=null});
  canvas.addEventListener('keydown',e=>{const keys={ArrowLeft:[-.1,0],ArrowRight:[.1,0],ArrowUp:[0,.1],ArrowDown:[0,-.1]};
    if(keys[e.key]){e.preventDefault();orbit(...keys[e.key])}});
  new ResizeObserver(drawSoon).observe(canvas);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop()});
  update();
})();
