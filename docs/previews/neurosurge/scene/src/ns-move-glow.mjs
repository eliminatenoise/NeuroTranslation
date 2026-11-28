













/** Display choices.
 *  max          the level a fast movement reaches (0..1).
 *  softDegS     joint speed (degrees per second) at which a channel reaches about 63 % of max
 *               (level = max * (1 - exp(-speed / softDegS)): a slow movement still shows, a fast one does not saturate early).
 *  lookSoftDegS the same for the left shoulder following the look (the look turns faster than a held limb moves).
 *  risePerS     how fast a level rises toward its target (per second): about 0.07 s to full.
 *  fallPerS     how fast it falls when the joint is still (per second): gone in about 0.4 s.
 *  min          levels at or below this are not drawn.
 */
export const MOVE_GLOW = Object.freeze({ max: 0.9, softDegS: 35, lookSoftDegS: 45, risePerS: 14, fallPerS: 2.2, min: 0.03 });

/** The level a joint moving at speedDegS (any sign) heads for. */
export function moveTargetLevel(speedDegS, softDegS = MOVE_GLOW.softDegS, o = MOVE_GLOW) {
  if (!Number.isFinite(speedDegS) || !(softDegS > 0)) return 0;
  return o.max * (1 - Math.exp(-Math.abs(speedDegS) / softDegS));
}

/**
 * The channels of one game: feed(key, speedDegS, row, softDegS?) once per moving joint per frame (the strongest feed of
 * a frame counts; `row` is kept from the first feed of that key), then step(dtSeconds) once per frame. A channel that
 * was not fed this frame heads for 0 and is dropped when it gets there. each(fn) calls fn(key, level, row) for every
 * channel above o.min. No per-frame objects: three Maps, changed in place.
 */
export function createMoveChannels(o = MOVE_GLOW) {
  const level = new Map(), target = new Map(), rows = new Map();
  return {
    feed(key, speedDegS, row, softDegS = o.softDegS) {
      const t = moveTargetLevel(speedDegS, softDegS, o);
      if (!(t > (target.get(key) || 0))) return;
      target.set(key, t);
      if (!rows.has(key)) rows.set(key, row);
    },
    step(dt) {
      const h = dt > 0 ? Math.min(dt, 0.1) : 0;
      for (const [key, lv] of level) {
        const t = target.get(key) || 0;
        const next = t > lv ? Math.min(t, lv + o.risePerS * h) : Math.max(t, lv - o.fallPerS * h);
        if (next > 0) level.set(key, next); else level.delete(key);
      }
      for (const [key, t] of target) if (!level.has(key)) { const first = Math.min(t, o.risePerS * h); if (first > 0) level.set(key, first); }
      target.clear();
    },
    each(fn) { for (const [key, lv] of level) if (lv > o.min) fn(key, lv, rows.get(key)); },
    row: key => rows.get(key),
    hasRow: key => rows.has(key),
    setRow(key, row) { rows.set(key, row); },
    levelOf: key => level.get(key) || 0,
    get size() { return level.size; },
    clear() { level.clear(); target.clear(); }
  };
}
