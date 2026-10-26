export function findAdmin(users: User[]) {
  return users.find((u) => u.role === 'admin');
}
