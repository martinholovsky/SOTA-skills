const swUrl = new URLSearchParams(location.search).get('sw') ?? '/sw.js';
navigator.serviceWorker.register(swUrl);
export {};
