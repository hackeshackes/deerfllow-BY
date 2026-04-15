import "server-only";

import { unstable_noStore as noStore } from "next/cache";

import { brand as defaultBrand } from "./config";

export type RuntimeBrand = {
  name: string;
  shortName: string;
  tagline: string;
  description: string;
  supportEmail: string;
  websitePath: string;
  docsPath: string;
};

type BrandingPayload = {
  name?: string;
  short_name?: string;
  tagline?: string;
  description?: string;
  support_email?: string;
  website_path?: string;
  docs_path?: string;
};

export async function getRuntimeBranding(): Promise<RuntimeBrand> {
  noStore();
  try {
    const baseUrl = process.env.DEER_FLOW_INTERNAL_GATEWAY_BASE_URL ?? process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://127.0.0.1:8001";
    const response = await fetch(`${baseUrl}/api/admin/public/branding`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Failed to load branding: ${response.status}`);
    }
    const branding = (await response.json()) as BrandingPayload;
    return {
      name: branding.name ?? defaultBrand.name,
      shortName: branding.short_name ?? defaultBrand.shortName,
      tagline: branding.tagline ?? defaultBrand.tagline,
      description: branding.description ?? defaultBrand.description,
      supportEmail: branding.support_email ?? defaultBrand.supportEmail,
      websitePath: branding.website_path ?? defaultBrand.websitePath,
      docsPath: branding.docs_path ?? defaultBrand.docsPath,
    };
  } catch {
    return {
      name: defaultBrand.name,
      shortName: defaultBrand.shortName,
      tagline: defaultBrand.tagline,
      description: defaultBrand.description,
      supportEmail: defaultBrand.supportEmail,
      websitePath: defaultBrand.websitePath,
      docsPath: defaultBrand.docsPath,
    };
  }
}
