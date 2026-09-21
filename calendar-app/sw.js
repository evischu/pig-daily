/* Dayline service worker — app shell cached so the app still opens with no
   signal. Calendar, account and weather requests always go to the network:
   stale schedule data is worse than none.

   The page itself (index.html, config.js) is network-first: try live first,
   fall back to cache only when the network is unreachable. A calendar app
   that silently keeps showing yesterday's code after every fix ships is a
   worse bug than the fast-paint cache-first trades away — a returning
   visitor must see today's version on the very next load, not the load
   after that. Only the rarely-changing icons/manifest stay cache-first. */

const VERSION = "dayline-v2";
const SHELL = [
  "./",
  "./index.html",
  "./config.js",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png"
];
const NETWORK_FIRST = new Set(["./", "./index.html", "./config.js"]);

function relPath(url){
  const rel = url.pathname.replace(self.registration.scope.replace(location.origin, ""), "");
  return rel === "" ? "./" : "./" + rel;
}

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
  if (url.origin !== self.location.origin) return;   // calendar/weather APIs: not this worker's concern

  const isNavigation = req.mode === "navigate";
  const path = relPath(url);

  if (isNavigation || NETWORK_FIRST.has(path)) {
    e.respondWith(
      fetch(req)
        .then(res => {
          if (res && res.ok) caches.open(VERSION).then(c => c.put(req, res.clone()));
          return res;
        })
        .catch(() => caches.match(req).then(hit => hit || caches.match("./index.html")))
    );
    return;
  }

  // Static, rarely-changing assets: instant from cache, refreshed for next time.
  e.respondWith(
    caches.match(req).then(hit => {
      const live = fetch(req)
        .then(res => {
          if (res && res.ok) caches.open(VERSION).then(c => c.put(req, res.clone()));
          return res;
        })
        .catch(() => hit);
      return hit || live;
    })
  );
});
