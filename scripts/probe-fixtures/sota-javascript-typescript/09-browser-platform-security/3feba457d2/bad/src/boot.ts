const cfg = window.appConfig || { cdn: 'https://cdn.example.com' };
const s = document.createElement('script');
s.src = cfg.cdn + '/app.js';
document.head.append(s);
