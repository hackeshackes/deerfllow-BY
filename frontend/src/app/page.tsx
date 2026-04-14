import { Footer } from "@/components/landing/footer";
import { Header } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { brand, supportMailto } from "@/core/brand/config";

const capabilities = [
  {
    title: "带上下文的研究能力",
    description:
      "在同一个空间中完成长链路研究、资料比对，并保留完整的对话和推理过程。",
  },
  {
    title: "围绕文件开展工作",
    description:
      "上传文档、分析内容，并把生成的产物与对话结果持续沉淀在一起。",
  },
  {
    title: "直接产出可交付结果",
    description:
      "无需切换工具，就能导出笔记、报告与各类可交付成果。",
  },
];

const workflows = [
  "深度研究、调研纪要与结构化摘要",
  "文章、方案、规范与操作文档写作",
  "围绕上传文件、生成文件和导出的产物工作流",
  "带待办、进度与后续建议的长任务执行",
];

export default function LandingPage() {
  return (
    <div className="min-h-screen w-full bg-[#07111f] text-white">
      <Header />
      <main className="flex w-full flex-col">
        <Hero />
        <section className="container-md mx-auto grid w-full gap-6 px-6 py-24 md:grid-cols-3">
          {capabilities.map((item) => (
            <div
              key={item.title}
              className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-xl shadow-black/10 backdrop-blur-sm"
            >
              <div className="text-lg font-semibold">{item.title}</div>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                {item.description}
              </p>
            </div>
          ))}
        </section>

        <section className="container-md mx-auto grid w-full gap-10 px-6 py-8 md:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-8 shadow-2xl shadow-black/15">
            <p className="text-sm font-medium tracking-[0.2em] text-cyan-300 uppercase">
              为什么选择 MicX
            </p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
              一个适合个人与团队协作的中文 AI 工作台。
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">
              {brand.name} 把智能体执行、文件处理、结果产出与协作上下文放在同一个工作区中，让你和团队成员不用频繁切换工具，也能完成高质量工作流。
            </p>
          </div>
          <div className="rounded-[2rem] border border-cyan-400/20 bg-cyan-400/10 p-8 text-slate-100 shadow-2xl shadow-cyan-950/20">
            <p className="text-sm font-medium tracking-[0.2em] text-cyan-200 uppercase">
              适合的使用场景
            </p>
            <ul className="mt-5 space-y-4 text-sm leading-7 text-slate-100/90">
              {workflows.map((workflow) => (
                <li key={workflow} className="flex gap-3">
                  <span className="mt-2 size-2 rounded-full bg-cyan-300" />
                  <span>{workflow}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="container-md mx-auto px-6 py-20">
          <div className="rounded-[2rem] border border-white/10 bg-white/5 px-8 py-10 shadow-2xl shadow-black/10 backdrop-blur-sm md:flex md:items-end md:justify-between">
            <div>
              <p className="text-sm font-medium tracking-[0.2em] text-cyan-300 uppercase">
                中文团队版
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
                支持个人空间与团队空间并行协作。
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">
                保留个人记忆与个人智能体的私有边界，同时让共享空间里的对话、上传和产物真正服务于团队协作。如需帮助，请联系 {brand.supportEmail}。
              </p>
            </div>
            <a
              className="mt-6 inline-flex rounded-full border border-white/15 bg-white px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-50 md:mt-0"
              href={supportMailto("MicX product inquiry")}
            >
              联系 MicX
            </a>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
