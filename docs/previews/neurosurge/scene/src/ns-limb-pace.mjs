/** NeuroSurge: the pace of your own limbs under the keys, the light of a limb at the end of its range, and limbs that
 * neither stay pushed after a movement from the brain nor pass through each other (22 November 2026, LIMBS2; a browser
 * hunt of Body update 64, findings H1, H2 and H3, and a check of the SEEMOVE rounds: a leg left 87 mm off its place).
 *
 * Pure maths, no DOM, no three.js: points are world metres [x, y, z], angles degrees. The app (ns-app stepLimbHold,
 * stepLimbPush) uses these. Display rules of this game's controls; nothing here is a measured movement, force or speed.
 */

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const len = a => Math.hypot(a[0], a[1], a[2]);

















export const HOLD_DRAWN = Object.freeze({ on: true });
export function holdBendAsDrawn(start, bendId, passive, o = HOLD_DRAWN) {
  const own = start && bendId ? start[bendId] : undefined;
  if (!o.on || typeof passive !== 'function' || !Number.isFinite(own)) return own;
  const drawn = passive(start)[bendId];
  return Number.isFinite(drawn) && Math.abs(drawn) > Math.abs(own) ? drawn : own;
}

/**
 * 25 November 2026 (FIX76, finding 7). BODY_SLIDE: the place a frame of the keys asks again when its answer was refused
 * for taking the hand deeper into the trunk's keep-out or the head's column (ns-app handKeepOut). The place the keys
 * ask for lies on their own line and may be clear of the body while the hand, a centimetre off that line, is at its
 * surface: the answer then carried the hand 5 to 8 mm in, was refused, and the next frame asked the same. Held W on the
 * right arm folded up beside the neck moved the hand 8 cm and then nothing, with the elbow at 128 degrees.
 *   from   the hand now; to: where the refused answer put it; out: `to` taken out to the surface (handKeepOut(to));
 *   way    the keys' own move this frame (all world m); cut: ns-app keyMoveCut.
 * Returns the place to ask for, `out` moved clearM further out along the way it was taken out, when what is left of the
 * move still goes the keys' way (cut > 0: at most keyFarDeg off it) and is more than minShare of it; else null: the
 * move went straight into the body and the hand stops there, as before. Pure. */
export const BODY_SLIDE = Object.freeze({ on: true, clearM: 0.003, minShare: 0.2 });
export function keyBodySlide(from, to, out, way, cut, o = BODY_SLIDE) {
  if (!o.on || !from || !to || !out || !way || typeof cut !== 'function') return null;
  const n = sub(out, to), nl = len(n), wl = len(way);
  if (!(nl > 1e-6) || !(wl > 1e-9)) return null;
  const T = [out[0] + n[0] / nl * o.clearM, out[1] + n[1] / nl * o.clearM, out[2] + n[2] / nl * o.clearM], m = sub(T, from);
  return len(m) > o.minShare * wl && cut(m, way) > 0 ? T : null;
}

























































export const LIMB_PACE = Object.freeze({ on: true, bendMost: 1.25, rhoFar: 2, creepMost: 0.5, releaseStops: true,
  swing: true, foldShare: 0.6, leg: Object.freeze({ bendMost: 2.5, rhoFar: null, creepMost: null, swing: false }) });








































export const LIMB_ACROSS = Object.freeze({ on: true, offDeg: 60, back: true, openMostDeg: 30 });

/** LIMB_ACROSS: the turn (degrees, signed) of the upper arm about its length that moves the end the keys' own way `way`
 * this frame (world m), from `perDeg` (world m: the end's move for +1 degree of the turn, measured), the turn now `rot`
 * and its range [lo, hi] (degrees); `stop` (optional): a value the turn does not go past (D turning back to where A's
 * turn began). 0 when the rule is off, the move would be more than offDeg off the way, or no range is left that way.
 * Pure. */
export function spinStepDeg(perDeg, way, { rot = 0, lo = -Infinity, hi = Infinity, stop = null } = {}, o = LIMB_ACROSS) {
  if (!o || o.on === false || !perDeg || !way) return 0;
  const wl = len(way), pl = len(perDeg);
  if (!(wl > 1e-9) || !(pl > 1e-9)) return 0;
  const c = (perDeg[0] * way[0] + perDeg[1] * way[1] + perDeg[2] * way[2]) / (wl * pl);
  if (Math.abs(c) < Math.cos((Number.isFinite(o.offDeg) ? o.offDeg : 60) * Math.PI / 180)) return 0;
  const sg = c > 0 ? 1 : -1;
  let to = rot + sg * (wl / pl);
  to = Math.min(hi, Math.max(lo, to));
  if (Number.isFinite(stop)) to = sg > 0 ? Math.min(to, Math.max(rot, stop)) : Math.max(to, Math.min(rot, stop));
  const d = to - rot;
  return Math.abs(d) > 1e-6 && Math.sign(d) === sg ? d : 0;
}

/**
 * LIMB_ACROSS: this frame's step of A (D: back) on a folded limb with a `spin` joint. q: the limb's angles now (degrees by
 * joint); chain: ns-grasp LIMB_CHAIN[limb]; across: A (toward the body's other half) rather than D; way: the keys' own move
 * of the end this frame (m, on the sphere about the root); wayLevel: the same step straight along the body's left or right
 * (m; the opening's way: with the hand already across, the sphere's way toward the left points back and down); endAt(q)
 * -> the end (m) for the limb's angles q; limits: by joint; spinRec / openRec: A's turn
 * and A's opening so far ({ from, last }, or null: none, or something else has moved that joint since). D undoes the
 * opening first, then the turn. Returns null (not this frame's way) or { id (the joint), d (degrees), from (where A's turn
 * or opening began), phase ('spin' | 'open'), back, way (the way this step was taken for) }; phase 'end' (id null, d 0):
 * A's own turn and opening are both at their end, so A moves the arm no further. Pure apart from endAt.
 */
export function acrossStep({ q, chain, across, way, wayLevel = null, endAt, limits, spinRec = null, openRec = null }, o = LIMB_ACROSS) {
  if (!o || o.on === false || !chain || !chain.spin || !way || typeof endAt !== 'function') return null;
  const id = chain.spin.joint, rot = q[id], bid = chain.bend, el = q[bid], sg = chain.bendSign || 1;
  if (!Number.isFinite(rot)) return null;
  const spinR = spinRec && Math.abs(spinRec.last - rot) < 0.05 ? spinRec : null;
  const canOpen = Number.isFinite(o.openMostDeg) && o.openMostDeg > 0 && Number.isFinite(el) && limits && limits[bid];
  const openR = canOpen && openRec && Math.abs(openRec.last - el) < 0.05 ? openRec : null;
  if (!across && !(o.back && (spinR || openR))) return null;
  const e0 = endAt(q);
  // (the end's move for +1 degree of joint j, probed the way the step will go: dir -1 probes 1 degree down and turns it
  // round; near a range's end a probe past it moves the end less than a degree's worth and the step came out 5 times
  // too long)
  const per = (j, v, dir = 1) => { const e1 = endAt({ ...q, [j]: v + dir }); return [(e1[0] - e0[0]) * dir, (e1[1] - e0[1]) * dir, (e1[2] - e0[2]) * dir]; };
  // D: the opening is closed back first, to where it began
  const wo = Array.isArray(wayLevel) ? wayLevel : way;
  if (!across && openR) {
    const lim = limits[bid], d = spinStepDeg(per(bid, el, sg), wo, { rot: el, lo: lim[0], hi: lim[1], stop: openR.from }, o);
    return d ? { id: bid, d, from: openR.from, phase: 'open', back: true, way: wo } : null;
  }
  const lim = limits[id];
  if (!lim) return null;
  const d = spinStepDeg(per(id, rot), way, { rot, lo: lim[0], hi: lim[1], stop: across ? null : spinR.from }, o);
  if (d) return { id, d, from: spinR ? spinR.from : rot, phase: 'spin', back: !across, way };
  if (!across || !canOpen) return null;
  // A at the turn's end: the elbow opens (only opening, at most openMostDeg from where it began)
  const from = openR ? openR.from : el, bl = limits[bid];
  const lo = sg > 0 ? Math.max(bl[0], from - o.openMostDeg) : el, hi = sg > 0 ? el : Math.min(bl[1], from + o.openMostDeg);
  const d2 = spinStepDeg(per(bid, el, -sg), wo, { rot: el, lo, hi }, o);
  if (d2) return { id: bid, d: d2, from, phase: 'open', back: false, way: wo };
  // (A's own turn and opening both made and at their end: the arm lies across; A moves it no further this way, and no
  // other way either: the swing that would take over raised the upper arm and the hand to the face, 100 mm above the
  // shoulder, measured on the game's body)
  return spinR && openR ? { id: null, d: 0, from, phase: 'end', back: false, way: wo } : null;
}

/** LIMB_PACE: the values for a limb ('rightArm', 'rightLeg', 'leftLeg'): the legs' own (LIMB_PACE.leg) over the arm's.
 * Pure. */
export function paceFor(limb, o = LIMB_PACE) {
  return o && o.leg && (limb === 'rightLeg' || limb === 'leftLeg') ? { ...o, ...o.leg } : o;
}

/** LIMB_PACE rhoFar: how many times as far the bend point goes as a swing of the limb as one piece about its root would
 * take it for the end's own move (before / after: { root, bend, end }, world m; the end's move counted at least
 * floorM). 1 for such a swing; 0 when the bend point does not move. Pure. */
export function limbBendRho(before, after, floorM = 1e-4) {
  const bm = len(sub(after.bend, before.bend));
  if (!(bm > 0)) return 0;
  const er = len(sub(before.end, before.root)), br = len(sub(before.bend, before.root));
  if (!(er > 1e-6)) return Infinity;
  return bm / (Math.max(len(sub(after.end, before.end)), floorM) * br / er);
}

/** LIMB_PACE: the share (0..1] of a frame's joint change the keys keep so that the bend point goes at most bendMost x
 * the keys' way (wayM, m), and at most creepMost x the way where it goes more than rhoFar x the one-piece swing's
 * (limbBendRho, the end's move counted at least a twentieth of the way). before / after: { root, bend, end } (world m;
 * after: where the whole change would put them). 1 when the rule is off, there is no way, or nothing is over. Pure (the
 * caller measures again after the cut: the pose is not linear in the joints). */
export function limbPaceShare(before, after, wayM, o = LIMB_PACE) {
  if (!o || o.on === false || !(wayM > 1e-9) || !before || !after) return 1;
  const bm = len(sub(after.bend, before.bend));
  let most = Number.isFinite(o.bendMost) ? o.bendMost : Infinity;
  if (Number.isFinite(o.rhoFar) && Number.isFinite(o.creepMost) && limbBendRho(before, after, 0.05 * wayM) > o.rhoFar) most = Math.min(most, o.creepMost);
  return bm > most * wayM ? (most * wayM) / bm : 1;
}

/** LIMB_PACE foldShare: whether a limb is folded: its end nearer its root than foldShare of its full reach (the upper and
 * lower segments' lengths together). pts: { root, bend, end } (world m). Pure. */
export function limbFolded(pts, o = LIMB_PACE) {
  if (!pts || !o || !Number.isFinite(o.foldShare)) return false;
  const reach = len(sub(pts.bend, pts.root)) + len(sub(pts.end, pts.bend));
  return reach > 1e-6 && len(sub(pts.end, pts.root)) < o.foldShare * reach;
}

/** LIMB_PACE swing: where A (ax -1) or D (+1) take `place` (world m; the end, or the place the keys keep ahead of it) on a
 * folded limb: the limb turned as one piece about its root, about the axis that turns the upper segment (root -> bend)
 * toward bodyRight (unit, world) or away from it, by the angle that moves the end stepM (m), at most the angle that moves
 * the bend point bendMost x stepM, and no further than the upper segment pointing straight along the body's right or
 * left. pts: { root, bend, end } (world m) as the limb is drawn now. null when the rule is off or the upper segment
 * already points that way (nothing to swing). Pure; returns a new [x, y, z]. */
export function limbSwingMove(pts, place, bodyRight, ax, stepM, o = LIMB_PACE) {
  if (!o || o.on === false || o.swing === false || !pts || !place || !ax || !(stepM > 0)) return null;
  const b = sub(pts.bend, pts.root), bl = len(b);
  if (!(bl > 1e-6)) return null;
  const u = [b[0] / bl, b[1] / bl, b[2] / bl], d = bodyRight[0] * u[0] + bodyRight[1] * u[1] + bodyRight[2] * u[2];
  const t = [bodyRight[0] - d * u[0], bodyRight[1] - d * u[1], bodyRight[2] - d * u[2]], tl = len(t);
  if (!(tl > 1e-3)) return null;
  const sg = ax > 0 ? 1 : -1, th = [t[0] / tl, t[1] / tl, t[2] / tl];
  const n = [(u[1] * th[2] - u[2] * th[1]) * sg, (u[2] * th[0] - u[0] * th[2]) * sg, (u[0] * th[1] - u[1] * th[0]) * sg]; // (unit: u and th are)
  const e = sub(pts.end, pts.root), ne = len([n[1] * e[2] - n[2] * e[1], n[2] * e[0] - n[0] * e[2], n[0] * e[1] - n[1] * e[0]]);
  const left = Math.atan2(tl, sg * d); // (the angle still to go before the upper segment points along the right or left)
  const bend = Number.isFinite(o.bendMost) ? (o.bendMost * stepM) / bl : Infinity;
  const ang = Math.min(ne > 1e-6 ? stepM / ne : Infinity, bend, left);
  if (!(ang > 0) || !Number.isFinite(ang)) return null;
  const v = sub(place, pts.root), c = Math.cos(ang), sn = Math.sin(ang), k = (n[0] * v[0] + n[1] * v[1] + n[2] * v[2]) * (1 - c);
  const x = [n[1] * v[2] - n[2] * v[1], n[2] * v[0] - n[0] * v[2], n[0] * v[1] - n[1] * v[0]];
  return [pts.root[0] + v[0] * c + x[0] * sn + n[0] * k, pts.root[1] + v[1] * c + x[1] * sn + n[1] * k, pts.root[2] + v[2] * c + x[2] * sn + n[2] * k];
}
















export const HOLD_LIGHT = Object.freeze({ on: true, minDeg: 0.02, flipDeg: 1 });

/** HOLD_LIGHT: one frame of the held limb's light. prev: the last result or null ({ acc: { jointId: degrees gone the
 * same way since the joint last turned (signed) }, lit: the joint and direction last named, { id, sign } }); d: this
 * frame's change of each joint (degrees). Returns { acc, lit, move (whether the change is a move at all), light (the
 * joint and direction to light this frame, or null; true when the rule is off: the joint that moved most) }. Pure. */
export function holdLightStep(prev, d, o = HOLD_LIGHT) {
  let big = 0;
  for (const v of Object.values(d || {})) if (Number.isFinite(v)) big = Math.max(big, Math.abs(v));
  if (!o || o.on === false) return { acc: {}, lit: null, move: big > 1e-6, light: true };
  const acc0 = prev && prev.acc ? prev.acc : {}, lit0 = prev && prev.lit ? prev.lit : null;
  if (!(big >= o.minDeg)) return { acc: acc0, lit: lit0, move: false, light: null };
  const acc = { ...acc0 };
  for (const [id, v] of Object.entries(d)) {
    if (!Number.isFinite(v) || Math.abs(v) < o.minDeg) continue;
    const a = Number.isFinite(acc[id]) ? acc[id] : 0;
    acc[id] = a !== 0 && Math.sign(a) !== Math.sign(v) ? v : a + v; // (a turn starts a new run)
  }
  const ok = id => Number.isFinite(d[id]) && Math.abs(d[id]) >= o.minDeg && Math.sign(d[id]) === Math.sign(acc[id]) && Math.abs(acc[id]) >= o.flipDeg;
  let light = lit0 && ok(lit0.id) && Math.sign(acc[lit0.id]) === lit0.sign ? lit0 : null;
  if (!light) {
    let best = null;
    for (const id of Object.keys(acc)) if (ok(id) && (best === null || Math.abs(acc[id]) > Math.abs(acc[best]))) best = id;
    light = best === null ? null : { id: best, sign: Math.sign(acc[best]) };
  }
  return { acc, lit: light || lit0, move: true, light };
}

































export const LIMB_BLOCK = Object.freeze({ on: true, deepM: 0.008, tolM: 0.001, ahead: true, aheadSteps: 5 });

/** LIMB_BLOCK ahead: the overlap (m) a move of the chosen limb may reach with another limb it is not blocked by: the
 * overlap now (penNow) or deepM past where they first touched (firstM: slackM when they do not touch yet), whichever is
 * more. Pure. */
export function aheadAllowM(penNow, firstM, o = LIMB_BLOCK) {
  return Math.max(Number.isFinite(penNow) ? penNow : -Infinity, (Number.isFinite(firstM) ? firstM : 0) + o.deepM);
}

/** LIMB_BLOCK ahead: the share (0..1) of a move to take. overAt(s): how far (m) the move's share s goes past what it may
 * reach (> 0: too deep; aheadAllowM against each limb, the worst); overAt(1) is asked first. 1 when the whole move is
 * within (tolM), else the largest share found within by aheadSteps halvings (0: none). Pure (overAt is the caller's). */
export function aheadShare(overAt, o = LIMB_BLOCK) {
  if (!o || o.on === false || o.ahead === false || typeof overAt !== 'function') return 1;
  if (!(overAt(1) > o.tolM)) return 1;
  let lo = 0, hi = 1;
  for (let i = 0; i < (o.aheadSteps || 5); i++) { const m = (lo + hi) / 2; if (overAt(m) > o.tolM) hi = m; else lo = m; }
  return lo;
}

/** The deepest overlap (m) of two limbs' rods (each { root, bend, tip, r: [upper, lower] }, world m): the largest sum
 * of two rods' thicknesses less their distance, over the four pairs of rods (negative: apart by that much). nearest:
 * the rods' nearest points (ns-app rodsNearest). Pure. */
export function limbsOverlapM(A, B, nearest) {
  if (!A || !B || typeof nearest !== 'function') return -Infinity;
  const ra = [[A.root, A.bend, A.r[0]], [A.bend, A.tip, A.r[1]]], rb = [[B.root, B.bend, B.r[0]], [B.bend, B.tip, B.r[1]]];
  let best = -Infinity;
  for (const a of ra) for (const b of rb) { const q = nearest(a[0], a[1], b[0], b[1]); best = Math.max(best, a[2] + b[2] - q.d); }
  return best;
}


















export const LEFT_ARM_BLOCK = Object.freeze({ on: true });

/** LEFT_ARM_BLOCK: the bend point of a two-rod limb whose end is moved to `at` (world m), its root fixed, the two rods'
 * lengths kept (root -> bend, bend -> end as they are now) and the bend on the side of the root -> end line it is on now
 * (the nearest point of the circle it can lie on). pts: { root, bend, end } now. A place beyond the reach is taken at
 * the reach on the same line (the limb straight), one nearer than the fold at the fold. Pure; returns a new [x, y, z]. */
export function twoRodBendAt(pts, at) {
  const r = pts.root, l1 = len(sub(pts.bend, r)), l2 = len(sub(pts.end, pts.bend));
  const v = sub(at, r), dRaw = len(v);
  if (!(dRaw > 1e-9) || !(l1 > 1e-9)) return pts.bend.slice();
  const u = [v[0] / dRaw, v[1] / dRaw, v[2] / dRaw];
  const d = Math.min(l1 + l2 - 1e-9, Math.max(Math.abs(l1 - l2) + 1e-9, dRaw));
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d), hh = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  // (the side: the bend's offset now across the new line; the old line's if that is too small)
  const b = sub(pts.bend, r), bu = b[0] * u[0] + b[1] * u[1] + b[2] * u[2];
  let w = [b[0] - bu * u[0], b[1] - bu * u[1], b[2] - bu * u[2]], wl = len(w);
  if (!(wl > 1e-6)) {
    const e = sub(pts.end, r), el = len(e) || 1, eu = [e[0] / el, e[1] / el, e[2] / el], k = b[0] * eu[0] + b[1] * eu[1] + b[2] * eu[2];
    const w2 = [b[0] - k * eu[0], b[1] - k * eu[1], b[2] - k * eu[2]], wu = w2[0] * u[0] + w2[1] * u[1] + w2[2] * u[2];
    w = [w2[0] - wu * u[0], w2[1] - wu * u[1], w2[2] - wu * u[2]]; wl = len(w);
  }
  if (!(wl > 1e-6)) return [r[0] + u[0] * l1, r[1] + u[1] * l1, r[2] + u[2] * l1];
  return [r[0] + u[0] * a + w[0] / wl * hh, r[1] + u[1] * a + w[1] / wl * hh, r[2] + u[2] * a + w[2] / wl * hh];
}

/** LEFT_ARM_BLOCK: the share (0..1) of the left hand's move from `from` toward `to` (world m) to take, and the place:
 * { share, at }. overAt(p): how far (m) the arm with its hand at p goes past what it may reach (> 0: too deep; the
 * caller's aheadAllowM against each limb, the worst); refuses(p): true when the move to p goes deeper into a limb that
 * blocks the arm (LIMB_BLOCK; optional). A move that refuses waits ({ share 0, at: from }); otherwise aheadShare. Pure
 * (the callbacks are the caller's). */
export function leftArmMoveCut(from, to, overAt, refuses = null, o = LIMB_BLOCK) {
  if (!from || !to) return { share: 1, at: to };
  const at = s => (s === 1 ? to : [from[0] + (to[0] - from[0]) * s, from[1] + (to[1] - from[1]) * s, from[2] + (to[2] - from[2]) * s]);
  if (typeof refuses === 'function' && refuses(to)) return { share: 0, at: from.slice() };
  const share = typeof overAt === 'function' && o && o.ahead !== false ? aheadShare(s => overAt(at(s)), o) : 1;
  return { share, at: share === 1 ? to : at(share) };
}

/** LIMB_BLOCK: whether a pair blocks, from its overlap now (pen) and when they first touched (pen0), both m. Pure. */
export function pushBlocks(pen, pen0, o = LIMB_BLOCK) {
  return Boolean(o && o.on !== false && Number.isFinite(pen) && Number.isFinite(pen0) && pen > pen0 + o.deepM);
}

/** LIMB_BLOCK: whether a blocked chosen limb's move waits: its overlap with the other limb would go from penNow to
 * penNew (m), deeper than now and deeper than `allowM` (the overlap when they first touched plus deepM: down to that a
 * limb that was drawn back out may come in again). Pure. */
export function blockRefuses(penNow, penNew, o = LIMB_BLOCK, allowM = -Infinity) {
  const floor = Math.max(Number.isFinite(penNow) ? penNow : -Infinity, Number.isFinite(allowM) ? allowM : -Infinity);
  return Boolean(o && o.on !== false && Number.isFinite(penNew) && penNew > floor + o.tolM);
}




































export const PUSH_BACK = Object.freeze({ on: true, shareMin: 0.02, restDegS: 90, chosenKept: true });

/** PUSH_BACK: the record of a limb pushed during a movement after one more push. rec: the record so far or null;
 * before / after: the limb's joint PLACES before and after this push (degrees by joint); away: how far the trunk is from
 * rest now (ns-app holdTrunkAway). The places to go back to stay those before the FIRST push (a joint first pushed later
 * gets its own); the way back is measured from this push on. Pure; returns a new record. */
export function pushBackAfter(rec, before, after, away) {
  const to = { ...before, ...(rec && rec.to ? rec.to : {}) };
  return { to, from: { ...after }, last: { ...after }, away0: away, share: 1 };
}

/** PUSH_BACK: one frame of a pushed limb's way back. rec: pushBackAfter's record (or the last step's); input { place: the
 * joints' places now (bodyGoal), moving(id): a movement of that joint or its return is under way, away: the trunk's
 * distance from rest, atRest, dt (s) }. Each joint's place goes from `from` to `to` in step with the share of the trunk's
 * way still to go (it never grows again); a moving joint is left alone; a joint whose place something else changed (the
 * end of its movement, another push) goes on from where it is; near rest and after it, what is left goes at most
 * restDegS. own (r30, chosenKept: the limb is the chosen one): a joint whose place something else changed was moved by
 * the player, and the change is carried into both ends of its way (`to` and `from`): kept, not undone; own may give the
 * player's change itself ({ jointId: degrees }, measured from where the joint WAS: a place set by the player is also
 * where the joint is, so the place's own change would count the joint's lag behind the way back as the player's).
 * ownTo (r31, KEY_SHADOW; with own): { jointId: degrees }, the place such a joint goes back to (the shadow's: the same
 * input played at rest), in place of the carried change; the change still shifts `from`. Returns { rec,
 * joints (places to set now), done (at rest, every joint home, none moving) }. Pure. */
export function pushBackStep(rec, { place = {}, moving = () => false, away = 0, atRest = false, dt = 0, own = false, ownTo = null } = {}, o = PUSH_BACK) {
  const share = atRest ? 0 : Math.max(0, Math.min(rec.share, rec.away0 > 1e-9 ? away / rec.away0 : 0));
  const from = { ...rec.from }, last = { ...(rec.last || {}) }, joints = {};
  let busy = false, left = false, goals = rec.to;
  for (const id of Object.keys(rec.to)) {
    let to = rec.to[id];
    if (!Number.isFinite(to)) continue;
    if (moving(id)) { busy = true; continue; }
    const p = Number.isFinite(place[id]) ? place[id] : to;
    const moved = Number.isFinite(last[id]) && Math.abs(p - last[id]) > 1e-6;
    const ownD = own && typeof own === 'object' && Number.isFinite(own[id]) ? own[id] : null;
    if (own && ownTo && Number.isFinite(ownTo[id]) && o.chosenKept !== false) {
      // (r31, KEY_SHADOW: the place to go back to is the shadow's, where the player's input ends at rest; the player's
      // change of the limb itself is carried into `from` only, so the way back goes on from where the limb now is)
      if (goals === rec.to) goals = { ...rec.to };
      to = goals[id] = ownTo[id] + 0;
      if ((moved || ownD !== null) && Number.isFinite(from[id])) from[id] += ownD !== null ? ownD : p - last[id];
    } else if ((moved || ownD !== null) && own && o.chosenKept !== false) {
      const d = ownD !== null ? ownD : p - last[id];
      if (goals === rec.to) goals = { ...rec.to };
      to = goals[id] = to + d + 0;
      if (Number.isFinite(from[id])) from[id] += d;
    } else if (moved && share > o.shareMin) from[id] = to + (p - to) / share;
    let v;
    if (share > o.shareMin) v = to + ((Number.isFinite(from[id]) ? from[id] : p) - to) * share;
    else { const step = o.restDegS * (dt > 0 ? Math.min(dt, 0.1) : 0); v = Math.abs(to - p) <= step ? to : p + Math.sign(to - p) * step; }
    if (Math.abs(v - p) > 1e-9) joints[id] = v + 0;
    last[id] = v + 0;
    if (Math.abs(v - to) > 1e-6) left = true;
  }
  return { rec: { ...rec, to: goals, from, last, share }, joints, done: atRest && !busy && !left };
}

























/* 23 November 2026, round r32 (LIMBS5; a check of update 69, case T5: keys on a pushed leg, another limb chosen in between,
 * then S on the leg again, ended 7.1 mm off their control). Measured: the other limb is not the cause (W then S on the
 * same leg, 7.1; S alone after the trunk is back, 6.4; S after the way back has ended, 2.2; S during the trunk, 0.0). The
 * pushed leg's way back runs on at rest (its last part at PUSH_BACK restDegS) and S came during it: the shadow took S
 * and the leg came home to the shadow's place, but the keys were still held, and the view's hold went on along the line
 * of the keys it had kept while the leg stood at its pushed pose (h.keyU, h.keyLen: the place kept up to 2 cm ahead of
 * the end), not the shadow's:
 *   lineAtHome  when the chosen limb's way back ends while a key is held, the hold takes over the shadow's line of the
 *               keys (keyShadowLine), so the keys go on as they would have with no trunk movement. (T5 7.1 -> 0.0 mm, S
 *               after the trunk 6.4 -> 0.0.) false: the hold keeps its own line (update 69). */



































export const KEY_SHADOW = Object.freeze({ on: true, waitMm: 40, lineAtHome: true, placeHome: true, homeOnLook: false, replayLast: true, carryKeyed: true, homeMps: 1.2, homeDoneMm: 0.5, homeMaxDt: 0.1 });
/** KEY_SHADOW placeHome (LIMBS5 pass 4): whether the held right arm's place goes home to the shadow `sh`'s end: the keys
 * were played on the shadow (sh.keysPlayed), or with homeOnLook any move of it (sh.everMoved). Pure. */
export function keyShadowHomeDue(sh, o = KEY_SHADOW) {
  return Boolean(o.on && o.placeHome && sh && (sh.keysPlayed === true || (o.homeOnLook && sh.everMoved === true)));
}
/**
 * KEY_SHADOW placeHome: one frame of the held right arm's place going home to its shadow's end. state: { share, awayRef }
 * from the frame before (null: none yet); place, home: the hold's place and the shadow's end (world m); away: the trunk's
 * distance from rest (degrees, ns-app holdTrunkAway); atRest; input: the player's keys or look moved the place (and the
 * shadow) this frame: nothing is cut and the count starts again (share 1, awayRef = away); dt (s). The place's offset from
 * home is cut by share' / share with share' = min(share, away / awayRef) (0 at rest), its move at most homeMps x dt.
 * Returns { at (the place: `place` itself when unchanged), state, done (at rest and within homeDoneMm) }. Pure.
 */
export function keyShadowHomeStep(state, { place, home, away = 0, atRest = false, input = false, dt = 0 } = {}, o = KEY_SHADOW) {
  const a = Number.isFinite(away) ? Math.max(0, away) : 0;
  if (!Array.isArray(place) || !Array.isArray(home)) return { at: place, state: state || { share: 1, awayRef: a }, done: false };
  if (input || !state) return { at: place, state: { share: 1, awayRef: a }, done: false };
  const share = atRest ? 0 : Math.max(0, Math.min(state.share, state.awayRef > 1e-9 ? a / state.awayRef : 0));
  const k = state.share > 1e-9 ? share / state.share : 0;
  const off = sub(place, home), goal = [home[0] + off[0] * k, home[1] + off[1] * k, home[2] + off[2] * k];
  const mv = sub(goal, place), n = len(mv), most = o.homeMps * Math.min(Math.max(Number.isFinite(dt) ? dt : 0, 0), o.homeMaxDt);
  const at = n <= 1e-9 ? place : n > most ? [place[0] + mv[0] * most / n, place[1] + mv[1] * most / n, place[2] + mv[2] * most / n] : goal;
  return { at, state: { share, awayRef: state.awayRef }, done: atRest && len(sub(at, home)) <= o.homeDoneMm / 1000 };
}
/** KEY_SHADOW lineAtHome: the shadow's line of the keys in the world: { keyU (unit), keyLen (m) } from its body-frame
 * keyU (unit) and keyLen (m), with toWorld(mm) -> m (the body's placing in the world); null when it has none. Pure. */
export function keyShadowLine(sh, toWorld) {
  if (!sh || !Array.isArray(sh.keyU) || !(sh.keyLen > 0) || typeof toWorld !== 'function') return null;
  const o = toWorld([0, 0, 0]), e = toWorld(sh.keyU.map(v => v * 1000)), u = sub(e, o), n = len(u);
  return n > 1e-6 ? { keyU: [u[0] / n, u[1] / n, u[2] / n], keyLen: sh.keyLen } : null;
}

const shDot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
/** KEY_SHADOW: a new shadow of `limb` standing at the joint places `q` (degrees by joint: the limb's own; the rest of the
 * body is env.base at each step). Pure. */
export function keyShadowNew(limb, q) {
  return { limb, q: { ...q }, keyU: null, keyLen: 0, lastErr: 0, memo: {}, stuck: null, keyed: false, spinA: null, openA: null, moved: false, place: null, keysPlayed: false };
}
/** KEY_SHADOW: the shadow's points (m, body frame): { root, bend, end }. env: as keyShadowStep. Pure. */
export function keyShadowPoints(sh, env) {
  const sg = env.asDrawn({ ...env.base, ...sh.q });
  return { root: env.limbPoint(env.rig, sg, sh.limb, 'root').map(v => v / 1000), bend: env.limbPoint(env.rig, sg, sh.limb, 'bend').map(v => v / 1000), end: env.limbPoint(env.rig, sg, sh.limb, 'end').map(v => v / 1000) };
}
/**
 * KEY_SHADOW: one frame of the keys (ax: +1 D, -1 A; az: +1 W, -1 S; dt s) on the shadow, as the view's hold plays a
 * frame of the keys on a body limb at rest (ns-app stepLimbHoldCore); a frame with no key ends the keys' line (the place
 * put on the end: LIMB_PACE releaseStops). env: { rig, chain (ns-grasp LIMB_CHAIN[limb]), base (the rest of the body's
 * angles, the trunk at rest), asDrawn(angles) -> segments, limbPoint, solveLimb, limits (holdLimits), project, opts:
 * { follow, track } (the solve's options), keyMove (limbKeyMove), keyFollow (limbKeyFollow), keyCut (keyMoveCut),
 * speedMps, leadM, maxDt, keepOut(angles, p m) -> m inside the trunk (an arm; optional) }. Returns a new shadow
 * (moved: whether this frame moved it). Pure apart from env's functions.
 */
export function keyShadowStep(sh0, ax, az, dt, env) {
  const sh = { ...sh0, q: { ...sh0.q }, moved: false };
  if (!ax && !az) { if (sh.keyed) { sh.keyU = null; sh.keyLen = 0; sh.keyed = false; } return sh; }
  sh.keysPlayed = true; // (LIMBS5 pass 4, KEY_SHADOW homeOnLook false: placeHome is due from now on)
  const limb = sh.limb, c = env.chain, pace = paceFor(limb), right = [-1, 0, 0];
  const full = q => ({ ...env.base, ...q });
  const ptsOf = q => { const sg = env.asDrawn(full(q)); return { sg, root: env.limbPoint(env.rig, sg, limb, 'root').map(v => v / 1000), bend: env.limbPoint(env.rig, sg, limb, 'bend').map(v => v / 1000), end: env.limbPoint(env.rig, sg, limb, 'end').map(v => v / 1000) }; };
  const sp = env.speedMps * Math.min(Math.max(dt, 0), env.maxDt || 0.1), lead = env.leadM;
  const P0 = ptsOf(sh.q), root = P0.root, end = P0.end, pts = { root, bend: P0.bend, end };
  const keepOut = typeof env.keepOut === 'function' ? p => env.keepOut(full(sh.q), p) : null;
  const folded = LIMB_PACE.on && ax !== 0 && az === 0 && limbFolded(pts, pace);
  let joints = null, acrossEnd = false;
  // (LIMB_ACROSS: A on a folded limb with a `spin` joint turns it first, then opens the elbow (open); D undoes the opening,
  // then the turn: acrossStep)
  if (folded && c.spin && LIMB_ACROSS.on) {
    const across = c.side === 'right' ? ax < 0 : ax > 0;
    const way0 = sub(env.keyMove(end, root, right, ax, 0, sp), end);
    const st = acrossStep({ q: sh.q, chain: c, across, way: way0, wayLevel: [right[0] * ax * sp, right[1] * ax * sp, right[2] * ax * sp], endAt: q => ptsOf(q).end, limits: env.limits, spinRec: sh.spinA, openRec: sh.openA });
    if (st && st.phase === 'end') acrossEnd = true;
    else if (st) {
      const id = st.id, v0 = sh.q[id];
      const q = env.project ? env.project(full({ ...sh.q, [id]: v0 + st.d })) : full({ ...sh.q, [id]: v0 + st.d }), js = {};
      for (const j of [...c.joints, c.spin.joint]) js[j] = q[j];
      const P1 = ptsOf({ ...sh.q, ...js }), fol = env.keyFollow(end, P1.end, st.way);
      const ok = fol.take && fol.share > 0.999 && limbPaceShare(pts, { root, bend: P1.bend, end: P1.end }, sp, pace) > 0.999 && Math.abs(js[id] - v0) > 1e-3
        && !(keepOut && keepOut(P1.end) > keepOut(end) + 1e-3);
      if (ok) {
        joints = js;
        const rec = st.back && Math.abs(js[id] - st.from) < 0.05 ? null : { from: st.from, last: js[id] };
        if (st.phase === 'open') sh.openA = rec; else sh.spinA = rec;
      }
    }
  }
  let T = acrossEnd ? end.slice() : null;
  if (!joints && !acrossEnd) {
    const from = sh.keyU ? [root[0] + sh.keyU[0] * sh.keyLen, root[1] + sh.keyU[1] * sh.keyLen, root[2] + sh.keyU[2] * sh.keyLen] : end;
    const swingOf = p => (folded ? limbSwingMove(pts, p, right, ax, sp, pace) : null);
    const classic = p => env.keyMove(p, root, right, ax, az, sp);
    T = swingOf(from) || classic(from);
    if (keepOut && keepOut(T) > keepOut(from) + 5e-4) T = end.slice(); // (an arm's key into the trunk moves nothing: no slide here)
    const gap = len(sub(T, end));
    if (gap > 0.0015) { // (a frame of the keys always solves: the hold's 'stuck' place is for still frames)
      const solve = (t, memo, track) => env.solveLimb({ rig: env.rig, segmentsFor: env.asDrawn, targets: full(sh.q), limb, targetMm: t.map(v => v * 1000), limits: env.limits, opts: track ? env.opts.track : env.opts.follow, project: env.project, memo, spin: Boolean(c.spin) });
      const take = (rs, way) => {
        const paceOf = (eM, bM) => limbPaceShare(pts, { root, bend: bM, end: eM }, sp, pace);
        const e0 = rs.endMm.map(v => v / 1000), fol = env.keyFollow(end, e0, way);
        if (!fol.take) return null;
        let out = { joints: rs.joints, end: e0, bend: rs.bendMm ? rs.bendMm.map(v => v / 1000) : null, folded: rs.folded, errorMm: rs.errorMm };
        const p0 = out.bend ? paceOf(out.end, out.bend) : 1;
        if (fol.share < 1 || p0 < 1) {
          let share = Math.min(fol.share, p0);
          for (let pass = 0; pass < 4; pass++) {
            const q = { ...sh.q }; for (const id of Object.keys(rs.joints)) q[id] = sh.q[id] + (rs.joints[id] - sh.q[id]) * share;
            const qp = env.project ? env.project(full(q)) : full(q), js = {}; for (const id of Object.keys(rs.joints)) js[id] = qp[id];
            const P1 = ptsOf({ ...sh.q, ...js }), kEnd = env.keyCut(sub(P1.end, end), way);
            if (!(kEnd > 0)) return null;
            out = { ...out, joints: js, end: P1.end, bend: P1.bend };
            const k = Math.min(kEnd, paceOf(P1.end, P1.bend));
            if (!(k < 0.999)) break;
            share *= k;
          }
        }
        if (keepOut && keepOut(out.end) > keepOut(end) + 1e-3) return null;
        return out;
      };
      const swEnd = swingOf(end), way = sub(swEnd || classic(end), end);
      let t = take(solve(T, sh.memo, !(sh.lastErr < 12 && gap < 0.06)), way);
      if (!t && swEnd) { // (the swing waits: the turn of the line for this frame)
        const w1 = sub(classic(end), end), wl = len(w1);
        if (wl > 1e-6) t = take(solve([end[0] + w1[0] * lead / wl, end[1] + w1[1] * lead / wl, end[2] + w1[2] * lead / wl], null, true), w1);
      }
      if (t) {
        sh.lastErr = t.errorMm;
        const inner = t.folded === true && t.errorMm > lead * 1000 + 2;
        if (!inner) {
          let big = 0; for (const id of Object.keys(t.joints)) big = Math.max(big, Math.abs(t.joints[id] - sh.q[id]));
          if (big >= HOLD_LIGHT.minDeg) joints = t.joints; else T = end.slice();
        } else T = end.slice();
      } else T = end.slice();
    }
  }
  if (joints) {
    Object.assign(sh.q, joints); sh.moved = true;
    if (sh.spinA && c.spin && Number.isFinite(sh.q[c.spin.joint])) sh.spinA = { ...sh.spinA, last: sh.q[c.spin.joint] };
    if (sh.openA && Number.isFinite(sh.q[c.bend])) sh.openA = { ...sh.openA, last: sh.q[c.bend] };
  }
  // (the keys' place: a direction from the root and a length, neither wound up beyond the end's own: as the hold keeps it)
  const end2 = sh.moved ? ptsOf(sh.q).end : end;
  const tp = T || end2, v = sub(tp, root), len0 = len(v);
  if (len0 > 1e-4) {
    let u = ax === 0 && sh.keyU ? sh.keyU : [v[0] / len0, v[1] / len0, v[2] / len0], L = len0;
    const e = sub(end2, root), en = len(e);
    if (en > 1e-4) {
      const eh = [e[0] / en, e[1] / en, e[2] / en], th = Math.acos(Math.max(-1, Math.min(1, shDot(u, eh)))), most = lead / Math.max(0.05, L);
      if (ax !== 0 && th > most) { const k = most / th, sn = Math.sin(th) || 1, a = Math.sin((1 - k) * th) / sn, b = Math.sin(k * th) / sn; u = [eh[0] * a + u[0] * b, eh[1] * a + u[1] * b, eh[2] * a + u[2] * b]; const un = len(u) || 1; u = [u[0] / un, u[1] / un, u[2] / un]; }
      const o = shDot(e, u); L = Math.max(o - lead, Math.min(o + lead, L));
    }
    sh.keyU = u; sh.keyLen = L;
  }
  sh.keyed = true;
  return sh;
}
/** KEY_SHADOW: the look carried the limb this frame: the shadow's end is solved to `target` (m, body frame; where the
 * same look carries it at rest), from where it stands (env.opts.reach). Taken when the solve ends within waitMm of it;
 * otherwise the shadow waits (a limb carried beyond its reach waits). Returns a new shadow. Pure apart from env's. */
export function keyShadowCarry(sh0, target, env, o = KEY_SHADOW) {
  const sh = { ...sh0, q: { ...sh0.q }, moved: false, keyU: null, keyLen: 0, keyed: false, stuck: null };
  if (!target) return sh;
  const full = q => ({ ...env.base, ...q });
  const r = env.solveLimb({ rig: env.rig, segmentsFor: env.asDrawn, targets: full(sh.q), limb: sh.limb, targetMm: target.map(v => v * 1000), limits: env.limits, opts: env.opts.reach, project: env.project, memo: null });
  if (!(r && r.errorMm <= o.waitMm)) return sh;
  let big = 0; for (const id of Object.keys(r.joints)) big = Math.max(big, Math.abs(r.joints[id] - sh.q[id]));
  if (big >= HOLD_LIGHT.minDeg) { Object.assign(sh.q, r.joints); sh.moved = true; }
  return sh;
}
/**
 * KEY_SHADOW carryKeyed (23 November 2026, round r32, LIMBS5 pass 4): a frame of the keys (ax, az, dt s) on which the
 * look turned too, played on the shadow as the view's hold plays it on a body limb at rest (ns-app holdTarget and
 * stepLimbHoldCore): the place is where the look carries it (`target`, m, body frame), moved from there by the keys
 * (env.keyMove; a key that takes the end deeper into the trunk moves nothing), and solved to as on a frame of the look:
 * no keys' cut, no swing, no turn of the upper arm (the hold asks those only on frames of the keys alone); one solve
 * step while the shadow is following closely, else two. The keys' line starts again from that place (a direction from
 * the root and a length within leadM of the end's own way out), as the hold's does. Returns a new shadow (moved: whether
 * this frame moved it; keysPlayed). Pure apart from env's functions.
 */
export function keyShadowCarryKeys(sh0, target, ax, az, dt, env) {
  const sh = { ...sh0, q: { ...sh0.q }, moved: false, keysPlayed: true, keyed: true, stuck: null };
  if (!target || !(ax || az)) return sh;
  const full = q => ({ ...env.base, ...q });
  const P0 = keyShadowPoints(sh, env), root = P0.root, end = P0.end, lead = env.leadM;
  const sp = env.speedMps * Math.min(Math.max(dt, 0), env.maxDt || 0.1);
  let T = env.keyMove(target, root, [-1, 0, 0], ax, az, sp);
  if (typeof env.keepOut === 'function' && env.keepOut(full(sh.q), T) > env.keepOut(full(sh.q), target) + 5e-4) T = target.slice();
  const gap = len(sub(T, end));
  if (gap > 0.0015) {
    const r = env.solveLimb({ rig: env.rig, segmentsFor: env.asDrawn, targets: full(sh.q), limb: sh.limb, targetMm: T.map(v => v * 1000), limits: env.limits, opts: sh.lastErr < 12 && gap < 0.06 ? env.opts.follow : env.opts.track, project: env.project, memo: sh.memo });
    if (r) {
      sh.lastErr = r.errorMm;
      const inner = r.folded === true && r.errorMm > lead * 1000 + 2;
      let big = 0; for (const id of Object.keys(r.joints)) big = Math.max(big, Math.abs(r.joints[id] - sh.q[id]));
      if (!inner && big >= HOLD_LIGHT.minDeg) { Object.assign(sh.q, r.joints); sh.moved = true; }
    }
  }
  // (the keys' line from the carried place: as the hold keeps it on such a frame)
  const end2 = sh.moved ? keyShadowPoints(sh, env).end : end, v = sub(T, root), len0 = len(v);
  if (len0 > 1e-4) {
    let u = [v[0] / len0, v[1] / len0, v[2] / len0], L = len0;
    const e = sub(end2, root), en = len(e);
    if (en > 1e-4) {
      const eh = [e[0] / en, e[1] / en, e[2] / en], th = Math.acos(Math.max(-1, Math.min(1, shDot(u, eh)))), most = lead / Math.max(0.05, L);
      if (ax !== 0 && th > most) { const k = most / th, sn = Math.sin(th) || 1, a = Math.sin((1 - k) * th) / sn, b = Math.sin(k * th) / sn; u = [eh[0] * a + u[0] * b, eh[1] * a + u[1] * b, eh[2] * a + u[2] * b]; const un = len(u) || 1; u = [u[0] / un, u[1] / un, u[2] / un]; }
      const out = shDot(e, u); L = Math.max(out - lead, Math.min(out + lead, L));
    }
    sh.keyU = u; sh.keyLen = L;
  }
  return sh;
}
























































export const TRUNK_RIDE = Object.freeze({ on: true, speedMps: 1.5, rootShare: 1, catchS: 0.1, maxLagMm: 400, doneMm: 2, snapMm: 300, maxDt: 0.1, reachM: 1.3 });

/** TRUNK_RIDE reachM (LIMBS5 pass 2, the check's cost): the most a trunk movement of stepDeg degrees in one frame (the
 * largest change of any of its angles) can carry a hand (m): reachM, a generous distance from the lowest joint of the spine
 * to the hand, on that arc. A frame whose bound is within the follow's least step (speedMps x dt) cannot leave a caught-up
 * hand behind, so the right arm's follow takes no pose of the body on it (the trunk's slow return). Pure. */
export function rideCarryBoundM(stepDeg, o = TRUNK_RIDE) {
  return Math.abs(Number.isFinite(stepDeg) ? stepDeg : Infinity) * Math.PI / 180 * o.reachM;
}

/** TRUNK_RIDE: one frame of a riding end. prev: where it was drawn last frame, ride: where the trunk and its own movement
 * put it now (m); rootStepM: how far the trunk moved its root (shoulder) this frame; ownStepM: how far its own movement
 * moved it; dt: the frame's time (s). Returns { at (where to draw it), lagM (how far behind it stays), capM (this frame's
 * step), done (no lag left: at is ride) }. Never more than maxLagMm behind, and no snap (catchS > 0). Pure. */
export function rideFollow(prev, ride, { rootStepM = 0, ownStepM = 0, dt = 1 / 60 } = {}, o = TRUNK_RIDE) {
  const t = Math.min(Math.max(Number.isFinite(dt) ? dt : 0, 0), o.maxDt);
  let cap = Math.max(o.speedMps * t, o.rootShare * (Number.isFinite(rootStepM) ? rootStepM : 0) + (Number.isFinite(ownStepM) ? ownStepM : 0));
  if (!Array.isArray(prev) || !prev.every(Number.isFinite)) return { at: ride.slice(), lagM: 0, capM: cap, done: true };
  const d = sub(ride, prev), n = len(d);
  const springs = o.catchS > 0;
  if (springs) cap = Math.max(cap, n * (1 - Math.exp(-t / o.catchS)));
  if (springs && o.maxLagMm > 0 && n - cap > o.maxLagMm / 1000) cap = n - o.maxLagMm / 1000; // (speeds up; never the whole gap at once)
  if (n <= cap || n <= o.doneMm / 1000 || (!springs && n > o.snapMm / 1000)) return { at: ride.slice(), lagM: 0, capM: Math.min(cap, n), done: true };
  const k = cap / n;
  return { at: [prev[0] + d[0] * k, prev[1] + d[1] * k, prev[2] + d[2] * k], lagM: n - cap, capM: cap, done: false };
}
/** TRUNK_RIDE: the trunk's own offsets as a key (the activity's trunk bend, side bend and turn; the look's bend is not
 * among them): the follow runs on a frame on which this key changed, or while an end is behind. Pure. */
export function trunkRideKey(offsets) {
  if (!offsets) return '';
  const v = k => (Number.isFinite(offsets[k]) ? Math.round(offsets[k] * 1000) / 1000 : 0);
  return `${v('trunk_flex')}|${v('trunk_side')}|${v('trunk_rot')}`;
}
/**
 * TRUNK_RIDE: one frame of a body limb riding the trunk (ns-app: the right arm when the view does not hold it), drawn
 * only. rec: the last frame's record { lag, q (the limb's own angles then), at, root (m, world: its end as drawn and its
 * root) }, or null (then env.last() gives the same of the last pose drawn); T: this frame's drawn angles (all joints).
 * env: { rig, limb, ids (the limb's own joints that move its end), segmentsFor(angles) -> segments, limbPoint,
 * toWorld(mm) -> m, toBody(m) -> mm, solveLimb, limits, project, opts (the solve's), memo, dt, last(), ownOff (LIMBS5 pass
 * 2: this frame's change of its own angles is not counted as its own movement: the first frame after the view let it
 * go, whose angles jump from the hold's to the activity's; the check of the first pass: a right arm let go during a bend
 * jumped 58 to 64 mm in that frame) }. The end goes
 * toward where T puts it by rideFollow's step; while it is behind, the limb's solved joints (env.solveLimb, from T) draw
 * it there. Returns { T (the angles to draw: T itself when the end is not behind), rec }. Pure apart from env's.
 */
export function rideLimbStep(rec, T, env, o = TRUNK_RIDE) {
  const q = {}; for (const id of env.ids) if (Number.isFinite(T[id])) q[id] = T[id];
  const P = (sg, w) => env.toWorld(env.limbPoint(env.rig, sg, env.limb, w));
  const segs = env.segmentsFor(T), rideW = P(segs, 'end'), rootW = P(segs, 'root');
  const was = rec || env.last();
  const prevQ = was && was.q ? was.q : q;
  // (its own movement this frame: its own angles changed, the trunk as now)
  const ownMoved = !env.ownOff && env.ids.some(id => Math.abs((Number.isFinite(q[id]) ? q[id] : 0) - (Number.isFinite(prevQ[id]) ? prevQ[id] : 0)) > 1e-6);
  const rootStepM = was && Array.isArray(was.root) ? len(sub(rootW, was.root)) : 0, at0 = was ? was.at : null;
  // (LIMBS5 pass 2, the check's cost: the own movement's pose only when the step without it leaves the end behind)
  let f = rideFollow(at0, rideW, { rootStepM, ownStepM: 0, dt: env.dt }, o);
  if (!f.done && ownMoved) f = rideFollow(at0, rideW, { rootStepM, ownStepM: len(sub(rideW, P(env.segmentsFor({ ...T, ...prevQ }), 'end'))), dt: env.dt }, o);
  if (f.done) return { T, rec: { lag: false, q, at: rideW, root: rootW } };
  // (the solve goes on from the joints it drew last frame, so it has only this frame's step to make, not the whole lag;
  // LIMBS5 pass 2: tried one step instead of two while the last answer ended within 3 to 10 mm of its target, for the
  // check's cost: the drawn steps then went unevenly, 50, 37, 16, 24 mm instead of 40, 38, 26, 24 in a turn; not kept)
  const warm = rec && rec.lag && rec.solved ? rec.solved : null;
  const r = env.solveLimb({ rig: env.rig, segmentsFor: env.segmentsFor, targets: warm ? { ...T, ...warm } : T, limb: env.limb, targetMm: env.toBody(f.at), limits: env.limits, opts: env.opts, project: env.project, memo: env.memo, startSegments: warm ? null : segs });
  if (!r || !Array.isArray(r.endMm)) return { T, rec: { lag: false, q, at: rideW, root: rootW } };
  return { T: { ...T, ...r.joints }, rec: { lag: true, q, at: env.toWorld(r.endMm), root: rootW, solved: { ...r.joints } } };
}
