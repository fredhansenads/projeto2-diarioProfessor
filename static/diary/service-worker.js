/* Only a generic, public connection message is stored. Never cache teacher data. */
const CACHE = 'diario-public-v1';
const OFFLINE = '/offline/';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(async cache => {
    const response = await fetch(OFFLINE, {cache: 'reload', credentials: 'omit'});
    if (!response.ok || response.redirected) throw new Error('Offline page unavailable');
    await cache.put(OFFLINE, response);
  }));
  // Updates activate after old tabs close; never interrupt unsaved forms.
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('diario-public-') && key !== CACHE)
      .map(key => caches.delete(key))
  )));
});
self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate' ||
      new URL(event.request.url).origin !== self.location.origin) return;
  // POST is sent once, directly to the server; no queue and no automatic retry.
  event.respondWith(fetch(event.request).catch(async () => {
    const cache = await caches.open(CACHE);
    const fallback = await cache.match(OFFLINE);
    const body = fallback ? await fallback.text() :
      'Sem conexão com o servidor. Se tentou salvar, confira o registro antes de repetir.';
    return new Response(body, {status: 503, headers: {
      'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'
    }});
  }));
});
