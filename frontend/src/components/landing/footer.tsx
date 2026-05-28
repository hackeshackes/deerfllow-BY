"use client";

import { useMemo } from "react";

import { useBrand } from "@/components/brand/brand-provider";
import { buildSupportMailto } from "@/core/brand/config";
import { useI18n } from "@/core/i18n/hooks";

export function Footer() {
  const brand = useBrand();
  const { t } = useI18n();
  const year = useMemo(() => new Date().getFullYear(), []);

  return (
    <footer className="container-md mx-auto mt-20 flex flex-col items-center justify-center px-6 pb-10">
      <hr className="m-0 h-px w-full border-none bg-linear-to-r from-transparent via-white/20 to-transparent" />
      <div className="container flex flex-col gap-8 py-10 text-sm text-slate-300 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-lg font-semibold text-white md:text-xl">{brand.name}</p>
          <p className="mt-2 max-w-xl leading-7 text-slate-400">
            {brand.tagline}
          </p>
        </div>
        <div className="text-left md:text-right">
          <p>{t.landing.footerBadge}</p>
          <a className="mt-2 inline-block text-white underline" href={buildSupportMailto(brand.supportEmail, "MicX support")}>{brand.supportEmail}</a>
        </div>
      </div>
      <div className="container mb-8 flex flex-col items-center justify-center text-xs text-slate-500">
        <p>{t.landing.license}</p>
        <p>&copy; {year} {brand.name}</p>
      </div>
    </footer>
  );
}
