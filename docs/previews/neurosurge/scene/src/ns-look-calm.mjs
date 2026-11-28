// NeuroSurge: calm light while walking the strip with a held arrow key, and the keyboard focus ring only for keyboard
// players (22 November 2026, package LOOK2, DESIGN-DECISIONS section 198). Pure rules (no three.js, no DOM) plus one
// small DOM binder that only sets a data attribute.
//

// rise, hold and fade, slowly; no blinking, no flicker.

const freeze = Object.freeze;

/** Holding a navigation arrow suppresses repeated gaze flashes. */
// (22 November 2026, second pass: keepMs 450 -> 600, with the controls' gate at 270 ms a held step comes about every
// 300 ms, and every held repeat now counts, also one the app's full queue drops while the steps wait)
export const AREA_WALK_QUIET = freeze({ on: true, keepMs: 600 });

/**
 * One frame of AREA_WALK_QUIET (pure). prev: null, or { from, lastMs } (a held walk is under way; from: the activity's
 * gaze area when it began, or null). heldStep: an area key's auto-repeat (the key is held) reached the game this
 * frame; released: an area key came up this frame; pending: a held step still waits to be done (the view was still
 * changing); blocked: this frame's gaze is silent for another reason (a carry, a held limb, a seed: the arrival would
 * be lost, so the walk waits); nowMs: the frame's clock; gazeArea: the activity's gaze area as the frame begins.
 * Returns { keep (the next prev), silent (record this frame's gaze silently), arrivedFrom (undefined, or the area to
 * tell this frame's gaze event: the stop block is then an arrival when it is not the one the walk began on) }.
 */
export function walkQuietStep(prev, { heldStep = false, released = false, pending = false, blocked = false, nowMs = 0, gazeArea = null } = {}, o = AREA_WALK_QUIET) {
  const none = { keep: null, silent: false, arrivedFrom: undefined };
  if (!o || o.on !== true) return none;
  const now = Number.isFinite(nowMs) ? nowMs : 0;
  if (heldStep) return { keep: { from: prev ? prev.from : (typeof gazeArea === 'string' ? gazeArea : null), lastMs: now }, silent: true, arrivedFrom: undefined };
  if (!prev) return none;
  const keepMs = Number.isFinite(o.keepMs) && o.keepMs > 0 ? o.keepMs : 450;
  const stale = !(now - prev.lastMs <= keepMs);
  if ((released || stale) && !pending && !blocked) return { keep: null, silent: false, arrivedFrom: typeof prev.from === 'string' ? prev.from : null };
  return { keep: prev, silent: true, arrivedFrom: undefined };
}

/**
 * One event of the controls' UI queue for the walk (pure): { push (queue the step: an area key's request while the
 * queue holds fewer than `limit`), held (an auto-repeat of a held area key: it keeps the walk quiet whether or not the
 * queue takes it), released (a held area key came up) }. queued: the requests waiting now.
 */
export function walkUiEvent(ev, queued = 0, limit = 2) {
  const area = Boolean(ev && ev.type === 'area' && (ev.dir === 1 || ev.dir === -1));
  return { push: area && queued < limit, held: area && ev.held === true, released: Boolean(ev && ev.type === 'areaUp') };
}

/** Show the canvas focus indicator during keyboard interaction. */
export const FOCUS_RING = freeze({ on: true, attr: 'data-ns-input', movePx: 4 });

/** The input that decides the canvas's focus ring after an event (pure): 'pointer' after a pointer press, 'keys' after
 * a Tab key press, otherwise `prev` (null before any). type: the DOM event type; key: KeyboardEvent.key. */
export function focusRingInput(prev, type, key = null) {
  // (25 November 2026, DESIGN-DECISIONS section 217: and a pointer that MOVES. Since the pointer is the aim (206) a mouse
  // player may play for minutes without a press, and the frame stood round the picture all that time. 'pointermoved' is
  // bindFocusRing's own event name for a pointer that has really moved, FOCUS_RING.movePx from where it was first seen:
  // a still mouse under a keyboard player's window does not count.)
  if (type === 'pointerdown' || type === 'mousedown' || type === 'touchstart' || type === 'pointermoved') return 'pointer';
  if (type === 'keydown' && key === 'Tab') return 'keys';
  return prev === 'pointer' || prev === 'keys' ? prev : null;
}

/** Keep FOCUS_RING's data attribute on doc.documentElement up to date (capture listeners on the window: a pointer
 * press anywhere on the page, a Tab key). Returns a function that removes the listeners. Never throws. */
export function bindFocusRing(win, o = FOCUS_RING) {
  if (!o || o.on !== true || !win || !win.document || typeof win.addEventListener !== 'function') return () => {};
  const root = win.document.documentElement;
  let cur = null;
  const on = e => {
    const next = focusRingInput(cur, e && e.type, e && e.key);
    if (next === cur) return;
    cur = next;
    try { if (next) root.setAttribute(o.attr, next); else root.removeAttribute(o.attr); } catch { /* a ring is a convenience */ }
  };
  const types = ['pointerdown', 'mousedown', 'touchstart', 'keydown'];
  for (const t of types) win.addEventListener(t, on, { capture: true, passive: true });
  // a pointer that really moves (see focusRingInput); nothing is done while the pointer already decides
  let seenAt = null;
  const moved = e => {
    if (cur === 'pointer' || !e || !Number.isFinite(e.clientX) || !Number.isFinite(e.clientY)) return;
    if (!seenAt) { seenAt = [e.clientX, e.clientY]; return; }
    if (Math.hypot(e.clientX - seenAt[0], e.clientY - seenAt[1]) >= (Number.isFinite(o.movePx) ? o.movePx : 4)) { seenAt = null; on({ type: 'pointermoved' }); }
  };
  win.addEventListener('pointermove', moved, { capture: true, passive: true });
  return () => { for (const t of types) win.removeEventListener(t, on, { capture: true, passive: true }); win.removeEventListener('pointermove', moved, { capture: true, passive: true }); };
}
