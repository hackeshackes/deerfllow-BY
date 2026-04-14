export const brand = {
  name: "MicX",
  shortName: "MicX",
  tagline: "面向个人与团队协作的中文智能服务工作台。",
  description:
    "MicX 是一个面向个人与团队协作的中文智能服务工作台，可以在一个空间里完成研究、写作、文件分析与结果沉淀。",
  supportEmail: "sabar.bao@me.com",
  websitePath: "/",
  docsPath: "/zh/docs",
};

export function supportMailto(subject?: string) {
  const email = brand.supportEmail;
  if (!subject) return `mailto:${email}`;
  return `mailto:${email}?subject=${encodeURIComponent(subject)}`;
}
