import { Footer } from "@/components/landing/footer";
import { Header } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { buildSupportMailto } from "@/core/brand/config";
import { getRuntimeBranding } from "@/core/brand/runtime";

export default async function LandingPage() {
  const brand = await getRuntimeBranding();

  const capabilities = [
    {
      title: brand.homepageCapabilitiesTitle,
      description: brand.homepageCapabilitiesDesc,
    },
    {
      title: brand.homepageCapabilitiesTitle2,
      description: brand.homepageCapabilitiesDesc2,
    },
    {
      title: brand.homepageCapabilitiesTitle3,
      description: brand.homepageCapabilitiesDesc3,
    },
  ];

  const workflows = [
    brand.homepageWorkflow1,
    brand.homepageWorkflow2,
    brand.homepageWorkflow3,
    brand.homepageWorkflow4,
  ];

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
              {brand.homepageWhyTitle.replace("{name}", brand.name)}
            </p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
              {brand.homepageWhySubtitle}
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">
              {brand.homepageWhyDescription.replace("{name}", brand.name)}
            </p>
          </div>
          <div className="rounded-[2rem] border border-cyan-400/20 bg-cyan-400/10 p-8 text-slate-100 shadow-2xl shadow-cyan-950/20">
            <p className="text-sm font-medium tracking-[0.2em] text-cyan-200 uppercase">
              {brand.homepageScenariosTitle}
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
                {brand.homepageTeamTitle}
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
                {brand.homepageTeamSubtitle}
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">
                {brand.homepageTeamDescription.replace("{name}", brand.name).replace("{support_email}", brand.supportEmail)}
              </p>
            </div>
            <a
              className="mt-6 inline-flex rounded-full border border-white/15 bg-white px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-50 md:mt-0"
              href={buildSupportMailto(brand.supportEmail, `${brand.name} product inquiry`)}
            >
              {brand.homepageTeamButton.replace("{name}", brand.name)}
            </a>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
