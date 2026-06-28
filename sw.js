const CACHE_NAME = 'watchtower-v1-4-1';
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
    return Promise.all(keys.map(function(key) {
      if (key !== CACHE_NAME) { return caches.delete(key); }
    }));
  }));
  self.clients.claim();
});

self.addEventListener('fetch', function(event) {
  if (event.request.method !== 'GET') { return; }
  event.respondWith(fetch(event.request).catch(function() {
    return caches.match(event.request).then(function(cached) {
      return cached || caches.match('./index.html');
    });
  }));
});
