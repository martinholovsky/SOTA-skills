'use server'
import { db } from '@/lib/db'

export async function deleteInvoice(id: string) {
  await db.invoice.delete({ where: { id } })
}
