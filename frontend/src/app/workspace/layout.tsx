import { cookies } from "next/headers";
import { Toaster } from "sonner";

import { QueryClientProvider } from "@/components/query-client-provider";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { CommandPalette } from "@/components/workspace/command-palette";
import { WorkspaceSidebar } from "@/components/workspace/workspace-sidebar";
import { requireSession } from "@/server/auth/session";

import { WorkspaceSwitcher } from "./components/WorkspaceSwitcher";

function parseSidebarOpenCookie(
  value: string | undefined,
): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}

export default async function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await requireSession();
  const cookieStore = await cookies();
  const initialSidebarOpen = parseSidebarOpenCookie(
    cookieStore.get("sidebar_state")?.value,
  );
  const currentSpaceId = cookieStore.get("micx_space")?.value;

  return (
    <QueryClientProvider>
      <SidebarProvider className="h-screen" defaultOpen={initialSidebarOpen}>
        <div className="flex h-full w-full flex-col">
          <div className="border-b px-4 py-3">
            <WorkspaceSwitcher currentSpaceId={currentSpaceId} />
          </div>
          <div className="flex min-h-0 flex-1">
            <WorkspaceSidebar
              sessionEmail={session.email}
              sessionRole={session.role}
              activeWorkspaceName={session.active_workspace_name ?? "Personal"}
            />
            <SidebarInset className="min-w-0">{children}</SidebarInset>
          </div>
        </div>
        <CommandPalette />
        <Toaster position="top-center" />
      </SidebarProvider>
    </QueryClientProvider>
  );
}
