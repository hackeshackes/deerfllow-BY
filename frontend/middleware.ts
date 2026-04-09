import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { AUTH_COOKIE_NAME, decodeSessionToken } from "./src/server/auth/session";

export async function middleware(request: NextRequest) {
  if (!request.nextUrl.pathname.startsWith("/workspace")) {
    return NextResponse.next();
  }

  const session = request.cookies.get(AUTH_COOKIE_NAME)?.value;

  if (session && (await decodeSessionToken(session))) {
    return NextResponse.next();
  }

  return NextResponse.redirect(new URL("/sign-in", request.url));
}

export const config = {
  matcher: ["/workspace/:path*"],
};
