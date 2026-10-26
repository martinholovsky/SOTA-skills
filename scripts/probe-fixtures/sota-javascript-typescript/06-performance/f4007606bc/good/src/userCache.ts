import { LRUCache } from 'lru-cache';
const cache = new LRUCache<string, User>({ max: 10_000, ttl: 60_000 });
export async function getUser(id: string) {
  if (!cache.has(id)) cache.set(id, await db.users.find(id));
  return cache.get(id);
}
