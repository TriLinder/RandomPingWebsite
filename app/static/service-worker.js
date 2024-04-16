'use strict';

self.addEventListener("pushsubscriptionchange", function(event) {
    const applicationServerKey = JSON.parse(localStorage.getItem("trilinder.randomnotificationsite.persistentDataStore")).serverInformation.publicKey;

    event.waitUntil(
        self.registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: applicationServerKey
        })
    );
});
  

self.addEventListener("push", function(event) {
    const notificationData = JSON.parse(event.data.text());

    const title = notificationData.title;
    const options = notificationData.options;

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );

    event.notification.close();
});