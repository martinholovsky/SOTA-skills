import { z } from 'zod'

export default defineEventHandler(async (event) => {
  const q = await getValidatedQuery(event, z.object({ id: z.string().uuid() }).parse)
  return { id: q.id }
})
