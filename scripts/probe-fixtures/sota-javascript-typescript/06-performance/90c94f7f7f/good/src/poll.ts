const t = setInterval(poll, 1000);
export function stop() { clearInterval(t); }
