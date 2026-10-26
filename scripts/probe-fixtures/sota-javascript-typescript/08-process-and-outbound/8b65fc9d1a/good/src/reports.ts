export const revenue = (region: string) =>
  knex('orders').where({ region }).sum('total');
