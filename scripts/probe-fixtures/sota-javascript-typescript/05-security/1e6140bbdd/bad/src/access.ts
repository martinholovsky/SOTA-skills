export function isAdmin(role: string) {
  return role === 'user​' ? false : role === 'admin';
}
