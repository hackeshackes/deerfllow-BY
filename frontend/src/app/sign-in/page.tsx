"use client";

import { AlertCircleIcon, ArrowRightIcon, LockKeyholeIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { BrandMark } from "@/components/brand/brand-mark";
import { useBrand } from "@/components/brand/brand-provider";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { buildSupportMailto } from "@/core/brand/config";
import { useI18n } from "@/core/i18n/hooks";

export default function SignInPage() {
  const brand = useBrand();
  const router = useRouter();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/session/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as
          | { message?: string; detail?: string }
          | null;
        setError(t.signIn.loginFailed);
        return;
      }

      router.replace("/workspace/chats/new");
      router.refresh();
    } catch {
      setError(t.signIn.connectionFailed);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(20,184,166,0.16),_transparent_30%),linear-gradient(180deg,_#07111f_0%,_#0b1321_55%,_#050913_100%)] px-6 py-12 text-white">
      <div className="absolute inset-0 bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.04)_45%,transparent_100%)]" />
      <div className="relative grid w-full max-w-5xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="flex flex-col justify-center gap-6">
          <BrandMark className="text-white" />
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-white backdrop-blur-sm">
              <LockKeyholeIcon className="size-4" />
              {brand.loginBadge}
            </div>
            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
              {brand.loginTitle.replace("{name}", brand.name)}
            </h1>
            <p className="max-w-xl text-base leading-7 text-slate-300 md:text-lg">
              {brand.loginSubtitle.replace("{name}", brand.name)}
            </p>
          </div>
          <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
              <div className="font-medium text-white">{brand.featureTitle1}</div>
              <p className="mt-1 text-sm text-slate-300">
                {brand.featureDesc1}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
              <div className="font-medium text-white">{brand.featureTitle2}</div>
              <p className="mt-1 text-sm text-slate-300">
                {brand.featureDesc2}
              </p>
            </div>
          </div>
        </section>

        <Card className="border-white/10 bg-white/95 py-0 text-slate-900 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <CardHeader className="gap-3 border-b border-slate-200/80 py-8">
              <CardTitle className="text-2xl">
                {brand.loginTitle.replace("{name}", brand.name)}
              </CardTitle>
              <CardDescription>
                {brand.loginSubtitle.replace("{name}", brand.name)}
              </CardDescription>
            </CardHeader>
          <CardContent className="space-y-6 py-8">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="text-sm font-medium">{t.signIn.email}</label>
                <Input
                  autoComplete="email"
                  inputMode="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder={brand.supportEmail}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">{t.signIn.password}</label>
                <Input
                  autoComplete="current-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={t.signIn.passwordPlaceholder}
                  required
                />
              </div>

              {error && (
                <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
                  <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button className="h-11 w-full rounded-xl" disabled={loading}>
                {loading ? t.signIn.loggingIn : t.signIn.login}
                {!loading && <ArrowRightIcon className="size-4" />}
              </Button>
            </form>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              {t.signIn.helpText}{" "}
              <a
                className="font-medium text-slate-900 underline"
                  href={buildSupportMailto(brand.supportEmail, `${brand.name} access request`)}
              >
                {brand.supportEmail}
              </a>
              . {t.signIn.inviteHint}
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
