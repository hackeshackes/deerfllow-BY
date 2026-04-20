"use client";

import { ActivityIcon, BlocksIcon, CoinsIcon, LayoutDashboardIcon, MessageCircleIcon, Settings2Icon, ShieldCheckIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const adminLinks = [
  { href: "/workspace/admin", label: "后台总览", icon: LayoutDashboardIcon },
  { href: "/workspace/admin/config", label: "配置中心", icon: Settings2Icon },
  { href: "/workspace/admin/monitoring", label: "监控中心", icon: ActivityIcon },
  { href: "/workspace/admin/token-usage", label: "Token 统计", icon: CoinsIcon },
  { href: "/workspace/admin/skills", label: "技能管理", icon: BlocksIcon },
  { href: "/workspace/admin/users", label: "用户管理", icon: ShieldCheckIcon },
  { href: "/workspace/admin/workspaces", label: "空间管理", icon: ShieldCheckIcon },
  { href: "/workspace/admin/models", label: "模型管理", icon: ShieldCheckIcon },
  { href: "/workspace/admin/models/mcp", label: "MCP 配置", icon: BlocksIcon },
  { href: "/workspace/admin/models/mcp/channels", label: "IM 渠道", icon: MessageCircleIcon },
] as const;

export function AdminPageShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <div className="rounded-3xl border bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 px-6 py-6 text-white shadow-sm">
        <Badge variant="secondary" className="bg-white/10 text-white">
          MicX Admin Console
        </Badge>
        <div className="mt-3 text-2xl font-semibold tracking-tight">{title}</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-200">{description}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <aside className="h-fit rounded-3xl border bg-white p-3 shadow-sm">
          <div className="mb-2 px-3 py-2 text-xs font-medium tracking-[0.12em] text-slate-500 uppercase">
            管理导航
          </div>
          <nav className="space-y-1">
            {adminLinks.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition-colors",
                    active ? "bg-slate-900 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950",
                  )}
                >
                  <Icon className="size-4" />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <div className="min-w-0 space-y-6">{children}</div>
      </div>
    </div>
  );
}
