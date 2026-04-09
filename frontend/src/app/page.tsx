import { Footer } from "@/components/landing/footer";
import { Header } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { brand, supportMailto } from "@/core/brand/config";

const capabilities = [
  {
    title: "Research with context",
    description:
      "Run long-form research, compare sources, and keep the full thread history in one workspace.",
  },
  {
    title: "Work with files",
    description:
      "Upload documents, analyze them with the agent runtime, and keep generated artifacts beside the conversation.",
  },
  {
    title: "Ship polished outputs",
    description:
      "Export notes, reports, and generated deliverables without leaving the app.",
  },
];

const workflows = [
  "Deep-dive research briefs and structured summaries",
  "Writing support for articles, notes, and operating docs",
  "Artifact-oriented work with uploads, generated files, and exports",
  "Long-running agent tasks with todos, progress, and follow-up prompts",
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
              Why BY
            </p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
              One private workspace for research, writing, execution, and review.
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">
              {brand.name} keeps the agent runtime, file handling, outputs, and
              session context together so you can run serious work without juggling
              multiple tools.
            </p>
          </div>
          <div className="rounded-[2rem] border border-cyan-400/20 bg-cyan-400/10 p-8 text-slate-100 shadow-2xl shadow-cyan-950/20">
            <p className="text-sm font-medium tracking-[0.2em] text-cyan-200 uppercase">
              Ideal workflows
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
                Private deployment
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
                BY is optimized for owner-operated, private use.
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">
                Keep the workspace restricted, customize the runtime for your own
                process, and contact {brand.supportEmail} when you need help.
              </p>
            </div>
            <a
              className="mt-6 inline-flex rounded-full border border-white/15 bg-white px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-50 md:mt-0"
              href={supportMailto("BY product inquiry")}
            >
              Contact BY
            </a>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
