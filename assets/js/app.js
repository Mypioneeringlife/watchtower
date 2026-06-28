const App = {
  topics: [],
  sources: [],
  signals: [],
  meta: {},
  filter: 'all',
  review: JSON.parse(localStorage.getItem('watchtower.review.v13') || '{}')
};

const sampleSignals = [
  {
    id: 'sample-highlander',
    title: 'Highlander reboot gains a new production update with Henry Cavill',
    topic: 'Highlander Reboot',
    source: 'Sample Feed',
    url: 'https://example.com/highlander-reboot-update',
    score: 96,
    priority: 'immediate',
    status: 'new',
    summary: 'A sample alert showing how a strong Highlander reboot match will appear in the inbox.',
    why: ['required: Highlander reboot', 'context: Henry Cavill', 'context: Chad Stahelski']
  },
  {
    id: 'sample-usda',
    title: 'USDA announces food safety recall guidance update',
    topic: 'Food Law USDA',
    source: 'Sample Feed',
    url: 'https://example.com/usda-food-safety',
    score: 84,
    priority: 'high',
    status: 'new',
    summary: 'A sample food law signal showing how official food safety updates should be reviewed.',
    why: ['required: USDA', 'context: food safety', 'context: recall']
  }
];

function byId(id){ return document.getElementById(id); }
function make(tag, className, text){
  const el = document.createElement(tag);
  if(className){ el.className = className; }
  if(text !== undefined){ el.textContent = text; }
  return el;
}
function setText(id, value){ const el = byId(id); if(el){ el.textContent = value; } }
function statusOf(signal){ return App.review[signal.id] || signal.status || 'new'; }
function saveReview(){ localStorage.setItem('watchtower.review.v13', JSON.stringify(App.review)); }
function slug(value){ return String(value || 'watchtower').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'') || 'watchtower'; }
function today(){ return new Date().toISOString().slice(0,10); }

async function loadJson(path, fallback){
  try{
    const response = await fetch(path, {cache:'no-store'});
    if(!response.ok){ return fallback; }
    return await response.json();
  }catch(error){
    return fallback;
  }
}

async function boot(){
  const watchlists = await loadJson('data/watchlists.json', {topics:[]});
  const sources = await loadJson('data/sources.json', {sources:[]});
  const signals = await loadJson('data/signals.json', []);
  const meta = await loadJson('data/watcher-meta.json', {});
  App.topics = watchlists.topics || [];
  App.sources = sources.sources || [];
  App.signals = Array.isArray(signals) && signals.length ? signals : sampleSignals;
  App.meta = meta || {};
  bindNavigation();
  bindFilters();
  bindTools();
  renderAll();
}

function bindNavigation(){
  document.querySelectorAll('[data-view]').forEach(function(button){
    button.addEventListener('click', function(){ showView(button.getAttribute('data-view')); });
  });
}
function bindFilters(){
  document.querySelectorAll('[data-filter]').forEach(function(button){
    button.addEventListener('click', function(){
      App.filter = button.getAttribute('data-filter');
      renderSignals();
    });
  });
}
function bindTools(){
  const noteFields = ['noteTitle','noteTopic','noteUrl','noteSummary'];
  noteFields.forEach(function(id){
    const el = byId(id);
    if(el){ el.addEventListener('input', buildMarkdown); }
  });
  const copyButton = byId('copyMarkdown');
  if(copyButton){ copyButton.addEventListener('click', copyMarkdown); }
}

function showView(name){
  document.querySelectorAll('.view').forEach(function(section){ section.classList.toggle('active', section.id === name); });
  document.querySelectorAll('[data-view]').forEach(function(button){ button.classList.toggle('active', button.getAttribute('data-view') === name); });
}

function renderAll(){
  renderDashboard();
  renderSignals();
  renderTopics();
  renderSources();
  buildMarkdown();
}

function renderDashboard(){
  const alertCount = App.signals.filter(function(s){ return Number(s.score || 0) >= 88 || s.priority === 'immediate'; }).length;
  const newCount = App.signals.filter(function(s){ return statusOf(s) === 'new'; }).length;
  const savedCount = App.signals.filter(function(s){ return statusOf(s) === 'saved'; }).length;
  const enabled = App.sources.filter(function(s){ return s.enabled; }).length;
  setText('signalCount', App.signals.length);
  setText('sampleCount', alertCount);
  setText('topicCount', App.topics.length);
  setText('sourceCount', enabled + '/' + App.sources.length);
  setText('lastRun', App.meta.last_run || 'Not run yet');
  setText('signalStatus', newCount + ' new, ' + savedCount + ' saved, ' + alertCount + ' alert-level.');
  setText('sourceStatus', enabled ? enabled + ' sources enabled.' : 'All real sources are still disabled until you choose feeds.');
}

function filteredSignals(){
  return App.signals.filter(function(signal){
    const score = Number(signal.score || 0);
    const status = statusOf(signal);
    if(App.filter === 'all'){ return true; }
    if(App.filter === 'alert'){ return score >= 88 || signal.priority === 'immediate'; }
    return status === App.filter;
  });
}

function renderSignals(){
  document.querySelectorAll('[data-filter]').forEach(function(button){
    button.classList.toggle('active', button.getAttribute('data-filter') === App.filter);
  });
  const list = byId('signalList');
  if(!list){ return; }
  list.textContent = '';
  const signals = filteredSignals();
  if(!signals.length){
    list.appendChild(make('div','empty','No signals match this filter.'));
    return;
  }
  signals.forEach(function(signal){ list.appendChild(signalCard(signal)); });
}

function signalCard(signal){
  const card = make('article','card signal-card');
  const score = make('div','score-ring', String(signal.score || 0));
  const body = make('div','signal-body');
  body.appendChild(make('div','signal-title', signal.title || 'Untitled signal'));
  body.appendChild(make('div','signal-meta', (signal.topic || 'No topic') + ' • ' + (signal.source || 'No source') + ' • ' + (signal.priority || 'normal')));
  const pills = make('div','pill-row');
  pills.appendChild(make('span','pill ' + (statusOf(signal) === 'saved' ? 'good' : statusOf(signal) === 'ignored' ? 'bad' : ''), statusOf(signal)));
  (signal.why || []).slice(0,4).forEach(function(reason){ pills.appendChild(make('span','pill', reason)); });
  body.appendChild(pills);
  const actions = make('div','actions');
  const open = make('a','btn','Open');
  open.setAttribute('href', signal.url || '#');
  open.setAttribute('target','_blank');
  open.setAttribute('rel','noopener');
  actions.appendChild(open);
  actions.appendChild(actionButton('Note','secondary', function(){ makeNote(signal); }));
  actions.appendChild(actionButton('Save','warn', function(){ setStatus(signal.id,'saved'); }));
  actions.appendChild(actionButton('Reviewed','secondary', function(){ setStatus(signal.id,'reviewed'); }));
  actions.appendChild(actionButton('Ignore','danger', function(){ setStatus(signal.id,'ignored'); }));
  body.appendChild(actions);
  card.appendChild(score);
  card.appendChild(body);
  return card;
}

function actionButton(label, className, handler){
  const button = make('button', className, label);
  button.setAttribute('type','button');
  button.addEventListener('click', handler);
  return button;
}

function setStatus(id, status){
  App.review[id] = status;
  saveReview();
  renderAll();
}

function renderTopics(){
  const names = App.topics.map(function(topic){ return topic.name; }).join(' • ');
  setText('topicNames', names || 'No topics loaded yet.');
}

function renderSources(){
  const enabled = App.sources.filter(function(source){ return source.enabled; }).length;
  setText('sourceStatus', enabled ? enabled + ' sources enabled.' : 'All real sources are disabled until you choose feeds.');
}

function makeNote(signal){
  const title = byId('noteTitle');
  const topic = byId('noteTopic');
  const url = byId('noteUrl');
  const summary = byId('noteSummary');
  if(title){ title.value = signal.title || ''; }
  if(topic){ topic.value = signal.topic || ''; }
  if(url){ url.value = signal.url || ''; }
  if(summary){ summary.value = signal.summary || (signal.why || []).join('; '); }
  buildMarkdown();
  showView('tools');
}

function buildMarkdown(){
  const title = byId('noteTitle') ? byId('noteTitle').value : 'Untitled signal';
  const topic = byId('noteTopic') ? byId('noteTopic').value : 'Watchtower';
  const url = byId('noteUrl') ? byId('noteUrl').value : '';
  const summary = byId('noteSummary') ? byId('noteSummary').value : '';
  const markdown = '---\n' +
    'title: "' + title.replaceAll('"', "'") + '"\n' +
    'type: "Web Watch"\n' +
    'status: "Inbox"\n' +
    'topic: "' + topic.replaceAll('"', "'") + '"\n' +
    'url: "' + url.replaceAll('"', "'") + '"\n' +
    'captured: "' + today() + '"\n' +
    'tags:\n  - web-watch\n  - ' + slug(topic) + '\n---\n\n' +
    '# ' + title + '\n\n' +
    '## Summary\n\n' + (summary || 'Captured by Watchtower. Review before promoting this into permanent research.') + '\n\n' +
    '## Why this matters\n\nThis signal may be useful for research, content planning, or a second-brain reference note.\n\n' +
    '## Processing log\n\n- [ ] Reviewed\n- [ ] Promoted to permanent note\n- [ ] Used in content\n- [ ] Discarded\n\n' +
    '## Link\n\n' + url + '\n';
  setText('markdownOut', markdown);
}

function copyMarkdown(){
  const output = byId('markdownOut');
  if(!output){ return; }
  navigator.clipboard.writeText(output.textContent || '').then(function(){ alert('Markdown copied.'); });
}

document.addEventListener('DOMContentLoaded', boot);
