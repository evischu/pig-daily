/* Dayline service worker — app shell cached so the app opens instantly and
   still opens with no signal. Calendar and weather requests always go to the
   network: stale schedule data is worse than none. */

const VERSION = "dayline-v1";
const SHELL = [
  "./",
  "./index.html",
  "./config.js",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png"
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => c.addAll(SHELL).catch(() => {}))   // a missing optional file must not fail install
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;

  // Never serve calendar, account or weather data from cache.
  if (!sameOrigin) return;

  e.respondWith(
    caches.match(req).then(hit => {
      const live = fetch(req)
        .then(res => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(VERSION).then(c => c.put(req, copy));
          }
          return res;
        })
        .catch(() => hit);            // offline: fall back to whatever we have
      return hit || live;             // cache-first for the shell, refreshed in the background
    })
  );
});
