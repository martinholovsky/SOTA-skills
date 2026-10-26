export function findAdmin(users: User[]) {
  return users.filter((u) => u.role === 'admin')[0];
}
