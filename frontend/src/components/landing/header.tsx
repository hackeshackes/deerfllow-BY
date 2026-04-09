import Link from "next/link";

import { BrandMark } from "@/components/brand/brand-mark";
import { Button } from "@/components/ui/button";
import { brand, supportMailto } from "@/core/brand/config";
import type { Locale } from "@/core/i18n/locale";
import { getI18n } from "@/core/i18n/server";
import { cn } from "@/lib/utils";

export type HeaderProps = {
  className?: string;
  homeURL?: string;
  locale?: Locale;
};

export async function Header({ className, homeURL, locale }: HeaderProps) {
  const { locale: resolvedLocale, t } = await getI18n(locale);
  const lang = resolvedLocale.substring(0, 2);

  return (
    <header
      className={cn(
        "container-md fixed top-0 right-0 left-0 z-20 mx-auto flex h-16 items-center justify-between border-b border-white/10 bg-slate-950/55 px-6 backdrop-blur-xl",
        className,
      )}
    >
      <Link href={homeURL ?? brand.websitePath}>
        <BrandMark compact />
      </Link>

      <nav className="mr-6 ml-auto hidden items-center gap-6 text-sm font-medium text-slate-300 md:flex">
        <Link href={`/${lang}/docs`} className="transition-colors hover:text-white">
          {t.home.docs}
        </Link>
        <a href={supportMailto("BY support")} className="transition-colors hover:text-white">
          Contact
        </a>
      </nav>

      <Button
        size="sm"
        asChild
        className="rounded-full bg-white text-slate-950 hover:bg-cyan-50"
      >
        <Link href="/sign-in">Open workspace</Link>
      </Button>
    </header>
  );
}
