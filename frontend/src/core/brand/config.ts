export const brand = {
  name: "BY",
  shortName: "BY",
  tagline: "Private AI workspace for focused research, writing, and execution.",
  description:
    "BY is a private AI workspace that researches, writes, analyzes files, and ships polished outputs from one place.",
  supportEmail: "sabar.bao@me.com",
  websitePath: "/",
  docsPath: "/en/docs",
};

export function supportMailto(subject?: string) {
  const email = brand.supportEmail;
  if (!subject) return `mailto:${email}`;
  return `mailto:${email}?subject=${encodeURIComponent(subject)}`;
}
