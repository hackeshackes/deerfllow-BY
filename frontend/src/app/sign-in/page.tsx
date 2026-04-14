"use client";

import { AlertCircleIcon, ArrowRightIcon, LockKeyholeIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { BrandMark } from "@/components/brand/brand-mark";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { brand, supportMailto } from "@/core/brand/config";

export default function SignInPage() {
  const router = useRouter();
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
        setError(body?.detail ?? body?.message ?? "登录失败，请稍后重试。");
        return;
      }

      router.replace("/workspace/chats/new");
      router.refresh();
    } catch {
      setError("无法连接登录服务，请稍后重试。");
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
            <div className="text-primary-foreground/80 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm backdrop-blur-sm">
              <LockKeyholeIcon className="size-4" />
              中文优先 · 邀请制团队工作台
            </div>
            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
              登录 {brand.name}
            </h1>
            <p className="max-w-xl text-base leading-7 text-slate-300 md:text-lg">
              {brand.name} 是一个面向个人与团队协作的中文智能服务工作台，适合研究、写作、文件分析和长任务执行。目前仅支持受邀账号登录使用。
            </p>
          </div>
          <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
              <div className="font-medium text-white">专注执行</div>
              <p className="mt-1 text-sm text-slate-300">
                在一个空间里完成复杂任务、查看进度并沉淀结果。
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
              <div className="font-medium text-white">协作有边界</div>
              <p className="mt-1 text-sm text-slate-300">
                支持个人空间与共享空间，适合私有部署和团队协作。
              </p>
            </div>
          </div>
        </section>

        <Card className="border-white/10 bg-white/95 py-0 text-slate-900 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <CardHeader className="gap-3 border-b border-slate-200/80 py-8">
              <CardTitle className="text-2xl">欢迎回来</CardTitle>
              <CardDescription>
              使用你的 {brand.name} 账号进入工作台。
              </CardDescription>
            </CardHeader>
          <CardContent className="space-y-6 py-8">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="text-sm font-medium">邮箱</label>
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
                <label className="text-sm font-medium">密码</label>
                <Input
                  autoComplete="current-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="请输入账号密码"
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
                {loading ? "登录中..." : "登录"}
                {!loading && <ArrowRightIcon className="size-4" />}
              </Button>
            </form>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              如需帮助，请联系{" "}
              <a
                className="font-medium text-slate-900 underline"
                  href={supportMailto(`${brand.name} access request`)}
              >
                {brand.supportEmail}
              </a>
              。如果你已经收到邀请，请先通过激活链接完成账号设置。
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
