// ==============================================================
// SW.JS - service worker for the private fitness PWA
// ==============================================================
// Scope: fitness.html only (boxing timer + gym session app,
// installable to iOS/Android home screen via manifest.json).
//
// Cache strategy: stale-while-revalidate.
//   - On fetch, serve from cache immediately if present.
//   - In parallel, fetch fresh from network and overwrite the
//     cached copy (only if the response is 200 - skips opaque
//     and error responses to avoid poisoning the cache).
//   - If network fails, the cached copy is still returned, so
//     the app works offline once it has loaded once.
//
// Lifecycle:
//   install   - precaches the ASSETS list; skipWaiting() so a
//               new SW activates immediately on next page load
//               rather than waiting for all tabs to close.
//   activate  - deletes any cache not matching CACHE_NAME
//               (old versions) and claims existing clients.
//   fetch     - the stale-while-revalidate handler above.
//
// Versioning: bump CACHE_NAME (e.g. 'fitness-v2') any time the
// precached ASSETS list changes meaningfully OR when fitness.html
// has a breaking change you want all installed clients to pick
// up on next visit. The new name triggers activate -> old cache
// purge -> fresh precache on the next SW install.
//
// Registered from: fitness.html (<script> that calls
// navigator.serviceWorker.register('sw.js')).
// ==============================================================

const CACHE_NAME = 'fitness-v1';
const ASSETS = [
  './fitness.html',
  './manifest.json',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(cached => {
      const fetched = fetch(e.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return response;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});
