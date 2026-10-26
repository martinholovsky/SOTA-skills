const name = new URLSearchParams(location.search).get('plugin') ?? 'default';
window[name] = loadPlugin(name);
export {};
