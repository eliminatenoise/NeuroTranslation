"use strict";
// Analytic trajectories in an invented camera plane. No recording is sampled.
globalThis.WristExamples = (() => {
  function build(onsetSide,missing) {
    const partner = onsetSide==="L"?"R":"L";
    const sideNames = [onsetSide,partner];
    function point(nativeSide,joint,t,earlier) {
      const active = nativeSide===onsetSide, handSign = nativeSide==="R"?1:-1;
      const phase = earlier ? 1.7 : 0;
      const wave = a => Math.sin(a*t+phase);
      const shoulder = [314+handSign*48+3*wave(.06),194+handSign*6+2*wave(.085)];
      const elbow = [shoulder[0]+handSign*(26+(active?8:4)*wave(.14)),
                     shoulder[1]+44+(active?9:3)*wave(.075)];
      const wrist = [elbow[0]+handSign*((active?28:16) + (active?18:5)*wave(.135) + (active?.44:.1)*t),
                     elbow[1] + (active?-18:23) + (active?15:4)*wave(.105)];
      return joint==="Wrist"?wrist:joint==="Elbow"?elbow:shoulder;
    }
    const times = Array.from({length:15},(_,i)=>i-14);
    function window(first,earlier) {
      const tracks = {};
      for (const side of sideNames) for (const joint of ["Wrist","Elbow","Shoulder"]) {
        tracks[side+"_"+joint] = times.map(t=>point(side,joint,t,earlier));
      }
      return {frame_indices:times.map((_,i)=>first+i),prior_by_name:tracks};
    }
    const input = {domain:"cross_person_wrist",implant_side:partner,annotated_wrist:onsetSide.toLowerCase()+"_wrist",
      ...window(7600,false),earlier_donor:window(3800,true)};
    const observed = Object.fromEntries(sideNames.map(side=>[side+"_Wrist",[8,15].map(h=>point(side,"Wrist",h,false))]));
    if (missing==="wrist") input.prior_by_name[partner+"_Wrist"][6] = [null,null];
    if (missing==="shoulder") input.prior_by_name[partner+"_Shoulder"][8] = [null,null];
    if (missing==="outcome") observed[onsetSide+"_Wrist"][1] = null;
    if (missing==="donor") delete input.earlier_donor;
    return {input,observed};
  }
  return {build};
})();
