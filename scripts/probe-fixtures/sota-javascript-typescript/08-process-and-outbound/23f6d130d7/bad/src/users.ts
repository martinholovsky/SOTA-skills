export const byId = (id: string) =>
  prisma.$queryRawUnsafe(`SELECT * FROM users WHERE id = '${id}'`);
