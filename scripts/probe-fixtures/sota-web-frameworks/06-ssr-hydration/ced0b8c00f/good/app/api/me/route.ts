export async function GET() {
  const me = await currentUser()
  return Response.json(me)
}
