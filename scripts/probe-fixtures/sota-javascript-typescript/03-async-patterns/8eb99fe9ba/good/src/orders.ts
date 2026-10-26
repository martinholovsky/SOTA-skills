export async function placeOrder(pool: Pool, order: Order) {
  await using client = await acquire(pool);
  await client.query('BEGIN');
  await client.query('INSERT INTO orders VALUES ($1)', [order.id]);
  await client.query('COMMIT');
}
