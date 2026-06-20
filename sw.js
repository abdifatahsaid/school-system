const CACHE_NAME = 'school-v7';
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
  // Static files — stale-while-revalidate:
  // serve the cached copy instantly (fast), but ALWAYS re-fetch in the
  // background and overwrite the cache so the next load gets the new file.
  // This fixes the old "cache-first" bug where an updated style.css/main.js
  // would never be picked up until the cache name was manually bumped.
  if(url.includes('/static/')) {
    e.respondWith(
      caches.open(CACHE_NAME).then(cache =>
        cache.match(e.request).then(cached => {
          const network = fetch(e.request).then(nr => {
            if (nr && nr.ok) cache.put(e.request, nr.clone());
            return nr;
          }).catch(() => cached);
          return cached || network;
        })
      )
    );
    return;
  }
  // Pages — network first, fallback cache
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});

/* ══════════════════════════════════════
   PUSH NOTIFICATIONS
   Shows OS-level notification with school
   logo + name, like WhatsApp/Facebook
══════════════════════════════════════ */
self.addEventListener('push', function(e){
  var data = {};
  try{ data = e.data ? e.data.json() : {}; }catch(err){
    data = { title: 'School Management System', body: e.data ? e.data.text() : 'You have a new notification' };
  }

  var title = data.title || 'School Management System';
  var options = {
    body: data.body || '',
    icon: data.icon || '/static/images/logo.png',
    badge: '/static/images/logo.png',
    image: data.image || undefined,
    tag: data.tag || 'school-notification',
    renotify: true,
    requireInteraction: false,
    vibrate: [120, 60, 120],
    data: { url: data.url || '/dashboard' },
    timestamp: Date.now()
  };

  e.waitUntil(self.registration.showNotification(title, options));
});

/* Clicking the notification opens/focuses the app */
self.addEventListener('notificationclick', function(e){
  e.notification.close();
  var targetUrl = (e.notification.data && e.notification.data.url) || '/dashboard';

  e.waitUntil(
    clients.matchAll({type:'window', includeUncontrolled:true}).then(function(windowClients){
      for(var i=0; i<windowClients.length; i++){
        var client = windowClients[i];
        if('focus' in client){
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if(clients.openWindow) return clients.openWindow(targetUrl);
    })
  );
});
