import { OrderSchema } from './schema';
export function toOrder(row: unknown): Order {
  return OrderSchema.parse(row);
}
