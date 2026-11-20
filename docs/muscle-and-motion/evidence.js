(function () {
  'use strict';
  const s = MuscleMotionStudy.evaluation, E = MuscleMotionExperiment;
  const f = v => (Math.abs(v) < .0005 ? 0 : v).toFixed(3);
  const signed = v => (v > 0 ? '+' : '') + f(v);
  const area = document.getElementById('study-results');
  function node(tag,text) { const el=document.createElement(tag); if(text!==undefined) el.textContent=text; return el; }
  function table(labels,rows,id) {
    const box=node('div');box.className='table-box';
    const tb=node('table');tb.id=id;box.append(tb);
    const hr=tb.createTHead().insertRow();
    for (const l of labels) {const cell=node('th',l);cell.scope='col';hr.append(cell);}
    const body=tb.createTBody();
    for(const row of rows) {
      const r=body.insertRow();row.forEach((v,i)=>{const c=node(i===0?'th':'td',v);if(i===0)c.scope='row';r.append(c);});
    }
    return box;
  }
  function detail(title,nodes) {
    const d=node('details');d.append(node('summary',title),...nodes);return d;
  }
  const lower = s.joint_advantage ? 'The joint model cleared both thresholds.' : 'The joint model fell short of the two-outcome test.';
  area.append(node('p','The model learned from 18 development participants. In the assessment, '+s.people+' people contributed '+s.events.toLocaleString('en-US')+' qualifying rotations with both directions and both postures. Earlier work had used their walking recordings for another outcome. Their standing records and these paired prediction targets were new to this comparison. Six reserve participants were kept aside.'));
  const delta = s.joint_minus_specialists;
  area.append(node('h3', lower),node('p','One Transformer learned both outputs. Each specialist used the same backbone and update schedule but learned one output. For the joint model to win, its error had to be lower for both muscle voltage and marker motion, with both upper uncertainty bounds below zero.'));
  const pair=node('div');pair.className='result-pair';
  for(const [key,label,unit] of [['muscle_mae_uv','Muscle voltage error','µV'],['path_mean_distance_mm','Marker path error','mm']]) {
    const d=delta[key],box=node('section');
    box.append(node('div',label+' · joint minus specialists'),node('strong',signed(d.mean)+' '+unit),
      node('p','95% interval '+signed(d.ci95[0])+' to '+signed(d.ci95[1])+' '+unit+'. Joint error was lower for '+d.people_lower+' of '+s.people+' people.'));
    pair.append(box);
  }
  area.append(pair,node('p','Intervals resample whole people together 5,000 times. The high end of each 95% interval is also the one-sided 97.5% upper bound used for the two-outcome test. The small number of people limits the precision of both estimates.'));
  const methods=[['joint','Joint Transformer'],['specialists','Separate specialists'],['hold_repeat32','Previous RMS + repeat path'],['hold_stationary','Previous RMS + stationary marker'],['hold_velocity16','Previous RMS + 16-step velocity'],['hold_velocity32','Previous RMS + 32-step velocity'],['posture_cue_typical','Typical future for posture and cue'],['linear','Regularized linear history model']];
  area.append(node('h3','Error against the recordings'),node('p','Voltage error averages the absolute RMS difference over eight muscles. Path error averages the three-dimensional distance from the measured marker over 32 time points. The final column checks the last position alone. Smaller values are better in each column.'));
  const wrap=node('div');wrap.className='results-wrap';
  wrap.append(table(['Forecast','Voltage (µV)','Path (mm)','Endpoint (mm)'],methods.map(([k,label])=>[label,...s.methods[k].map(f)]),'held-errors'));
  area.append(wrap);
  const l=s.joint_minus_linear;
  const ci=(x,unit)=>signed(x[0])+' to '+signed(x[1])+' '+unit;
  area.append(node('p','Compared with the linear history model, the joint Transformer reduced mean voltage error by '+f(-l.mean_difference[0])+' µV and mean path error by '+f(-l.mean_difference[1])+' mm. All six people improved on both measures. The paired 95% intervals for joint minus linear were '+ci(l.ci95[0],'µV')+' and '+ci(l.ci95[1],'mm')+'.'));
  const sh=s.swapped_minus_correct_history;
  area.append(detail('What happens with a different event’s muscle signal?',[
    node('p','For '+String(s.swapped_events.toLocaleString('en-US'))+' rotations, the model kept the original marker history and replaced the eight voltage channels together with readings from a different nonoverlapping rotation. The donor matched the person, posture, visual cue and third of the session.'),
    node('p','Swapping the voltages raised mean RMS forecast error by '+f(sh.muscle_mae_uv.mean)+' µV (95% interval '+ci(sh.muscle_mae_uv.ci95,'µV')+') and mean path error by '+f(sh.path_mean_distance_mm.mean)+' mm ('+ci(sh.path_mean_distance_mm.ci95,'mm')+'). This checks whether correctly paired electrical history carries predictive information under the study conditions.')
  ]));
  const postureRows=[];
  for(const [k,label] of [['stand','Standing'],['walk','Walking']]) {
    const p=s.postures[k];
    for(const [m,title] of [['joint','Joint'],['specialists','Specialists']]) postureRows.push([label+' · '+title,p.events,...p[m].map(f)]);
  }
  area.append(detail('Errors by posture',[table(['Posture and model','Rotations','Voltage (µV)','Path (mm)','Endpoint (mm)'],postureRows,'posture-errors')]));
  const g=s.group_means;
  area.append(detail('Measured and forecast group averages',[
    node('p','Each person contributes equally. Within a person, standing and walking contribute equally, and each rotation direction contributes equally within a posture. The tables compare those group averages. Opposite errors can cancel here, so use the error table above to judge forecast accuracy.'),
    node('h3','Next-window muscle voltage (RMS µV)'),
    table(['Muscle','Measured','Joint','Specialists'],E.labels.map((name,i)=>[name,f(g.observed_rms[i]),f(g.joint_rms[i]),f(g.specialists_rms[i])]),'observed-emg'),
    node('h3','Next-window marker displacement (mm)'),
    node('p','Each cell lists ML, SI and AP in source-axis order. Positions are relative to the last observed point.'),
    table(['Time (ms)','Measured','Joint','Specialists'],g.observed_path.map((r,i)=>[((i+1)*1000/256).toFixed(1),...[r,g.joint_path[i],g.specialists_path[i]].map(a=>a.map(f).join(', '))]),'observed-path')
  ]));
})();
