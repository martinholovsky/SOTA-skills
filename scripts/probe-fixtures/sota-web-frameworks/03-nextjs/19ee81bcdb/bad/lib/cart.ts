import { db } from './db'

export async function getCart(sessionToken: string) {
  'use cache'
  return db.cart.findFirst({ where: { session: sessionToken } })
}
