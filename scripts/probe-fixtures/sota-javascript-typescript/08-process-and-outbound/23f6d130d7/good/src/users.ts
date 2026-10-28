export const byId = (id: string) =>
  prisma.$queryRaw`SELECT * FROM users WHERE id = ${id}`;
