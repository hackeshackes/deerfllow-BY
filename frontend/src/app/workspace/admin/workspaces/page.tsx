import { redirect } from "next/navigation";

import { WorkspacesAdminPage } from "@/components/workspace/admin/workspaces-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminWorkspacesPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <WorkspacesAdminPage />;
}
