import { draftMode } from 'next/headers'
import { redirect } from 'next/navigation'
import { timingSafeEqual } from 'node:crypto'
import { getPostBySlug } from '@/lib/cms'

function safeEqual(a: string, b: string) {
  const x = Buffer.from(a), y = Buffer.from(b)
  return x.length === y.length && timingSafeEqual(x, y)
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const token = searchParams.get('secret') ?? ''
  if (!safeEqual(token, process.env.DRAFT_SECRET ?? '')) return new Response('Invalid token', { status: 401 })
  const post = await getPostBySlug(searchParams.get('slug') ?? '')
  if (!post) return new Response('Unknown slug', { status: 404 })
  ;(await draftMode()).enable()
  redirect(`/posts/${post.slug}`)
}
