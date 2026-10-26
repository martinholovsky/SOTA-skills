import { revalidateTag } from 'next/cache'

export async function POST(request: Request) {
  const { tag } = await request.json()
  revalidateTag(tag, 'max')
  return Response.json({ revalidated: true })
}
