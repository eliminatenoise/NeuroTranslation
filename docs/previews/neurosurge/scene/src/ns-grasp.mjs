


















/** The limbs that can be held (ids used by the app and the texts). */
export const LIMB_IDS = Object.freeze(['rightArm', 'leftArm', 'rightLeg', 'leftLeg']);

/**
 * The solved limbs: joints (two root joints and the bend), the root pivot (shoulder / hip), the bend joint and its sign
 * (+1: flexion is positive, as r_elbow_flex; -1: flexion is negative, as knee_ext), the end point (a pivot or a
 * segment's rest centre carried by a segment), and the dial: the rotation joint a drag across the limb turns, the
 * sign that maps a right-handed turn about root -> end onto that joint (r_pronation counts toward palm down, so a
 * supinating turn lowers it; hip_rot_L counts external positive, which is a left-handed turn for the left leg), and
 * the motor area lit when no body-map action moves that joint. upperDial: a press on the right UPPER arm turns the
 * upper arm (r_shoulder_rot) instead of the forearm.
 */




























/* 21 November 2026, late (a check of the above found two residues, both shown offline on the game's body).
 *   handMm    the leave ENDS, and none is given, once the hand's place is no longer on the body's other side of the
 *             shoulder (0: level with it or outside). The leave lasted until the look next carried the limb, so the
 *             keys alone could take it out to the side: across the chest 43 / -31, S 1.5 s, W, D, then S again turned
 *             the upper arm from -49.0 to -56.1 with the elbow 29 cm OUTSIDE the shoulder (4 of 24 such runs, 2 to 7
 *             degrees). While S draws a hand in from across the chest its place stays inside (it moves on the line to
 *             the shoulder), so those runs end as before.
 *   again     an upper arm that the keys have turned, and that nothing else has turned since, is given the leave again
 *             without the elbow's test, as long as the hand's place is still inside (the solve keeps in its memo the
 *             turn's value before and after the last frame that turned it, `spinTurn`; the next frame's value must lie
 *             between the two: the app may take only a share of a frame's answer, and the limb turn, a drag or a reset
 *             put the joint elsewhere and end the record). The app takes the leave away whenever the look carries the
 *             limb; at raise 70 / across 30, after half a second of S and a small look movement, the elbow was 79 mm
 *             inside (under elbowMm), no leave was given again, and S ended with the hand 28 degrees off its line and
 *             the turn stuck at -19, where the uninterrupted run ends 9 degrees off at -44. (A first version gave the
 *             leave again to any upper arm turned inward of 12 degrees: the limb turn's own overside end is -15, so
 *             after a double tap of Space the low arms that elbowMm refuses would have been turned again.)
 *   againElbowMm  the renewed leave still asks the elbow to be this far inside (60 mm, against elbowMm's 80 for a
 *             first leave). A second check found the record outlives the look's carry (the app solves the carried arm
 *             with no spin, so the turn and the record stay): S across the chest, then the look carried the arm down
 *             to a low pose, then S turned the upper arm 3 to 20 degrees more in 65 of 96 such poses, with elbows from
 *             97 mm outside to 55 mm inside the shoulder; the same poses with no record were left alone. The residue
 *             this rule exists for had the elbow 79 mm inside. null: no elbow test for the renewed leave.
 * Null for either: that rule is off. */
export const LIMB_CHAIN = Object.freeze({
  rightArm: Object.freeze({ joints: Object.freeze(['r_shoulder_flex', 'r_shoulder_abd', 'r_elbow_flex']), root: 'r_glenohumeral', rootSeg: 'r_upperarm',
    bend: 'r_elbow_flex', bendSign: 1, bendPivot: 'r_elbow', endSeg: 'r_hand', endCentreOf: 'r_hand', framePivot: 'r_wrist', side: 'right',
    dial: Object.freeze({ joint: 'r_pronation', sign: -1, area: 'lh_forearm' }), upperDial: Object.freeze({ joint: 'r_shoulder_rot', sign: 1, area: 'lh_shoulder' }),
    spin: Object.freeze({ joint: 'r_shoulder_rot', weight: 0.35, bendFrom: 20, bendTo: 70, across: Object.freeze({ medialMm: 20, elbowMm: 80, handMm: 0, again: true, againElbowMm: 60, seg: 'sternum', toMedial: Object.freeze([1, 0, 0]) }) }) }),
  rightLeg: Object.freeze({ joints: Object.freeze(['hip_flex_R', 'hip_abd_R', 'knee_ext_R']), root: 'r_hip', rootSeg: 'r_thigh',
    bend: 'knee_ext_R', bendSign: -1, bendPivot: 'r_knee', endSeg: 'r_shank', endPivot: 'r_ankle', side: 'right',
    dial: Object.freeze({ joint: 'hip_rot_R', sign: 1, area: 'lh_hip' }) }),
  leftLeg: Object.freeze({ joints: Object.freeze(['hip_flex_L', 'hip_abd_L', 'knee_ext_L']), root: 'l_hip', rootSeg: 'l_thigh',
    bend: 'knee_ext_L', bendSign: -1, bendPivot: 'l_knee', endSeg: 'l_shank', endPivot: 'l_ankle', side: 'left',
    dial: Object.freeze({ joint: 'hip_rot_L', sign: -1, area: 'rh_hip' }) })
});

/** Display choices for holding and turning a limb.
 *  speedMps: how fast W/A/S/D move a held limb's end (metres per second).
 *  solveIters / tolMm / lambdaMm / stepCapDeg / probeDeg: the joint solve (damped least squares on a numerical
 *    Jacobian; at most stepCapDeg per joint per iteration; probe of probeDeg for each Jacobian column).
 *  rollDegPerPx: degrees of turn per CSS pixel of drag across the limb (about a quarter turn for a 230 px drag).
 *  (No floor: a held limb goes wherever its joints let it; the earlier groundMarginMm went with the leg ground model.)
 */
export const LIMB_GRASP = Object.freeze({
  speedMps: 0.35, solveIters: 6, tolMm: 0.5, lambdaMm: 8, stepCapDeg: 12, probeDeg: 0.5,
  rollDegPerPx: 0.4
});

/**
 * 19 November 2026 (a check: looking round with a limb held ran at 48 to 55 frames a second; the solve was 4 to 5 ms
 * of every frame). The solve's options for a limb that FOLLOWS a moving target frame after frame (ns-app
 * stepLimbGrasp): each iteration poses the whole body three times, the target moves only a few mm a frame, and the
 * next frame goes on from where this one ended, so two iterations a frame track it; minGain ends the frame's solve as
 * soon as an iteration no longer brings the end 5% nearer (a target out of reach or a joint at its limit used to burn
 * all six iterations on every frame).
 */
export const LIMB_TRACK = Object.freeze({ ...LIMB_GRASP, solveIters: 2, minGain: 0.05 });
/**
 * 19 November 2026 (the chosen limb held by the view, ns-app LIMB_KEYS.view.hold). The tracking solve with the damping
 * in proportion to the limb's lever arm (lambdaShare x the distance root -> end, in place of the fixed lambdaMm): with
 * the fixed 8 a folded arm, its hand 11 cm from the shoulder, turned about a twentieth of what a frame asked for and
 * the hand sank instead of going out level; in proportion the turn is the same share of the asked one at every bend.
 */
export const LIMB_HOLD_TRACK = Object.freeze({ ...LIMB_TRACK, lambdaShare: 0.006, lambdaMinMm: 0.5, reuseDeg: 6 });
/** The same with one step a frame: for the frames on which the limb is already following (the solve of the frame
 * before ended close to its target), where one step with the remembered columns is enough. */
export const LIMB_HOLD_FOLLOW = Object.freeze({ ...LIMB_HOLD_TRACK, solveIters: 1 });
/** And for a limb that waits at the end of its range while the view goes on: one step with the columns it has (keepColumns:
 * they are not found afresh because a step did not close in; at a joint's end no columns would). */
export const LIMB_HOLD_WAIT = Object.freeze({ ...LIMB_HOLD_FOLLOW, keepColumns: true, reuseDeg: 12 });
/** 20 November 2026, evening (LIMBFREE): the one longer solve that asks whether a waiting limb can reach the place its
 * look has come to rest on (ns-app stepLimbHold: rejoin). Up to ten steps of at most stepCapDeg each, from where the
 * limb is; run once per place at rest, not every frame. */
export const LIMB_HOLD_REACH = Object.freeze({ ...LIMB_HOLD_TRACK, solveIters: 10, minGain: 0.01 });

/** The arm pose remains within its supported range during a grasp. */




export const LIMB_HOLD_LIMITS = Object.freeze({});
/** limits with LIMB_HOLD_LIMITS applied for the pose `now` ({ jointId: degrees }): each capped joint keeps the side of
 * its cap it is already beyond (a joint a brain movement took past the cap is not snapped back; it can only come in).
 * Pure; returns `limits` itself when no cap applies to this limb. */
export function holdLimits(limits, limb, now, caps = LIMB_HOLD_LIMITS) {
  const c = LIMB_CHAIN[limb];
  if (!c || !limits || !caps) return limits;
  let out = limits;
  for (const id of c.joints) {
    const cap = caps[id], L = limits[id];
    if (!cap || !L) continue;
    const v = now && Number.isFinite(now[id]) ? now[id] : null;
    const lo = Math.max(L[0], v === null ? cap[0] : Math.min(cap[0], v)), hi = Math.min(L[1], v === null ? cap[1] : Math.max(cap[1], v));
    if (out === limits) out = { ...limits };
    out[id] = [lo, hi];
  }
  return out;
}

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const len = a => Math.hypot(a[0], a[1], a[2]);
const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);
const apply = (m, p) => [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13], m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]];

/** A point of the posed limb (drawn mm): the root ('root'), the bend ('bend') or the end ('end'). */
export function limbPoint(rig, segments, limb, which) {
  const c = LIMB_CHAIN[limb];
  if (!c) throw new Error(`ns:grasp: unknown solved limb ${JSON.stringify(limb)}`);
  const P = k => (rig.pivots[k] && rig.pivots[k].point) || null;
  if (which === 'root') return apply(segments[c.rootSeg], P(c.root));
  if (which === 'bend') return apply(segments[c.rootSeg], P(c.bendPivot));
  const p = c.endPivot ? P(c.endPivot) : rig.segments[c.endCentreOf] && rig.segments[c.endCentreOf].restCentroid;
  if (!p) throw new Error(`ns:grasp: the rig has no end point for ${limb}`);
  return apply(segments[c.endSeg], p);
}

/** Solve 3x3 (J J^T + l^2 I) y = e and return J^T y (damped least squares step). J: 3 x n columns (arrays of 3). */
function dlsStep(J, e, lambda) {
  const A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (const c of J) for (let i = 0; i < 3; i++) for (let k = 0; k < 3; k++) A[i][k] += c[i] * c[k];
  for (let i = 0; i < 3; i++) A[i][i] += lambda * lambda;
  // Cramer's rule (3x3).
  const det = m => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  const D = det(A);
  if (!(Math.abs(D) > 1e-12)) return J.map(() => 0);
  const y = [0, 1, 2].map(k => det(A.map((row, i) => row.map((v, j) => (j === k ? e[i] : v)))) / D);
  return J.map(c => c[0] * y[0] + c[1] * y[1] + c[2] * y[2]);
}

















export const LIMB_CLICK = Object.freeze({ followsLook: false, lookAwayDeg: 24 });

/**
 * Which own limb a click controls after an event. latch: the limb controlled now ('rightArm' | 'rightLeg' |
 * 'leftLeg') or null. Events:
 *   { type: 'click', limb }           a plain click on own limb `limb`: it is taken; the controlled limb itself: let go;
 *                                     'leftArm' (the game arm, which the keys move anyway): no limb is controlled
 *   { type: 'click', nothing: true }  a plain click on nothing (open space, bare brain): let go
 *   { type: 'click' }                 a click on anything else (a motor area, an arrow, the mirror body): no change
 *   { type: 'view' }                  the view was changed (E)
 *   { type: 'look', awayDeg }         how far the look has turned from where the limb was clicked or last moved
 *   { type: 'reset' }                 Reset body
 * Anything else (Space pressed or let go, a pause, a lost focus) leaves it as it is. Pure.
 */
export function limbLatchAfter(latch, ev, rule = LIMB_CLICK) {
  const cur = typeof latch === 'string' && latch !== 'leftArm' && LIMB_CHAIN[latch] ? latch : null;
  if (!ev || typeof ev !== 'object') return cur;
  if (ev.type === 'view' || ev.type === 'reset') return null;
  if (ev.type === 'look') return cur && rule && rule.followsLook !== true && Number.isFinite(rule.lookAwayDeg) && Number.isFinite(ev.awayDeg) && ev.awayDeg > rule.lookAwayDeg ? null : cur;
  if (ev.type === 'click') {
    if (ev.nothing === true || ev.limb === 'leftArm') return null;
    if (typeof ev.limb === 'string' && LIMB_CHAIN[ev.limb]) return ev.limb === cur ? null : ev.limb;
  }
  return cur;
}
/** The angle (degrees) between two looks ({ yaw, pitch } in radians). Pure. */
export function lookAwayDeg(a, b) {
  if (!a || !b) return 0;
  const d = Math.sin(a.pitch) * Math.sin(b.pitch) + Math.cos(a.pitch) * Math.cos(b.pitch) * Math.cos(a.yaw - b.yaw);
  return Math.acos(Math.max(-1, Math.min(1, d))) * 180 / Math.PI;
}
/**
 * Joint angles that bring the limb's end to targetMm (drawn mm), each inside limits[id] = [lo, hi] (degrees).
 * segmentsFor(targets) -> the posed segments for a full targets object (ns-body poseBodySegments with the drawn
 * options). The bend joint comes from the distance root -> target (law of cosines on the posed upper / lower lengths,
 * counted from the inner angle the limb has now; see the bend step below), so a straight elbow or knee bends when the end is pulled in and straightens when it is pushed out; then a few damped
 * least-squares steps over the two root joints point the limb at the target. (A first version solved all three joints
 * together; with the arm straight forward and the end lifted it folded the elbow a little every frame until the hand
 * was at the face, so the bend is now left to the distance alone.) Returns { joints: { id: deg } (the limb's three joints), endMm (where the end now is), bendMm (where the elbow or knee now is), errorMm, iterations }.
 */
export function solveLimb({ rig, segmentsFor, targets, limb, targetMm, limits, opts = LIMB_GRASP, project = null, memo = null, startSegments = null, spin = false }) {
  const c0 = LIMB_CHAIN[limb];
  if (!c0) throw new Error(`ns:grasp: unknown solved limb ${JSON.stringify(limb)}`);
  if (!targetMm || targetMm.length !== 3 || !targetMm.every(Number.isFinite)) throw new Error('ns:grasp: targetMm must be finite mm');
  // (21 November 2026, LIMB_CHAIN spin: the keys' solve of the right arm turns the upper arm too, weighted)
  const sp = spin && c0.spin && !c0.joints.includes(c0.spin.joint) ? c0.spin : null;
  const c = sp ? { ...c0, joints: [...c0.joints, sp.joint] } : c0;
  const lim = id => (limits && limits[id] ? limits[id] : [-180, 180]);
  let q = { ...targets };
  for (const id of c.joints) q[id] = clamp(Number.isFinite(q[id]) ? q[id] : 0, lim(id)[0], lim(id)[1]);
  // project (19 November 2026): the rule that brings a whole set of targets inside the ranges that depend on each other
  // (ns-body clampBodyJointTargets' combined-range rule), applied to the limb's joints after every change, so the
  // angles returned are the angles drawn. (Without it the solve could hold an angle the drawn pose refuses, an arm
  // across the body with no forward raise, and then worked from a pose that was not on screen.)
  const fit = () => { if (typeof project !== 'function') return; const p = project(q); if (p) for (const id of c.joints) if (Number.isFinite(p[id])) q[id] = p[id]; };
  // startSegments (19 November 2026): the posed segments of `targets` when the caller has them already (one pose of the
  // whole body saved); used only while the start angles are untouched by the limits and the rule above.
  const q0 = c.joints.map(id => q[id]);
  // (21 November 2026, late, LIMB_CHAIN across.again: is the upper arm's turn still where the keys' last turn left it?
  // memo.spinTurn = [value before, value after] of the last frame of the keys that turned it)
  const spinStart = sp ? q[sp.joint] : null;
  const spinMine = Boolean(sp && memo && Array.isArray(memo.spinTurn) && spinStart >= Math.min(memo.spinTurn[0], memo.spinTurn[1]) - 0.5 && spinStart <= Math.max(memo.spinTurn[0], memo.spinTurn[1]) + 0.5);
  if (sp && memo && memo.spinTurn && !spinMine) memo.spinTurn = null;
  fit();
  let seg = startSegments && c.joints.every((id, i) => q[id] === q0[i] && q[id] === targets[id]) ? startSegments : segmentsFor(q);
  // folded: the target is nearer the root than the limb can bring its end with the bend at its end (the caller may
  // then leave the limb alone instead of letting the folded limb swing round its root).
  let folded = false;
  // The bend, from the distance root -> target.
  {
    const root = limbPoint(rig, seg, limb, 'root'), bend = limbPoint(rig, seg, limb, 'bend'), end = limbPoint(rig, seg, limb, 'end');
    const L1 = len(sub(bend, root)), L2 = len(sub(end, bend)), D = clamp(len(sub(targetMm, root)), Math.abs(L1 - L2) + 1e-6, L1 + L2 - 1e-6);
    const angleAt = d => Math.acos(clamp((L1 * L1 + L2 * L2 - d * d) / (2 * L1 * L2), -1, 1)) * 180 / Math.PI;
    // The end point (the hand's centre, the ankle) is not exactly on the line of the lower segment, so a straight limb
    // is not a 180-degree triangle: measure the inner angle now and count the bend from it (a bend of b degrees closes
    // the inner angle by b), so the distance the limb has now asks for exactly the bend it has now (no drift).
    const innerNow = angleAt(clamp(len(sub(end, root)), Math.abs(L1 - L2) + 1e-6, L1 + L2 - 1e-6));
    const inner = angleAt(D);
    const raw = q[c.bend] + c.bendSign * (innerNow - inner);
    const want = clamp(raw, lim(c.bend)[0], lim(c.bend)[1]);
    if (Math.abs(want - q[c.bend]) > 0.05) { q[c.bend] = want; fit(); seg = segmentsFor(q); }
    folded = c.bendSign * (raw - q[c.bend]) > 1; // (asked for more bend than the joint, or the combined-range rule, gives)
  }
  // Then the two root joints point the limb at the target (the bend stays as the distance asks: pulling the end in bends
  // the elbow / knee, moving it up or sideways swings the whole limb at the shoulder / hip, as a person would).
  const rootJoints = c.joints.filter(id => id !== c.bend);
  let end = limbPoint(rig, seg, limb, 'end'), it = 0;
  let lastErr = Infinity;
  const lambda = Number.isFinite(opts.lambdaShare) ? Math.max(Number.isFinite(opts.lambdaMinMm) ? opts.lambdaMinMm : 0.5, opts.lambdaShare * len(sub(end, limbPoint(rig, seg, limb, 'root')))) : opts.lambdaMm;
  for (; it < opts.solveIters; it++) {
    const e = sub(targetMm, end), err = len(e);
    if (err <= opts.tolMm) break;
    if (Number.isFinite(opts.minGain) && lastErr - err < opts.minGain * lastErr) break; // (LIMB_TRACK: no longer getting nearer)
    lastErr = err;
    // memo (19 November 2026; a caller that solves the same limb frame after frame): the two columns found last are used
    // again while the limb's joints are within opts.reuseDeg of where they were found and the last step made with them
    // still closed in on the target. Each column costs one pose of the whole body, so this halves a tracking solve.
    const reuse = memo && memo.limb === limb && memo.J && !memo.stale && Number.isFinite(opts.reuseDeg) && memo.J.length === rootJoints.length
      && c.joints.every(id => Number.isFinite(memo.at[id]) && Math.abs(q[id] - memo.at[id]) <= opts.reuseDeg);
    const J = reuse ? memo.J : rootJoints.map(id => {

      // cuts back (project) went into a range the pose does not take: its column came out zero, or worse, it showed a
      // drawn coupling's move the step could never make (a thigh past 100 degrees bends its drawn knee instead), and the
      // step then never used that joint, or pushed it the wrong way: A could not bring a leg back in from the end of its
      // sideways range, and a thigh lifted to its end could not be lowered again. Such a probe is made the other way.
      // (A drawn coupling can also leave a few degrees at a range's end that move nothing: the probe then goes on, up to
      // 8 times as far, inward.)
      const at = hh => {
        if (q[id] + hh < lim(id)[0] || q[id] + hh > lim(id)[1]) return null;
        const qq = { ...q, [id]: q[id] + hh };
        if (typeof project === 'function') { const pp = project(qq); if (pp && Number.isFinite(pp[id]) && Math.abs(pp[id] - qq[id]) > 1e-6) return null; }
        const pk = limbPoint(rig, segmentsFor(qq), limb, 'end');
        return len(sub(pk, end)) >= 1e-4 ? pk : null;
      };
      const h0 = q[id] + opts.probeDeg <= lim(id)[1] ? opts.probeDeg : -opts.probeDeg;
      let h = h0, p = at(h0);
      if (!p) for (const k of [-1, -4, 4, -8, 8]) { const pk = at(h0 * k); if (pk) { h = h0 * k; p = pk; break; } }
      if (!p) { h = h0; p = limbPoint(rig, segmentsFor({ ...q, [id]: q[id] + h0 }), limb, 'end'); }
      return sub(p, end).map(v => v / h);
    });
    if (memo && !reuse) { memo.limb = limb; memo.J = J; memo.at = {}; for (const id of c.joints) memo.at[id] = q[id]; memo.stale = false; memo.made = (memo.made || 0) + 1; }
    // (spin: the upper arm's turn costs 1 / weight^2 of the others: its column is scaled down and its step with it; and a
    // shoulder joint the step pushes past what its range or the combined-range rule gives is left out of a second step,
    // so the turn takes over where the raise and the sideways swing are at their end)
    // (the turn moves the hand only round a bent elbow: its weight grows from nothing at bendFrom to all at bendTo
    // degrees of bend, so with the arm straight the keys never turn the upper arm for the hand's few millimetres)
    const spinW = sp ? sp.weight * (u => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u)))((c.bendSign * q[c.bend] - sp.bendFrom) / (sp.bendTo - sp.bendFrom)) : 0;


    // first step leaves the turn out; only a step that pushes the raise or the sideways swing past their range is made
    // again with the turn in their place.)
    const wOf = (id, on) => (sp && id === sp.joint ? (on ? spinW : 0) : 1);
    const solveStep = (cols, on) => dlsStep(cols.map((col, i) => col.map(v => v * wOf(rootJoints[i], on))), e, lambda).map((v, i) => v * wOf(rootJoints[i], on));
    let dq = solveStep(J, false);
    // (memo.spinAcross: once the keys found the hand across the body, the turn stays allowed as the hand comes in toward
    // the shoulder and so leaves the across side, until the caller clears it)
    // (21 November 2026, evening, FIX63, LIMB_CHAIN across.elbowMm: and only with the upper arm itself brought across,
    // the elbow toward the body's other side of the shoulder; a hanging arm's elbow is outside it. Late: handMm, the
    // leave ends once the hand's place is level with the shoulder or outside it; again, an upper arm the keys have
    // turned, and nothing else since, is given the leave again without the elbow's test)
    const acrossNow = !sp || !sp.across || (() => {
      const A = sp.across, S = seg[A.seg], m = A.toMedial, latched = Boolean(memo && memo.spinAcross === true);
      if (!S) return latched;
      const d = [S[0] * m[0] + S[4] * m[1] + S[8] * m[2], S[1] * m[0] + S[5] * m[1] + S[9] * m[2], S[2] * m[0] + S[6] * m[1] + S[10] * m[2]];
      const medial = (p, ref) => (p[0] - ref[0]) * d[0] + (p[1] - ref[1]) * d[1] + (p[2] - ref[2]) * d[2]; // (mm that p lies toward the body's other side of ref)
      const shoulder = limbPoint(rig, seg, limb, 'root');
      if (Number.isFinite(A.handMm) && !(medial(targetMm, shoulder) > A.handMm)) { if (latched) memo.spinAcross = false; return false; }
      if (latched) return true;
      const elbow = limbPoint(rig, seg, limb, 'bend'), elbowIn = medial(elbow, shoulder);
      // (again: a turn the keys made gives the leave again with a looser elbow test, againElbowMm, not none)
      if (A.again === true && spinMine && !(Number.isFinite(A.againElbowMm) && !(elbowIn > A.againElbowMm))) return true;
      if (Number.isFinite(A.elbowMm) && !(elbowIn > A.elbowMm)) return false;
      return medial(targetMm, elbow) > A.medialMm;
    })();
    if (sp && acrossNow && memo) memo.spinAcross = true;
    if (sp && spinW > 0 && acrossNow) {
      const qq = { ...q };
      rootJoints.forEach((id, i) => { qq[id] = clamp(q[id] + clamp(dq[i], -opts.stepCapDeg, opts.stepCapDeg), lim(id)[0], lim(id)[1]); });
      const pp = typeof project === 'function' ? project(qq) || qq : qq;
      const blocked = rootJoints.map((id, i) => id !== sp.joint && Math.abs(dq[i]) > 1e-6 && Math.abs((Number.isFinite(pp[id]) ? pp[id] : qq[id]) - q[id]) < 0.5 * Math.min(Math.abs(dq[i]), opts.stepCapDeg));
      if (blocked.some(Boolean)) { const d2 = solveStep(J.map((col, i) => (blocked[i] ? col.map(() => 0) : col)), true); dq = d2.map((v, i) => (blocked[i] ? 0 : v)); }
    }
    let moved = false;
    const before = rootJoints.map(id => q[id]);
    rootJoints.forEach((id, i) => { q[id] = clamp(q[id] + clamp(dq[i], -opts.stepCapDeg, opts.stepCapDeg), lim(id)[0], lim(id)[1]); });
    fit();
    rootJoints.forEach((id, i) => { if (q[id] !== before[i]) moved = true; });
    if (!moved) break;
    seg = segmentsFor(q);
    end = limbPoint(rig, seg, limb, 'end');
    // (columns used again that no longer close in: found afresh at the next step)
    if (memo && reuse && opts.keepColumns !== true && len(sub(targetMm, end)) > 0.7 * err) memo.stale = true;
  }
  // (across.again: this frame turned the upper arm, or left alone a turn that is still the keys' own)
  if (sp && memo) { if (q[sp.joint] !== spinStart) memo.spinTurn = [spinStart, q[sp.joint]]; else if (spinMine) memo.spinTurn = [spinStart, spinStart]; }
  const joints = {};
  for (const id of c.joints) joints[id] = q[id];
  // (22 November 2026, LIMBS2: bendMm, where the elbow or knee is in the answer, for the keys' pace of the bend point,
  // ns-limb-pace LIMB_PACE; the segments of the answer are at hand, so it costs no pose)
  return { joints, endMm: end, bendMm: limbPoint(rig, seg, limb, 'bend'), errorMm: len(sub(targetMm, end)), iterations: it, folded };
}

/**
 * Turn (degrees, right-handed about the limb's long axis pointing from root to end) for a drag across it, like rolling
 * a rod under a finger: the near surface (toward the eye) follows the pointer. axisWorld: root -> end (world, any
 * length); viewDirWorld: from the eye toward the limb; rightWorld / upWorld: the screen's right and up in the world;
 * dx / dy: CSS px (dy down). Returns degrees (0 when the limb points along the view).
 */
export function rollDeg({ axisWorld, viewDirWorld, rightWorld, upWorld, dx, dy, degPerPx = LIMB_GRASP.rollDegPerPx }) {
  const a = axisWorld, la = len(a);
  if (!(la > 1e-9)) return 0;
  const u = a.map(v => v / la);
  // The near surface's offset from the axis: toward the eye, perpendicular to the axis.
  const n0 = viewDirWorld.map(v => -v);
  const d = n0[0] * u[0] + n0[1] * u[1] + n0[2] * u[2];
  const n = [n0[0] - d * u[0], n0[1] - d * u[1], n0[2] - d * u[2]], ln = len(n);
  if (!(ln > 1e-6)) return 0;
  // A right-handed turn about u moves the near surface along u x n.
  const t = [u[1] * n[2] - u[2] * n[1], u[2] * n[0] - u[0] * n[2], u[0] * n[1] - u[1] * n[0]].map(v => v / ln);
  const w = [rightWorld[0] * dx - upWorld[0] * dy, rightWorld[1] * dx - upWorld[1] * dy, rightWorld[2] * dx - upWorld[2] * dy];
  return (w[0] * t[0] + w[1] * t[1] + w[2] * t[2]) * degPerPx;
}











export function jointAreaIndex(bodyMap, restDeg = {}, limits = null) {
  const out = {};
  const regions = bodyMap && Array.isArray(bodyMap.regions) ? bodyMap.regions : [];
  const stopSide = (id, end) => {
    const L = limits && Array.isArray(limits[id]) ? limits[id] : null;
    return !L ? null : Math.abs(end - L[1]) < 0.5 ? '1' : Math.abs(end - L[0]) < 0.5 ? '-1' : null;
  };
  for (const single of [true, false]) {
    for (const r of regions) {
      for (const a of (r && Array.isArray(r.actions) ? r.actions : [])) {
        const j = a && a.joints && typeof a.joints === 'object' ? Object.keys(a.joints) : [];
        if (!j.length || (single && j.length !== 1)) continue;
        for (const id of j) {
          const end = a.joints[id], rest = Number.isFinite(restDeg[id]) ? restDeg[id] : 0;
          if (!Number.isFinite(end)) continue;
          const side = Math.abs(end - rest) >= 0.5 ? (end > rest ? '1' : '-1') : stopSide(id, end);
          if (!side) continue;
          out[id] = out[id] || {};
          if (!out[id][side]) out[id][side] = { regionId: r.id, actionId: a.id };
        }
      }
    }
  }
  return out;
}
