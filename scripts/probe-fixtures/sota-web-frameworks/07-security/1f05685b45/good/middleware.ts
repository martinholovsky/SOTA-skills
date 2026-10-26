import { NextResponse, type NextRequest } from 'next/server'

const UPSTREAM = 'https://api.internal.example.com'

export function middleware(req: NextRequest) {
  return NextResponse.rewrite(new URL(req.nextUrl.pathname, UPSTREAM))
}
