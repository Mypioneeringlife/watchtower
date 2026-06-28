function showView(name){
  document.querySelectorAll('.view').forEach(function(section){
    section.classList.toggle('active', section.id === name);
  });
  document.querySelectorAll('[data-view]').forEach(function(button){
    button.classList.toggle('active', button.getAttribute('data-view') === name);
  });
}

function setText(id, value){
  var el = document.getElementById(id);
  if(el){ el.textContent = value; }
}

function renderTopicCount(){
  fetch('data/watchlists.json', {cache:'no-store'})
    .then(function(response){ return response.json(); })
    .then(function(data){
      var topics = data.topics || [];
      setText('topicCount', topics.length);
      var names = topics.map(function(topic){ return topic.name; }).join(' • ');
      setText('topicNames', names || 'No topics loaded yet.');
    })
    .catch(function(){ setText('topicNames', 'Topic file could not be loaded.'); });
}

function renderSourceCount(){
  fetch('data/sources.json', {cache:'no-store'})
    .then(function(response){ return response.json(); })
    .then(function(data){
      var sources = data.sources || [];
      var enabled = sources.filter(function(source){ return source.enabled; }).length;
      setText('sourceCount', enabled + '/' + sources.length);
      setText('sourceStatus', enabled ? 'Some sources are enabled.' : 'All real sources are disabled until you choose feeds.');
    })
    .catch(function(){ setText('sourceStatus', 'Source file could not be loaded.'); });
}

function renderSignalCount(){
  fetch('data/signals.json', {cache:'no-store'})
    .then(function(response){ return response.json(); })
    .then(function(signals){
      if(!Array.isArray(signals)){ signals = []; }
      setText('signalCount', signals.length);
      setText('signalStatus', signals.length ? 'Real watcher signals found.' : 'No real signals yet. Sample cards are shown below.');
    })
    .catch(function(){ setText('signalStatus', 'Signal file could not be loaded.'); });
}

function renderMeta(){
  fetch('data/watcher-meta.json', {cache:'no-store'})
    .then(function(response){ return response.json(); })
    .then(function(meta){ setText('lastRun', meta.last_run || 'Not run yet'); })
    .catch(function(){ setText('lastRun', 'Not available'); });
}

function bindNavigation(){
  document.querySelectorAll('[data-view]').forEach(function(button){
    button.addEventListener('click', function(){ showView(button.getAttribute('data-view')); });
  });
}

document.addEventListener('DOMContentLoaded', function(){
  bindNavigation();
  renderTopicCount();
  renderSourceCount();
  renderSignalCount();
  renderMeta();
});
