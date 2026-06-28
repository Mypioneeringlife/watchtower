async function wtLoadJson(path, fallback){
  try{
    const response = await fetch(path, {cache:'no-store'});
    if(!response.ok){ return fallback; }
    return await response.json();
  }catch(error){
    return fallback;
  }
}

function wtSetText(id, value){
  const el = document.getElementById(id);
  if(el){ el.textContent = value; }
}

function wtMake(tag, className, text){
  const el = document.createElement(tag);
  if(className){ el.className = className; }
  if(text !== undefined){ el.textContent = text; }
  return el;
}

function renderRunLogCard(run){
  const card = wtMake('article','card');
  card.appendChild(wtMake('h3','', run.started_at || 'Watcher run'));
  card.appendChild(wtMake('p','', 'Mode: ' + (run.mode || 'unknown') + ' • Finished: ' + (run.finished_at || 'unknown')));

  const pills = wtMake('div','pill-row');
  pills.appendChild(wtMake('span','pill good', 'New signals: ' + (run.new_signals || 0)));
  pills.appendChild(wtMake('span','pill', 'Items checked: ' + (run.items_checked || 0)));
  pills.appendChild(wtMake('span','pill', 'Notes: ' + (run.notes_written || 0)));
  pills.appendChild(wtMake('span', run.source_errors ? 'pill bad' : 'pill good', 'Errors: ' + (run.source_errors || 0)));
  card.appendChild(pills);

  const sourceList = wtMake('div','run-sources');
  (run.sources || []).forEach(function(source){
    const row = wtMake('div','run-source');
    const name = wtMake('strong','', source.name || source.id || 'Unnamed source');
    const status = wtMake('span', source.status === 'error' ? 'pill bad' : 'pill good', source.status || 'unknown');
    row.appendChild(name);
    row.appendChild(status);
    row.appendChild(wtMake('small','', 'Items: ' + (source.items_checked || 0) + ' • Matches: ' + (source.matches || 0) + ' • Notes: ' + (source.notes_written || 0)));
    if(source.error){ row.appendChild(wtMake('small','', source.error)); }
    sourceList.appendChild(row);
  });
  card.appendChild(sourceList);
  return card;
}

async function renderRunLog(){
  const log = await wtLoadJson('data/run-log.json', {runs:[]});
  const runs = log.runs || [];
  wtSetText('runCount', String(runs.length));
  if(!runs.length){
    wtSetText('runStatus', 'No watcher runs have been recorded yet. Run the GitHub Action once to populate this screen.');
    const list = document.getElementById('runLogList');
    if(list){
      list.textContent = '';
      const empty = wtMake('div','empty','No run log yet. Go to GitHub Actions, open Watchtower, and tap Run workflow.');
      list.appendChild(empty);
    }
    return;
  }
  const latest = runs[0];
  wtSetText('runStatus', 'Last run checked ' + (latest.items_checked || 0) + ' items and found ' + (latest.new_signals || 0) + ' new signals.');
  wtSetText('runItemsMetric', String(latest.items_checked || 0));
  wtSetText('runSignalsMetric', String(latest.new_signals || 0));
  wtSetText('runErrorsMetric', String(latest.source_errors || 0));
  wtSetText('runNotesMetric', String(latest.notes_written || 0));
  const list = document.getElementById('runLogList');
  if(list){
    list.textContent = '';
    runs.slice(0,10).forEach(function(run){ list.appendChild(renderRunLogCard(run)); });
  }
}

document.addEventListener('DOMContentLoaded', renderRunLog);
