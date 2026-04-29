export const brand = {
  name: "MicX",
  shortName: "MicX",
  tagline: "面向个人与团队协作的中文智能服务工作台。",
  description:
    "MicX 是一个面向个人与团队协作的中文智能服务工作台，可以在一个空间里完成研究、写作、文件分析与结果沉淀。",
  supportEmail: "sabar.bao@me.com",
  websitePath: "/",
  docsPath: "/zh/docs",
  loginBadge: "中文优先 · 邀请制团队工作台",
  loginTitle: "登录 {name}",
  loginSubtitle:
    "{name} 是一个面向个人与团队协作的中文智能服务工作台，适合研究、写作、文件分析和长任务执行。目前仅支持受邀账号登录使用。",
  featureTitle1: "专注执行",
  featureDesc1: "在一个空间里完成复杂任务、查看进度并沉淀结果。",
  featureTitle2: "协作有边界",
  featureDesc2: "支持个人空间与共享空间，适合私有部署和团队协作。",
  homepageCapabilitiesTitle: "带上下文的研究能力",
  homepageCapabilitiesDesc:
    "在同一个空间中完成长链路研究、资料比对，并保留完整的对话和推理过程。",
  homepageCapabilitiesTitle2: "围绕文件开展工作",
  homepageCapabilitiesDesc2:
    "上传文档、分析内容，并把生成的产物与对话结果持续沉淀在一起。",
  homepageCapabilitiesTitle3: "直接产出可交付结果",
  homepageCapabilitiesDesc3:
    "无需切换工具，就能导出笔记、报告与各类可交付成果。",
  homepageWorkflow1: "深度研究、调研纪要与结构化摘要",
  homepageWorkflow2: "文章、方案、规范与操作文档写作",
  homepageWorkflow3: "围绕上传文件、生成文件和导出的产物工作流",
  homepageWorkflow4: "带待办、进度与后续建议的长任务执行",
  homepageWhyTitle: "为什么选择 {name}",
  homepageWhySubtitle: "一个适合个人与团队协作的中文 AI 工作台。",
  homepageWhyDescription:
    "{name} 把智能体执行、文件处理、结果产出与协作上下文放在同一个工作区中，让你和团队成员不用频繁切换工具，也能完成高质量工作流。",
  homepageScenariosTitle: "适合的使用场景",
  homepageTeamTitle: "中文团队版",
  homepageTeamSubtitle: "支持个人空间与团队空间并行协作。",
  homepageTeamDescription:
    "保留个人记忆与个人智能体的私有边界，同时让共享空间里的对话、上传和产物真正服务于团队协作。如需帮助，请联系 {support_email}。",
  homepageTeamButton: "联系 {name}",
};

export function buildSupportMailto(email: string, subject?: string) {
  if (!subject) return `mailto:${email}`;
  return `mailto:${email}?subject=${encodeURIComponent(subject)}`;
}

export function supportMailto(subject?: string) {
  return buildSupportMailto(brand.supportEmail, subject);
}
