const el = document.getElementById('app-config');
const cfg = AppConfig.parse(JSON.parse(el instanceof HTMLScriptElement ? el.text : '{}'));
const s = document.createElement('script');
s.src = cfg.cdn + '/app.js';
document.head.append(s);
