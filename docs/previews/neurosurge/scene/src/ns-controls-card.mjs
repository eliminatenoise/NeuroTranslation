















/** How long the card stays (ms). */
export const CONTROLS_CARD_MS = 5000;
const CONTROLS_HELP = 'Esc for controls and settings';

/** The card's chunks, in reading order (pure; the test and the Esc page read the same grouping). keys: rows of key
 * names, top to bottom; words: one short word for the chunk, or one per key (same order as the keys read left to
 * right); acts: [gesture, what it does] rows of the trackpad. */
export const CONTROLS_CARD_CHUNKS = Object.freeze([
  Object.freeze({ id: 'wasd', keys: Object.freeze([Object.freeze(['W']), Object.freeze(['A', 'S', 'D'])]), words: Object.freeze(['move']) }),
  Object.freeze({ id: 'er', keys: Object.freeze([Object.freeze(['E', 'R'])]), words: Object.freeze(['view', 'info']) }),
  Object.freeze({ id: 'space', keys: Object.freeze([Object.freeze(['Space'])]), words: Object.freeze(['grip']) }),
  Object.freeze({ id: 'pad', acts: Object.freeze([Object.freeze(['Move', 'look']), Object.freeze(['Click', 'press']), Object.freeze(['Drag', 'turn'])]) })
]);

/** What a screen reader hears instead of the picture (pure). */
export function controlsCardLabel(chunks = CONTROLS_CARD_CHUNKS) {
  const parts = [];
  for (const c of chunks) {
    if (c.acts) { parts.push(`trackpad: ${c.acts.map(([g, w]) => `${g.toLowerCase()} to ${w}`).join(', ')}`); continue; }
    const keys = c.keys.flat();
    if (c.words.length === keys.length) keys.forEach((k, i) => parts.push(`${k} ${c.words[i]}`));
    else parts.push(`${keys.join(' ')} ${c.words[0]}`);
  }
  return `Main controls: ${parts.join('; ')}. ${CONTROLS_HELP}.`;
}

/** Draw the card into `host` for `ms`. Returns the element (null when the document cannot build it). */
export function showControlsCard({ host, doc = globalThis.document, ms = CONTROLS_CARD_MS } = {}) {
  try {
    const el = (tag, cls, parent, text) => { const e = doc.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; if (parent) parent.appendChild(e); return e; };
    const card = el('div', 'ns-keys ns-ctl', host);
    card.setAttribute('role', 'note');
    card.setAttribute('aria-label', controlsCardLabel());
    card.style.setProperty('--ns-keys-ms', `${ms}ms`);
    // Left: the three key chunks, laid out as they lie on a keyboard (E and R right of W, Space under them).
    // Right: the trackpad. The middle of the picture, where the body is, stays free.
    const keysSide = el('div', 'ns-ctl-side ns-ctl-side-keys', card);
    const padSide = el('div', 'ns-ctl-side ns-ctl-side-pad', card);
    for (const c of CONTROLS_CARD_CHUNKS) {
      const chunk = el('div', `ns-ctl-chunk ns-ctl-${c.id}`, c.acts ? padSide : keysSide);
      chunk.setAttribute('aria-hidden', 'true');
      if (c.acts) {
        const plate = el('div', 'ns-pad-plate', chunk);
        el('span', 'ns-pad-finger', plate);
        el('span', 'ns-pad-click', plate);
        const acts = el('dl', 'ns-ctl-acts', chunk);
        for (const [g, w] of c.acts) { el('dt', '', acts, g); el('dd', '', acts, w); }
        continue;
      }
      const perKey = c.words.length === c.keys.flat().length && c.words.length > 1;
      let n = 0;
      for (const row of c.keys) {
        const r = el('div', 'ns-ctl-row', chunk);
        for (const k of row) {
          const cell = perKey ? el('div', 'ns-ctl-cell', r) : r;
          el('kbd', k === 'Space' ? 'ns-key ns-key-space' : 'ns-key', cell, k);
          if (perKey) el('span', 'ns-ctl-word', cell, c.words[n]);
          n++;
        }
      }
      if (!perKey) el('span', 'ns-ctl-word', chunk, c.words[0]);
    }
    const help = el('p', 'ns-ctl-help', keysSide, CONTROLS_HELP);
    help.setAttribute('aria-hidden', 'true');
    card.addEventListener('animationend', ev => { if (ev.animationName === 'ns-keys-out') { try { card.remove(); } catch { /* gone */ } } });
    return card;
  } catch { return null; }
}
