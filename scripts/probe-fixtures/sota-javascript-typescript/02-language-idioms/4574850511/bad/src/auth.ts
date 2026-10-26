export function requireUser(u?: User) {
  if (!u) throw 'unauthorized';
  return u;
}
