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
  loginBadge: string;
  loginTitle: string;
  loginSubtitle: string;
  featureTitle1: string;
  featureDesc1: string;
  featureTitle2: string;
  featureDesc2: string;
  homepageCapabilitiesTitle: string;
  homepageCapabilitiesDesc: string;
  homepageCapabilitiesTitle2: string;
  homepageCapabilitiesDesc2: string;
  homepageCapabilitiesTitle3: string;
  homepageCapabilitiesDesc3: string;
  homepageWorkflow1: string;
  homepageWorkflow2: string;
  homepageWorkflow3: string;
  homepageWorkflow4: string;
  homepageWhyTitle: string;
  homepageWhySubtitle: string;
  homepageWhyDescription: string;
  homepageScenariosTitle: string;
  homepageTeamTitle: string;
  homepageTeamSubtitle: string;
  homepageTeamDescription: string;
  homepageTeamButton: string;
};

type BrandingPayload = {
  name?: string;
  short_name?: string;
  tagline?: string;
  description?: string;
  support_email?: string;
  website_path?: string;
  docs_path?: string;
  login_badge?: string;
  login_title?: string;
  login_subtitle?: string;
  feature_title_1?: string;
  feature_desc_1?: string;
  feature_title_2?: string;
  feature_desc_2?: string;
  homepage_capabilities_title?: string;
  homepage_capabilities_desc?: string;
  homepage_capabilities_title_2?: string;
  homepage_capabilities_desc_2?: string;
  homepage_capabilities_title_3?: string;
  homepage_capabilities_desc_3?: string;
  homepage_workflow_1?: string;
  homepage_workflow_2?: string;
  homepage_workflow_3?: string;
  homepage_workflow_4?: string;
  homepage_why_title?: string;
  homepage_why_subtitle?: string;
  homepage_why_description?: string;
  homepage_scenarios_title?: string;
  homepage_team_title?: string;
  homepage_team_subtitle?: string;
  homepage_team_description?: string;
  homepage_team_button?: string;
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
      loginBadge: branding.login_badge ?? defaultBrand.loginBadge,
      loginTitle: branding.login_title ?? defaultBrand.loginTitle,
      loginSubtitle: branding.login_subtitle ?? defaultBrand.loginSubtitle,
      featureTitle1: branding.feature_title_1 ?? defaultBrand.featureTitle1,
      featureDesc1: branding.feature_desc_1 ?? defaultBrand.featureDesc1,
      featureTitle2: branding.feature_title_2 ?? defaultBrand.featureTitle2,
      featureDesc2: branding.feature_desc_2 ?? defaultBrand.featureDesc2,
      homepageCapabilitiesTitle: branding.homepage_capabilities_title ?? defaultBrand.homepageCapabilitiesTitle,
      homepageCapabilitiesDesc: branding.homepage_capabilities_desc ?? defaultBrand.homepageCapabilitiesDesc,
      homepageCapabilitiesTitle2: branding.homepage_capabilities_title_2 ?? defaultBrand.homepageCapabilitiesTitle2,
      homepageCapabilitiesDesc2: branding.homepage_capabilities_desc_2 ?? defaultBrand.homepageCapabilitiesDesc2,
      homepageCapabilitiesTitle3: branding.homepage_capabilities_title_3 ?? defaultBrand.homepageCapabilitiesTitle3,
      homepageCapabilitiesDesc3: branding.homepage_capabilities_desc_3 ?? defaultBrand.homepageCapabilitiesDesc3,
      homepageWorkflow1: branding.homepage_workflow_1 ?? defaultBrand.homepageWorkflow1,
      homepageWorkflow2: branding.homepage_workflow_2 ?? defaultBrand.homepageWorkflow2,
      homepageWorkflow3: branding.homepage_workflow_3 ?? defaultBrand.homepageWorkflow3,
      homepageWorkflow4: branding.homepage_workflow_4 ?? defaultBrand.homepageWorkflow4,
      homepageWhyTitle: branding.homepage_why_title ?? defaultBrand.homepageWhyTitle,
      homepageWhySubtitle: branding.homepage_why_subtitle ?? defaultBrand.homepageWhySubtitle,
      homepageWhyDescription: branding.homepage_why_description ?? defaultBrand.homepageWhyDescription,
      homepageScenariosTitle: branding.homepage_scenarios_title ?? defaultBrand.homepageScenariosTitle,
      homepageTeamTitle: branding.homepage_team_title ?? defaultBrand.homepageTeamTitle,
      homepageTeamSubtitle: branding.homepage_team_subtitle ?? defaultBrand.homepageTeamSubtitle,
      homepageTeamDescription: branding.homepage_team_description ?? defaultBrand.homepageTeamDescription,
      homepageTeamButton: branding.homepage_team_button ?? defaultBrand.homepageTeamButton,
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
      loginBadge: defaultBrand.loginBadge,
      loginTitle: defaultBrand.loginTitle,
      loginSubtitle: defaultBrand.loginSubtitle,
      featureTitle1: defaultBrand.featureTitle1,
      featureDesc1: defaultBrand.featureDesc1,
      featureTitle2: defaultBrand.featureTitle2,
      featureDesc2: defaultBrand.featureDesc2,
      homepageCapabilitiesTitle: defaultBrand.homepageCapabilitiesTitle,
      homepageCapabilitiesDesc: defaultBrand.homepageCapabilitiesDesc,
      homepageCapabilitiesTitle2: defaultBrand.homepageCapabilitiesTitle2,
      homepageCapabilitiesDesc2: defaultBrand.homepageCapabilitiesDesc2,
      homepageCapabilitiesTitle3: defaultBrand.homepageCapabilitiesTitle3,
      homepageCapabilitiesDesc3: defaultBrand.homepageCapabilitiesDesc3,
      homepageWorkflow1: defaultBrand.homepageWorkflow1,
      homepageWorkflow2: defaultBrand.homepageWorkflow2,
      homepageWorkflow3: defaultBrand.homepageWorkflow3,
      homepageWorkflow4: defaultBrand.homepageWorkflow4,
      homepageWhyTitle: defaultBrand.homepageWhyTitle,
      homepageWhySubtitle: defaultBrand.homepageWhySubtitle,
      homepageWhyDescription: defaultBrand.homepageWhyDescription,
      homepageScenariosTitle: defaultBrand.homepageScenariosTitle,
      homepageTeamTitle: defaultBrand.homepageTeamTitle,
      homepageTeamSubtitle: defaultBrand.homepageTeamSubtitle,
      homepageTeamDescription: defaultBrand.homepageTeamDescription,
      homepageTeamButton: defaultBrand.homepageTeamButton,
    };
  }
}
