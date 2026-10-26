import { logger } from './logger';
export async function createOrder(input: OrderInput) {
  logger.info({ orderId: input.id }, 'creating order');
  return repo.insert(input);
}
