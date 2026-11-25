import {followHands, handSelections} from './hand-pose.mjs';

const maxAgeMs = 200.001;
const otherSide = {leftHand: 'rightHand', rightHand: 'leftHand'};

function closeTo([x, y], [u, v], distance) { return Math.hypot(x - u, y - v) <= distance; }
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

function record(path, timestamp, width, height) {
  const points = path.flat().map(([x, y]) => [x * width, y * height]);
  const x = points.map(p => p[0]), y = points.map(p => p[1]);
  const left = Math.min(...x), right = Math.max(...x), top = Math.min(...y), bottom = Math.max(...y);
  return {wrist: points[0], center: [(left + right) / 2, (top + bottom) / 2],
    span: Math.max(right - left, bottom - top), timestamp};
}

function target(history, now, width, height) {
  const [past, last] = history;
  if (!last || now - last.timestamp > maxAgeMs || now <= last.timestamp) return null;
  let shift = [0, 0];
  if (past && last.timestamp > past.timestamp && now - past.timestamp <= maxAgeMs) {
    const travel = last.wrist.map((xy, i) => (xy - past.wrist[i]) * (now - last.timestamp) / (last.timestamp - past.timestamp));
    const fraction = Math.min(1, Math.max(6, .6 * last.span) / (Math.hypot(...travel) || 1));
    shift = travel.map(value => value * fraction);
  }
  const wrist = last.wrist.map((value, i) => value + shift[i]);
  if (wrist[0] < 0 || wrist[0] >= width || wrist[1] < 0 || wrist[1] >= height) return null;
  const side = Math.min(width, height, 170, Math.max(48, 2.2 * last.span));
  const left = clamp(last.center[0] + shift[0] - side / 2, 0, width - side);
  const top = clamp(last.center[1] + shift[1] - side / 2, 0, height - side);
  return {wrist, side, left, top, tolerance: Math.max(10, .4 * last.span)};
}

export function createHandHistory(load) {
  let history = {};
  let frameKey, end, detector, context, starting, scratch, paint;
  let unavailable = false;

  function clear() { history = {}; end = undefined; }

  function disable() {
    unavailable = true;
    const original = detector;
    detector = null;
    try { original?.close(); } catch { /* Optional context already lost. */ }
  }

  async function start() {
    const canvas = new OffscreenCanvas(224, 224);
    canvas.addEventListener('webglcontextlost', disable, {once: true});
    detector = await load(canvas);
    context = canvas.getContext('webgl2');
    if (unavailable || !context || context.isContextLost()) disable();
  }

  function keep(current, frame, limb, selection, timestamp) {
    if (!Number.isFinite(timestamp)) { clear(); return current; }
    const key = `${frame.width}/${frame.height}/${limb}/${selection}`;
    if (key !== frameKey || (end !== undefined && timestamp <= end)) clear();
    frameKey = key;
    end = timestamp;
    const {width, height} = frame;
    for (const [side, path] of Object.entries(current.paths ?? {})) {
      const last = history[side]?.[1];
      history[side] = [last, record(path, timestamp, width, height)];
    }
    if (!unavailable && Object.keys(current.paths ?? {}).length) starting ??= Promise.resolve().then(start).catch(disable);
    const wanted = handSelections[limb].filter(side => !current.paths?.[side]);
    const candidates = Object.fromEntries(wanted.map(side => [side, target(history[side] ?? [], timestamp, width, height)]));
    const eligible = Object.entries(candidates).filter(([, value]) => value);
    if (unavailable || !detector || !eligible.length) return current;

    const recovered = {};
    try {
      scratch ??= new OffscreenCanvas(224, 224);
      paint ??= scratch.getContext('2d');
      for (const [hand, {wrist, side, left, top, tolerance}] of eligible) {
        paint.drawImage(frame, left, top, side, side, 0, 0, 224, 224);
        const observation = followHands(detector.detect(scratch), hand);
        if (!observation.paths?.[hand]) continue;
        const absolute = ([x, y]) => [left + x * side, top + y * side];
        const path = observation.paths[hand];
        const best = absolute(path[0][0]);
        if (!closeTo(wrist, best, tolerance)) continue;
        const oppositeSample = current.paths?.[otherSide[hand]]?.[0][0];
        const other = oppositeSample ? [oppositeSample[0] * width, oppositeSample[1] * height] : candidates[otherSide[hand]]?.wrist;
        if (other && Math.hypot(best[0] - other[0], best[1] - other[1]) <= Math.hypot(best[0] - wrist[0], best[1] - wrist[1]) + 6) continue;
        recovered[hand] = {wrist: best, pose: observation.pose, path: path.map(chain => chain.map(point => {
          const [x, y] = absolute(point);
          return [x / width, y / height];
        }))};
      }
      if (context.isContextLost()) { disable(); return current; }
    } catch { disable(); return current; }
    if (recovered.leftHand && recovered.rightHand && closeTo(recovered.leftHand.wrist, recovered.rightHand.wrist, 12)) return current;
    let result = current;
    for (const [side, value] of Object.entries(recovered)) {
      result = {pose: {...result.pose, ...value.pose}, paths: {...result.paths, [side]: value.path}};
    }
    return result;
  }

  return {keep};
}
