const CACHE_NAME = 'school-system-v1';
const urlsToCache = ['/', '/static/css/style.css', '/static/js/main.js', '/static/images/logo.png'];
self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)).catch(err => console.log('Cache error:', err)));
});
self.addEventListener('fetch', event => {
    event.respondWith(caches.match(event.request).then(response => {
        if (response) return response;
        return fetch(event.request).catch(() => caches.match('/'));
    }));
});
self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))));
});
