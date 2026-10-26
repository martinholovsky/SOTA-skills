export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  return await db.order.create({ data: body })
})
