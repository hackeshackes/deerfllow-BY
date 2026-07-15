import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { env } from "@/env";

export const AUTH_COOKIE_NAME = "by_session";

export type AuthSession = {
  id: string;
  email: string;
  role: "owner" | "member";
  name: string;
  status: string;
  active_workspace_id?: string;
  active_workspace_name?: string;
  active_workspace_role?: string;
};

function authSecret() {
  const configured = env.BETTER_AUTH_SECRET;
  if (!configured) {
    if (process.env.NODE_ENV !== "production" && process.env.BY_ALLOW_DEV_AUTH_SECRET === "1") {
      return "by-local-dev-secret";
    }
    throw new Error(
      "BETTER_AUTH_SECRET environment variable is required. Set it to a 32+ char random value.",
    );
  }
  if (configured === "by-local-dev-secret" && process.env.NODE_ENV === "production") {
    throw new Error("BETTER_AUTH_SECRET must not be the well-known development default in production.");
  }
  return configured;
}

function encodeBase64Url(value: Uint8Array) {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(value)
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  }
  let binary = "";
  value.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  if (typeof Buffer !== "undefined") {
    return Uint8Array.from(Buffer.from(padded, "base64"));
  }
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

async function sign(payload: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(authSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(payload),
  );
  return encodeBase64Url(new Uint8Array(signature));
}

export async function decodeSessionToken(token: string): Promise<AuthSession | null> {
  const [payloadB64, signature] = token.split(".", 2);
  if (!payloadB64 || !signature) {
    return null;
  }

  const expected = await sign(payloadB64);
  if (expected !== signature) {
    return null;
  }

  try {
    const payloadJson = new TextDecoder().decode(decodeBase64Url(payloadB64));
    const payload = JSON.parse(payloadJson) as Partial<AuthSession> & { sub?: string };
    if (!payload?.sub || !payload?.email || !payload?.role) {
      return null;
    }
    return {
      id: payload.sub,
      email: payload.email,
      role: payload.role,
      name: payload.name ?? payload.email,
      status: payload.status ?? "active",
      active_workspace_id: payload.active_workspace_id,
      active_workspace_name: payload.active_workspace_name,
      active_workspace_role: payload.active_workspace_role,
    };
  } catch {
    return null;
  }
}

export async function getCurrentSession() {
  const cookieStore = await cookies();
  const rawToken = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!rawToken) {
    return null;
  }
  const session = await decodeSessionToken(rawToken);
  if (session?.status !== "active") {
    return null;
  }
  return session;
}

export async function requireSession() {
  const session = await getCurrentSession();
  if (!session) {
    redirect("/sign-in");
  }
  return session;
}
