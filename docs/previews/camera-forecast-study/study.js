const choice = document.querySelector('#group');
const caption = document.querySelector('#selected-group');
const table = document.querySelector('table');
const edition = document.querySelector('[data-edition]');
const download = document.querySelector('#download');
const rows = Array.from(table.tBodies[0].rows);
const measures = ['endpoint_px', 'movement_px'];
const decimals = Number(table.dataset.decimals ?? 2);

function csvField(value) {
  return typeof value === 'string' ? '"' + value.replaceAll('"', '""') + '"' : value;
}

async function loadResults() {
  const response = await fetch(new URL('results.json', import.meta.url));
  if (!response.ok) return null;
  return response.json();
}

function enableComparison({groups}) {
  const all = new Map(groups.map(group => [group.id, group]));
  const scale = measures.map(measure => Math.max(...groups.flatMap(
    group => rows.map(row => group.errors[measure][row.dataset.method]),
  )));
  const sections = new Map();
  for (const group of groups.slice(1)) {
    if (!sections.has(group.group)) {
      const section = document.createElement('optgroup');
      section.label = group.group;
      choice.append(section);
      sections.set(group.group, section);
    }
    sections.get(group.group).append(new Option(group.label, group.id));
  }

  const values = rows.map(row => measures.map((measure, index) => {
    const cell = row.cells[index + 1];
    const number = document.createTextNode('');
    const bar = document.createElement('span');
    bar.className = 'score-meter';
    bar.setAttribute('aria-hidden', 'true');
    cell.replaceChildren(number, bar);
    return {method: row.dataset.method, measure, index, number, bar};
  })).flat();

  function render() {
    const url = new URL(location.href);
    const group = all.get(url.searchParams.get('group')) ?? groups[0];
    choice.value = group.id;
    caption.textContent = `${group.label} · ${group.people} people`;
    for (const {method, measure, index, number, bar} of values) {
      const score = group.errors[measure][method];
      number.data = score.toFixed(decimals);
      bar.style.setProperty('--bar-width', `${100 * score / scale[index]}%`);
    }
    const alternate = new URL(edition.href);
    if (group.id === 'overall') alternate.searchParams.delete('group');
    else alternate.searchParams.set('group', group.id);
    edition.href = alternate;
  }

  choice.addEventListener('change', () => {
    const url = new URL(location.href);
    if (choice.value === 'overall') url.searchParams.delete('group');
    else url.searchParams.set('group', choice.value);
    history.replaceState(null, '', url);
    render();
  });
  addEventListener('popstate', render);
  download.addEventListener('click', () => {
    const header = 'group,people,forecast,final_position_error_px,movement_error_px';
    const data = groups.flatMap(group => rows.map(row => {
      const method = row.dataset.method;
      const forecast = row.cells[0].textContent;
      const scores = measures.map(measure => group.errors[measure][method]);
      return [group.label, group.people, forecast, ...scores].map(csvField).join(',');
    }));
    const blob = new Blob([[header, ...data].join('\r\n') + '\r\n'], {type: 'text/csv;charset=utf-8'});
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = 'movi-camera-forecast-scores.csv';
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
  });

  render();
  choice.closest('label').hidden = false;
  download.hidden = false;
}

const results = await loadResults().catch(() => null);
if (results) enableComparison(results);
