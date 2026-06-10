const CACHE_NAME = 'school-v5';
const STATIC = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/images/logo.png',
  '/dashboard',
  '/attendance',
  '/grades',
  '/fees',
  '/monthly_fees',
  '/votes',
  '/announcement'
];
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(c => c.addAll(STATIC.map(u => new Request(u, {credentials:'same-origin'}))))
      .catch(() => {})
  );
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  var url = e.request.url;
  // API calls — network only, no cache
  if(url.includes('/search_student') || url.includes('/submit_') ||
     url.includes('/pay_') || url.includes('/save_') || url.includes('/add_') ||
     url.includes('/edit_') || url.includes('/delete_') || url.includes('/toggle_')) {
    e.respondWith(fetch(e.request).catch(() => new Response('{"success":false,"message":"Offline"}', {headers:{'Content-Type':'application/json'}})));
    return;
  }
  // Static files — cache first
  if(url.includes('/static/')) {
    e.respondWith(
      caches.match(e.request).then(r => r || fetch(e.request).then(nr => {
        caches.open(CACHE_NAME).then(c => c.put(e.request, nr.clone()));
        return nr;
      }))
    );
    return;
  }
  // Pages — network first, fallback cache
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
