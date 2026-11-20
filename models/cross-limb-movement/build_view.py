"""Build the offline synthetic-event inspector from the single public inference graph."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
parts=[(P/'inference.mjs').read_text().replace('export const ','const ').replace('export function ','function ')]
for name,file in (('weights','model-joint.json'),('byBody','path-maps/s1641-f0-separate.json'),('byTime','path-maps/s1641-f0-matched.json'),('upper','synthetic-upper-amplitude.json'),('lower','synthetic-lower.json')):
    parts.append('const '+name+'='+json.dumps(json.loads((P/file).read_text()),separators=(',',':'))+';')
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Wrist and sacrum forecast | NeuroTranslation</title><style>
:root{color-scheme:light dark;font:100%/1.5 system-ui,sans-serif}body{max-width:52rem;margin:3rem auto;padding:0 1rem}h1{font-size:clamp(1.75rem,5vw,3rem);line-height:1.1}h2{font-size:1.22rem;margin:1.4rem 0 .4rem}select{font:inherit;padding:.35rem}table{font-variant-numeric:tabular-nums;border-collapse:collapse;margin:.4rem 0 1.2rem;width:100%}td,th{border-bottom:1px solid #8888;padding:.28rem .35rem;text-align:right}td:first-child,th:first-child{text-align:left}details{margin:1rem 0}summary{cursor:pointer}p{max-width:66ch}
</style><main><h1>Where does the marker go next?</h1><p>A shared temporal Transformer reads twenty bins of synthetic muscle and marker history and predicts the following 125 milliseconds. Each example uses its study’s own measurement frame.</p><label for="study">Synthetic example </label><select id="study"><option value="upper">Right wrist, light-cued lift</option><option value="lower">Sacrum, walking during visual rotation</option></select> <label for="maps">Movement model </label><select id="maps"><option value="original">Original shared model</option><option value="body">Wrist or pelvis map</option><option value="time">Early and late maps</option></select><p id="units"></p><h2>Predicted muscle activity</h2><table><thead><tr><th>Recorded channel</th><th id="amp">RMS</th></tr></thead><tbody id="rms"></tbody></table><h2>Predicted path</h2><p id="endpoint"></p><details><summary>Show all 32 positions</summary><table><thead><tr id="axes"></tr></thead><tbody id="path"></tbody></table></details><p>Distances are relative to the last observed marker position. The demo uses fitted weights, separate measurement scales and mathematical inputs. Group outcomes are in <a href="RESULTS.md">the results</a>.</p></main><script>
'''
script="""
const elem=(id)=>document.getElementById(id);
function cells(values,kind='td'){const row=document.createElement('tr');for(const value of values){const el=document.createElement(kind);el.textContent=value;row.append(el);}return row;}
function show(){
  const arm=elem('study').value==='upper', event=arm?upper:lower;
  const selected={original:weights,body:byBody,time:byTime}[elem('maps').value];
  const out=predict(selected,event), axes=arm?['X','Y','Z']:['ML','SI','AP'];
  const unit=arm?'WAY native units':'µV';
  elem('units').textContent=arm?'Four named right-arm channels are available in this example. WAY recorded their amplitude in source-native units.':'Eight leg channels are available. Their surface electrical amplitude is expressed in microvolts.';
  elem('amp').textContent='RMS ('+unit+')';
  elem('rms').replaceChildren(...out.rms.flatMap((x,i)=>x===null?[]:[cells([muscles[i],arm?x.toFixed(6):x.toFixed(3)])]));
  elem('endpoint').textContent='At 125 ms: '+axes.map((a,i)=>a+' '+out.path_mm[31][i].toFixed(3)+' mm').join(', ')+'.';
  elem('axes').replaceChildren(...cells(['Time (ms)',...axes.map(v=>v+' (mm)')],'th').children);
  elem('path').replaceChildren(...out.path_mm.map((row,i)=>cells([((i+1)*1000/256).toFixed(3),...row.map(x=>x.toFixed(3))])));
}
for (const id of ['study','maps']) elem(id).addEventListener('change',show);show();
"""
(P/'forecast.html').write_text(html+'\n'.join(parts)+script+'</script></html>\n')
