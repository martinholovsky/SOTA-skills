export async function GET() {
  return Response.json(await db.doc.findMany())
}
