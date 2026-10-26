import { z } from 'zod'

const Order = z.object({ sku: z.string(), qty: z.number().int().positive() })

export default defineEventHandler(async (event) => {
  const { user } = await requireUserSession(event)
  const body = await readValidatedBody(event, Order.parse)
  return await db.order.create({ data: { ...body, userId: user.id } })
})
