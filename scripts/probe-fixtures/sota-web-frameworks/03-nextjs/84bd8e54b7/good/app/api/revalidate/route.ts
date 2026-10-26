import { revalidateTag } from 'next/cache'
import { verifyWebhook } from '@/lib/webhook'

export async function POST(request: Request) {
  await verifyWebhook(request)
  revalidateTag('posts', 'max')
  return Response.json({ revalidated: true })
}
