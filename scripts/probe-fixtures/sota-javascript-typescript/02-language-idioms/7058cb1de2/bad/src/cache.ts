export function readCache(key: string) {
  try {
    return JSON.parse(store.get(key));
  } catch (e) {}
}
