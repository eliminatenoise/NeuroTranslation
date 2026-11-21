"use strict";
globalThis.CrossWrist = (() => {
  const roles = ["contralateral", "ipsilateral"];
  const horizons = [8, 15];
  const names = ["R", "L"].flatMap(side => ["Wrist", "Elbow", "Shoulder"].map(joint => side + "_" + joint));
  const primary = ["ridge", "damped_velocity", "velocity", "persistence"];
  const networkMethods = {
    intact: ["full", "intact"], blocked: ["full", "blocked"], intact_swapped: ["full", "intact", true],
    matched_intact: ["matched", "intact"], matched_blocked: ["matched", "blocked"],
    matched_intact_swapped: ["matched", "intact", true], trained_swap: ["matched", "trained_swap", true]
  };
  const baselines = ["zero", "mean_px", "mean_normalized", "constant_velocity", "kinematic_ridge"];
  const methods = [...primary, ...Object.keys(networkMethods), ...baselines];
  const map2 = fn => [fn(0), fn(1)];
  const add = (a,b) => a.map((x,i) => x + b[i]);
  const sub = (a,b) => a.map((x,i) => x - b[i]);
  const scale = (a,k) => a.map(x => x*k);
  const dot = (a,b) => a.reduce((sum,x,i) => sum + x*b[i], 0);
  const mean = a => a.reduce((x,y) => x+y, 0) / a.length;
  const median15 = a => [...a].sort((x,y) => x-y)[7];
  const finite = p => p.every(Number.isFinite);
  const matrix = (row, weights) => {
    const result = Array(weights[0].length).fill(0);
    for (let i=0; i<row.length; i++) {
      for (let j=0; j<result.length; j++) result[j] += row[i]*weights[i][j];
    }
    return result;
  };
  function exactKeys(value,required,optional=[]) {
    if (!value || typeof value!=="object" || Array.isArray(value) || required.some(key=>!Object.hasOwn(value,key)) ||
        Object.keys(value).some(key=>!required.includes(key) && !optional.includes(key))) {
      throw Error("Unexpected or missing JSON fields. See the input format.");
    }
  }
  function validateWindow(win) {
    const idx = win?.frame_indices, tracks = win?.prior_by_name;
    if (!Array.isArray(idx) || idx.length!==15 || idx.some((v,i) => !Number.isSafeInteger(v) || v<0)) {
      throw Error("Supply 15 consecutive, nonnegative camera frame indices.");
    }
    if (!tracks || typeof tracks!=="object" || Array.isArray(tracks)) throw Error("Supply six named landmark histories.");
    exactKeys(tracks,[],names);
    for (const key of Object.keys(tracks)) {
      const series = tracks[key];
      if (!Array.isArray(series) || series.length!==15 || series.some(p => !Array.isArray(p) || p.length!==2 || p.some(v => !(v===null || (Number.isFinite(v) && Math.abs(v)<=1e8))))) {
        throw Error("Use 15 [x, y] pairs for " + key + ". Write null for a missing coordinate.");
      }
    }
    return idx[14];
  }
  function validateCase(input) {
    exactKeys(input,["domain","implant_side","annotated_wrist","frame_indices","prior_by_name"],["earlier_donor"]);
    if (input?.domain !== "cross_person_wrist") throw Error("Use a cross_person_wrist input.");
    const valid = {L:"r_wrist", R:"l_wrist"};
    if (!Object.hasOwn(valid,input.implant_side) || valid[input.implant_side]!==input.annotated_wrist) {
      throw Error("The annotated wrist must be opposite the implant. Use L with r_wrist or R with l_wrist.");
    }
    const last = validateWindow(input);
    if (Object.hasOwn(input,"earlier_donor")) {
      exactKeys(input.earlier_donor,["frame_indices","prior_by_name"]);
      const previous = validateWindow(input.earlier_donor);
      if (last-previous<900 || Math.floor((previous+1)/3600)>=Math.floor((last+1)/3600)) {
        throw Error("The earlier arm must come from the same recording, at least 900 frames earlier and in a previous two-minute block.");
      }
    }
    return input;
  }
  function geometry(win,sides) {
    const tracks = win.prior_by_name;
    if (win.frame_indices.some((n,i,a)=>i>0 && n!==a[i-1]+1)) return {reason:"nonconsecutive_prior_frames"};
    const armPoints = sides.map(side => Array.from({length:15},(_,i) =>
      ["Wrist","Elbow","Shoulder"].map(j => tracks[side+"_"+j]?.[i] || [null,null])));
    const shoulders = armPoints.map(arm => arm.map(frame => frame[2]));
    if (shoulders.some(track => track.some(p => !finite(p)))) return {reason:"missing_prior_shoulder"};
    const differences = shoulders[0].map((p,i) => sub(p,shoulders[1][i]));
    const width = median15(differences.map(p => Math.hypot(...p)));
    if (width<1) return {reason:"shoulder_width_below_floor"};
    const direction = map2(i => mean(differences.map(x => x[i])));
    const magnitude = Math.hypot(...direction);
    if (magnitude<width*.5) return {reason:"unstable_shoulder_direction"};
    const axis = scale(direction,1/magnitude);
    if (Math.abs(axis[0])<.1) return {reason:"ambiguous_image_up_axis"};
    const axes = [axis,scale([axis[1],-axis[0]],axis[0]<0?-1:1)];
    const origin = scale(add(shoulders[0][14],shoulders[1][14]),.5);
    const ref = {origin, axes, width};
    const arms = armPoints.map(points => {
      if (points.some(frame => frame.some(p => !finite(p)))) return {reason:"missing_role_landmark"};
      const pose = points.map(frame => frame.map(p => axes.map(a => dot(sub(p,origin),a))));
      const normalized = pose.map(frame => frame.map(p => scale(p,1/width)));
      const lengths = pose.map(([w,e,s]) => Math.hypot(...sub(w,e))+Math.hypot(...sub(e,s)));
      const length = median15(lengths);
      const wrist = pose[14][0], shoulder = pose[14][2];
      const features = length>1e-6 ? pose.map(([w,e,s]) => scale([
        ...sub(w,e), ...sub(e,s), ...sub(s,shoulder), ...sub(w,wrist)
      ],1/length)) : null;
      return {pose,normalized,wrist,length,features};
    });
    return {ref,arms};
  }
  function decode(p,ref) {
    return add(ref.origin, map2(i => p[0]*ref.axes[0][i]+p[1]*ref.axes[1][i]));
  }
  function ridgeDisplacement(arm,head,h,method) {
    const frames = arm.normalized;
    const w = frames[14][0];
    if (method==="persistence") return [0,0];
    if (method==="velocity" || method==="damped_velocity") {
      return scale(sub(w,frames[0][0]),h/14*(method==="velocity"?1:head.gain));
    }
    const inputs = frames.flatMap(frame => frame.flatMap(p => sub(p,w)));
    const z = inputs.map((v,i) => (v-head.mean[i])/head.std[i]);
    return add(matrix(z,head.coef),head.bias);
  }
  function ridgeVelocityFeatures(arm) {
    const series = arm.pose.map(([w,e,s]) => [s,sub(e,s),sub(w,e)]);
    return [0,1,2].flatMap(joint => [4,8,15].flatMap(count => {
      const frames = series.slice(-count);
      const times = frames.map((_,i) => i-(count-1)/2);
      return map2(axis => dot(times,frames.map(x => x[joint][axis]))/dot(times,times)/arm.length);
    }));
  }
  // One attention layer, followed by a position-wise feed-forward layer. Only the last
  // token of each arm reaches a readout. Keys and values still use the entire history.
  function correction(features,weight,side,blocked) {
    const x = features.flatMap((arm,s) => arm.map((row,t) =>
      add(add(matrix(row,weight("input")),weight("input_bias")),add(weight("side")[s],weight("time")[t]))));
    const last = x[side*15+14], query = matrix(last,weight("query"));
    const source = blocked ? x.slice(15*side,15*(side+1)) : x;
    const keys = source.map(row => matrix(row,weight("key")));
    const values = source.map(row => matrix(row,weight("value")));
    const context = [0,1].flatMap(head => {
      const start = 6*head, end = start+6;
      const q = query.slice(start,end);
      const logits = keys.map((k,i) => dot(q,k.slice(start,end))/Math.sqrt(6) +
        ((!blocked && Math.floor(i/15)!==side) ? weight("other_bias")[head] : 0));
      const max = Math.max(...logits);
      const exp = logits.map(v => Math.exp(v-max));
      const sum = exp.reduce((a,b) => a+b,0);
      return Array.from({length:6},(_,j) => dot(exp,values.map(v => v[start+j]))/sum);
    });
    const residual = add(last,matrix(context,weight("out")));
    const hidden = add(matrix(residual,weight("ff_in")),weight("ff_bias")).map(Math.tanh);
    const final = add(residual,matrix(hidden,weight("ff_out")));
    const d = add(matrix(final,weight("decode")),weight("decode_bias"));
    const g = add(matrix(final,weight("gate")),weight("gate_bias"));
    return d.map((v,i) => .5*Math.tanh(v)/(1+Math.exp(-Math.max(-700,Math.min(700,g[i])))));
  }
  function run(input,weights,selected=methods) {
    validateCase(input);
    const sides = input.annotated_wrist==="r_wrist"?["R","L"]:["L","R"];
    const history = geometry(input,sides);
    const donor = input.earlier_donor && geometry(input.earlier_donor,sides);
    const ref = history.ref;
    const results = {};
    for (const method of new Set(selected)) {
      if (!methods.includes(method)) throw Error("Unknown forecasting method.");
      const out = {endpoint_native_px:map2(()=>[null,null]),endpoint_shoulder_widths:map2(()=>[null,null]),reason:["available","available"]};
      out.reason_by_horizon = map2(()=>["available","available"]);
      function unavailable(reason) {
        out.reason.fill(reason);
        out.reason_by_horizon.forEach(row=>row.fill(reason));
      }
      if (!primary.includes(method)) {
        out.delta_arm_lengths=map2(()=>[null,null]);
        out.endpoint_from_last_shoulder_arm_lengths=map2(()=>[null,null]);
        out.span_change_px=[null,null];
      }
      results[method] = out;
      if (!ref) {unavailable(history.reason);continue;}
      if (primary.includes(method)) {
        history.arms.forEach((arm,s) => {
          if (arm.reason) {out.reason[s]=arm.reason;out.reason_by_horizon.forEach(row=>{row[s]=arm.reason;});return;}
          horizons.forEach((h,k) => {
            const head = weights.heads[roles[s]+"_"+h];
            if (!head.count) {out.reason_by_horizon[k][s]="unfitted_head";return;}
            const point = add(arm.wrist,scale(ridgeDisplacement(arm,head,h,method),ref.width));
            out.endpoint_native_px[k][s] = decode(point,ref);
            out.endpoint_shoulder_widths[k][s] = scale(point,1/ref.width);
          });
        });
        out.reason=map2(s=>out.reason_by_horizon[0][s]===out.reason_by_horizon[1][s]?out.reason_by_horizon[0][s]:"see_reason_by_horizon");
        continue;
      }
      if (history.arms.some(a => !a.features)) {
        unavailable(history.arms.some(a=>a.reason)?"incomplete_bilateral_prior":"invalid_projected_arm_scale");
        continue;
      }
      const [partition,kind,swap] = networkMethods[method] || ["full"];
      if (swap && (!donor?.ref || donor.arms.some(a => !a.features))) {
        unavailable(!donor?"missing_earlier_donor":!donor.ref?"donor_"+donor.reason:
          donor.arms.some(a=>a.reason)?"donor_incomplete_bilateral_prior":"donor_invalid_projected_arm_scale");continue;
      }
      const prior = key => weights.transport[partition+".prior."+key];
      history.arms.forEach((arm,s) => {
        let changes;
        if (kind) {
          const features = history.arms.map((a,j) => swap && j!==s?donor.arms[j].features:a.features);
          const corrections = [17,43,97].map(seed => {
            const prefix = partition+"."+kind+"."+seed+".";
            return correction(features,key => weights.transport[prefix+key],s,kind==="blocked");
          });
          changes = horizons.map((_,k) => add(prior("mean")[k][s],
            map2(j => mean(corrections.map(v => v[k*2+j])))));
        } else {
          changes = horizons.map((h,k) => {
            if (method==="zero") return [0,0];
            if (method==="mean_normalized") return prior("mean")[k][s];
            if (method==="mean_px") return scale(prior("mean_px")[k][s],1/arm.length);
            if (method==="constant_velocity") return scale(sub(arm.wrist,arm.pose[10][0]),h/(4*arm.length));
            return add(matrix(scale(ridgeVelocityFeatures(arm),h),prior("ridge")[k][s]),prior("ridge_bias")[k][s]);
          });
        }
        changes.forEach((change,k) => {
          const point = add(arm.wrist,scale(change,arm.length));
          out.delta_arm_lengths[k][s]=change;
          out.endpoint_from_last_shoulder_arm_lengths[k][s]=add(scale(sub(arm.wrist,arm.pose[14][2]),1/arm.length),change);
          out.endpoint_native_px[k][s]=decode(point,ref);
          out.endpoint_shoulder_widths[k][s]=scale(point,1/ref.width);
        });
      });
      const earlierSpan=Math.hypot(...sub(history.arms[0].wrist,history.arms[1].wrist));
      out.span_change_px = out.endpoint_native_px.map(([a,b])=>Math.hypot(...sub(a,b))-earlierSpan);
    }
    const paired = ref && history.arms.every(a=>a.features);
    return {domain:"cross_person_wrist",fit_source:weights.source,horizons_frames:horizons,nominal_hz:30,roles,
      role_wrist:Object.fromEntries(roles.map((r,s)=>[r,sides[s]+"_Wrist"])),
      reference:ref?{origin_px:ref.origin,basis:ref.axes,width_px:ref.width}:null,
      role_arm_scale_px:paired?history.arms.map(a=>a.length):[null,null],
      role_reason:Object.fromEntries(roles.map((r,s)=>[r,ref?(history.arms[s].reason || "available"):history.reason])),
      methods:results};

  }

  function validateWeights(weights,template) {
    function compare(a,b) {
      if (typeof b==="number") {
        if (!Number.isFinite(a)) throw Error("Each coefficient must be a finite number.");
      } else if (Array.isArray(b)) {
        if (!Array.isArray(a) || a.length!==b.length) throw Error("Coefficient array shape differs from the trained model.");
        b.forEach((v,i)=>compare(a[i],v));
      } else if (b && typeof b==="object") {
        if (!a || typeof a!=="object") throw Error("Missing checkpoint group.");
        for (const key of Object.keys(b)) compare(a[key],b[key]);
      }
    }
    exactKeys(weights,["format","source","heads","transport"]);
    if (weights.format!==template.format || !["synthetic","local"].includes(weights.source)) throw Error("Unsupported checkpoint format or source.");
    exactKeys(weights.transport,Object.keys(template.transport));
    exactKeys(weights.heads,Object.keys(template.heads));
    compare(weights.transport,template.transport);
    for (const name of Object.keys(weights.heads)) {
      const head = weights.heads[name];
      if (head?.count===0) {exactKeys(head,["count"]);continue;}
      exactKeys(head,Object.keys(template.heads[name]));
      compare(head,template.heads[name]);
    }
    for (const head of Object.values(weights.heads)) {
      if (!head.count) continue;
      if (!Number.isSafeInteger(head.count) || head.count<0 || head.std.some(v => v<=0) || head.gain<0 || head.gain>1) {
        throw Error("Training counts, feature scales or velocity gains are invalid.");
      }
    }
    return weights;
  }
  return {run,validateCase,validateWeights,roles,horizons,primary,methods,names};
})();
