// ナギカルのサービスワーカー：アプリの外枠だけをキャッシュし、電波が弱くてもアプリを開けるようにする。
// 予報（Open-Meteo）と祝日APIはここでは扱わない（アプリ側の localStorage で30分キャッシュしているため）。
// 公開のたびに VERSION を上げる。上げないと、利用者の端末では古い index.html が使われ続ける。
const VERSION = "v5";
const CACHE = `nagical-${VERSION}`;
const SHELL = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/icon-maskable-512.png",
  "icons/apple-touch-icon.png",
  "icons/favicon-32.png",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

// 新しい版が有効になったら、古い版のキャッシュを消す
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith("nagical-") && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// 同じサイトのファイルだけ、キャッシュを優先して返す。ほかのサイトへの通信には手を出さない
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  e.respondWith(
    caches.match(req, { ignoreSearch: true })
      .then(hit => hit || (req.mode === "navigate" ? caches.match("./") : null))
      .then(hit => hit || fetch(req))
  );
});
