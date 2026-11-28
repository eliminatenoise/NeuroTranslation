'use strict';
{
const HISTORY_FRAMES = 101;
const FINGERS = 4;
const LEAD = 8;
const TEMPLATE_FRAMES = 10;
const MIN_DELAY = 8;
const MAX_DELAY = 75;
const FIRST_COMPLETED = HISTORY_FRAMES - 1 - 16;
const LAST_COMPLETED = HISTORY_FRAMES - 1 - 8;
const COMPLETED_COUNT = LAST_COMPLETED - FIRST_COMPLETED + 1;

function columnsFromHistory(history) {
  if (!Array.isArray(history) || history.length !== HISTORY_FRAMES) {
    throw new TypeError('Expected 101 consecutive angle frames.');
  }
  const columns = Array.from({ length: FINGERS }, () => []);
  for (let frame = 0; frame < HISTORY_FRAMES; frame += 1) {
    const row = history[frame];
    if (!Array.isArray(row) || row.length !== FINGERS) {
      throw new TypeError('Each angle frame must contain four numbers.');
    }
    for (let finger = 0; finger < FINGERS; finger += 1) {
      const angle = row[finger];
      if (!Number.isFinite(angle)) {
        throw new TypeError('Every angle must be a finite number in degrees.');
      }
      columns[finger].push(angle);
    }
  }
  return columns;
}

function match(angles, issue) {
  let best = Infinity;
  let chosen = MIN_DELAY;
  const first = issue - TEMPLATE_FRAMES + 1;
  for (let delay = MIN_DELAY; delay <= MAX_DELAY; delay += 1) {
    let levelError = 0;
    let differenceError = 0;
    for (let frame = first; frame <= issue; frame += 1) {
      const previous = frame - delay;
      const level = angles[frame] - angles[previous];
      levelError += level * level;
      if (frame > first) {
        const currentDifference = angles[frame] - angles[frame - 1];
        const earlierDifference = angles[previous] - angles[previous - 1];
        const error = currentDifference - earlierDifference;
        differenceError += error * error;
      }
    }
    const cost = levelError / TEMPLATE_FRAMES + 0.5 * (differenceError / (TEMPLATE_FRAMES - 1));
    if (cost < best) {
      best = cost;
      chosen = delay;
    }
  }
  return chosen;
}

function recentReplayWins(angles) {
  let replayError = 0;
  let holdError = 0;
  for (let issue = FIRST_COMPLETED; issue <= LAST_COMPLETED; issue += 1) {
    const delay = match(angles, issue);
    const observedChange = angles[issue + LEAD] - angles[issue];
    const replayChange = angles[issue - delay + LEAD] - angles[issue];
    replayError += Math.abs(replayChange - observedChange);
    holdError += Math.abs(observedChange);
  }
  return replayError / COMPLETED_COUNT < holdError / COMPLETED_COUNT;
}

/** Forecast four absolute angles eight frames after the latest 25 Hz sample. */
function forecastFromHistory(history) {
  const columns = columnsFromHistory(history);
  const issue = HISTORY_FRAMES - 1;
  const result = { hold: [], replay: [], adaptive: [], delayFrames: [], usesReplay: [] };
  for (const angles of columns) {
    // Keep squared differences finite if an input is far outside degree-scale data.
    // This positive power-of-two rescaling is only for comparison arithmetic.
    const comparison = angles.some(angle => Math.abs(angle) > 1e150)
      ? angles.map(angle => angle * 2 ** -600)
      : angles;
    const delay = match(comparison, issue);
    const usesReplay = recentReplayWins(comparison);
    const hold = angles[issue];
    const replay = angles[issue - delay + LEAD];
    result.hold.push(hold);
    result.replay.push(replay);
    result.adaptive.push(usesReplay ? replay : hold);
    result.delayFrames.push(delay);
    result.usesReplay.push(usesReplay);
  }
  return result;
}

globalThis.FingerGestureReplay = Object.freeze({forecastFromHistory});
}
