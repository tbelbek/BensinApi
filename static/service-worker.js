self.addEventListener('install', function(event) {
    console.log('Service Worker installing.');
    // Perform install steps if needed
});

self.addEventListener('activate', function(event) {
    console.log('Service Worker activating.');
    // Perform activate steps if needed
});

self.addEventListener('fetch', function(event) {
    // Optionally handle fetch events if needed
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    // Handle the notification click event
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(function(clientList) {
            for (var i = 0; i < clientList.length; i++) {
                var client = clientList[i];
                if (client.url === '/' && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow('/'); // Replace '/' with the URL you want to open
            }
        })
    );
});