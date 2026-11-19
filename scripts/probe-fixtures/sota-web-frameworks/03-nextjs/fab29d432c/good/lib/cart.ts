import { db } from './db'

export async function getCart(userId: string, permVersion: number) {
  'use cache'
  return db.cart.findFirst({ where: { userId } })
}
