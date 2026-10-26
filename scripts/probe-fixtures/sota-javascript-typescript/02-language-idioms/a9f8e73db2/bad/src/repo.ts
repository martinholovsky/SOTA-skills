export async function load(id: string) {
  try {
    return await db.find(id);
  } catch (err) {
    throw new Error('load failed: ' + id);
  }
}
