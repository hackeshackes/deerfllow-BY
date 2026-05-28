"use client";

import { Building2Icon, ChevronsUpDownIcon, UserIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";

type WorkspaceSummary = {
  id: string;
  name: string;
  role: string;
  default_personal: boolean;
};

export function WorkspaceSwitcher({
  activeWorkspaceName,
}: {
  activeWorkspaceName: string;
}) {
  const router = useRouter();
  const { t } = useI18n();
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [switchingTo, setSwitchingTo] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    let cancelled = false;

    async function loadWorkspaces() {
      try {
        const response = await fetch("/api/workspaces");
        if (!response.ok) return;
        const payload = (await response.json()) as {
          workspaces: WorkspaceSummary[];
        };
        if (!cancelled) {
          setWorkspaces(payload.workspaces);
        }
      } catch {
        // The rest of the workspace UI remains usable if this menu fails.
      }
    }

    void loadWorkspaces();
    return () => {
      cancelled = true;
    };
  }, []);

  const activeWorkspace = workspaces.find(
    (workspace) => workspace.name === activeWorkspaceName,
  );
  const isPersonal = activeWorkspace?.default_personal ?? /personal|个人/i.test(activeWorkspaceName);
  const ActiveIcon = isPersonal ? UserIcon : Building2Icon;
  const triggerContent = (
    <>
      <ActiveIcon className="text-muted-foreground" />
      <div className="min-w-0 flex-1 text-left">
        <div className="truncate text-sm font-medium">{activeWorkspaceName}</div>
        <div className="text-muted-foreground text-xs">
          {isPersonal ? t.workspace.personalSpace : t.workspace.sharedSpace}
        </div>
      </div>
      <ChevronsUpDownIcon className="text-muted-foreground ml-auto size-4" />
    </>
  );

  async function switchWorkspace(workspaceId: string) {
    setSwitchingTo(workspaceId);
    try {
      await fetch("/api/session/workspace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_id: workspaceId }),
      });
      router.refresh();
    } finally {
      setSwitchingTo(null);
    }
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        {!mounted ? (
          <SidebarMenuButton
            size="lg"
            className="border bg-sidebar-accent/40"
            disabled
          >
            {triggerContent}
          </SidebarMenuButton>
        ) : (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="border bg-sidebar-accent/40 data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              {triggerContent}
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-60 rounded-lg"
            align="start"
            side="bottom"
            sideOffset={4}
          >
            <DropdownMenuLabel>{t.workspace.workspaceManagement}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {workspaces.map((workspace) => {
              const Icon = workspace.default_personal ? UserIcon : Building2Icon;
              const active = workspace.name === activeWorkspaceName;
              return (
                <DropdownMenuItem
                  key={workspace.id}
                  disabled={active || switchingTo === workspace.id}
                  onClick={() => void switchWorkspace(workspace.id)}
                >
                  <Icon className="text-muted-foreground" />
                  <div className="min-w-0">
                    <div className="truncate font-medium">{workspace.name}</div>
                    <div className="text-muted-foreground text-xs">
                      {workspace.default_personal ? t.workspace.personalSpace : t.workspace.sharedSpace}
                      {active ? ` · ${t.workspace.currentSpace}` : ""}
                    </div>
                  </div>
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>
        )}
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
