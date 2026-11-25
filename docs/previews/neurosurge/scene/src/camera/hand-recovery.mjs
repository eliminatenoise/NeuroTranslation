import { followHands, handSelections } from './hand-pose.mjs';

const anchors = {
  leftHand: {wrist: 15, elbow: 13, other: 16},
  rightHand: {wrist: 16, elbow: 14, other: 15}
};
const cropPixels = 224;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function visiblePoint(point, width, height) {
  if (!point || !(point.visibility >= .65) || !(point.x >= 0 && point.x <= 1) || !(point.y >= 0 && point.y <= 1)) return null;
  return [point.x * width, point.y * height];
}

function cropAtWrist(frame, points, part) {
  const {wrist, elbow, other} = anchors[part];
  const {width, height} = frame;
  const hand = visiblePoint(points[wrist], width, height);
  const forearm = visiblePoint(points[elbow], width, height);
  if (!hand || !forearm) return null;
  const dx = hand[0] - forearm[0];
  const dy = hand[1] - forearm[1];
  const reach = Math.hypot(dx, dy);
  if (reach < 12) return null;
  const size = Math.min(width, height, 170, Math.max(48, 1.8 * reach));
  return {left: clamp(hand[0] + .35 * dx - size / 2, 0, width - size),
    top: clamp(hand[1] + .35 * dy - size / 2, 0, height - size), size, hand,
    other: visiblePoint(points[other], width, height), tolerance: Math.max(6, .28 * reach)};
}

export function createHandRecovery(load) {
  let crop, paint, context, detector, starting;
  let disabled = false;

  function disable() {
    disabled = true;
    const old = detector;
    detector = null;
    try { old?.close(); } catch { /* The lost context may already be invalid. */ }
  }

  async function start() {
    const target = new OffscreenCanvas(cropPixels, cropPixels);
    target.addEventListener('webglcontextlost', disable, {once: true});
    detector = await load(target);
    context = target.getContext('webgl2');
    if (disabled || !context || context.isContextLost()) disable();
  }

  function recover(frame, points, armPose, selection, direct) {
    if (disabled || !points || !armPose) return direct;
    const regions = [];
    for (const part of handSelections[selection]) {
      const visibleArm = part === 'leftHand' ? armPose.leftArm : Number.isFinite(armPose.joints?.r_elbow_flex);
      if (direct.paths?.[part] || !visibleArm) continue;
      const region = cropAtWrist(frame, points, part);
      if (region) regions.push({region, part});
    }
    if (!regions.length) return direct;

    starting ??= Promise.resolve().then(start).catch(disable);
    if (!detector) return direct;

    let current = direct;
    try {
      crop ??= new OffscreenCanvas(cropPixels, cropPixels);
      paint ??= crop.getContext('2d');
      for (const {region, part} of regions) {
        const {left, top, size, hand, other, tolerance} = region;
        paint.drawImage(frame, left, top, size, size, 0, 0, cropPixels, cropPixels);
        const found = followHands(detector.detect(crop), part);
        if (!found.pose) continue;
        const absolute = ([x, y]) => [left + x * size, top + y * size];
        const [x, y] = absolute(found.paths[part][0][0]);
        const distance = Math.hypot(x - hand[0], y - hand[1]);
        // Crossing wrists can make a valid hand appear in the opposite crop.
        if (distance > tolerance || (other && distance + 6 >= Math.hypot(x - other[0], y - other[1]))) continue;
        const path = found.paths[part].map(chain => chain.map(point => {
          const [x, y] = absolute(point);
          return [x / frame.width, y / frame.height];
        }));
        current = {pose: {...current.pose, ...found.pose}, paths: {...current.paths, [part]: path}};
      }
      if (!context.isContextLost()) return current;
    } catch { /* Keep the direct detections if the optional tracker fails. */ }
    disable();
    return direct;
  }

  return {get available() { return !disabled && (!starting || Boolean(detector)); }, recover};
}
