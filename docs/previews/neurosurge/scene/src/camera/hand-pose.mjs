const digits = [['index', 5], ['middle', 9], ['ring', 13], ['little', 17]];
const palmChains = [[0, 1, 2, 3, 4], ...digits.map(([, start]) => [0, start, start + 1, start + 2, start + 3])];
const leftLimits = [[-10, 90], [0, 105], [0, 75]];
const ends = ['mcp', 'pip', 'dip'];

export const handSelections = Object.freeze({
  leftHand: ['leftHand'], rightHand: ['rightHand'], bothHands: ['leftHand', 'rightHand']
});
export const handTrackingMessages = Object.freeze({
  loading: 'Loading finger tracking on this device.',
  unavailable: 'Finger tracking is unavailable. Choose an arm or leg to keep tracking.'
});
export const leftHandTargets = Object.freeze({
  ...Object.fromEntries(digits.flatMap(([digit]) => ends.map((end, index) => [`${digit}_${end}_flex`, leftLimits[index]]))),
  thumb_mcp_flex: [-10, 55], thumb_ip_flex: [-20, 70]
});
export const rightHandTargets = Object.freeze({
  ...Object.fromEntries(digits.map(([digit]) => [`r_${digit}_flex`, [-30, 90]])),
  r_thumb_flex: [-20, 90], r_grasp: [0, 0], r_open: [0, 0]
});

const isPoint = p => p && [p.x, p.y, p.z].every(Number.isFinite);
const difference = (a, b) => [a.x - b.x, a.y - b.y, a.z - b.z];
const unit = v => {
  const length = Math.hypot(...v);
  return length > 1e-5 ? v.map(x => x / length) : null;
};
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const degrees = angle => angle * 180 / Math.PI;
const bend = (a, b) => degrees(Math.atan2(Math.hypot(...cross(a, b)), dot(a, b)));
const range = (value, [low, high]) => Math.max(low, Math.min(high, value));

// The left rig accepts separate angles. The right rig has one bend value per
// digit, with fixed joint shares in ns-body.mjs. Project onto those shares.
function combinedBend(values, shares) {
  return values.reduce((sum, value, index) => sum + value * shares[index], 0) /
    shares.reduce((sum, share) => sum + share ** 2, 0);
}

function handJoints(points, side) {
  if (!Array.isArray(points) || points.length !== 21 || !points.every(isPoint)) return null;
  const across = unit(difference(points[5], points[17]));
  const ahead = unit(difference(points[9], points[0]));
  if (!across || !ahead) return null;
  const perpendicular = unit(cross(across, ahead));
  if (!perpendicular) return null;
  const palm = side === 'rightHand' ? perpendicular : perpendicular.map(v => -v);
  const left = side === 'leftHand';
  const targets = left ? leftHandTargets : rightHandTargets;
  const joints = left ? {} : {r_grasp: 0, r_open: 0};

  for (const [digit, start] of digits) {
    const links = [0, 1, 2].map(i => unit(difference(points[start + i + 1], points[start + i])));
    if (links.includes(null)) return null;
    const [base, middle, tip] = links;
    const angles = [degrees(Math.asin(range(dot(base, palm), [-1, 1]))), bend(base, middle), bend(middle, tip)];
    if (left) {
      for (const [index, end] of ends.entries()) {
        const id = `${digit}_${end}_flex`;
        joints[id] = range(angles[index], targets[id]);
      }
    } else {
      const id = `r_${digit}_flex`;
      joints[id] = range(combinedBend(angles, [1, 1.16, .95]), targets[id]);
    }
  }
  const thumb = [1, 2, 3].map(i => unit(difference(points[i + 1], points[i])));
  if (thumb.includes(null)) return null;
  const thumbAngles = [bend(thumb[0], thumb[1]), bend(thumb[1], thumb[2])];
  if (left) {
    joints.thumb_mcp_flex = range(thumbAngles[0], targets.thumb_mcp_flex);
    joints.thumb_ip_flex = range(thumbAngles[1], targets.thumb_ip_flex);
  } else {
    joints.r_thumb_flex = range(combinedBend(thumbAngles, [.56, .9]), targets.r_thumb_flex);
  }
  return joints;
}

export function followHands(result, selection) {
  if (!Object.hasOwn(handSelections, selection)) return {pose: null, paths: null};
  const side = label => label === 'Left' ? 'leftHand' : label === 'Right' ? 'rightHand' : null;
  const candidates = (result.handedness ?? result.handednesses ?? []).map((items, index) => ({
    part: side(items[0]?.categoryName), confidence: items[0]?.score, index
  }));
  const pose = {}, paths = {};
  for (const part of handSelections[selection]) {
    // Withhold ambiguous images. A second estimate of that side can come from
    // another person, and the application cannot safely choose between them.
    const matching = candidates.filter(row => row.part === part);
    if (matching.length !== 1 || !(matching[0].confidence >= .85)) continue;
    const index = matching[0].index;
    const image = result.landmarks?.[index];
    if (!Array.isArray(image) || image.length !== 21 ||
        !image.every(p => isPoint(p) && p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1)) continue;
    const joints = handJoints(result.worldLandmarks?.[index], part);
    if (!joints) continue;
    if (part === 'leftHand') pose.leftHand = joints;
    else pose.joints = joints;
    paths[part] = palmChains.map(chain => chain.map(i => [image[i].x, image[i].y]));
  }
  return Object.keys(paths).length ? {pose, paths} : {pose: null, paths: null};
}
