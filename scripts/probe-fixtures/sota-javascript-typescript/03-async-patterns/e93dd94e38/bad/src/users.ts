export async function loadUsers(ids: string[]) {
  const users = [];
  for (const id of ids) {
    users.push(await getUser(id));
  }
  return users;
}
