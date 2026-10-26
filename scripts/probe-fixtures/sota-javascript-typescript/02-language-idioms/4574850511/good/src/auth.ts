export function requireUser(u?: User) {
  if (!u) throw new AuthError('unauthorized');
  return u;
}
