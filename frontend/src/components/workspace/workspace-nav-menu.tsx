"use client";

import {
  CircleUserIcon,
  ChevronsUpDown,
  GlobeIcon,
  InfoIcon,
  LogOutIcon,
  MailIcon,
  MonitorCogIcon,
  ShieldCheckIcon,
  Settings2Icon,
  SettingsIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { brand, supportMailto } from "@/core/brand/config";
import { useI18n } from "@/core/i18n/hooks";

import { SettingsDialog } from "./settings";

function NavMenuButtonContent({
  isSidebarOpen,
  t,
}: {
  isSidebarOpen: boolean;
  t: ReturnType<typeof useI18n>["t"];
}) {
  return isSidebarOpen ? (
    <div className="text-muted-foreground flex w-full items-center gap-2 text-left text-sm">
      <SettingsIcon className="size-4" />
      <span>{t.workspace.settingsAndMore}</span>
      <ChevronsUpDown className="text-muted-foreground ml-auto size-4" />
    </div>
  ) : (
    <div className="flex size-full items-center justify-center">
      <SettingsIcon className="text-muted-foreground size-4" />
    </div>
  );
}

export function WorkspaceNavMenu({
  sessionEmail,
  sessionRole,
  activeWorkspaceName,
}: {
  sessionEmail: string;
  sessionRole: "owner" | "member";
  activeWorkspaceName: string;
}) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsDefaultSection, setSettingsDefaultSection] = useState<
    "appearance" | "memory" | "notification" | "about"
  >("appearance");
  const [mounted, setMounted] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [workspaces, setWorkspaces] = useState<
    Array<{ id: string; name: string; role: string; default_personal: boolean }>
  >([]);
  const { open: isSidebarOpen } = useSidebar();
  const { t } = useI18n();
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    async function loadWorkspaces() {
      try {
        const response = await fetch("/api/workspaces");
        if (!response.ok) return;
        const payload = (await response.json()) as {
          workspaces: Array<{
            id: string;
            name: string;
            role: string;
            default_personal: boolean;
          }>;
        };
        setWorkspaces(payload.workspaces);
      } catch {
        // ignore workspace menu failures
      }
    }

    void loadWorkspaces();
  }, []);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await fetch("/api/session/logout", { method: "POST" });
    } finally {
      router.replace("/sign-in");
      router.refresh();
      setLoggingOut(false);
    }
  }

  async function handleWorkspaceSwitch(workspaceId: string) {
    await fetch("/api/session/workspace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId }),
    });
    router.refresh();
  }

  return (
    <>
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        defaultSection={settingsDefaultSection}
      />
      <SidebarMenu className="w-full">
        <SidebarMenuItem>
          {mounted ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <NavMenuButtonContent isSidebarOpen={isSidebarOpen} t={t} />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
                <DropdownMenuContent
                  className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
                  align="end"
                  sideOffset={4}
                >
                  <div className="px-3 py-2">
                    <div className="text-xs font-medium tracking-[0.12em] text-slate-500 uppercase">
                      {brand.name}
                    </div>
                    <div className="mt-1 text-sm font-medium">{sessionEmail}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      当前空间：{activeWorkspaceName}
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  {workspaces.length > 0 && (
                    <>
                      <DropdownMenuGroup>
                        {workspaces.map((workspace) => (
                          <DropdownMenuItem
                            key={workspace.id}
                            onClick={() => void handleWorkspaceSwitch(workspace.id)}
                          >
                            {workspace.default_personal ? `个人空间 · ${workspace.name}` : `共享空间 · ${workspace.name}`}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuGroup>
                      <DropdownMenuSeparator />
                    </>
                  )}
                  <DropdownMenuGroup>
                  <DropdownMenuItem
                    onClick={() => {
                      setSettingsDefaultSection("appearance");
                      setSettingsOpen(true);
                    }}
                  >
                    <Settings2Icon />
                    {t.common.settings}
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/workspace/account">
                      <CircleUserIcon />
                      我的账号
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <a
                    href={brand.websitePath}
                  >
                    <DropdownMenuItem>
                      <GlobeIcon />
                      {t.workspace.officialWebsite}
                    </DropdownMenuItem>
                  </a>
                  <a href={supportMailto("MicX support request")}>
                    <DropdownMenuItem>
                      <MailIcon />
                      {t.workspace.contactUs}
                    </DropdownMenuItem>
                  </a>
                  {sessionRole === "owner" && (
                    <>
                      <DropdownMenuItem asChild>
                        <Link href="/workspace/admin">
                          <ShieldCheckIcon />
                          后台总览
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/workspace/admin/config">
                          <Settings2Icon />
                          配置中心
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/workspace/admin/monitoring">
                          <MonitorCogIcon />
                          监控中心
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/workspace/admin/skills">
                          <ShieldCheckIcon />
                          技能管理
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/workspace/admin/users">
                          <ShieldCheckIcon />
                          用户管理
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                      <Link href="/workspace/admin/workspaces">
                        <ShieldCheckIcon />
                        空间管理
                      </Link>
                    </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href="/workspace/admin/models">
                          <MonitorCogIcon />
                          模型管理
                        </Link>
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => {
                    setSettingsDefaultSection("about");
                    setSettingsOpen(true);
                  }}
                >
                  <InfoIcon />
                  {t.workspace.about}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => void handleLogout()}>
                  <LogOutIcon />
                  {loggingOut ? "退出中..." : "退出登录"}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <SidebarMenuButton size="lg" className="pointer-events-none">
              <NavMenuButtonContent isSidebarOpen={isSidebarOpen} t={t} />
            </SidebarMenuButton>
          )}
        </SidebarMenuItem>
      </SidebarMenu>
    </>
  );
}
