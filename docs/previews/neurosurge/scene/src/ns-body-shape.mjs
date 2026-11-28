































































export const BODY_SHAPE = Object.freeze({
  limbs: Object.freeze({
    on: true,
    ease: 0.25,
    arm: Object.freeze({ upper: 1.22, fore: 1.15, end: 1.08, upperZone: Object.freeze([0.16, 0.85]), foreZone: Object.freeze([0.16, 0.86]), endFromMm: 12, band: 60, reachMm: Object.freeze([70, 110]) }),
    leg: Object.freeze({ upper: 1.1, fore: 1.15, end: 1.08, upperZone: Object.freeze([0.17, 0.84]), foreZone: Object.freeze([0.14, 0.86]), endFromMm: 20, footBelowMm: Object.freeze([-22, 18]), band: 24, reachMm: Object.freeze([110, 160]) })
  }),
  trunk: Object.freeze({
    on: true,
    backYMm: -70, onsetMm: 40,
    chest: Object.freeze({ share: 0.4, zMm: Object.freeze([1372, 1322, 1220, 1070]), xMm: Object.freeze([70, 190]) }),
    belly: Object.freeze({ share: 0.2, zMm: Object.freeze([1150, 1010, 930, 845]), xMm: Object.freeze([80, 170]) })
  }),
  basis: "display choice: smooth rules on the source model, not a measured body"
});

const sstep = t => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
// (square roots only, no Math.hypot: the page and the tools must get the same numbers to the last bit, ns-body
// shapeBody's entry metadata goes into the rig file the page checks itself against)
const len = a => Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
const unit = a => { const l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

/** The share (0..1) of a zone's gain reached at fraction f of the segment, for a zone [a, b] whose stretch eases in
 * over e (a share of the zone) and out over e: a smooth ramp, 0 before a, 1 after b, its slope constant in the middle
 * and smooth at both ends (a C1 curve). Pure. */
export function shapeRamp(f, [a, b], e = BODY_SHAPE.limbs.ease) {
  if (!(f > a)) return 0;
  if (!(f < b)) return 1;
  const w = b - a, E = Math.min(0.5, Math.max(1e-6, e)) * w, peak = 1 / (w - E); // slope in the middle
  if (f < a + E) { const u = f - a; return 0.5 * peak * u * u / E; }
  if (f > b - E) { const u = b - f; return 1 - 0.5 * peak * u * u / E; }
  return peak * (f - a - E / 2);
}
/** Like shapeRamp but without an end: 0 before a, easing in over e mm, then rising 1 per mm. */
const openRamp = (t, a, e) => (t <= a ? 0 : t < a + e ? 0.5 * (t - a) * (t - a) / e : t - a - e / 2);

/** The lengthening of one limb (pure). kind 'arm' | 'leg', pts [P0, P1, P2, P3] (source mm). Returns
 * { at(x, y, z, out) -> writes the displacement (mm) into out[0..2], reach(x, y, z) -> 0..1 (the loading picture's
 * weight by distance from the axes), axes, lengths: { before: [upper, fore], after: [...] } }. */
export function limbLengthField(kind, pts, rule = BODY_SHAPE.limbs) {
  const S = rule[kind], arm = kind === 'arm', [P0, P1, P2, P3] = pts;
  const d1 = sub(P1, P0), d2 = sub(P2, P1), L1 = len(d1), L2 = len(d2), u1 = unit(d1), u2 = unit(d2);
  const E1 = (S.upper - 1) * L1, E2 = (S.fore - 1) * L2, e = rule.ease;
  // the hand's line (wrist -> the middle finger's knuckle) or the foot's (the level line from the ankle to the ball)
  const u3 = arm ? unit(sub(P3, P2)) : unit([P3[0] - P2[0], P3[1] - P2[1], 0]);
  const k3 = S.end - 1, from3 = S.endFromMm, ease3 = 25;
  function at(x, y, z, out) {
    const q1 = (x - P0[0]) * u1[0] + (y - P0[1]) * u1[1] + (z - P0[2]) * u1[2];
    const q2 = (x - P1[0]) * u2[0] + (y - P1[1]) * u2[1] + (z - P1[2]) * u2[2];
    const g1 = E1 * shapeRamp(q1 / L1, S.upperZone, e), g2 = E2 * shapeRamp(q2 / L2, S.foreZone, e);
    let g3 = 0;
    if (k3 !== 0) {
      const q3 = (x - P2[0]) * u3[0] + (y - P2[1]) * u3[1] + (z - P2[2]) * u3[2];
      g3 = k3 * openRamp(q3, from3, ease3);
      // past the shin's own end only (the hand: beyond the forearm's zone; the foot: below the ankle)
      if (g3 !== 0) g3 *= arm ? sstep((q2 / L2 - S.foreZone[1]) / (1 - S.foreZone[1])) : 1 - sstep((z - P2[2] - S.footBelowMm[0]) / (S.footBelowMm[1] - S.footBelowMm[0]));
    }
    out[0] = g1 * u1[0] + g2 * u2[0] + g3 * u3[0];
    out[1] = g1 * u1[1] + g2 * u2[1] + g3 * u3[1];
    out[2] = g1 * u1[2] + g2 * u2[2] + g3 * u3[2];
    return out;
  }
  // distance from the axes: the two long segments and the hand / foot line carried on past P3 (fingers, toes)
  const segD = (x, y, z, A, u, L, open) => {
    const t = (x - A[0]) * u[0] + (y - A[1]) * u[1] + (z - A[2]) * u[2], c = Math.max(0, open ? t : Math.min(L, t));
    const dx = x - A[0] - c * u[0], dy = y - A[1] - c * u[1], dz = z - A[2] - c * u[2];
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  };
  const L3 = len(sub(P3, P2));
  function reach(x, y, z) {
    const r = Math.min(segD(x, y, z, P0, u1, L1, false), segD(x, y, z, P1, u2, L2, false), segD(x, y, z, P2, u3, L3, true));
    return 1 - sstep((r - S.reachMm[0]) / (S.reachMm[1] - S.reachMm[0]));
  }
  return { at, reach, axes: { u1, u2, u3, L1, L2 }, lengths: { before: [L1, L2], after: [L1 + E1, L2 + E2] } };
}

/** The trunk rule (pure): at(x, y, z) -> the move along y (mm; positive = toward the back). */
export function trunkShapeField(rule = BODY_SHAPE.trunk) {
  const ys = rule.backYMm, U = rule.onsetMm, C = rule.chest, B = rule.belly;
  const wz = (z, [z0, z1, z2, z3]) => (z >= z0 ? 0 : z > z1 ? sstep((z0 - z) / (z0 - z1)) : z >= z2 ? 1 : z > z3 ? sstep((z - z3) / (z2 - z3)) : 0);
  const wx = (x, [x0, x1]) => 1 - sstep((Math.abs(x) - x0) / (x1 - x0));
  const depth = u => (u <= 0 ? 0 : u < U ? u * u / (2 * U) : u - U / 2);
  function at(x, y, z) {
    const h = depth(ys - y);
    if (!(h > 0)) return 0;
    const c = C.share * wz(z, C.zMm) * wx(x, C.xMm) - B.share * wz(z, B.zMm) * wx(x, B.xMm);
    return c * h;
  }
  // the box outside which nothing moves (the line in front of the spine, the heights and the sides of both parts)
  const zHi = Math.max(C.zMm[0], B.zMm[0]), zLo = Math.min(C.zMm[3], B.zMm[3]), xHi = Math.max(C.xMm[1], B.xMm[1]);
  /** Whether a mesh with bounds { min, max } can be moved at all (false: it lies wholly outside the rule's box). */
  // (with 10 mm to spare: a mesh's recorded bounds may be a few millimetres out after the earlier reshaping steps)
  const reaches = b => !(b && b.min && b.max) || (b.min[1] < ys + 10 && b.max[2] > zLo - 10 && b.min[2] < zHi + 10 && b.min[0] < xHi + 10 && b.max[0] > -xHi - 10);
  /** positions (xyz) -> a new Float32Array (or into `out`) moved by the rule; returns { q, maxMm }. `bounds` ({ min, max },
   * optional): a mesh wholly outside the rule's box is handed back as it is ({ q: p, maxMm: 0 }) without a pass. */
  function apply(p, out = null, bounds = null) {
    if (bounds && !reaches(bounds)) return { q: p, maxMm: 0 };
    if (!out) out = new Float32Array(p.length);
    let maxMm = 0;
    for (let i = 0; i + 2 < p.length; i += 3) {
      const d = at(p[i], p[i + 1], p[i + 2]);
      out[i] = p[i]; out[i + 1] = p[i + 1] + d; out[i + 2] = p[i + 2];
      if (Math.abs(d) > maxMm) maxMm = Math.abs(d);
    }
    return { q: out, maxMm };
  }
  /** The source y of a moved point (the rule undone): the y whose move lands on `y` at this x, z. The move changes y
   * by at most chest.share of the change in depth, so the step below closes in on it. */
  function sourceY(x, y, z) {
    let q = y;
    for (let k = 0; k < 40; k++) { const next = y - at(x, q, z); if (Math.abs(next - q) < 1e-6) return next; q = next; }
    return q;
  }
  return { at, apply, sourceY, reaches };
}
