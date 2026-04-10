"use client";

import { AlertCircleIcon, ArrowRightIcon, MailCheckIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { BrandMark } from "@/components/brand/brand-mark";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function ActivatePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = useMemo(() => searchParams.get("token") ?? "", [searchParams]);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setError("Invite token is missing.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/users/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError(body?.detail ?? "Unable to activate account.");
        return;
      }
      router.replace("/workspace");
      router.refresh();
    } catch {
      setError("Unable to reach the activation service.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(20,184,166,0.16),_transparent_30%),linear-gradient(180deg,_#07111f_0%,_#0b1321_55%,_#050913_100%)] px-6 py-12 text-white">
      <div className="absolute inset-0 bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.04)_45%,transparent_100%)]" />
      <div className="relative grid w-full max-w-5xl gap-8 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="flex flex-col justify-center gap-6">
          <BrandMark className="text-white" />
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-slate-200 backdrop-blur-sm">
              <MailCheckIcon className="size-4" />
              Invite-only access
            </div>
            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
              Activate your BY account.
            </h1>
            <p className="max-w-xl text-base leading-7 text-slate-300 md:text-lg">
              Set your password once to unlock your personal workspace and any shared workspaces you were invited to.
            </p>
          </div>
        </section>

        <Card className="border-white/10 bg-white/95 py-0 text-slate-900 shadow-2xl shadow-black/20 backdrop-blur-xl">
          <CardHeader className="gap-3 border-b border-slate-200/80 py-8">
            <CardTitle className="text-2xl">Complete account setup</CardTitle>
            <CardDescription>Choose a password for your invited BY account.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 py-8">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="text-sm font-medium">Invite token</label>
                <Input value={token} readOnly className="bg-slate-50" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">New password</label>
                <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Confirm password</label>
                <Input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required minLength={8} />
              </div>
              {error && (
                <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
                  <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
              <Button className="h-11 w-full rounded-xl" disabled={loading}>
                {loading ? "Activating..." : "Activate account"}
                {!loading && <ArrowRightIcon className="size-4" />}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
