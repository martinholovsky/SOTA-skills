export async function loadUsers(ids: string[]) {
  return Promise.all(ids.map((id) => getUser(id)));
}
