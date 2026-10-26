const name = new URLSearchParams(location.search).get('plugin') ?? 'default';
const registry = new Map<string, Plugin>();
registry.set(name, loadPlugin(name));
export {};
