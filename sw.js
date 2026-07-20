
//explication: ce fichier est le service worker qui permet de recevoir les notifications push
self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'Verset du jour', body: event.data ? event.data.text() : '' };
  }

  const title = data.title || 'Verset du jour';
  const options = {
    body: data.body || '',
    tag: 'verset-du-jour',
    renotify: true,
  };
//explication:
  event.waitUntil(self.registration.showNotification(title, options));
});
//explication: ce fichier est le service worker qui permet de recevoir les notifications push
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});
