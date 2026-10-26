export const revenue = (region: string) =>
  knex.raw(`SELECT sum(total) FROM orders WHERE region = '${region}'`);
