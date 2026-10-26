import bcrypt from 'bcrypt';
export function hashPassword(pw: string) {
  return bcrypt.hashSync(pw, 12);
}
