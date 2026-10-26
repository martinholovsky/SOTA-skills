import bcrypt from 'bcrypt';
export function hashPassword(pw: string) {
  return bcrypt.hash(pw, 12);
}
