(function () {
  'use strict';
  const E = MuscleMotionExperiment, plots = MuscleMotionPlots;
  const $ = id => document.getElementById(id);
  const currentRadio = name => Number(document.querySelector('input[name="' + name + '"]:checked').value);
  const setRadio = (name, value) => {document.querySelector('input[name="' + name + '"][value="' + value + '"]').checked = true;};
  const compareNames = {specialists:'Specialists',repeat:'Repeat',stationary:'Stationary',velocity16:'16-step velocity',velocity32:'32-step velocity'};
  const n = (v, places = 2) => (Math.abs(v) < 0.5 * 10 ** -places ? 0 : v).toFixed(places);
  let base, current, joint, specialists, other;
  function drawPlots() {
    if (!current || !joint || !other) return;
    const i = Number($('sample').value), row = joint.future_path_mm[i-1];
    $('sample-time').textContent = n(i * 1000 / 256, 1) + ' ms · ' + i + '/32';
    $('coordinates').replaceChildren(...E.axes.map((a, k) => {
      const s = document.createElement('span'); s.textContent = a + ' ' + n(row[k]) + ' mm'; return s;
    }));
    plots.drawPath($('path-plot'),current,joint.future_path_mm,other.future_path_mm,$('view').value,i);
    plots.drawSignal($('signal-plot'),current,Number($('channel').value));
  }
  function meshTable(id,rows) {
    const frag = document.createDocumentFragment();
    for (const row of rows) {
      const tr = document.createElement('tr');
      for (const [i,v] of row.entries()) {
        const cell = document.createElement(i===0 ? 'th' : 'td');
        if (i===0) cell.scope='row'; cell.textContent=v; tr.append(cell);
      }
      frag.append(tr);
    }
    $(id).tBodies[0].replaceChildren(frag);
  }
  function plotBars(prev) {
    const all = [...joint.future_rms_uv,...other.future_rms_uv,...prev];
    const high = Math.max(.1,...all), low = Math.min(0,...all), range = high-low;
    const f = v => (v-low)*100/range;
    const rows = E.names.concat(E.names).map((label,i) => {
      const row=document.createElement('div'); row.className='bar-row';
      const name=document.createElement('span'), side=document.createElement('span');
      side.className='bar-side';side.textContent=i<4 ? 'L' : 'R';name.append(side, label);
      const track=document.createElement('div'); track.className='bar-track';
      [['j',joint.future_rms_uv[i]],['b',other.future_rms_uv[i]]].forEach(([k,v]) => {
        const bar=document.createElement('i');bar.className=k;bar.style.width=Math.abs(v)*100/range+'%';
        bar.style.marginLeft=f(Math.min(v,0))+'%';track.append(bar);
      });
      const h=document.createElement('i'); h.className='h';h.style.left='calc('+f(prev[i])+'% - 1px)';
      track.append(h);row.append(name,track);return row;
    });
    $('bars').replaceChildren(...rows);
    $('bar-max').previousElementSibling.textContent=n(low)+' µV';
    $('bar-max').textContent=n(high)+' µV';
  }
  function renderComparison() {
    if (!joint) return;
    const method=$('comparison').value;
    other = method==='specialists' ? specialists : E.reference(current,method);
    document.querySelectorAll('[data-compare]').forEach(el=>{el.textContent=compareNames[method];});
    const prev=E.previousRms(current.leg_uv);
    plotBars(prev);
    meshTable('emg-table',E.labels.map((label,i)=>[label,n(prev[i]),n(joint.future_rms_uv[i]),n(other.future_rms_uv[i])]));
    meshTable('path-table',joint.future_path_mm.map((p,i)=>[n((i+1)*1000/256,1),...Array.from(p,x=>n(x,3)),...Array.from(other.future_path_mm[i],x=>n(x,3))]));
    drawPlots();
  }
  function forecast(val) {
    const j=MuscleMotion.predict(MuscleMotionWeights,val,'joint');
    const s=MuscleMotion.predict(MuscleMotionWeights,val,'specialists');
    if (!E.validOutput(j) || !E.validOutput(s)) throw Error('This numeric range produced a nonfinite forecast. Reduce the invented magnitudes.');
    return [j,s];
  }
  function renderInput() {
    const lf=Number($('leg-scale').value)/100, pf=Number($('path-scale').value)/100;
    $('leg-factor').textContent=n(lf)+'×'; $('path-factor').textContent=n(pf)+'×';
    try {
      const val=E.scaled(base,currentRadio('posture'),currentRadio('direction'),lf,pf);
      const [j,s]=forecast(val);
      current=val; joint=j; specialists=s;
      $('message').textContent=''; document.querySelector('.forecast-grid').hidden=false;
      $('raw').value=JSON.stringify(current);
      renderComparison();
    } catch(e) {
      $('message').textContent=e.message;
      document.querySelector('.forecast-grid').hidden=true; current=joint=specialists=other=null;
    }
  }
  function reset() {
    base=E.validate(MuscleMotionStudy.example);
    $('leg-scale').value=$('path-scale').value='100';$('view').value='3d';$('channel').value='0';$('sample').value='32';
    $('comparison').value='specialists';setRadio('posture',base.posture);setRadio('direction',base.direction);
    $('edit-report').textContent='';renderInput();
  }
  function apply() {
    const report=$('edit-report');
    try {
      const d=E.validate(JSON.parse($('raw').value));
      forecast(d);
      base=d; $('leg-scale').value=$('path-scale').value='100';
      setRadio('posture',d.posture);setRadio('direction',d.direction);renderInput();
      report.textContent='Applied 160 samples.';delete report.dataset.error;
    } catch(e) {
      report.textContent='Input was not applied. '+e.message;report.dataset.error='';
    }
  }
  try {
    for (const [k,name] of E.labels.entries()) $('channel').add(new Option(name,k));
    $('download').hidden = !/^https?:$/.test(location.protocol);
    $('comparison').addEventListener('change',renderComparison);
    document.querySelectorAll('input[name="posture"],input[name="direction"]').forEach(el=>el.addEventListener('change',renderInput));
    for (const id of ['leg-scale','path-scale']) $(id).addEventListener('input',renderInput);
    for (const id of ['sample','view','channel']) $(id).addEventListener('input',drawPlots);
    $('signal-plot').closest('details').addEventListener('toggle',drawPlots);
    $('reset').addEventListener('click',reset);$('apply').addEventListener('click',apply);
    const observer=new ResizeObserver(drawPlots);
    observer.observe($('path-plot'));observer.observe($('signal-plot'));
    reset();
  } catch(e) {
    $('message').textContent='The model could not open. Extract every file from the ZIP together. '+e.message;
    document.querySelector('.forecast-grid').hidden=true;
  }
})();
