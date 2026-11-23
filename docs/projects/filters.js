const filters = document.querySelector('.filters');
const choices = [...filters.querySelectorAll('button')];
const typeChoice = document.querySelector('#resource-type');
const projects = [...document.querySelectorAll('[data-project]')];
const status = document.querySelector('#filter-status');
const gameEntry = document.querySelector('[data-game-entry]');

function applyFilters(project, type) {
  let count = 0;
  for (const section of projects) {
    const showProject = project === 'all' || section.id === project;
    let visible = 0;
    for (const card of section.querySelectorAll('[data-kind]')) {
      card.hidden = !showProject || (type !== 'all' && card.dataset.kind !== type);
      if (!card.hidden) visible += 1;
    }
    section.hidden = visible === 0;
    count += visible;
  }
  for (const button of choices) {
    button.setAttribute('aria-pressed', String(button.value === project));
  }
  gameEntry.hidden = (project !== 'all' && project !== 'neurosurge') || (type !== 'all' && type !== 'try');
  typeChoice.value = type;
  status.textContent = `${count} ${count === 1 ? 'resource' : 'resources'} shown`;
}

function readLocation() {
  const url = new URL(location.href);
  const project = url.searchParams.get('project');
  const type = url.searchParams.get('type');
  applyFilters(
    choices.some(button => button.value === project) ? project : 'all',
    [...typeChoice.options].some(option => option.value === type) ? type : 'all',
  );
}

function choose(project, type) {
  const url = new URL(location.href);
  if (project === 'all') url.searchParams.delete('project');
  else url.searchParams.set('project', project);
  if (type === 'all') url.searchParams.delete('type');
  else url.searchParams.set('type', type);
  url.hash = '';
  if (url.href !== location.href) history.pushState(null, '', url);
  applyFilters(project, type);
}

for (const button of choices) {
  button.addEventListener('click', () => choose(button.value, typeChoice.value));
}
typeChoice.addEventListener('change', () => {
  const project = choices.find(button => button.getAttribute('aria-pressed') === 'true');
  choose(project.value, typeChoice.value);
});
addEventListener('popstate', readLocation);
readLocation();
filters.hidden = false;
