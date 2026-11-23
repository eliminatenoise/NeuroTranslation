const filters = document.querySelector('.filters');
const projectFilter = document.querySelector('.project-filter');
const choices = [...projectFilter.querySelectorAll('button')];
const typeChoice = document.querySelector('#resource-type');
const search = document.querySelector('#resource-search');
const projects = [...document.querySelectorAll('[data-project]')];
const status = document.querySelector('#filter-status');
const empty = document.querySelector('.no-results');
const shortcuts = document.querySelector('[data-shortcuts]');
const shortcutGroups = [...document.querySelectorAll('[data-shortcuts] [data-for-project]')];
const gameEntry = document.querySelector('[data-game-entry]');
const editionLinks = document.querySelectorAll('[data-edition-link]');

function writeFilters(url, project, type, query) {
  if (project === 'all') url.searchParams.delete('project');
  else url.searchParams.set('project', project);
  if (type === 'all') url.searchParams.delete('type');
  else url.searchParams.set('type', type);
  if (query.trim()) url.searchParams.set('q', query.trim());
  else url.searchParams.delete('q');
  url.hash = '';
  return url;
}

function matchesType(item, type) {
  return type === 'all' || item.dataset.kind === type;
}

function applyFilters(project, type, query) {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  let count = 0;
  for (const section of projects) {
    const showProject = project === 'all' || section.id === project;
    const title = section.querySelector('h2').textContent;
    let visible = 0;
    for (const card of section.querySelectorAll('[data-kind]')) {
      const words = (title + ' ' + card.textContent).toLowerCase();
      card.hidden = !showProject || !matchesType(card, type) || !terms.every(term => words.includes(term));
      if (!card.hidden) visible += 1;
    }
    section.hidden = visible === 0;
    count += visible;
  }
  for (const button of choices) {
    button.setAttribute('aria-pressed', String(button.value === project));
  }
  for (const group of shortcutGroups) {
    const links = [...group.querySelectorAll('a[data-kind]')];
    for (const link of links) link.hidden = !matchesType(link, type);
    group.hidden = (project !== 'all' && group.dataset.forProject !== project) || links.every(link => link.hidden);
  }
  if (shortcuts) shortcuts.hidden = shortcutGroups.every(group => group.hidden);
  if (gameEntry) gameEntry.hidden = (project !== 'all' && project !== 'neurosurge') || (type !== 'all' && type !== 'try');
  typeChoice.value = type;
  if (search && search.value !== query) search.value = query;
  if (empty) empty.hidden = count > 0;
  status.textContent = `${count} ${count === 1 ? 'resource' : 'resources'} shown`;
  for (const link of editionLinks) {
    link.href = writeFilters(new URL(link.href), project, type, query);
  }
}

function readLocation() {
  const url = new URL(location.href);
  const project = url.searchParams.get('project') ?? url.hash.slice(1);
  const type = url.searchParams.get('type');
  applyFilters(
    choices.some(button => button.value === project) ? project : 'all',
    [...typeChoice.options].some(option => option.value === type) ? type : 'all',
    search ? (url.searchParams.get('q') ?? '').slice(0, search.maxLength) : '',
  );
}

function activeProject() {
  return choices.find(button => button.getAttribute('aria-pressed') === 'true').value;
}

function choose(project, type, query, replace = false) {
  const url = writeFilters(new URL(location.href), project, type, query);
  if (url.href !== location.href) {
    if (replace) history.replaceState(null, '', url);
    else history.pushState(null, '', url);
  }
  applyFilters(project, type, query);
}

for (const button of choices) {
  button.addEventListener('click', () => choose(button.value, typeChoice.value, search?.value ?? ''));
}
typeChoice.addEventListener('change', () => choose(activeProject(), typeChoice.value, search?.value ?? ''));
search?.addEventListener('input', () => choose(activeProject(), typeChoice.value, search.value, true));
document.querySelector('[data-show-all]')?.addEventListener('click', () => {
  choose('all', 'all', '');
  search?.focus();
});
addEventListener('popstate', readLocation);
readLocation();
projectFilter.hidden = false;
filters.hidden = false;
status.hidden = false;
document.querySelector('[data-fallback-jumps]')?.setAttribute('hidden', '');
