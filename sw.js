const CACHE_NAME = 'watchtower-v1-3-signal-inbox';
const APP_SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/icons/watchtower.svg',
  './assets/css/app.css',
  './assets/js/app.js',
  './data/watchlists.json',
  './data/sources.json',
  './data/signals.json',
  './data/watcher-meta.json'
];

self.addEventListener('install', function(event) {
  event.waitUntil(caches.open(CACHE_NAME).then(function(cache) { return cache.addAll(APP_SHELL); }));
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(caches.keys().then(function(keys) {
    return Promise.all(keys.filter(function(key) { return key !== CACHE_NAME; }).map(function(key) { return caches.delete(key); }));
  }));
  self.clients.claim();
});

self.addEventListener('fetch', function(event) {
  if (event.request.method !== 'GET') { return; }
  event.respondWith(caches.match(event.request).then(function(cached) {
    if (cached) { return cached; }
    return fetch(event.request).then(function(response) {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, copy); });
      return response;
    }).catch(function() { return caches.match('./index.html'); });
  }));
});
