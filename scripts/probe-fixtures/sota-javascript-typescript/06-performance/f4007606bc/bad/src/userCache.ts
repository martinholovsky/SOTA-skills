const cache = new Map<string, User>();
export async function getUser(id: string) {
  if (!cache.has(id)) cache.set(id, await db.users.find(id));
  return cache.get(id);
}
