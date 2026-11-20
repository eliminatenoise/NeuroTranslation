/** Browser-local metadata report. This view makes no pairing or model claim. */
const text = (tag, value, className = '') => {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
};

const uniqueReasons = (mapping, checked) => {
  const seen = new Set();
  // The policy reasons cover descriptor gaps; the bridge's repeated informational
  // omissions are grouped separately below. Keep the complete reports unchanged.
  return (checked?.reasons || mapping?.diagnostics || []).filter(reason => {
    if (reason.severity === 'info') return false;
    const key = `${reason.code}\n${reason.path}\n${reason.message}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const explanation = reason => ({
  MEASUREMENT_UNKNOWN: 'The file does not name a recognised measurement type.',
  RIGHTS_UNKNOWN: 'Permission to use or redistribute these data has not been checked.',
  SIMULATION_PROVENANCE_INCOMPLETE: 'The file does not fully describe how these simulated signals were generated.',
  SPLIT_UNKNOWN: 'The training, validation, test or held-out role is not declared.',
  SUBJECT_NAMESPACE_UNDECLARED: 'The subject and recording IDs lack a declared scope. Matching IDs cannot establish the same person or event.'
}[reason.code] || reason.message || reason.code || 'Undeclared metadata.');
const counted = (value, noun) => `${value} ${noun}${value===1?'':'s'}`;

/** Render supplied plain reports only; no file, network, storage or timer access. */
export function renderMetadataReport(container, {mapping = null, report = null} = {}) {
  container.replaceChildren();
  const header = text('div', '', 'metadata-heading');
  header.append(text('h3', 'What the files declare'));
  container.append(header);
  if (!mapping) {
    container.append(text('p', 'Import a recording to check its measurement, units, clocks and provenance.'));
    return;
  }
  container.append(text('p', 'These checks read your file declarations. They do not verify the recording, synchronize clocks or establish biological correspondence.', 'quiet'));
  if (mapping.status !== 'mapped' || report?.status !== 'evaluated') {
    container.append(text('p', 'Some metadata cannot be checked. The original samples remain available to inspect.', 'metadata-status'));
    const list = text('ul', '');
    const addReason = (reason, identity = '') => {
      const item = text('li', `${identity ? `${identity}: ` : ''}${explanation(reason)}`);
      if (reason.path) item.append(text('code', ` ${reason.path}`, 'metadata-path'));
      list.append(item);
    };
    for (const reason of mapping.diagnostics || []) addReason(reason);
    for (const reason of report?.inputReasons || []) addReason(reason);
    // A rejected stream can leave the envelope diagnostics empty. Its own
    // diagnostics still explain the rejection and must remain visible.
    for (const stream of mapping.streamResults || []) {
      const id = stream.identityMap?.original;
      const identity = id ? `${id.datasetId} / ${id.streamId}` : 'Stream';
      for (const reason of stream.diagnostics || []) if (reason.severity !== 'info') addReason(reason, identity);
    }
    if (list.children.length) container.append(list);
    return;
  }
  const checks = new Map((report.descriptors || []).map(item => [item.streamId, item]));
  for (const stream of mapping.streamResults || []) {
    const id = stream.identityMap?.original || {};
    const descriptor = stream.descriptor || {};
    const checked = checks.get(descriptor.streamId);
    const reasons = uniqueReasons(stream, checked);
    const issueCount = reasons.length;
    const details = document.createElement('details');
    details.className = 'metadata-stream';
    const summary = document.createElement('summary');
    summary.append(text('strong', descriptor.label || id.streamId || 'Unnamed stream'));
    summary.append(text('span', checked?.status === 'invalid' ? 'Needs more metadata' : issueCount ? 'Has unchecked details' : 'Declarations consistent', 'metadata-status'));
    details.append(summary);
    details.append(text('p', `${id.datasetId ?? 'Unknown dataset'} · ${id.streamId ?? 'Unknown stream'} · ${descriptor.origin ?? 'Unknown origin'} · ${descriptor.quantity?.unit ?? 'Unknown unit'}`, 'quiet'));
    const observations = descriptor.observations;
    if (observations) details.append(text('p', `${counted(observations.sampleCount,'timestamp')} · ${counted(observations.finiteCount,'finite value')} · ${counted(observations.nullCount,'missing value')}`));
    if (reasons.length) {
      const list = document.createElement('ul');
      for (const reason of reasons) {
        const item = document.createElement('li');
        item.append(text('span', explanation(reason)));
        if (reason.path) item.append(text('code', ` ${reason.path}`, 'metadata-path'));
        list.append(item);
      }
      details.append(list);
    } else details.append(text('p', 'No declaration conflict was found. Source identity, permissions and scientific validity still require independent evidence.'));
    const absent = (stream.diagnostics || []).filter(item => item.code === 'DECLARATION_ABSENT').map(item => item.path).filter(Boolean);
    if (absent.length) details.append(text('p', `Undeclared fields: ${[...new Set(absent)].join(', ')}.`, 'quiet'));
    container.append(details);
  }
  container.append(text('p', 'No biological pairing or learned translation was created by this check.', 'quiet'));
}
