import "@/styles/globals.css";
import "katex/dist/katex.min.css";

import { type Metadata } from "next";

import { BrandProvider } from "@/components/brand/brand-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { getRuntimeBranding } from "@/core/brand/runtime";
import { I18nProvider } from "@/core/i18n/context";
import { detectLocaleServer } from "@/core/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const brand = await getRuntimeBranding();
  return {
    title: brand.name,
    description: brand.description,
  };
}

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await detectLocaleServer();
  const brand = await getRuntimeBranding();
  return (
    <html lang={locale} suppressContentEditableWarning suppressHydrationWarning>
      <body>
        <BrandProvider brand={brand}>
          <ThemeProvider attribute="class" enableSystem disableTransitionOnChange>
            <I18nProvider initialLocale={locale}>{children}</I18nProvider>
          </ThemeProvider>
        </BrandProvider>
      </body>
    </html>
  );
}
