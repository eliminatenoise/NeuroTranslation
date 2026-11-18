import {parsePacket,parseCsv,validatePacket,combinePackets,summarizePackets,alignPackets,examplePacket,stringifyRecording} from './core.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.mjs';
import {normalizeFinite,buildPlotSegments} from './plot.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.mjs';
import {toPolicyEnvelope} from './packet-policy-bridge.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.mjs';
import {evaluate as evaluateMetadata} from './compat-policy.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.mjs';
import {renderMetadataReport} from './policy-report-view.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.mjs';
import {createPalmReplay} from './replay-view.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.mjs';
import {showCalibrationStudy} from './calibration-view.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.mjs';

const $=id=>document.getElementById(id);
const colors={neural:'#7757d8',muscle:'#cd6446',displacement:'#287dba',mechanics:'#278476'};
const sampleLabels={
  original:'Original sample',
  nearest:'Nearest sample',
  linear:'Linear interpolation',
  missing_input:'Missing in source',
  long_gap:'Gap exceeds limit',
  outside_range:'Outside recording range'
};
const state={packets:[],aligned:null,cursor:0,animationFrame:null,traces:[],metadata:null,metadataPackets:null};
const originalSelections = new WeakMap();
const isExample=()=>state.packets.length>0&&state.packets.every(p=>p.dataset.origin==='constructed_example');
const streams=()=>state.packets.flatMap(p=>p.streams.map(s=>({...s,dataset:p.dataset,originalStream:s})));
function element(tag,className,text){const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e;}
function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
function download(name,value){const blob=new Blob([stringifyRecording(value,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
const setReplayPackets = createPalmReplay({openImport, download});
const exactNumber = value => Object.is(value, -0) ? '-0' : String(value);
function stop(){
  if(state.animationFrame!==null)cancelAnimationFrame(state.animationFrame);
  state.animationFrame=null;
  $('play').textContent='▶';
  $('play').setAttribute('aria-label','Play aligned signals');
}
function clearAlignment(){stop();state.aligned=null;state.cursor=0;}
function getAlignedStreams(){return state.aligned?.streams||[];}
function renderMetadata(){
  if(state.metadataPackets!==state.packets){
    state.metadataPackets=state.packets;state.metadata=null;
    if(state.packets.length){
      try{const mapping=toPolicyEnvelope(state.packets);state.metadata={mapping,report:mapping.policyInput?evaluateMetadata(mapping.policyInput):null};}
      catch{state.metadata={mapping:{status:'blocked',diagnostics:[{message:'The metadata check could not finish. Your original samples are unchanged.'}]},report:null};}
    }
  }
  renderMetadataReport($('metadata-report'),state.metadata||{});
  const pending=state.metadata?.report?.descriptors?.filter(d=>d.status==='invalid'||d.reasons?.some(r=>r.severity!=='info')).length||0;
  const blocked=state.metadata&&(state.metadata.mapping.status!=='mapped'||state.metadata.report?.status!=='evaluated');
  $('metadata-summary').textContent=!state.packets.length?'Metadata checks · no recordings':blocked?'Metadata checks · needs attention':pending?`Metadata checks · ${pending} ${pending===1?'stream needs':'streams need'} more detail`:'Metadata checks · inspect the declarations';
  $('export-metadata').disabled=!state.metadata;
}
function render(){
  const all=streams();$('packet-count').textContent=`${state.packets.length} loaded`;
  $('example-notice').hidden=!isExample();
  for(const kind of Object.keys(colors)){
    const ss=all.filter(s=>s.modality===kind);$(`count-${kind}`).textContent=`${ss.length} stream${ss.length===1?'':'s'}`;
    $(`origin-${kind}`).textContent=ss.length?[...new Set(ss.map(s=>s.dataset.origin==='constructed_example'?'Example':s.origin))].join(' / '):'No data';
  }
  $('recording-list').replaceChildren();
  for(const p of state.packets){
    const card=element('article','recording-card'),top=element('div','recording-top');top.append(element('h3','',p.dataset.name));
    const remove=element('button','remove-recording','×');remove.setAttribute('aria-label',`Remove ${p.dataset.name}`);remove.addEventListener('click',()=>{state.packets=state.packets.filter(x=>x!==p);clearAlignment();render();message('Recording removed.');});top.append(remove);card.append(top);
    card.append(element('p','',p.dataset.origin==='constructed_example'?'Constructed software example':`${p.dataset.organism||'Unknown organism'} · subject: ${p.dataset.subjectId||'unknown'}`));
    card.append(element('p','',`Clock: ${p.dataset.timebase||'unknown'}`));
    const dots=element('div','type-dots');for(const modality of [...new Set(p.streams.map(s=>s.modality))]){const dot=element('span');dot.style.background=colors[modality];dot.title=modality;dots.append(dot);}card.append(dots);
    card.append(element('p','',`${p.streams.length} ${p.streams.length===1?'stream':'streams'} · ${p.streams.reduce((n,s)=>n+s.t.length,0).toLocaleString()} samples`));
    card.append(element('p','',`Partition: ${p.dataset.split||'unspecified'} · ${p.dataset.license||'permission unspecified'}`));
    $('recording-list').append(card);
  }
  $('neural-coverage').replaceChildren();
  for(const [region,label] of [['brain','Brain'],['spinal','Spinal'],['peripheral','Peripheral'],['autonomic','Autonomic'],['visceral','Visceral']]){
    const ss=all.filter(s=>s.modality==='neural'&&s.region===region);const measured=ss.filter(s=>s.origin==='measured'&&s.dataset.origin!=='constructed_example');
    const origins=[...new Set(ss.map(s=>s.dataset.origin==='constructed_example'?'Example':s.origin))];
    const row=element('div','regionrow');row.append(element('span','',label),element('span','',measured.length?`${measured.length} measured`:ss.length?origins.join(' / '):'No recording'));$('neural-coverage').append(row);
  }
  const unspecified=all.filter(s=>s.modality==='neural'&&!s.region).length;
  if(unspecified){const row=element('div','regionrow');row.append(element('span','','Region undeclared'),element('span','',`${unspecified} streams`));$('neural-coverage').append(row);}
  $('alignment-warnings').replaceChildren();
  const warnings=state.packets.length?summarizePackets(state.packets).warnings:[];
  $('alignment-warnings').hidden=!warnings.length;
  if(warnings.length){$('alignment-warnings').append(element('strong','','Check the recording metadata'));const list=element('ul');for(const warning of warnings)list.append(element('li','',warning));$('alignment-warnings').append(list);}
  const aligned=Boolean(state.aligned);$('mode-badge').textContent=aligned?'Aligned samples':'Original samples';
  $('alignment-caption').textContent=aligned?`${isExample()?'Example clock':'Declared common clock'} · ${state.aligned.t.length.toLocaleString()} points · ${$('method').selectedOptions[0].textContent}`:'Each trace uses its own declared clock. Cross-dataset synchronization has not been established.';
  const sampleCount=state.aligned?.t.length??0;
  $('playback').hidden=!aligned;
  $('show-originals').hidden=!aligned;
  $('play').disabled=sampleCount<2;
  $('cursor').disabled=sampleCount<2;
  $('cursor').max=Math.max(0,sampleCount-1);
  $('export').disabled=!aligned;
  $('align').disabled=!all.length;
  renderMetadata();renderTraces();setReplayPackets(state.packets);
}
function appendOriginalInspector(trace, plot, stream, name) {
  const original = stream.originalStream;
  const selection = originalSelections.get(original) ?? { index: 0, open: false };
  originalSelections.set(original, selection);
  const count = stream.t.length;
  const details = element('details', 'original-inspector');
  const summary = element('summary', '', 'Inspect original samples');
  summary.setAttribute('aria-label', `Inspect original samples for ${name}`);
  details.append(summary);

  const readout = element('p', 'original-reading');
  const position = element('span');
  const amplitude = element('strong');
  readout.append(position, amplitude);
  details.append(readout);
  const slider = element('input');
  slider.type = 'range';
  slider.min = '0';
  slider.max = String(count - 1);
  slider.step = '1';
  slider.value = String(selection.index);
  slider.disabled = count === 1;
  slider.setAttribute('aria-label', `Original sample for ${name}`);
  details.append(slider);
  const description = [];
  if (stream.measurement) description.push(stream.measurement);
  if (typeof stream.sourceUnit === 'string' && stream.sourceUnit.trim() && stream.sourceUnit !== stream.unit) {
    description.push(`The source file labels the unit “${stream.sourceUnit}”.`);
  }
  if (description.length) details.append(element('p', 'original-measurement', description.join(' · ')));

  const marker = element('span', 'sample-marker');
  marker.setAttribute('aria-hidden', 'true');
  plot.append(marker);
  function showSample() {
    const index = selection.index;
    const time = stream.t[index];
    const value = stream.values[index];
    position.textContent = `Sample ${index + 1} of ${count} · ${exactNumber(time)} s`;
    amplitude.textContent = value === null ? 'Missing in source' : `${exactNumber(value)} ${stream.unit}`;
    slider.setAttribute('aria-valuetext', `${position.textContent}, ${amplitude.textContent}`);
    marker.style.setProperty('--sample-position', `${100 * normalizeFinite(time, stream.t[0], stream.t.at(-1))}%`);
    marker.hidden = !details.open;
  }
  details.open = selection.open;
  slider.addEventListener('input', () => {
    selection.index = slider.valueAsNumber;
    showSample();
  });
  details.addEventListener('toggle', () => {
    selection.open = details.open;
    marker.hidden = !details.open;
  });
  showSample();
  trace.append(details);
}
function renderTraces(){
  $('traces').replaceChildren();state.traces=[];
  const ss=state.aligned?getAlignedStreams():streams();
  if(!ss.length){$('traces').append(element('p','empty','Import a recording or load the constructed example.'));return;}
  for(const s of ss){
    const duplicateChannel = ss.some(other => other.dataset.id === s.dataset.id && other.id !== s.id && other.label === s.label);
    const channelName = duplicateChannel ? `${s.label} (${s.id})` : s.label;
    const duplicateRecording = state.packets.some(p => p.dataset.id !== s.dataset.id && p.dataset.name === s.dataset.name);
    const recordingName = duplicateRecording ? `${s.dataset.name} (${s.dataset.id})` : s.dataset.name;
    const name = `${channelName} in ${recordingName}`;
    const origin = s.dataset.origin === 'constructed_example' ? 'constructed example' : s.origin;
    const trace=element('article','trace'),head=element('div','trace-head'),label=element('div');
    label.append(element('strong','',channelName),element('span','unit',s.unit));label.style.color=colors[s.modality];
    head.append(label,element('span','trace-origin',`${s.modality} · ${origin}`));trace.append(head);
    const plot=element('div','trace-plot');
    const canvas=element('canvas');
    canvas.setAttribute('role','img');
    canvas.setAttribute('aria-label',`${name}, ${s.unit}, ${origin} ${s.modality} signal`);
    plot.append(canvas);
    let marker,value,source;
    if(state.aligned){
      marker=element('span','sample-marker');
      marker.setAttribute('aria-hidden','true');
      plot.append(marker);
      const reading=element('p','sample-reading');
      value=element('strong','sample-value');
      source=element('span','sample-source');
      reading.append(value,source);
      head.append(reading);
    }
    trace.append(plot);
    const time=state.aligned?state.aligned.t:s.t;const clock=s.dataset?.timebase||'declared packet clock';
    const sourceName = state.packets.length > 1 ? recordingName + ' · ' : '';
    trace.append(element('p','trace-clock',`${sourceName}${time[0].toFixed(3)}–${time.at(-1).toFixed(3)} s · ${clock}${s.frame?` · frame: ${s.frame}`:''}`));
    if(!state.aligned) appendOriginalInspector(trace,plot,s,name);
    $('traces').append(trace);state.traces.push({canvas,marker,value,source,stream:s,time});
  }
  drawTraces();
  if(state.aligned)renderCursor();
}
function drawTraces(){
  for(const {canvas,stream,time} of state.traces){
    const width=Math.max(100,canvas.clientWidth),height=68,dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=width*dpr;canvas.height=height*dpr;
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,width,height);ctx.strokeStyle='#edf1f6';ctx.lineWidth=1;
    for(const fraction of [.25,.5,.75]){ctx.beginPath();ctx.moveTo(0,height*fraction);ctx.lineTo(width,height*fraction);ctx.stroke();}
    const values=stream.values;let low=Infinity,high=-Infinity;for(const v of values){if(v!==null&&Number.isFinite(v)){low=Math.min(low,v);high=Math.max(high,v);}}
    if(low===Infinity){ctx.fillStyle='#627181';ctx.font='10px Arial, sans-serif';ctx.fillText('No values to plot',10,36);continue;}
    const y=v=>height-8-normalizeFinite(v,low,high)*(height-16),x=i=>normalizeFinite(time[i],time[0],time.at(-1))*(width-1);
    ctx.strokeStyle=colors[stream.modality]||'#315ae6';ctx.lineWidth=1.35;
    // Bins retain extrema and break at missing samples; original/aligned values remain in export.
    for(const points of buildPlotSegments(values,Math.floor(width))){
      ctx.beginPath();ctx.moveTo(x(points[0]),y(values[points[0]]));
      for(const index of points.slice(1))ctx.lineTo(x(index),y(values[index]));ctx.stroke();
      if(points.length===1){ctx.fillStyle=colors[stream.modality]||'#315ae6';ctx.beginPath();ctx.arc(x(points[0]),y(values[points[0]]),1.4,0,Math.PI*2);ctx.fill();}
    }
    ctx.fillStyle='#9aa7b7';ctx.font='8px Arial, sans-serif';ctx.fillText(high.toPrecision(3),3,9);ctx.fillText(low.toPrecision(3),3,height-1);
  }
}
function renderCursor(){
  const grid=state.aligned.t;
  const index=state.cursor;
  const selectedTime=grid[index];
  const displayTime=Number(selectedTime.toPrecision(12));
  const position=normalizeFinite(selectedTime,grid[0],grid.at(-1))*100;
  $('cursor').value=index;
  $('cursor').setAttribute('aria-valuetext',`${displayTime} seconds, point ${index+1} of ${grid.length}`);
  $('cursor-time').textContent=`${displayTime} s`;
  $('cursor-time').title=`${selectedTime} s`;
  $('cursor-step').textContent=`${index+1} of ${grid.length}`;
  for(const {marker,value,source,stream} of state.traces){
    const sample=stream.values[index];
    marker.style.setProperty('--sample-position',`${position}%`);
    value.textContent=sample===null?'Missing':`${Number(sample.toPrecision(8))} ${stream.unit}`;
    value.title=sample===null?'':`${sample} ${stream.unit}`;
    source.textContent=sampleLabels[stream.status[index]];
  }
}
function selectSample(index){
  if(index===state.cursor)return;
  state.cursor=index;
  renderCursor();
}
function align(){
  try{
    stop();
    state.aligned=alignPackets(state.packets,{stepSeconds:Number($('step').value),maxGapSeconds:Number($('max-gap').value),method:$('method').value});
    state.cursor=0;render();
    const missing=getAlignedStreams().reduce((n,s)=>n+s.values.filter(v=>v===null).length,0);
    message(`${isExample()?'Constructed example aligned':'Aligned using your declared subject, recording and clock'}. ${missing.toLocaleString()} missing values retained. No samples extrapolated.`);
  }catch(error){clearAlignment();render();message(error.message||String(error),true);}
}
function loadExample(){state.packets=[validatePacket(examplePacket())];clearAlignment();render();align();}
function openImport(){$('import-error').textContent='';$('import-dialog').showModal();}
function setCsvMode(enabled){
  const fields=$('csv-fields');fields.hidden=!enabled;
  for(const control of fields.querySelectorAll('input,select'))control.disabled=!enabled;
}
setCsvMode(false);
$('load-example').addEventListener('click',loadExample);$('import-open').addEventListener('click',openImport);$('add-source').addEventListener('click',openImport);$('import-close').addEventListener('click',()=>$('import-dialog').close());
$('clear-all').addEventListener('click',()=>{state.packets=[];clearAlignment();render();message('Recordings cleared.');});
$('file').addEventListener('change',()=>setCsvMode(Boolean($('file').files[0]?.name.toLowerCase().endsWith('.csv'))));
$('import-form').addEventListener('submit',async event=>{
  event.preventDefault();$('import-error').textContent='';const file=$('file').files[0];if(!file)return;
  try{
    if(file.size>5*1024*1024)throw new Error('Use a file no larger than 5 MiB.');const text=await file.text();let packet;
    if(file.name.toLowerCase().endsWith('.csv')){
      const f=Object.fromEntries(new FormData(event.target));
      packet=parseCsv(text,{dataset:{id:f.datasetId,name:f.name,sourceUrl:f.sourceUrl,license:f.license,organism:f.organism,subjectId:f.subjectId,recordingId:f.recordingId,task:f.task,timebase:f.timebase,split:f.split},stream:{id:`${f.datasetId}-${f.modality}`,modality:f.modality,region:f.modality==='neural'?(f.region||undefined):undefined,label:f.label,unit:f.unit,frame:f.frame||undefined,origin:f.origin}});
    }else packet=parsePacket(text);
    const kept=isExample()&&packet.dataset.origin!=='constructed_example'?[]:state.packets;
    if(kept.some(p=>p.dataset.id===packet.dataset.id))throw new Error('That dataset ID is already loaded. Remove it first or use a distinct ID.');
    const prospective=[...kept,packet];
    if(prospective.reduce((n,p)=>n+p.streams.length,0)>64)throw new Error('This browser preview supports 64 selected streams. Import a smaller channel selection.');
    combinePackets(prospective); // Enforce aggregate byte/row/identity bounds before mutating UI state.
    state.packets=prospective;clearAlignment();render();$('import-dialog').close();$('import-form').reset();setCsvMode(false);message('Recording imported. Inspect its metadata, then align compatible recordings.');
  }catch(error){$('import-error').textContent=error.message||String(error);}
});
$('align').addEventListener('click',align);
$('show-originals').addEventListener('click',()=>{
  clearAlignment(); render();
  document.querySelector('.original-inspector summary')?.focus();
  message('Showing original samples on each recording’s clock.');
});
for(const id of ['step','max-gap','method'])$(id).addEventListener('change',()=>{clearAlignment();render();message('Settings changed. Align again to apply them.');});
$('cursor').addEventListener('input',()=>{stop();selectSample($('cursor').valueAsNumber);});
$('play').addEventListener('click',()=>{
  if(state.animationFrame!==null){stop();return;}
  const startedAt=performance.now();
  const startIndex=state.cursor;
  const count=state.aligned.t.length;
  $('play').textContent='Ⅱ';
  $('play').setAttribute('aria-label','Pause aligned signals');
  function tick(now){
    const steps=Math.floor(Math.max(0,now-startedAt)*count/10000);
    selectSample((startIndex+steps)%count);
    state.animationFrame=requestAnimationFrame(tick);
  }
  state.animationFrame=requestAnimationFrame(tick);
});
$('export').addEventListener('click',()=>{if(state.aligned)download('neurotranslate-0.0-aligned.json',{application:'NeuroTranslate 0.0',operation:'declared-clock alignment, not learned translation',example:isExample(),sourcePackets:state.packets,alignment:state.aligned,metadataCheck:state.metadata});});
$('export-metadata').addEventListener('click',()=>{if(state.metadata)download('neurotranslate-0.0-inspection.json',{application:'NeuroTranslate 0.0',operation:'Original source samples and metadata checks; no pairing or learned translation',example:isExample(),sourcePackets:state.packets,metadataCheck:state.metadata});});
$('download-template').addEventListener('click',()=>download('neurotranslate-0.0-example.json',examplePacket()));
window.addEventListener('resize',drawTraces);
async function catalogue(){
  try{const response=await fetch('datasets.d4915a6997132b045e9706ddf362c5bde1d1aa0c3d3ff82bdb2aaeb4f2f43d9b.json');if(!response.ok)return;const data=await response.json();for(const d of data.datasets||data){const card=element('article','dataset-card');card.append(element('h3','',d.name),element('p','',d.modalities?.join(' · ')||d.modality||''),element('p','',d.description||d.coverage||''),element('p','catalogue-limit',d.limit||d.pairingLimit||''));card.append(element('p','',`Reference metadata · ${(d.license||[]).join(', ')} · recordings not included`));if(d.url&&/^https:\/\//i.test(d.url)){const link=element('a','',`Source ↗`);link.href=d.url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}$('catalogue-list').append(card);}$('catalogue-section').hidden=!$('catalogue-list').children.length;}catch{/* Optional catalogue is independent of data import and alignment. */}
}
loadExample();catalogue();showCalibrationStudy();
