"""Pack the weights and invented example into a browser page that opens offline."""
from pathlib import Path
import json

p = Path(__file__).resolve().parent
shell = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Forecast a walking marker history · NeuroTranslation</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f7f7f4;color:#202924;font:17px/1.5 Inter,Arial,sans-serif}
main{max-width:52rem;margin:6vh auto;padding:1.75rem}h1{font-size:clamp(2rem,6vw,3.9rem);line-height:1.02;letter-spacing:-.05em;margin:.2em 0 .35em}
h2{font-size:1.18rem}p{max-width:58ch}section{padding:1.2rem 0;border-top:1px solid #acb6ad}
fieldset{border:0;padding:0;margin:0 0 .7em}label{display:inline-block;margin-right:1.1em;padding:.35em 0}
legend,th{font-weight:650}th,td{text-align:right;padding:.55em .3em;border-bottom:1px solid #cdd1cb}
th:first-child{text-align:left}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
input::file-selector-button,button{font:inherit;color:inherit;background:white;border:1px solid #839185;padding:.25em .55em;border-radius:.3em}
label,input[type=file]{max-width:100%}input[type=file]{width:100%}fieldset{min-inline-size:0}@media(max-width:400px){main{padding:1rem;margin:1rem auto}th,td{font-size:.9em}}small{font-size:.85em}#status{color:#395745;font-weight:650}
</style></head><body><main>
<h1>Forecast a walking marker history</h1>
<p>Watch the pelvis and right heel for 200 milliseconds. How far will each move in the next 100?</p>
<section><h2>Motion through the cutoff</h2>
<p id="status" role="status"></p>
<label>Load a local JSON window <input id="file" type="file" accept=".json,application/json"></label>
<button id="reset">Use invented example</button>
<p><small>Supply 21 frames in the walking coordinate system. The README gives the millimetre input format. Your file stays in this browser.</small></p>
</section><section><fieldset><legend>Instruction supplied to the model</legend>
<label><input type="radio" name="condition" value="4" checked> As usual</label>
<label><input type="radio" name="condition" value="5"> Fast but not running</label>
<label><input type="radio" name="condition" value="null"> Withhold</label></fieldset>
<table aria-label="Predicted signed displacement in millimetres"><caption>Predicted displacement in millimetres</caption>
<thead><tr><th scope="col">Landmark</th><th scope="col">Forward</th><th scope="col">Left</th><th scope="col">Up</th></tr></thead>
<tbody id="values"></tbody></table>
<p>Withholding the instruction uses a second model trained on motion and elapsed time. For ten people held out of fitting, neither landmark showed a clear gain from adding the instruction. The invented example has no measured future.</p></section></main>
<script src="predict.js"></script><script>
const weights=__WEIGHTS__, example=__EXAMPLE__;
const statusText=document.querySelector('#status'), values=document.querySelector('#values');
let current=example.input, description="Invented example";
function selected(){return JSON.parse(document.querySelector('input[name=condition]:checked').value);}
function display(){
  const deltas=WalkingForecast.predict(weights,{...current,instruction:selected()});
  values.replaceChildren();
  for(const [j,name] of ['Pelvis','Right heel'].entries()){
    const tr=values.insertRow(), th=document.createElement('th');
    th.scope='row';th.textContent=name;tr.appendChild(th);
    for(const v of deltas[j])tr.insertCell().textContent=v.toFixed(3);
  }
  statusText.textContent=description+' · '+(10*current.offset)+' ms after right foot strike';
}
document.querySelectorAll('input[name=condition]').forEach(r=>r.onchange=display);
document.querySelector('#file').onchange=async e=>{
 const f=e.target.files[0];if(!f)return;
 try{
   const obj=JSON.parse(await f.text()), windowInput=obj.input||obj;
   WalkingForecast.predict(weights,{...windowInput,instruction:selected()});
   current=windowInput;description=f.name;display();
 }catch(err){statusText.textContent='Could not load this window. '+err.message+' The table still shows '+description+'.';}
};
document.querySelector('#reset').onclick=()=>{current=example.input;description='Invented example';document.querySelector('#file').value='';display();};
display();
</script></body></html>
"""
for token, filename in (("__WEIGHTS__", "weights.json"), ("__EXAMPLE__", "example.json")):
    data = json.loads((p/filename).read_text())
    shell = shell.replace(token, json.dumps(data, separators=(",",":"), allow_nan=False).replace("<","\\u003c"))
(p/"forecast.html").write_text(shell)
