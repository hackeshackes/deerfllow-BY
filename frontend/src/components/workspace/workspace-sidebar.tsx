"use client";

import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";

import { RecentChatList } from "./recent-chat-list";
import { ScheduledTasksList } from "./scheduled-tasks-list";
import { WorkspaceHeader } from "./workspace-header";
import { WorkspaceNavChatList } from "./workspace-nav-chat-list";
import { WorkspaceNavMenu } from "./workspace-nav-menu";
import { WorkspaceSwitcher } from "./workspace-switcher";

export function WorkspaceSidebar({
  sessionEmail,
  sessionRole,
  activeWorkspaceName,
  ...props
}: React.ComponentProps<typeof Sidebar> & {
  sessionEmail: string;
  sessionRole: "owner" | "member";
  activeWorkspaceName: string;
}) {
  const { open: isSidebarOpen } = useSidebar();
  return (
    <>
      <Sidebar variant="sidebar" collapsible="icon" {...props}>
        <SidebarHeader className="py-0">
          <WorkspaceHeader />
          {isSidebarOpen && (
            <div className="px-2 pb-2">
              <WorkspaceSwitcher activeWorkspaceName={activeWorkspaceName} />
            </div>
          )}
        </SidebarHeader>
        <SidebarContent>
          <WorkspaceNavChatList />
          {isSidebarOpen && <RecentChatList />}
          {isSidebarOpen && <ScheduledTasksList />}
        </SidebarContent>
        <SidebarFooter>
          <WorkspaceNavMenu
            sessionEmail={sessionEmail}
            sessionRole={sessionRole}
            activeWorkspaceName={activeWorkspaceName}
          />
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
    </>
  );
}
