import { db } from '@/lib/db'

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  await db.order.delete({ where: { id } })
  return new Response(null, { status: 204 })
}
