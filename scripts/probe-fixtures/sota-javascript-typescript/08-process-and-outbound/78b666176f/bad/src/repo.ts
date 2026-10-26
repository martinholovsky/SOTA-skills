export const byEmail = (email: string) =>
  pool.query(`SELECT * FROM users WHERE email = '${email}'`);
