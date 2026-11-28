

































































/** Tuning (display choices; see the rule above).
 *  stepStrokeS / slowStrokeS  seconds for a full end-to-end stroke: a double tap's quick switch (0.4 s for every limb;
 *                             it was 1.0 s before 18 November 2026) / the slow turn of a double tap held (1.0 s at
 *                             tempo 1; 2.6 s before 19 November 2026)
 *  tempo                      per-limb speed factors; ratios chosen so no two limbs stay in step (not coordinated)
 *  endEps                     a limb within this fraction of its range of the end it is heading for turns round
 *  moveEpsDeg                 a joint change smaller than this (degrees) is not counted as a movement (history)
 *  glowFullSpeed              turning speed (fraction of the range per second) shown as activity level 1
 *  followGlow                 a follower joint's share of that level (its turn is small and only accompanies the leader) */
export const DANCE = Object.freeze({
  stepStrokeS: 0.4,


  slowStrokeS: 1.0,
  tempo: Object.freeze({ leftArm: 1.0, rightArm: 1.27, leftLeg: 0.86, rightLeg: 1.13 }),
  endEps: 0.004,
  moveEpsDeg: 0.05,
  glowFullSpeed: 1.2,
  followGlow: 0.35
});





















export const DANCE_FOLLOW = Object.freeze({ hipDeg: 0 });






export const LEG_TURN_ENDS = Object.freeze({ open: 25, closed: -65, restOutDeg: 20 });





















// inward (65 before). The forearm still turns the palm right over (160 degrees); with the upper arm turning 60 degrees
// in all instead of 100 the slightly bent elbow no longer swings the forearm far out to the side and back (which read
// as the elbow going varus and valgus).
// 19 November 2026, later (a look at both arms on the overside, from the eyes and from outside): at 25 inward the right
// hand still swung in over the thigh and its elbow stood out, while the left hand (which keeps its place while its arm
// turns) lay beside the thigh: 25 -> 15. The upper arm now turns 50 degrees in all; the palm still turns right over.
export const ARM_TURN = Object.freeze({ shoulder: Object.freeze({ open: 35, closed: -15 }), lag: 0.3, glow: 0.6 });
// (a follower that turns nothing takes its joint's own range as its nominal ends, so history and speeds stay finite)
const follower = (id, deg, lo, hi) => Object.freeze({ id, open: deg ? deg / 2 : hi, closed: deg ? -deg / 2 : lo, follow: deg, lo, hi });
// 18 November 2026, late: a joint with its own two ends that turns over part of each stroke: phase [start, end] of
// the stroke (0..1). The forearm leads over [0, 1 - lag], the upper arm follows over [lag, 1].
const armJoints = (fore, foreOpen, foreClosed, shoulder) => Object.freeze([
  Object.freeze({ id: fore, open: foreOpen, closed: foreClosed, phase: Object.freeze([0, 1 - ARM_TURN.lag]) }),
  Object.freeze({ id: shoulder, open: ARM_TURN.shoulder.open, closed: ARM_TURN.shoulder.closed, lo: -70, hi: 90, phase: Object.freeze([ARM_TURN.lag, 1]), glow: ARM_TURN.glow })
]);
export const DANCE_LIMBS = Object.freeze({
  leftArm: armJoints('l_forearm', -80, 80, 'l_shoulder_rot'),
  rightArm: armJoints('r_pronation', 0, 160, 'r_shoulder_rot'),
  leftLeg: Object.freeze([Object.freeze({ id: 'leg_turn_L', open: LEG_TURN_ENDS.open, closed: LEG_TURN_ENDS.closed }), follower('hip_rot_L', DANCE_FOLLOW.hipDeg, -40, 45)]),
  rightLeg: Object.freeze([Object.freeze({ id: 'leg_turn_R', open: LEG_TURN_ENDS.open, closed: LEG_TURN_ENDS.closed }), follower('hip_rot_R', DANCE_FOLLOW.hipDeg, -40, 45)])
});
export const DANCE_LIMB_IDS = Object.freeze(Object.keys(DANCE_LIMBS));
/** The UNDERSIDE view (rule 6): every joint with ends of its own at its "open" end (the forearms and the upper arms,
 * the leg turns; not the hips, which only follow). The game starts here. */
export const DANCE_UNDERSIDE = Object.freeze(Object.fromEntries(DANCE_LIMB_IDS.flatMap(l => DANCE_LIMBS[l].filter(j => !isFinite(j.follow)).map(j => [j.id, j.open]))));
/** The OVERSIDE view: the same joints at their "closed" ends. */
export const DANCE_OVERSIDE = Object.freeze(Object.fromEntries(DANCE_LIMB_IDS.flatMap(l => DANCE_LIMBS[l].filter(j => !isFinite(j.follow)).map(j => [j.id, j.closed]))));
export const DANCE_JOINT_IDS = Object.freeze(DANCE_LIMB_IDS.flatMap(l => DANCE_LIMBS[l].map(j => j.id)));
/**
 * 18 November 2026, late: the upper arm's turn range at a given elevation, mirrored from ns-body (BODY_JOINT_LIMITS
 * r_shoulder_rot -70..90 and COMBINED_RANGE.shoulder.rotAtFullElevationDeg 30; a test keeps the two equal): the full
 * range up to shoulder height, narrowing to +-30 with the arm straight up (the joint is close-packed there). elevDeg:
 * the upper arm's angle from hanging along the trunk. Returns [lo, hi] degrees (+ outward).
 */
export const SHOULDER_TURN_RANGE = Object.freeze({ lo: -70, hi: 90, atFullElevationDeg: 30 });
export function shoulderTurnRange(elevDeg) {
  const R = SHOULDER_TURN_RANGE, u = clamp(((isNum(elevDeg) ? elevDeg : 0) - 90) / 90, 0, 1);
  return [R.lo + (-R.atFullElevationDeg - R.lo) * u, R.hi + (R.atFullElevationDeg - R.hi) * u];
}
/** The right upper arm's elevation (degrees from hanging) for ns-body's sideways lift then forward swing (the same
 * formula as ns-body shoulderCombinedRange, without its own clamps of the two angles). */
export function shoulderElevationDeg(flexDeg, abdDeg) {
  const D = Math.PI / 180, f = isNum(flexDeg) ? flexDeg : 0, a = isNum(abdDeg) ? abdDeg : 0;
  return Math.acos(clamp(Math.cos(a * D) * Math.cos(f * D), -1, 1)) / D;
}

const fail = (code, message) => { throw new Error(`ns:${code}: ${message}`); };
const isNum = v => typeof v === 'number' && Number.isFinite(v);
const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);

/** A joint's two ends after an optional [lo, hi] range: { open, closed }. */
function endsOf(j, ranges) {
  const r = ranges && Array.isArray(ranges[j.id]) && ranges[j.id].length === 2 && isNum(ranges[j.id][0]) && isNum(ranges[j.id][1]) ? ranges[j.id] : null;
  if (!r) return { open: j.open, closed: j.closed };
  const lo = Math.min(r[0], r[1]), hi = Math.max(r[0], r[1]);
  return { open: clamp(j.open, lo, hi), closed: clamp(j.closed, lo, hi) };
}
/** Openness 0 (closed end) .. 1 (open end) of an angle against the joint's FULL range. */
const openness = (j, deg) => (deg - j.closed) / (j.open - j.closed);

function checkAngles(angles) {
  if (!angles || typeof angles !== 'object') fail('dance_input', 'angles must be an object of joint id -> degrees');
  for (const id of DANCE_JOINT_IDS) if (!isNum(angles[id])) fail('dance_input', `angle ${id} must be finite degrees`);
}

/**
 * A fresh dance state for the start angles (plain JSON). A limb with no history moves first toward the end that is
 * farther from where it starts (its bigger movement), measured on its first joint (the forearm for an arm).
 */
export function createDance(angles) {
  checkAngles(angles);
  const limbs = {};
  for (const l of DANCE_LIMB_IDS) {
    const j = DANCE_LIMBS[l][0];
    limbs[l] = { dir: openness(j, angles[j.id]) <= 0.5 ? 1 : -1, stroke: null, level: 0, done: true };
  }
  const seen = {}, levels = {};
  for (const id of DANCE_JOINT_IDS) { seen[id] = angles[id] + 0; levels[id] = 0; }
  // mode: null (nothing turns) | 'step' (a double tap's one stroke per limb) | 'hold' (the slow turn of a double tap held).
  // A limb's `done` is true once it has made its stroke of the current step (and whenever no step runs).
  return { limbs, seen, levels, mode: null, active: false };
}


export const TURN_MODES = Object.freeze(['step', 'hold']);
const strokeSecondsFor = mode => (mode === 'step' ? DANCE.stepStrokeS : DANCE.slowStrokeS);

/** True when a value is a dance state (shape check for the activity's state validator). */
export function isDanceState(d) {
  if (!d || typeof d !== 'object' || !(d.mode === null || TURN_MODES.includes(d.mode)) || typeof d.active !== 'boolean' || !d.limbs || !d.seen || !d.levels) return false;
  for (const id of DANCE_JOINT_IDS) if (!isNum(d.seen[id]) || !isNum(d.levels[id]) || d.levels[id] < 0 || d.levels[id] > 1) return false;
  for (const l of DANCE_LIMB_IDS) {
    const s = d.limbs[l];
    if (!s || (s.dir !== 1 && s.dir !== -1) || !isNum(s.level) || s.level < 0 || s.level > 1 || typeof s.done !== 'boolean') return false;
    if (s.stroke !== null) {
      const k = s.stroke;
      if (!k || !isNum(k.t) || !isNum(k.T) || !(k.T > 0) || k.t < 0 || !k.from || !k.to || !TURN_MODES.includes(k.mode)) return false;
      for (const j of DANCE_LIMBS[l]) if (!isNum(k.from[j.id]) || !isNum(k.to[j.id])) return false;
    }
  }
  return true;
}

/**
 * History (rule 2): compare the current angles with the last ones seen and record, per limb, the direction any outside
 * movement took (an activation, a drag, a reset). A running stroke is dropped when its limb was moved from outside, so
 * the next stroke starts from where the limb now is. Returns a new state (the input is not changed).
 */
export function observeDance(dance, angles) {
  checkAngles(angles);
  const d = { ...dance, limbs: { ...dance.limbs }, seen: { ...dance.seen } };
  for (const l of DANCE_LIMB_IDS) {
    let sum = 0, moved = false;
    for (const j of DANCE_LIMBS[l]) {
      const delta = angles[j.id] - d.seen[j.id];
      if (Math.abs(delta) > DANCE.moveEpsDeg) { moved = true; sum += delta / (j.open - j.closed); }
    }
    if (moved) {
      d.limbs[l] = { ...d.limbs[l], dir: sum > 0 ? 1 : sum < 0 ? -1 : d.limbs[l].dir, stroke: null };
      // The reference moves on only once a movement is counted, so a slow movement (less than moveEpsDeg per step, for
      // example the tail of an ease) still adds up and counts, and the direction is that of the whole movement.
      for (const j of DANCE_LIMBS[l]) d.seen[j.id] = angles[j.id] + 0;
    }
  }
  return d;
}

const ease = q => 0.5 - 0.5 * Math.cos(Math.PI * q);
const easeRate = q => 0.5 * Math.PI * Math.sin(Math.PI * q); // d ease / d q

/** A new stroke for limb l from the current angles in direction dir (null when the leading joint is already at that
 * end). The leader goes to its end; each follower turns the same way by its `follow` degrees times the share of a
 * whole stroke the leader still has to go, from where it is, inside its own range (and a narrower one in `ranges`). */
function newStroke(l, angles, dir, ranges, strokeS, tempo = DANCE.tempo[l]) {
  const from = {}, to = {};
  const joints = DANCE_LIMBS[l], lead = joints[0], e0 = endsOf(lead, ranges);
  from[lead.id] = angles[lead.id];
  to[lead.id] = dir > 0 ? e0.open : e0.closed;
  let frac = Math.abs(to[lead.id] - from[lead.id]) / Math.abs(lead.open - lead.closed);
  // 18 November 2026, late: a joint with ends of its own (the upper arm) counts too, so a limb whose forearm is
  // already at the end but whose upper arm is not (a turn stopped during the upper arm's later part) still finishes.
  for (let i = 1; i < joints.length; i++) {
    const j = joints[i];
    if (isNum(j.follow)) continue;
    const e = endsOf(j, ranges), goal = dir > 0 ? e.open : e.closed;
    frac = Math.max(frac, Math.abs(goal - angles[j.id]) / Math.abs(j.open - j.closed));
  }
  if (!(frac > DANCE.endEps)) return null;
  for (let i = 1; i < joints.length; i++) {
    const j = joints[i];
    from[j.id] = angles[j.id];
    if (isNum(j.follow)) {
      const r = ranges && Array.isArray(ranges[j.id]) && ranges[j.id].length === 2 && isNum(ranges[j.id][0]) && isNum(ranges[j.id][1]) ? ranges[j.id] : null;
      const lo = Math.max(j.lo, r ? Math.min(r[0], r[1]) : -Infinity), hi = Math.min(j.hi, r ? Math.max(r[0], r[1]) : Infinity);
      // A follower already outside a narrowed range is not pushed further; it may only come back.
      to[j.id] = clamp(from[j.id] + dir * j.follow * Math.min(1, frac), Math.min(lo, from[j.id]), Math.max(hi, from[j.id]));
    } else {
      const e = endsOf(j, ranges);
      to[j.id] = dir > 0 ? e.open : e.closed;
    }
  }
  return { from, to, t: 0, T: (frac * strokeS) / tempo, frac };
}








export function startTurnStep(dance) {
  let sum = 0;
  for (const l of DANCE_LIMB_IDS) { const j = DANCE_LIMBS[l][0]; sum += clamp(openness(j, dance.seen[j.id]), 0, 1); }
  const running = dance.mode === 'step' && (dance.target === 1 || dance.target === -1) && DANCE_LIMB_IDS.some(l => !dance.limbs[l].done);
  const target = running ? -dance.target : (sum / DANCE_LIMB_IDS.length >= 0.5 ? -1 : 1);
  const limbs = {};
  for (const l of DANCE_LIMB_IDS) limbs[l] = { ...dance.limbs[l], dir: target, stroke: null, done: false };
  return { ...dance, limbs, mode: 'step', active: true, target };
}






export function startTurnHold(dance) {
  const limbs = {};
  for (const l of DANCE_LIMB_IDS) limbs[l] = { ...dance.limbs[l], done: false };
  return { ...dance, limbs, mode: 'hold', active: true };
}

/**
 * Advance the turn by h seconds (rules 1-4) in the state's own mode (dance.mode: 'step' | 'hold'; with no mode nothing
 * moves). angles: the current joint angles (every DANCE_JOINT_IDS id). opts: { ranges: { jointId: [lo, hi] } (narrowing
 * only) }. Returns { dance, angles } (new objects; the angles object holds every dance joint). With h = 0 nothing moves.
 * A step ends by itself once every limb is done (the returned state then has mode null and active false).
 */
export function stepDance(dance, angles, h, { ranges = null } = {}) {
  checkAngles(angles);
  if (!(isNum(h) && h >= 0)) fail('dance_input', 'h must be finite seconds >= 0');
  const out = {};
  for (const id of DANCE_JOINT_IDS) out[id] = angles[id];
  const mode = dance.mode;
  if (!TURN_MODES.includes(mode)) return { dance: stopDance(dance), angles: out };
  const strokeS = strokeSecondsFor(mode);
  const d = { ...dance, limbs: { ...dance.limbs }, levels: { ...dance.levels }, active: true };
  for (const l of DANCE_LIMB_IDS) {
    const jspeed = {};
    for (const j of DANCE_LIMBS[l]) jspeed[j.id] = 0;
    let s = { ...d.limbs[l] };
    // The running stroke is copied before its clock advances (the input state is never changed).
    if (s.stroke) s.stroke = { ...s.stroke };
    // A stroke started in the other mode (the double tap's step, now held) keeps its progress q and only takes longer:
    // T and t are stretched by the ratio of the stroke times, so the limb slows down where it is (no restart, no jump).
    if (s.stroke && s.stroke.mode !== mode) {
      const r = strokeS / strokeSecondsFor(s.stroke.mode);
      s.stroke = { ...s.stroke, T: s.stroke.T * r, t: s.stroke.t * r, mode };
    }
    let left = h, speed = 0, guard = 0;
    while (guard++ < 8) {
      if (!s.stroke) {
        if (mode === 'step' && s.done) break; // this step's stroke is made: the limb waits where it is
        const cur = {};
        for (const j of DANCE_LIMBS[l]) cur[j.id] = out[j.id];
        // A quick switch (rule 6) moves every limb at one speed and leaves a limb that is already on the wanted side.
        let k = newStroke(l, cur, s.dir, ranges, strokeS, mode === 'step' ? 1 : DANCE.tempo[l]);
        if (!k && mode === 'step') { s.done = true; break; }
        if (!k) { s.dir = -s.dir; k = newStroke(l, cur, s.dir, ranges, strokeS); }
        if (!k) { s.done = true; break; } // a limb with no room at all (both ends at its angle) stays where it is
        s.stroke = { ...k, mode };
      }
      const k = s.stroke;
      const dtq = Math.min(left, k.T - k.t);
      k.t = Math.min(k.T, k.t + dtq);
      left -= dtq;
      const q = k.t / k.T;
      // 18 November 2026, late: each joint turns over its own phase of the stroke (the forearm first, the upper arm
      // after it; a joint with no phase over the whole stroke), each with its own smooth start and stop.
      speed = 0;
      for (const j of DANCE_LIMBS[l]) {
        const p0 = j.phase ? j.phase[0] : 0, span = j.phase ? j.phase[1] - j.phase[0] : 1;
        const qj = clamp((q - p0) / span, 0, 1), inside = q > p0 && q < p0 + span;
        out[j.id] = k.from[j.id] + (k.to[j.id] - k.from[j.id]) * ease(qj);
        // speed as a fraction of the range per second (the limb: its fastest joint; and each joint)
        const sj = inside ? (Math.abs(k.to[j.id] - k.from[j.id]) / Math.abs(j.open - j.closed)) * easeRate(qj) / (k.T * span) : 0;
        speed = Math.max(speed, sj);
        // (a follower's small turn is shown fainter than the leader's: the wrist and the ankle are what the turn is about)
        jspeed[j.id] = sj * (isNum(j.follow) ? DANCE.followGlow : 1);
      }
      if (k.t >= k.T - 1e-12) {
        s.stroke = null; s.dir = -s.dir;
        // A step makes one stroke per limb; the slow hold goes on with the next one.
        if (mode === 'step' || left <= 1e-12) { if (mode === 'step') s.done = true; speed = 0; for (const j of DANCE_LIMBS[l]) jspeed[j.id] = 0; break; }
        continue;
      }
      if (left <= 1e-12) break;
    }
    s.level = h > 0 ? clamp(speed / DANCE.glowFullSpeed, 0, 1) : s.level;
    // (18 November 2026, late: a joint's glow share, the upper arm's ARM_TURN.glow, scales its level after the clamp, so
    // it holds in a quick switch too, where every turning joint's speed is past full)
    if (h > 0) for (const j of DANCE_LIMBS[l]) d.levels[j.id] = clamp(jspeed[j.id] / DANCE.glowFullSpeed, 0, 1) * (isNum(j.glow) ? j.glow : 1);
    d.limbs[l] = s;
  }
  d.seen = { ...dance.seen };
  for (const id of DANCE_JOINT_IDS) d.seen[id] = out[id] + 0;
  // The step is over once every limb has made its stroke.
  if (mode === 'step' && DANCE_LIMB_IDS.every(l => d.limbs[l].done)) return { dance: stopDance(d), angles: out };
  return { dance: d, angles: out };
}

/** The turn ends (Space let go after a double tap and hold, a step finished, a pause, Reset body): the limbs stay where
 * they are; the running strokes end, the directions are kept. */
export function stopDance(dance) {
  const limbs = {}, levels = {};
  for (const l of DANCE_LIMB_IDS) limbs[l] = { ...dance.limbs[l], stroke: null, level: 0, done: true };
  for (const id of DANCE_JOINT_IDS) levels[id] = 0;
  return { ...dance, limbs, levels, mode: null, active: false };
}
