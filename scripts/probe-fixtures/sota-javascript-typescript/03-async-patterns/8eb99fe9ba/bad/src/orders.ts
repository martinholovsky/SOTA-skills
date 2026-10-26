export async function placeOrder(pool: Pool, order: Order) {
  const client = await pool.connect();
  await client.query('BEGIN');
  await client.query('INSERT INTO orders VALUES ($1)', [order.id]);
  await client.query('COMMIT');
  client.release();
}
