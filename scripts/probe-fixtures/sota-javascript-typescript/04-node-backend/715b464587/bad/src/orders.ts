export async function createOrder(input: OrderInput) {
  console.log('creating order', input);
  return repo.insert(input);
}
