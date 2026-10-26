export function readCache(key: string) {
  try {
    return JSON.parse(store.get(key));
  } catch (e) {
    throw new CacheError(`bad entry ${key}`, { cause: e });
  }
}
