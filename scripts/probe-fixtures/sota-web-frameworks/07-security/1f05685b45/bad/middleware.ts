import { NextResponse, type NextRequest } from 'next/server'

export function middleware(req: NextRequest) {
  return NextResponse.rewrite(new URL(req.nextUrl.pathname, req.headers.get('x-upstream') ?? 'http://localhost'))
}
