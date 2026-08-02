// Service worker: permite abrir la app aunque falle la red y acelera el arranque.
// Estrategia: la interfaz se sirve de caché; los datos, siempre de la red.

const CACHE = 'obrasec-v1';
const ESTATICOS = [
  '/',
  '/static/styles.css',
  '/static/js/app.js',
  '/static/js/api.js',
  '/static/js/ui.js',
  '/static/js/estado.js',
  '/static/js/forms.js',
  '/static/js/views.js',
  '/static/js/ia.js',
  '/static/js/ajustes.js',
  '/static/icono-192.png',
  '/static/icono-512.png',
  '/manifest.webmanifest',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(ESTATICOS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(claves.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  // Los datos nunca se cachean: en obra, un dato viejo es peor que ninguno.
  if (url.pathname.startsWith('/api/')) return;

  e.respondWith(
    caches.match(e.request).then((guardado) => {
      const red = fetch(e.request)
        .then((r) => {
          if (r.ok) {
            const copia = r.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copia));
          }
          return r;
        })
        .catch(() => guardado || caches.match('/'));
      // Caché primero para que la app abra al instante; se refresca por detrás.
      return guardado || red;
    })
  );
});
