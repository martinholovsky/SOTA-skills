export async function GET() {
  const me = await currentUser()
  return Response.json(me, { headers: { 'Cache-Control': 'public, s-maxage=3600' } })
}
