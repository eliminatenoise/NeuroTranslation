(() => {
  const {models, cases, names, labels, results} = window.MUSCLE_STUDY;
  const el = id => document.getElementById(id);
  function options(node, entries) {
    for (const [value, title] of entries) node.add(new Option(title, value));
  }
  options(el('case'),cases.map((c,i)=>[String(i),c.title]));
  options(el('muscle'),names.map((n,i)=>[String(i),labels[n] || n.replaceAll('_',' ')]));
  el('muscle').value=String(names.indexOf('bicep_lh'));
  el('result').textContent=results;
  const ns='http://www.w3.org/2000/svg';
  function svg(tag, attrs, text) {
    const child=document.createElementNS(ns,tag);
    for(const [k,v] of Object.entries(attrs)) child.setAttribute(k,String(v));
    if(text!==undefined) child.textContent=text;
    el('chart').append(child);
  }
  function changes(c, arm, scale, muscle) {
    // The fitted map is linear in displacement with pose-dependent coefficients.
    // Averaging its three seed predictions is equivalent to mapping their average path.
    const anchor=c.anchor.map((v,i)=>(v-models.anchor_mean[i])/models.anchor_sd[i]);
    return c[arm].map(row=>{
      const dx=row.map((v,i)=>scale*v/models.motion_rms[i]);
      const features=dx.concat(dx.flatMap(v=>anchor.map(p=>v*p)));
      return 1000*features.reduce((s,x,i)=>s+x*models.geometry[i][muscle],0);
    });
  }
  function draw(estimated, reference) {
    const chart=el('chart');chart.replaceChildren();
    const values=[0,...estimated,...(reference || [])];
    const low=Math.min(0,...values), high=Math.max(0,...values);
    const pad=Math.max(.025,(high-low)*.12);
    const left=83,right=674,top=25,bottom=215;
    const X=i=>left+(right-left)*i/10, Y=v=>bottom-(v-low+pad)/(high-low+2*pad)*(bottom-top);
    for(let j=0;j<=4;j++){
      const t=low-pad+(high-low+2*pad)*j/4, y=Y(t);
      svg('line',{x1:left,x2:right,y1:y,y2:y,stroke:'#d2ddda'});
      svg('text',{x:left-8,y:y+4,'text-anchor':'end',fill:'#3d5355','font-size':16},t.toFixed(2));
    }
    svg('line',{x1:left,x2:right,y1:Y(0),y2:Y(0),stroke:'#889d99'});
    for(let t=0;t<=100;t+=20) svg('text',{x:X(t/10),y:bottom+24,'text-anchor':'middle','font-size':16,fill:'#3d5355'},t);
    const trace=(v,stroke,dash)=>svg('polyline',{points:[0,...v].map((z,i)=>X(i)+','+Y(z)).join(' '),fill:'none',stroke,'stroke-width':3.5,'stroke-dasharray':dash});
    if(reference)trace(reference,'#ab4a18','7 5');
    trace(estimated,'#006b60','none');
    svg('text',{x:left,y:17,'font-size':16,fill:'#3d5355'},'mm');
    svg('text',{x:(left+right)/2,y:263,'text-anchor':'middle','font-size':16,fill:'#3d5355'},'Time since last input position (ms)');
  }
  function addRow(parent, tag, values) {
    const tr=document.createElement('tr');
    for(const v of values){const c=document.createElement(tag);c.textContent=v;tr.append(c);}
    parent.append(tr);
  }
  function render(){
    const c=cases[Number(el('case').value)],m=Number(el('muscle').value),arm=el('arm').value;
    const scale=Number(el('scale').value)/100,edited=scale!==1;
    const predicted=changes(c,arm,scale,m),reference=edited?null:c.reference.map(r=>1000*r[m]);
    el('identity').textContent=c.description;
    el('scaleText').textContent=Math.round(scale*100)+'%';
    el('refLegend').hidden=edited;
    el('endpoint').textContent=predicted[9].toFixed(3)+' mm at 100 ms';
    el('description').textContent=edited?'This is an edited movement. The curve shows the model calculation for that path; the original recording supplies no matching outcome.':arm==='measured_path'?'The cameras and handle had already recorded these positions at the end of the reach window. This curve tests the length calculation with the movement supplied.':'The solid line uses information available before the movement window. The dashed line shows the change in the original OpenSim arm model for this same reach.';
    draw(predicted,reference);
    el('head').replaceChildren();el('rows').replaceChildren();
    addRow(el('head'),'th',['Time (ms)','Estimate (mm)',...(edited?[]:['OpenSim (mm)'])]);
    predicted.forEach((v,i)=>addRow(el('rows'),'td',[10*(i+1),v.toFixed(5),...(edited?[]:[reference[i].toFixed(5)])]));
  }
  for (const name of ['case','muscle','arm','scale'])el(name).addEventListener('input',render);
  el('case').addEventListener('change',()=>{el('scale').value=100;render()});
  el('restore').addEventListener('click',()=>{el('scale').value=100;render()});
  render();
})();
