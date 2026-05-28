"use client";

import { ActivityIcon, BlocksIcon, BookOpenIcon, BrainIcon, CoinsIcon, LayoutDashboardIcon, MessageCircleIcon, MicIcon, Settings2Icon, ShieldCheckIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

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
  const { t } = useI18n();

  const adminLinks = [
    { href: "/workspace/admin", label: t.workspace.adminOverview, icon: LayoutDashboardIcon },
    { href: "/workspace/admin/config", label: t.workspace.configCenter, icon: Settings2Icon },
    { href: "/workspace/admin/monitoring", label: t.workspace.monitoringCenter, icon: ActivityIcon },
    { href: "/workspace/admin/token-usage", label: t.workspace.tokenStatistics, icon: CoinsIcon },
    { href: "/workspace/admin/skills", label: t.workspace.skillsManagement, icon: BlocksIcon },
    { href: "/workspace/admin/users", label: t.workspace.userManagement, icon: ShieldCheckIcon },
    { href: "/workspace/admin/workspaces", label: t.workspace.workspaceManagement, icon: ShieldCheckIcon },
    { href: "/workspace/admin/models", label: t.workspace.modelManagement, icon: ShieldCheckIcon },
    { href: "/workspace/admin/models/mcp", label: t.workspace.mcpConfig, icon: BlocksIcon },
    { href: "/workspace/admin/models/mcp/channels", label: t.workspace.imChannels, icon: MessageCircleIcon },
    { href: "/workspace/admin/conversations", label: t.workspace.conversationManagement, icon: MessageCircleIcon },
    { href: "/workspace/admin/knowledge", label: t.workspace.knowledgeManagement, icon: BookOpenIcon },
    { href: "/workspace/admin/memory", label: t.workspace.memoryManagement, icon: BrainIcon },
    { href: "/workspace/admin/voice", label: t.workspace.voiceConfig, icon: MicIcon },
  ];

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
            {t.workspace.adminNavigation}
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
