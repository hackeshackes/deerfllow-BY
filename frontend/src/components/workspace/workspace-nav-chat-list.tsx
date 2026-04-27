"use client";

import {
  BookOpenIcon,
  BotIcon,
  MessagesSquare,
  MessageSquarePlusIcon,
  RepeatIcon,
  WorkflowIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";

export function WorkspaceNavChatList() {
  const { t } = useI18n();
  const pathname = usePathname();
  const navItems = [
    {
      href: "/workspace/chats/new",
      label: t.sidebar.newChat,
      icon: MessageSquarePlusIcon,
      active: pathname === "/workspace/chats/new",
    },
    {
      href: "/workspace/chats",
      label: t.sidebar.chats,
      icon: MessagesSquare,
      active: pathname === "/workspace/chats",
    },
    {
      href: "/workspace/knowledge",
      label: t.sidebar.sources,
      icon: BookOpenIcon,
      active: pathname.startsWith("/workspace/knowledge"),
    },
    {
      href: "/workspace/automations",
      label: t.sidebar.automations,
      icon: RepeatIcon,
      active:
        pathname.startsWith("/workspace/automations") ||
        pathname.startsWith("/workspace/tasks"),
    },
    {
      href: "/workspace/workflows",
      label: t.sidebar.workflows,
      icon: WorkflowIcon,
      active:
        pathname.startsWith("/workspace/workflows") ||
        pathname.startsWith("/workspace/settings/skills"),
    },
    {
      href: "/workspace/agents",
      label: t.sidebar.agents,
      icon: BotIcon,
      active: pathname.startsWith("/workspace/agents"),
    },
  ];

  return (
    <SidebarGroup className="pt-1">
      <SidebarMenu>
        {navItems.map((item) => (
          <SidebarMenuItem key={item.href}>
            <SidebarMenuButton isActive={item.active} asChild>
              <Link className="text-muted-foreground" href={item.href}>
                <item.icon />
                <span>{item.label}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
