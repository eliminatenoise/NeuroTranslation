// Browser port of the stride-continuation NumPy reference. Calculations use doubles.
function decodeWeights(bytes, precision) {
  const raw = Uint8Array.from(atob(bytes), character => character.charCodeAt(0));
  const littleEndian = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;
  if (littleEndian) return precision === 64 ? new Float64Array(raw.buffer) : new Float32Array(raw.buffer);
  const view = new DataView(raw.buffer);
  const width = precision / 8;
  return Float64Array.from({length:raw.length / width}, (_, i) =>
    width === 8 ? view.getFloat64(i * width, true) : view.getFloat32(i * width, true));
}
function loadParameters(pack) {
  const values = decodeWeights(pack.base64, pack.precision);
  const parameters = {};
  let offset = 0;
  for (const [name, shape] of pack.layout) {
    const size = shape.reduce((a, b) => a * b, 1);
    parameters[name] = values.subarray(offset, offset + size);
    offset += size;
  }
  if (offset !== values.length) throw Error('The fitted weights are incomplete.');
  return parameters;
}
function validateWindow(history, action) {
  if (!['run','walk'].includes(action)) throw Error('Use the action “walk” or “run”.');
  if (!history || !Array.isArray(history.timesS) || history.timesS.length !== 11 ||
      !history.timesS.every((t,i,all) => Number.isFinite(t) && (!i || Math.abs(t-all[i-1]-.05) <= 1e-6))) {
    throw Error('Use eleven timestamps, each 0.05 seconds after the last.');
  }
  if (!Array.isArray(history.positionsMm) || history.positionsMm.length !== 11 ||
      !history.positionsMm.every(frame => Array.isArray(frame) && frame.length === 18 &&
        frame.every(p => Array.isArray(p) && p.length === 3 && p.every(Number.isFinite)))) {
    throw Error('Use eleven complete 18-site frames of finite XYZ coordinates in millimetres.');
  }
}
const hipOf = frame => frame[2].map((v, axis) => (v + frame[3][axis]) / 2);
function encodeWindow(frames) {
  const last = frames[10];
  const dx = last[3][0] - last[2][0], dy = last[3][1] - last[2][1];
  const width = Math.hypot(dx,dy);
  if (width < 40 || !Number.isFinite(width)) throw Error('The final waist sites need at least 40 mm of horizontal separation.');
  const u = dx / width, v = dy / width, origin = hipOf(last);
  const toBody = (p, c) => [(p[0]-c[0])*u + (p[1]-c[1])*v, -(p[0]-c[0])*v + (p[1]-c[1])*u, p[2]-c[2]];
  const toLab = (p,c) => [p[0]*u-p[1]*v+c[0], p[0]*v+p[1]*u+c[1],p[2]+c[2]];
  const x = frames.map(frame => {
    const hip = hipOf(frame);
    return [...frame.flatMap(p => toBody(p,hip)), ...toBody(hip,origin)].map(n => n / 250);
  });
  const body0 = last.map(p => toBody(p,origin));
  const velocity = toBody(hipOf(frames[6]),origin).map(n => -n/.2);
  return {x,origin,body0,velocity,toLab};
}
function networkResidual(encoded, token, w) {
  function linear(row, name) {
    const matrix = w[name+'.weight'], bias = w[name+'.bias'];
    const result = new Float64Array(bias.length), n = row.length;
    for (let i = 0; i < result.length; i++) {
      let s = bias[i], offset = i*n;
      for (let j = 0; j < n; j++) s += matrix[offset+j]*row[j];
      result[i] = s;
    }
    return result;
  }
  function norm(row, name) {
    const mean = row.reduce((a,b) => a+b,0)/row.length;
    const sd = Math.sqrt(row.reduce((a,b) => a + (b-mean)**2,0)/row.length + 1e-5);
    return row.map((v,i) => (v-mean)/sd*w[name+'.weight'][i] + w[name+'.bias'][i]);
  }
  function attention(tokens, name) {
    const qkv = tokens.map(row => linear(norm(row,name+'ln1'),name+'qkv'));
    return qkv.map((query,t) => {
      const mix = new Float64Array(48);
      for (let head = 0; head < 4; head++) {
        const start = head*12;
        const scores = qkv.map(key => {
          let dot = 0;
          for (let d=0; d<12; d++) dot += query[start+d]*key[48+start+d];
          return dot/Math.sqrt(12);
        });
        const peak = Math.max(...scores), exp = scores.map(v => Math.exp(v-peak));
        const total = exp.reduce((a,b) => a+b,0);
        for (let j=0; j<qkv.length; j++) {
          for (let d=0; d<12; d++) mix[start+d] += exp[j]/total*qkv[j][96+start+d];
        }
      }
      const attended = linear(mix,name+'out').map((v,i) => v+tokens[t][i]);
      const activation = linear(norm(attended,name+'ln2'),name+'ff1').map(v => Math.max(0,v));
      return linear(activation,name+'ff2').map((v,i) => v+attended[i]);
    });
  }
  let h = encoded.x.map((row,t) => linear(row,'input').map((v,i) => v+w.position[t*48+i]+w['action.weight'][token*48+i]));
  for (let layer=0; layer<2; layer++) h=attention(h,'blocks.'+layer+'.');
  const anchors = linear(norm(h[10],'final'),'readout');
  return Array.from({length:12},(_,t) => {
    const start = Math.floor(t/2)*57, current = anchors.slice(start,start+57);
    return t%2 ? current : current.map((v,j) => (v+(start ? anchors[start-57+j] : 0))/2);
  });
}
function ridgeResidual(encoded, w) {
  const flat = encoded.x.flat(), result = Float64Array.from(w.bias);
  for (let i=0; i<flat.length; i++) {
    const offset = i*result.length;
    for (let j=0; j<result.length; j++) result[j] += flat[i]*w.coef[offset+j];
  }
  return Array.from({length:12},(_,i) => result.subarray(i*57,(i+1)*57));
}
function makeForecast(history, action, method, w) {
  validateWindow(history,action);
  const enc = encodeWindow(history.positionsMm);
  const residual = method === 'ridge' ? ridgeResidual(enc,w) : networkResidual(enc,Number(method==='conditional' && action==='run'),w);
  const pelvisMm = [], timesS = [];
  const positionsMm = residual.map((row,t) => {
    const dt=(t+1)/20;
    timesS.push(history.timesS[10]+dt);
    const root=enc.toLab(enc.velocity.map((v,i) => row[54+i]*100+dt*v),enc.origin);
    pelvisMm.push(root);
    const body=enc.body0.map((site,i) => site.map((v,j) => row[3*i+j]*100+v));
    const mean=hipOf(body);
    return body.map(site => enc.toLab(site.map((v,j) => v-mean[j]),root));
  });
  if (!positionsMm.every(frame => frame.every(p => p.every(Number.isFinite)))) throw Error('The coordinates exceed the numerical range of the model.');
  return {positionsMm,pelvisMm,timesS};
}
