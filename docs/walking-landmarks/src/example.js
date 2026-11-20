// Coordinates are in laboratory millimetres; the invented walker travels along +X.
const Walk = (() => {
  const names = ['Left ankle', 'Right ankle', 'Left knee', 'Right knee', 'Left wrist', 'Right wrist'];
  const sourceLabels = ['L_FAL', 'R_FAL', 'L_FLE', 'R_FLE', 'L_RSP', 'R_RSP', 'L_IAS', 'R_IAS'];
  const muscles = ['Tibialis anterior', 'Soleus', 'Medial gastrocnemius', 'Vastus medialis', 'Rectus femoris',
    'Semitendinosus', 'Gluteus maximus', 'Gluteus medius'];
  const plus = (a,b) => a.map((v,i) => v+b[i]);
  const minus = (a,b) => a.map((v,i) => v-b[i]);
  const times = (a,s) => a.map(v => v*s);
  const mix = (a,b,k) => plus(times(a,1-k),times(b,k));
  const mag = a => Math.hypot(...a);
  const unit = a => times(a,1/(mag(a)||1));
  function pose(t,o) {
    const cycle = Math.PI * o.cadence * t / 60;
    const root = [o.speed*t*1000, 14*Math.sin(cycle), 914+14*Math.cos(2*cycle)];
    const body = {pelvis:root};
    body.neck = plus(root, [28,0,475]);
    body.head = plus(body.neck,[12,0,130]);
    const markers = Array(8);
    for (let s=0;s<2;s++) {
      const sign = s===0 ? 1 : -1;
      const a = cycle + s*Math.PI;
      const bend = 0.12 + 0.80*Math.max(0, -Math.cos(a+0.58))**2;
      const thigh = 0.40*Math.sin(a)+0.09;
      const shin = thigh-bend;
      const upper = -0.28*Math.sin(a)-0.05;
      const hip = plus(root,[-12,sign*92,-12]);
      const knee = plus(hip,[420*Math.sin(thigh),sign*8,-420*Math.cos(thigh)]);
      const ankle = plus(knee,[420*Math.sin(shin),sign*3,-420*Math.cos(shin)]);
      const shoulder = plus(root,[14+12*Math.cos(a),sign*175,390]);
      const elbow = plus(shoulder,[288*Math.sin(upper),sign*33,-288*Math.cos(upper)]);
      const forearm = upper+0.31+0.10*Math.sin(a);
      const wrist = plus(elbow,[245*Math.sin(forearm),sign*8,-245*Math.cos(forearm)]);
      const hand = plus(wrist,[55*Math.sin(forearm),sign*2,-76]);
      const toe = plus(ankle,[113+18*Math.cos(a),sign*3,-39+12*Math.sin(a)]);
      body[s] = {hip,knee,ankle,shoulder,elbow,wrist,hand,toe};
      markers[s] = plus(ankle,[0,sign*29,0]);
      markers[2+s] = plus(knee,[0,sign*39,0]);
      markers[4+s] = plus(wrist,[8,sign*21,0]);
      markers[6+s] = plus(root,[71,sign*108,18]);
    }
    return {body,markers};
  }
  function emg(t,o) {
    const period = 120/o.cadence;
    const phase = t/period;
    const peak = [0.75,0.33,0.38,0.04,0.12,0.88,0.06,0.17];
    const size = [42,69,59,35,32,48,27,38];
    return peak.map((p,i) => {
      const delta = phase-p-Math.round(phase-p);
      return o.gain*(4+size[i]*Math.exp(-0.5*(delta/0.095)**2));
    });
  }
  function sample(o) {
    const t = o.phase/100*120/o.cadence;
    const observed = Array.from({length:40},(_,k)=>pose(t+(k-39)/100,o).markers);
    const envelopes = Array.from({length:8},(_,k)=>emg(t+(k-7)*0.05-0.020,o));
    return {body:pose(t,o).body, observed, envelopes, next:pose(t+0.2,o).markers.slice(0,6)};
  }
  return {names,sourceLabels,muscles,plus,minus,times,mix,mag,unit,sample};
})();
if (typeof module !== 'undefined') module.exports = Walk;
