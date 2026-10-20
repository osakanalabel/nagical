// ナギカルのサービスワーカー：アプリの外枠をキャッシュし、電波が弱くてもアプリを開けるようにする。
// 予報（Open-Meteo）と祝日APIはここでは扱わない（アプリ側の localStorage で30分キャッシュしているため）。
// 画面（index.html）は通信を優先し、つながらないときだけ保存分を出す。アイコンなどはキャッシュを優先する。
// 公開のたびに VERSION を上げる（アイコンなどを取り込み直し、古い版のキャッシュを消すため）。
const VERSION = "v7";
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
const WAIT = 3000;  // 画面の取得をこれ以上待たずに保存分を出す（ミリ秒）

// 取り込むときはブラウザの保存分（GitHub Pages は10分間有効）を使わず、必ずサーバーから取る
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE)
    .then(c => c.addAll(SHELL.map(u => new Request(u, { cache: "reload" }))))
    .then(() => self.skipWaiting()));
});

// 新しい版が有効になったら、古い版のキャッシュを消す
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith("nagical-") && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// 画面：サーバーに確かめて最新を取り、保存分も入れ替える
function fetchPage(req) {
  return fetch(req.url, { cache: "no-cache", credentials: "same-origin" }).then(res => {
    if (res.ok) {
      const a = res.clone(), b = res.clone();
      caches.open(CACHE).then(c => Promise.all([c.put("./", a), c.put("index.html", b)]));
    }
    return res;
  });
}
// 画面は通信を優先する。失敗したとき・WAIT ミリ秒たっても返事がないときは保存分を出す
function pageFirst(req) {
  const net = fetchPage(req);
  const saved = () => caches.match("./");
  const late = new Promise(r => setTimeout(r, WAIT)).then(saved).then(hit => hit || net);
  return Promise.race([net.catch(() => saved().then(hit => hit || Promise.reject())), late]);
}

// 同じサイトのファイルだけ扱う。ほかのサイトへの通信には手を出さない
self.addEventListener("fetch", e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (req.mode === "navigate" || /\/(index\.html)?$/.test(url.pathname)) {
    e.respondWith(pageFirst(req));
    return;
  }
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req)));
});
